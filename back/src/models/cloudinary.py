"""
Cloudinary models for preset configuration and image variant management
"""

from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID


class PresetUseCase(str, Enum):
    """Use cases for transformation presets"""
    META_CATALOG = "meta_catalog"
    WHATSAPP_PRODUCT = "whatsapp_product"
    DASHBOARD_THUMB = "dashboard_thumb"
    PRODUCT_LIST = "product_list"
    MOBILE_OPTIMIZED = "mobile_optimized"
    DETAILED_VIEW = "detailed_view"


class PresetProfile(str, Enum):
    """Preset profiles that group multiple presets together"""
    STANDARD = "standard"
    PREMIUM = "premium"
    MOBILE_FIRST = "mobile_first"
    CATALOG_FOCUS = "catalog_focus"


class ImageDimensions(BaseModel):
    """Image dimensions model"""
    width: int = Field(..., ge=1, le=5000)
    height: int = Field(..., ge=1, le=5000)


class PresetConstraints(BaseModel):
    """Constraints for transformation presets"""
    max_width: int = Field(..., ge=100, le=5000)
    max_height: int = Field(..., ge=100, le=5000)
    maintain_aspect_ratio: bool = True
    min_quality: int = Field(50, ge=1, le=100)
    max_file_size_kb: Optional[int] = Field(None, ge=1)


class CloudinaryTransformPreset(BaseModel):
    """Single transformation preset definition"""
    id: str = Field(..., pattern=r'^[a-zA-Z0-9_-]+$')
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    transformation: str = Field(..., min_length=1)
    use_cases: List[PresetUseCase]
    eager: bool = True
    constraints: PresetConstraints
    enabled: bool = True
    sort_order: int = 0

    @validator('transformation')
    def validate_transformation_syntax(cls, v):
        """Basic validation of Cloudinary transformation syntax"""
        import re
        has_crop = bool(re.search(r'\bc_(limit|fill|fit)\b', v))
        has_w_or_h = ('w_' in v) or ('h_' in v)
        has_f = 'f_auto' in v
        has_q = 'q_auto' in v
        if not (has_crop and has_w_or_h and has_f and has_q):
            raise ValueError('Transformation must include crop (limit/fill/fit), width or height, f_auto, and q_auto')
        return v


class PresetProfileConfig(BaseModel):
    """Collection of presets that work together"""
    profile_id: PresetProfile
    name: str
    description: str
    presets: Dict[str, str]  # variant_name -> preset_id mapping
    default_eager_variants: List[str]
    recommended_for: List[str]


class ImageVariant(BaseModel):
    """Generated image variant information"""
    url: str
    preset_id: str
    file_size_kb: Optional[int]
    dimensions: Optional[ImageDimensions]
    format: Optional[str]
    quality_score: Optional[int]
    processing_time_ms: Optional[int]


class PresetStats(BaseModel):
    """Usage statistics for a preset"""
    preset_id: str
    usage_count: int = 0
    avg_file_size_kb: Optional[int]
    avg_processing_time_ms: Optional[int]
    quality_score_avg: Optional[float]
    last_used_at: Optional[datetime]


# API Request/Response Models

class UploadWithPresetsRequest(BaseModel):
    """Request model for uploading with preset profiles"""
    is_primary: bool = Field(False, description="Whether this is the primary product image")
    alt_text: Optional[str] = Field(None, description="Alternative text for accessibility")
    preset_profile: PresetProfile = Field(PresetProfile.STANDARD, description="Preset profile to use")


class ProductImageWithVariantsResponse(BaseModel):
    """Enhanced product image response with variants"""
    id: UUID = Field(..., description="Image unique identifier")
    product_id: UUID = Field(..., description="Associated product ID")
    cloudinary_public_id: str = Field(..., description="Cloudinary public ID")
    preset_profile: PresetProfile = Field(..., description="Preset profile used")
    variants: Dict[str, ImageVariant] = Field(..., description="Generated image variants")
    is_primary: bool = Field(..., description="Whether this is the primary product image")
    alt_text: Optional[str] = Field(None, description="Alternative text")
    upload_status: str = Field(..., description="Upload status")
    preset_version: int = Field(..., description="Preset version used")
    optimization_stats: Optional[Dict[str, Any]] = Field(None, description="Optimization statistics")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
        json_schema_extra = {
            "example": {
                "id": "img_uuid",
                "product_id": "prod_uuid",
                "cloudinary_public_id": "sayar/products/merchant_id/image_uuid",
                "preset_profile": "standard",
                "variants": {
                    "main": {
                        "url": "https://res.cloudinary.com/cloud/image/upload/c_limit,w_1600,h_1600,f_auto,q_auto:good/v123/sayar/products/merchant_id/image_uuid.jpg",
                        "preset_id": "main_catalog",
                        "file_size_kb": 245,
                        "dimensions": {"width": 1600, "height": 1067},
                        "format": "webp",
                        "quality_score": 85
                    },
                    "thumb": {
                        "url": "https://res.cloudinary.com/cloud/image/upload/c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco/v123/sayar/products/merchant_id/image_uuid.jpg",
                        "preset_id": "dashboard_thumb",
                        "file_size_kb": 85,
                        "dimensions": {"width": 600, "height": 600},
                        "format": "webp",
                        "quality_score": 75
                    }
                },
                "is_primary": True,
                "alt_text": "Product image",
                "upload_status": "completed",
                "preset_version": 1,
                "optimization_stats": {
                    "total_processing_time_ms": 1350,
                    "eager_variants_count": 2,
                    "on_demand_variants_count": 2
                },
                "created_at": "2025-01-16T10:30:00Z",
                "updated_at": "2025-01-16T10:30:00Z"
            }
        }


class PresetTestRequest(BaseModel):
    """Request to test a preset with a sample image"""
    preset_id: str = Field(..., description="Preset ID to test")
    test_image_url: str = Field(..., pattern=r'^https?://.+', description="URL of test image")


class PresetTestResult(BaseModel):
    """Result of preset testing"""
    success: bool
    transformed_url: Optional[str]
    estimated_file_size_kb: Optional[int]
    dimensions: Optional[ImageDimensions]
    format: Optional[str]
    quality_score: Optional[int]
    processing_time_ms: Optional[int]
    error_message: Optional[str]


class PresetManagementResponse(BaseModel):
    """Response for preset management operations"""
    success: bool
    data: Dict[str, Any]


class PresetListResponse(BaseModel):
    """Response for listing presets"""
    presets: List[Dict[str, Any]]


class PresetStatsResponse(BaseModel):
    """Response for preset usage statistics"""
    preset_id: str
    name: str
    transformation: str
    use_cases: List[PresetUseCase]
    eager: bool
    stats: PresetStats


class PresetProfileStatsResponse(BaseModel):
    """Response for preset profile statistics"""
    profile_id: PresetProfile
    name: str
    description: str
    total_usage: int
    avg_processing_time_ms: Optional[int]
    presets: List[PresetStatsResponse]


# Database Models for SQLAlchemy (for reference)

class CloudinaryPresetStatsDBModel:
    """Database model structure for preset statistics tracking"""
    # This is a reference model - actual SQLAlchemy model will be in sqlalchemy_models.py
    fields = {
        "id": "UUID PRIMARY KEY",
        "merchant_id": "UUID NOT NULL REFERENCES merchants(id)",
        "preset_id": "TEXT NOT NULL",
        "usage_count": "INTEGER DEFAULT 0",
        "avg_file_size_kb": "INTEGER",
        "avg_processing_time_ms": "INTEGER",
        "quality_score_avg": "DECIMAL(3,1)",
        "last_used_at": "TIMESTAMPTZ",
        "created_at": "TIMESTAMPTZ NOT NULL DEFAULT NOW()",
        "updated_at": "TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    }


class ProductImageEnhancementsDBModel:
    """Database model enhancements for product_images table"""
    # Additional fields to be added to existing product_images table
    additional_fields = {
        "preset_profile": "TEXT DEFAULT 'standard'",
        "variants": "JSONB DEFAULT '{}'::jsonb",
        "optimization_stats": "JSONB DEFAULT '{}'::jsonb",
        "preset_version": "INTEGER DEFAULT 1"
    }


# Validation utilities

def validate_preset_profile_consistency(
    profile: PresetProfileConfig,
    available_presets: Dict[str, CloudinaryTransformPreset]
) -> bool:
    """Validate that a preset profile is consistent with available presets"""
    # Check all referenced presets exist
    for variant_name, preset_id in profile.presets.items():
        if preset_id not in available_presets:
            return False

    # Check eager variants are valid
    for variant_name in profile.default_eager_variants:
        if variant_name not in profile.presets:
            return False

        preset_id = profile.presets[variant_name]
        if not available_presets[preset_id].eager:
            return False

    return True


def get_variant_url(
    cloudinary_public_id: str,
    transformation: str,
    version: Optional[int] = None,
    cloud_name: str = None
) -> str:
    """Generate Cloudinary URL with transformation"""
    if not cloud_name:
        import os
        cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")

    base_url = f"https://res.cloudinary.com/{cloud_name}/image/upload"

    if version:
        if transformation:
            return f"{base_url}/{transformation}/v{version}/{cloudinary_public_id}"
        else:
            return f"{base_url}/v{version}/{cloudinary_public_id}"
    else:
        if transformation:
            return f"{base_url}/{transformation}/{cloudinary_public_id}"
        else:
            return f"{base_url}/{cloudinary_public_id}"