"""
Supabase Storage utilities for media upload functionality
Handles file validation, upload, and signed URL generation
"""

import os
import re
from typing import BinaryIO, Tuple, Optional
from uuid import UUID
from datetime import datetime, timedelta
from supabase import create_client, Client
from fastapi import HTTPException, UploadFile
import logging

from ..models.media import (
    ALLOWED_LOGO_TYPES, 
    ALLOWED_LOGO_EXTENSIONS, 
    DEFAULT_MAX_SIZE, 
    DEFAULT_SIGNED_URL_EXPIRY
)
from ..utils.logger import get_logger
from ..utils.metrics import increment_counter, record_histogram

logger = get_logger(__name__)

def _detect_mime_type_from_signature(file_content: bytes, file_ext: str) -> str:
    """
    Detect MIME type from file signature (magic bytes) and extension.
    
    Args:
        file_content: File content as bytes
        file_ext: File extension (e.g., '.png', '.jpg')
        
    Returns:
        MIME type string
    """
    # File signature mappings for common image formats
    signatures = {
        b'\x89PNG\r\n\x1a\n': 'image/png',
        b'\xff\xd8\xff': 'image/jpeg',
        b'\x47\x49\x46\x38': 'image/gif',  # GIF87a or GIF89a
        b'RIFF': 'image/webp',  # WebP files start with RIFF
        b'\x00\x00\x01\x00': 'image/x-icon',  # ICO files
        b'BM': 'image/bmp',
    }
    
    # Check file signatures
    for signature, mime_type in signatures.items():
        if file_content.startswith(signature):
            return mime_type
    
    # Fallback to extension-based detection
    extension_mime_map = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.ico': 'image/x-icon',
        '.bmp': 'image/bmp',
    }
    
    return extension_mime_map.get(file_ext.lower(), 'application/octet-stream')

class StorageClient:
    """Singleton Supabase Storage client for media operations."""
    
    _instance: Optional[Client] = None
    _bucket_name: str = "merchant-logos"

    @classmethod
    def get_client(cls) -> Client:
        """Get or create Supabase client instance."""
        if cls._instance is None:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY")
            
            if not supabase_url or not supabase_service_key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")
            
            cls._instance = create_client(supabase_url, supabase_service_key)
            logger.info("Initialized Supabase Storage client")
            
        return cls._instance

    @classmethod
    def get_bucket_name(cls) -> str:
        """Get the configured bucket name."""
        return os.getenv("SUPABASE_STORAGE_BUCKET", cls._bucket_name)

def validate_logo_file(file: UploadFile, max_size: Optional[int] = None) -> Tuple[str, int]:
    """
    Validate uploaded logo file for type, size, and security.
    
    Args:
        file: FastAPI UploadFile object
        max_size: Maximum file size in bytes (defaults to DEFAULT_MAX_SIZE)
        
    Returns:
        Tuple of (normalized_filename, file_size)
        
    Raises:
        HTTPException: If validation fails
    """
    if max_size is None:
        max_size = int(os.getenv("MEDIA_MAX_SIZE", str(DEFAULT_MAX_SIZE)))
    
    allowed_types = os.getenv("MEDIA_ALLOWED_TYPES", ",".join(ALLOWED_LOGO_TYPES)).split(",")
    
    # Check if file is provided
    if not file or not file.filename:
        logger.warning("No file provided for upload")
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Sanitize and validate filename
    original_filename = file.filename.lower().strip()
    
    # Check for path traversal attempts
    if ".." in original_filename or "/" in original_filename or "\\" in original_filename:
        logger.warning(f"Path traversal attempt detected: {original_filename}")
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    # Validate file extension
    file_ext = None
    for ext in ALLOWED_LOGO_EXTENSIONS:
        if original_filename.endswith(ext.lower()):
            file_ext = ext
            break
    
    if not file_ext:
        logger.warning(f"Invalid file extension: {original_filename}")
        raise HTTPException(
            status_code=415, 
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_LOGO_EXTENSIONS)}"
        )
    
    # Normalize filename to logo.<ext>
    normalized_filename = f"logo{file_ext}"
    
    # Read file content for validation
    file_content = file.file.read()
    file_size = len(file_content)
    
    # Reset file position for later reading
    file.file.seek(0)
    
    # Check file size
    if file_size > max_size:
        logger.warning(f"File too large: {file_size} bytes (max: {max_size})")
        raise HTTPException(
            status_code=413, 
            detail=f"File too large. Maximum size: {max_size // (1024*1024)}MB"
        )
    
    if file_size == 0:
        logger.warning("Empty file uploaded")
        raise HTTPException(status_code=400, detail="Empty file not allowed")
    
    # Validate MIME type using file signature and extension
    try:
        # Get MIME type from FastAPI UploadFile first
        mime_type = file.content_type
        
        # If content_type is not available or unreliable, use file signature
        if not mime_type or mime_type == "application/octet-stream":
            mime_type = _detect_mime_type_from_signature(file_content, file_ext)
        
        if mime_type not in allowed_types:
            logger.warning(f"Invalid MIME type: {mime_type}")
            raise HTTPException(
                status_code=415, 
                detail=f"Unsupported file type. Allowed types: {', '.join(allowed_types)}"
            )
    except Exception as e:
        logger.error(f"Error detecting MIME type: {str(e)}")
        raise HTTPException(status_code=400, detail="Unable to validate file type")
    
    logger.info(f"File validation passed: {normalized_filename}, size: {file_size}, type: {mime_type}")
    return normalized_filename, file_size

def get_logo_storage_path(merchant_id: UUID, filename: str) -> str:
    """
    Generate storage path for merchant logo.
    
    Args:
        merchant_id: Merchant UUID
        filename: Normalized filename
        
    Returns:
        Storage path string
    """
    return f"{merchant_id}/{filename}"

async def upload_logo_to_storage(
    merchant_id: UUID, 
    file: UploadFile, 
    filename: str
) -> Tuple[str, str, int]:
    """
    Upload logo file to Supabase Storage.
    
    Args:
        merchant_id: Merchant UUID
        file: FastAPI UploadFile object
        filename: Normalized filename
        
    Returns:
        Tuple of (storage_path, content_type, file_size)
        
    Raises:
        HTTPException: If upload fails
    """
    client = StorageClient.get_client()
    bucket_name = StorageClient.get_bucket_name()
    storage_path = get_logo_storage_path(merchant_id, filename)
    
    logger.info(f"Uploading logo to storage: {bucket_name}/{storage_path}")
    increment_counter("media_upload_attempts_total", {"merchant_id": str(merchant_id)})
    
    try:
        # Read file content
        file_content = file.file.read()
        file_size = len(file_content)
        
        # Upload to Supabase Storage
        result = client.storage.from_(bucket_name).upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": file.content_type, "upsert": True}
        )
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Storage upload failed: {result.error}")
            increment_counter("media_upload_failures_total", {"error": "storage_error"})
            raise HTTPException(status_code=500, detail="Failed to upload file to storage")
        
        # Get public URL (even though file is private)
        public_url_result = client.storage.from_(bucket_name).get_public_url(storage_path)
        
        if hasattr(public_url_result, 'error') and public_url_result.error:
            logger.error(f"Failed to get public URL: {public_url_result.error}")
            # This is not critical, we can still proceed
            storage_url = f"/{bucket_name}/{storage_path}"
        else:
            storage_url = public_url_result
        
        increment_counter("media_uploads_total", {"merchant_id": str(merchant_id)})
        record_histogram("media_upload_size_bytes", file_size, {"merchant_id": str(merchant_id)})
        
        logger.info(f"Successfully uploaded logo: {storage_path}, size: {file_size}")
        return storage_path, file.content_type or "application/octet-stream", file_size
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during upload: {str(e)}")
        increment_counter("media_upload_failures_total", {"error": "unexpected_error"})
        raise HTTPException(status_code=500, detail="Internal server error during upload")

async def generate_signed_url(
    merchant_id: UUID, 
    filename: str = "logo.png",
    expiry_seconds: Optional[int] = None
) -> Tuple[str, datetime]:
    """
    Generate signed URL for accessing merchant logo.
    
    Args:
        merchant_id: Merchant UUID
        filename: Logo filename (defaults to logo.png)
        expiry_seconds: URL expiry in seconds (defaults to DEFAULT_SIGNED_URL_EXPIRY)
        
    Returns:
        Tuple of (signed_url, expires_at)
        
    Raises:
        HTTPException: If signed URL generation fails
    """
    if expiry_seconds is None:
        expiry_seconds = int(os.getenv("SIGNED_URL_EXPIRY", str(DEFAULT_SIGNED_URL_EXPIRY)))
    
    client = StorageClient.get_client()
    bucket_name = StorageClient.get_bucket_name()
    storage_path = get_logo_storage_path(merchant_id, filename)
    expires_at = datetime.utcnow() + timedelta(seconds=expiry_seconds)
    
    logger.info(f"Generating signed URL for: {bucket_name}/{storage_path}")
    increment_counter("signed_url_requests_total", {"merchant_id": str(merchant_id)})
    
    try:
        # Generate signed URL
        result = client.storage.from_(bucket_name).create_signed_url(
            path=storage_path,
            expires_in=expiry_seconds
        )
        
        if hasattr(result, 'error') and result.error:
            logger.error(f"Failed to generate signed URL: {result.error}")
            increment_counter("signed_url_failures_total", {"error": "generation_failed"})
            raise HTTPException(status_code=404, detail="Logo not found or access denied")
        
        signed_url = result.get('signedURL') if isinstance(result, dict) else result
        
        if not signed_url:
            logger.error("Empty signed URL returned from Supabase")
            increment_counter("signed_url_failures_total", {"error": "empty_url"})
            raise HTTPException(status_code=500, detail="Failed to generate signed URL")
        
        increment_counter("signed_urls_generated_total", {"merchant_id": str(merchant_id)})
        
        logger.info(f"Successfully generated signed URL, expires at: {expires_at}")
        return signed_url, expires_at
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error generating signed URL: {str(e)}")
        increment_counter("signed_url_failures_total", {"error": "unexpected_error"})
        raise HTTPException(status_code=500, detail="Internal server error generating signed URL")

async def delete_logo_from_storage(merchant_id: UUID, filename: str = "logo.png") -> bool:
    """
    Delete logo file from Supabase Storage.
    
    Args:
        merchant_id: Merchant UUID
        filename: Logo filename (defaults to logo.png)
        
    Returns:
        True if deletion was successful, False otherwise
    """
    client = StorageClient.get_client()
    bucket_name = StorageClient.get_bucket_name()
    storage_path = get_logo_storage_path(merchant_id, filename)
    
    logger.info(f"Deleting logo from storage: {bucket_name}/{storage_path}")
    
    try:
        result = client.storage.from_(bucket_name).remove([storage_path])
        
        if hasattr(result, 'error') and result.error:
            logger.warning(f"Failed to delete logo: {result.error}")
            return False
        
        logger.info(f"Successfully deleted logo: {storage_path}")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error deleting logo: {str(e)}")
        return False

def ensure_bucket_exists() -> bool:
    """
    Ensure the merchant-logos bucket exists.
    
    Returns:
        True if bucket exists or was created, False otherwise
    """
    client = StorageClient.get_client()
    bucket_name = StorageClient.get_bucket_name()
    
    try:
        # Try to list buckets to check if our bucket exists
        buckets = client.storage.list_buckets()
        bucket_exists = any(bucket.name == bucket_name for bucket in buckets)
        
        if not bucket_exists:
            logger.warning(f"Bucket {bucket_name} does not exist")
            return False
        
        logger.info(f"Bucket {bucket_name} exists and is accessible")
        return True
        
    except Exception as e:
        logger.error(f"Error checking bucket existence: {str(e)}")
        return False