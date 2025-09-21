"""
Cloudinary client integration for secure image upload and management
"""

import os
import hashlib
import hmac
import time
import uuid
from typing import Dict, Optional, Any, Tuple, List
from io import BytesIO
import requests
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from ..models.errors import APIError, ErrorCode
from ..models.cloudinary import (
    CloudinaryTransformPreset,
    PresetProfile,
    ImageVariant,
    ImageDimensions,
    PresetTestResult
)
from ..config.cloudinary_presets import (
    get_preset_by_id,
    get_profile_by_id,
    get_eager_presets_for_profile,
    get_all_presets_for_profile
)


class CloudinaryConfig:
    """Cloudinary configuration from environment variables"""

    def __init__(self):
        self.cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
        self.api_key = os.getenv("CLOUDINARY_API_KEY")
        self.api_secret = os.getenv("CLOUDINARY_API_SECRET")
        self.upload_timeout = int(os.getenv("CLOUDINARY_UPLOAD_TIMEOUT", "30"))
        self.webhook_timeout = int(os.getenv("CLOUDINARY_WEBHOOK_TIMEOUT", "5"))
        self.max_image_size_mb = int(os.getenv("MAX_IMAGE_SIZE_MB", "5"))
        self.supported_formats = os.getenv("SUPPORTED_IMAGE_FORMATS", "png,jpg,jpeg,webp").split(",")

    def is_configured(self) -> bool:
        """Check if all required environment variables are set"""
        return bool(self.cloud_name and self.api_key and self.api_secret)

    def get_base_url(self) -> str:
        """Get Cloudinary API base URL"""
        return f"https://api.cloudinary.com/v1_1/{self.cloud_name}"


class CloudinaryClient:
    """Cloudinary API client with image upload and management capabilities"""

    def __init__(self, config: Optional[CloudinaryConfig] = None):
        self.config = config or CloudinaryConfig()
        if not self.config.is_configured():
            raise APIError(
                code=ErrorCode.CLOUDINARY_NOT_CONFIGURED,
                message="Cloudinary credentials not configured in environment variables"
            )

    def verify_health(self) -> Dict[str, Any]:
        """
        Verify Cloudinary connection by calling usage API
        Returns dict with configured status and verification timestamp
        """
        try:
            url = f"{self.config.get_base_url()}/usage"
            response = requests.get(
                url,
                auth=(self.config.api_key, self.config.api_secret),
                timeout=self.config.webhook_timeout
            )

            if response.status_code == 200:
                return {
                    "configured": True,
                    "cloud_name": self.config.cloud_name,
                    "verified_at": time.time()
                }
            else:
                raise APIError(
                    code=ErrorCode.CLOUDINARY_HEALTHCHECK_FAILED,
                    message=f"Cloudinary API returned status {response.status_code}"
                )

        except requests.RequestException as e:
            raise APIError(
                code=ErrorCode.CLOUDINARY_HEALTHCHECK_FAILED,
                message=f"Failed to connect to Cloudinary: {str(e)}"
            )

    def validate_image_file(self, file_content: bytes, filename: str) -> Tuple[int, int, str]:
        """
        Validate image file size, format, and dimensions
        Returns (width, height, format) if valid
        Raises APIError if validation fails
        """
        # Check file size
        file_size = len(file_content)
        max_bytes = self.config.max_image_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise APIError(
                code=ErrorCode.IMAGE_TOO_LARGE,
                message=f"Image file too large: {file_size} bytes, max {max_bytes} bytes"
            )

        # Check file format by examining actual image data
        try:
            image = Image.open(BytesIO(file_content))
            format_lower = image.format.lower() if image.format else ""

            # Check if format is supported
            if format_lower not in self.config.supported_formats:
                raise APIError(
                    code=ErrorCode.UNSUPPORTED_IMAGE_TYPE,
                    message=f"Unsupported image format: {format_lower}. Supported: {self.config.supported_formats}"
                )

            # Check minimum dimensions (Meta Catalog requirement)
            width, height = image.size
            min_dimension = 500  # Meta-safe minimum short edge
            if min(width, height) < min_dimension:
                raise APIError(
                    code=ErrorCode.IMAGE_DIMENSIONS_TOO_SMALL,
                    message=f"Image too small: {width}x{height}. Minimum: {min_dimension}px short edge"
                )

            return width, height, format_lower

        except Exception as e:
            if isinstance(e, APIError):
                raise
            raise APIError(
                code=ErrorCode.UNSUPPORTED_IMAGE_TYPE,
                message=f"Invalid image file: {str(e)}"
            )

    def upload_image_with_presets(
        self,
        file_content: bytes,
        merchant_id: str,
        product_id: str,
        filename: str,
        preset_profile: PresetProfile = PresetProfile.STANDARD,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image to Cloudinary with preset-based transformations
        Returns upload response with all variants based on profile
        """
        # Validate image file
        width, height, file_format = self.validate_image_file(file_content, filename)

        # Generate unique public ID
        image_uuid = str(uuid.uuid4())
        public_id = f"sayar/products/{merchant_id}/{image_uuid}"

        # Get eager presets for the profile
        eager_presets = get_eager_presets_for_profile(preset_profile)
        eager_transformations = [preset.transformation for preset in eager_presets.values()]

        # Prepare upload parameters
        upload_params = {
            "folder": f"sayar/products/{merchant_id}/{product_id}",
            "public_id": image_uuid,
            "overwrite": True,
            "resource_type": "image",
            "type": "upload",
            "eager": eager_transformations,
            "eager_async": True,
        }

        # Add webhook notification if provided
        if webhook_url:
            upload_params["notification_url"] = webhook_url

        # Add signature
        timestamp = int(time.time())
        upload_params["timestamp"] = timestamp
        signature = self._generate_signature(upload_params)
        upload_params["signature"] = signature
        upload_params["api_key"] = self.config.api_key

        try:
            # Prepare multipart form data
            files = {"file": (filename, file_content)}

            # Upload to Cloudinary
            url = f"{self.config.get_base_url()}/image/upload"
            response = requests.post(
                url,
                data=upload_params,
                files=files,
                timeout=self.config.upload_timeout
            )

            if response.status_code != 200:
                raise APIError(
                    code=ErrorCode.CLOUDINARY_UPLOAD_FAILED,
                    message=f"Cloudinary upload failed: {response.text}"
                )

            result = response.json()

            # Generate all variants for the profile
            all_presets = get_all_presets_for_profile(preset_profile)
            variants = {}

            # Process eager transformations from response
            eager_results = {}
            if "eager" in result:
                for eager in result["eager"]:
                    transformation = eager.get("transformation", "")
                    eager_results[transformation] = eager

            # Build variants dict
            for variant_name, preset in all_presets.items():
                if preset.eager and preset.transformation in eager_results:
                    # Use eager result
                    eager_data = eager_results[preset.transformation]
                    variants[variant_name] = ImageVariant(
                        url=eager_data.get("secure_url", ""),
                        preset_id=preset.id,
                        file_size_kb=eager_data.get("bytes", 0) // 1024 if eager_data.get("bytes") else None,
                        dimensions=ImageDimensions(
                            width=eager_data.get("width", 0),
                            height=eager_data.get("height", 0)
                        ) if eager_data.get("width") and eager_data.get("height") else None,
                        format=eager_data.get("format")
                    )
                else:
                    # Generate on-demand URL
                    on_demand_url = self.generate_variant_url(
                        public_id=result["public_id"],
                        transformation=preset.transformation,
                        version=result.get("version")
                    )
                    variants[variant_name] = ImageVariant(
                        url=on_demand_url,
                        preset_id=preset.id
                    )

            return {
                "public_id": result["public_id"],
                "variants": variants,
                "preset_profile": preset_profile.value,
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "version": result.get("version"),
                "created_at": result.get("created_at")
            }

        except requests.RequestException as e:
            raise APIError(
                code=ErrorCode.CLOUDINARY_UPLOAD_FAILED,
                message=f"Failed to upload to Cloudinary: {str(e)}"
            )

    def upload_image(
        self,
        file_content: bytes,
        merchant_id: str,
        product_id: str,
        filename: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upload image to Cloudinary with transformation presets
        Returns upload response with secure URLs for main and thumbnail presets
        """
        # Validate image file
        width, height, file_format = self.validate_image_file(file_content, filename)

        # Generate unique public ID
        image_uuid = str(uuid.uuid4())
        public_id = f"sayar/products/{merchant_id}/{image_uuid}"

        # Prepare upload parameters
        upload_params = {
            "folder": f"sayar/products/{merchant_id}/{product_id}",
            "public_id": image_uuid,
            "overwrite": True,
            "resource_type": "image",
            "type": "upload",
            "eager": [
                "c_limit,w_1600,h_1600,f_auto,q_auto:good",  # main preset
                "c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco"  # thumb preset
            ],
            "eager_async": True,
        }

        # Add webhook notification if provided
        if webhook_url:
            upload_params["notification_url"] = webhook_url

        # Add signature
        timestamp = int(time.time())
        upload_params["timestamp"] = timestamp
        signature = self._generate_signature(upload_params)
        upload_params["signature"] = signature
        upload_params["api_key"] = self.config.api_key

        try:
            # Prepare multipart form data
            files = {"file": (filename, file_content)}

            # Upload to Cloudinary
            url = f"{self.config.get_base_url()}/image/upload"
            response = requests.post(
                url,
                data=upload_params,
                files=files,
                timeout=self.config.upload_timeout
            )

            if response.status_code != 200:
                raise APIError(
                    code=ErrorCode.CLOUDINARY_UPLOAD_FAILED,
                    message=f"Cloudinary upload failed: {response.text}"
                )

            result = response.json()

            # Extract transformation URLs
            main_url = result.get("secure_url")  # Original upload URL
            thumb_url = None

            # Find main and thumbnail URLs from eager transformations
            if "eager" in result:
                for eager in result["eager"]:
                    transformation = eager.get("transformation", "")
                    if "c_limit,w_1600,h_1600" in transformation:
                        main_url = eager.get("secure_url")
                    elif "c_fill,w_600,h_600" in transformation:
                        thumb_url = eager.get("secure_url")

            return {
                "public_id": result["public_id"],
                "secure_url": main_url,
                "thumbnail_url": thumb_url,
                "width": result.get("width"),
                "height": result.get("height"),
                "format": result.get("format"),
                "bytes": result.get("bytes"),
                "version": result.get("version"),
                "created_at": result.get("created_at")
            }

        except requests.RequestException as e:
            raise APIError(
                code=ErrorCode.CLOUDINARY_UPLOAD_FAILED,
                message=f"Failed to upload to Cloudinary: {str(e)}"
            )

    def delete_image(self, public_id: str) -> bool:
        """
        Delete image from Cloudinary
        Returns True if successful, raises APIError if failed
        """
        try:
            timestamp = int(time.time())
            params = {
                "public_id": public_id,
                "timestamp": timestamp
            }

            signature = self._generate_signature(params)
            params["signature"] = signature
            params["api_key"] = self.config.api_key

            url = f"{self.config.get_base_url()}/image/destroy"
            response = requests.post(
                url,
                data=params,
                timeout=self.config.upload_timeout
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("result") == "ok"
            else:
                raise APIError(
                    code=ErrorCode.CLOUDINARY_DELETE_FAILED,
                    message=f"Cloudinary delete failed: {response.text}"
                )

        except requests.RequestException as e:
            raise APIError(
                code=ErrorCode.CLOUDINARY_DELETE_FAILED,
                message=f"Failed to delete from Cloudinary: {str(e)}"
            )

    def verify_webhook_signature(
        self,
        payload_body: bytes,
        signature: str,
        timestamp: str
    ) -> bool:
        """
        Verify Cloudinary webhook signature
        Returns True if signature is valid and timestamp is recent
        """
        try:
            # Check timestamp freshness (within 5 minutes)
            webhook_time = int(timestamp)
            current_time = int(time.time())
            if abs(current_time - webhook_time) > 300:  # 5 minutes
                return False

            # Generate expected signature
            signature_data = payload_body + self.config.api_secret.encode()
            expected_signature = hashlib.sha1(signature_data).hexdigest()

            # Compare signatures using constant-time comparison
            return hmac.compare_digest(signature, expected_signature)

        except (ValueError, TypeError):
            return False

    def generate_variant_url(
        self,
        public_id: str,
        transformation: str,
        version: Optional[int] = None
    ) -> str:
        """
        Generate Cloudinary URL with transformation for on-demand variants
        """
        base_url = f"https://res.cloudinary.com/{self.config.cloud_name}/image/upload"

        if version:
            return f"{base_url}/{transformation}/v{version}/{public_id}"
        else:
            return f"{base_url}/{transformation}/{public_id}"

    def test_preset_transformation(
        self,
        preset_id: str,
        test_image_url: str
    ) -> PresetTestResult:
        """
        Test a preset transformation with a sample image URL
        Returns estimated results without actual transformation
        """
        try:
            # Get preset configuration
            preset = get_preset_by_id(preset_id)

            # Generate test URL
            # Extract public_id from test URL (basic extraction)
            if "cloudinary.com" in test_image_url:
                # Extract public_id from Cloudinary URL
                parts = test_image_url.split("/")
                if len(parts) > 3:
                    public_id = "/".join(parts[-2:]).split(".")[0]
                else:
                    public_id = "sample"
            else:
                public_id = "sample"

            # Generate transformed URL
            transformed_url = self.generate_variant_url(
                public_id=public_id,
                transformation=preset.transformation
            )

            # Estimate file size based on constraints
            estimated_size = None
            if preset.constraints.max_file_size_kb:
                # Use target size from constraints
                estimated_size = min(
                    preset.constraints.max_file_size_kb,
                    int(preset.constraints.max_file_size_kb * 0.8)  # 80% of max
                )

            return PresetTestResult(
                success=True,
                transformed_url=transformed_url,
                estimated_file_size_kb=estimated_size,
                dimensions=ImageDimensions(
                    width=preset.constraints.max_width,
                    height=preset.constraints.max_height
                ),
                format="webp",  # f_auto typically chooses webp
                quality_score=preset.constraints.min_quality,
                processing_time_ms=500  # Estimated
            )

        except Exception as e:
            return PresetTestResult(
                success=False,
                error_message=str(e)
            )

    def verify_variant_url_exists(self, url: str) -> bool:
        """
        Verify that a variant URL exists and returns 200
        Used for catalog sync validation
        """
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_image_analysis(self, public_id: str) -> Optional[Dict[str, Any]]:
        """
        Get image analysis data from Cloudinary
        Returns quality metrics if available
        """
        try:
            # This would use Cloudinary's analysis API if available
            # For now, return None as this is an advanced feature
            return None
        except Exception:
            return None

    def batch_generate_variants(
        self,
        public_id: str,
        preset_ids: List[str],
        version: Optional[int] = None
    ) -> Dict[str, str]:
        """
        Generate multiple variant URLs for a single image
        """
        variants = {}
        for preset_id in preset_ids:
            try:
                preset = get_preset_by_id(preset_id)
                url = self.generate_variant_url(
                    public_id=public_id,
                    transformation=preset.transformation,
                    version=version
                )
                variants[preset_id] = url
            except Exception:
                # Skip invalid presets
                continue

        return variants

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        Generate Cloudinary API signature for authenticated requests
        """
        # Sort parameters and create query string
        sorted_params = sorted(
            (k, v) for k, v in params.items()
            if k not in ["api_key", "signature", "file"]
        )

        query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
        signature_string = query_string + self.config.api_secret

        return hashlib.sha1(signature_string.encode()).hexdigest()