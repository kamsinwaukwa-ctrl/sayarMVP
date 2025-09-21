"""
Simple logo upload function using cloudinary library
This is a working replacement for the problematic upload function
"""

from fastapi import HTTPException, UploadFile
import uuid
import cloudinary
import cloudinary.uploader


async def upload_merchant_logo_simple(file: UploadFile, merchant_id: str, config):
    """
    Simple logo upload using cloudinary library
    """
    try:
        # Read file content
        file_content = await file.read()

        # Configure cloudinary
        cloudinary.config(
            cloud_name=config.cloud_name,
            api_key=config.api_key,
            api_secret=config.api_secret
        )

        # Create unique public_id for logo
        image_uuid = str(uuid.uuid4())

        # Upload to Cloudinary using the official library
        upload_result = cloudinary.uploader.upload(
            file_content,
            folder=f"sayar/merchants/{merchant_id}/brand",
            public_id=image_uuid,
            overwrite=True,
            resource_type="image",
            transformation="c_limit,w_500,h_500,f_auto,q_auto:good"
        )

        return {
            "logo": {
                "url": upload_result["secure_url"],
                "public_id": upload_result["public_id"],
                "width": upload_result.get("width"),
                "height": upload_result.get("height"),
                "format": upload_result.get("format"),
                "bytes": upload_result.get("bytes"),
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload logo: {str(e)}"
        )