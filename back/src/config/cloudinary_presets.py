"""
Cloudinary transformation presets configuration

This module defines standardized transformation presets for consistent image optimization
across different platform use cases (Meta Catalog, dashboards, mobile, thumbnails).
"""

from typing import Dict
from ..models.cloudinary import (
    CloudinaryTransformPreset,
    PresetProfileConfig,
    PresetProfile,
    PresetUseCase,
    PresetConstraints
)

# Preset version for tracking changes
PRESETS_VERSION = 1

# Standard Preset Definitions
STANDARD_PRESETS: Dict[str, CloudinaryTransformPreset] = {
    "main_catalog": CloudinaryTransformPreset(
        id="main_catalog",
        name="Main (Meta Catalog)",
        description="Optimized for Meta Catalog display - 1600x1600 max, high quality for WhatsApp commerce",
        transformation="c_limit,w_1600,h_1600,f_auto,q_auto:good",
        use_cases=[PresetUseCase.META_CATALOG, PresetUseCase.WHATSAPP_PRODUCT],
        eager=True,
        constraints=PresetConstraints(
            max_width=1600,
            max_height=1600,
            min_quality=80,
            max_file_size_kb=300
        ),
        sort_order=1
    ),

    "dashboard_thumb": CloudinaryTransformPreset(
        id="dashboard_thumb",
        name="Dashboard Thumbnail",
        description="Square thumbnails for merchant dashboard - 600x600, optimized for fast loading",
        transformation="c_fill,w_600,h_600,g_auto,f_auto,q_auto:eco",
        use_cases=[PresetUseCase.DASHBOARD_THUMB],
        eager=True,
        constraints=PresetConstraints(
            max_width=600,
            max_height=600,
            min_quality=70,
            max_file_size_kb=100
        ),
        sort_order=2
    ),

    "mobile_optimized": CloudinaryTransformPreset(
        id="mobile_optimized",
        name="Mobile Optimized",
        description="Bandwidth-optimized for mobile devices - 800x800 max, balanced quality/size",
        transformation="c_limit,w_800,h_800,f_auto,q_auto:auto",
        use_cases=[PresetUseCase.MOBILE_OPTIMIZED],
        eager=False,  # Generate on-demand for mobile
        constraints=PresetConstraints(
            max_width=800,
            max_height=800,
            min_quality=65,
            max_file_size_kb=150
        ),
        sort_order=3
    ),

    "product_list": CloudinaryTransformPreset(
        id="product_list",
        name="Product List",
        description="Small thumbnails for product lists - 400x300, very fast loading",
        transformation="c_fill,w_400,h_300,g_auto,f_auto,q_auto:auto",
        use_cases=[PresetUseCase.PRODUCT_LIST],
        eager=False,
        constraints=PresetConstraints(
            max_width=400,
            max_height=300,
            min_quality=60,
            max_file_size_kb=50
        ),
        sort_order=4
    ),

    "detailed_view": CloudinaryTransformPreset(
        id="detailed_view",
        name="Detailed View",
        description="High-quality for product detail pages - 2000x2000 max, premium quality",
        transformation="c_limit,w_2000,h_2000,f_auto,q_auto:best",
        use_cases=[PresetUseCase.DETAILED_VIEW],
        eager=False,  # Generate on-demand
        constraints=PresetConstraints(
            max_width=2000,
            max_height=2000,
            min_quality=90,
            max_file_size_kb=500
        ),
        sort_order=5
    )
}

# Preset Profile Configurations
PRESET_PROFILES: Dict[PresetProfile, PresetProfileConfig] = {
    PresetProfile.STANDARD: PresetProfileConfig(
        profile_id=PresetProfile.STANDARD,
        name="Standard Profile",
        description="Balanced optimization for general commerce use",
        presets={
            "main": "main_catalog",
            "thumb": "dashboard_thumb",
            "mobile": "mobile_optimized",
            "list": "product_list"
        },
        default_eager_variants=["main", "thumb"],
        recommended_for=["general_commerce", "mixed_traffic"]
    ),

    PresetProfile.PREMIUM: PresetProfileConfig(
        profile_id=PresetProfile.PREMIUM,
        name="Premium Profile",
        description="High-quality optimization for premium brands",
        presets={
            "main": "main_catalog",
            "thumb": "dashboard_thumb",
            "mobile": "mobile_optimized",
            "list": "product_list",
            "detail": "detailed_view"
        },
        default_eager_variants=["main", "thumb", "detail"],
        recommended_for=["luxury_brands", "high_quality_products"]
    ),

    PresetProfile.MOBILE_FIRST: PresetProfileConfig(
        profile_id=PresetProfile.MOBILE_FIRST,
        name="Mobile-First Profile",
        description="Optimized for mobile-heavy traffic with bandwidth consideration",
        presets={
            "main": "mobile_optimized",  # Use mobile as main
            "thumb": "product_list",     # Smaller thumbs
            "catalog": "main_catalog"    # Keep catalog quality for WhatsApp
        },
        default_eager_variants=["main", "catalog"],
        recommended_for=["mobile_heavy_traffic", "bandwidth_sensitive"]
    ),

    PresetProfile.CATALOG_FOCUS: PresetProfileConfig(
        profile_id=PresetProfile.CATALOG_FOCUS,
        name="Catalog-Focused Profile",
        description="Optimized primarily for WhatsApp catalog performance",
        presets={
            "main": "main_catalog",
            "thumb": "dashboard_thumb"
        },
        default_eager_variants=["main"],
        recommended_for=["whatsapp_commerce", "catalog_heavy"]
    )
}

# Quality thresholds and targets
QUALITY_TARGETS = {
    "file_size_kb": {
        "main_catalog": {"target": 250, "max": 300},
        "dashboard_thumb": {"target": 80, "max": 100},
        "mobile_optimized": {"target": 120, "max": 150},
        "product_list": {"target": 35, "max": 50},
        "detailed_view": {"target": 400, "max": 500}
    },
    "loading_time_ms": {
        "3g": {"acceptable": 3000, "good": 1500},
        "4g": {"acceptable": 1000, "good": 500},
        "wifi": {"acceptable": 500, "good": 200}
    }
}

# Performance configuration
PERFORMANCE_CONFIG = {
    "preset_cache_ttl_hours": 168,  # 1 week
    "performance_check_interval_hours": 24,
    "quality_threshold_warning": 0.2,  # 20% deviation from target
    "file_size_threshold_warning": 0.15,  # 15% deviation from target
    "on_demand_cache_size_mb": 1024,
    "eager_retry_attempts": 3,
    "transformation_timeout_seconds": 30
}


def get_preset_by_id(preset_id: str) -> CloudinaryTransformPreset:
    """Get preset configuration by ID"""
    if preset_id not in STANDARD_PRESETS:
        raise ValueError(f"Unknown preset ID: {preset_id}")
    return STANDARD_PRESETS[preset_id]


def get_profile_by_id(profile_id: PresetProfile) -> PresetProfileConfig:
    """Get profile configuration by ID"""
    if profile_id not in PRESET_PROFILES:
        raise ValueError(f"Unknown profile ID: {profile_id}")
    return PRESET_PROFILES[profile_id]


def get_eager_presets_for_profile(profile_id: PresetProfile) -> Dict[str, CloudinaryTransformPreset]:
    """Get all eager presets for a given profile"""
    profile = get_profile_by_id(profile_id)
    eager_presets = {}

    for variant_name in profile.default_eager_variants:
        if variant_name in profile.presets:
            preset_id = profile.presets[variant_name]
            preset = get_preset_by_id(preset_id)
            if preset.eager:
                eager_presets[variant_name] = preset

    return eager_presets


def get_all_presets_for_profile(profile_id: PresetProfile) -> Dict[str, CloudinaryTransformPreset]:
    """Get all presets (eager and on-demand) for a given profile"""
    profile = get_profile_by_id(profile_id)
    all_presets = {}

    for variant_name, preset_id in profile.presets.items():
        preset = get_preset_by_id(preset_id)
        all_presets[variant_name] = preset

    return all_presets


def validate_preset_configuration() -> bool:
    """Validate all preset configurations for consistency"""
    try:
        # Validate all presets
        for preset_id, preset in STANDARD_PRESETS.items():
            # Check transformation syntax
            transformation = preset.transformation
            if not all(req in transformation for req in ['c_', 'f_auto', 'q_auto']):
                raise ValueError(f"Invalid transformation for preset {preset_id}: missing required parameters")

        # Validate all profiles
        for profile_id, profile in PRESET_PROFILES.items():
            # Check that all referenced presets exist
            for variant_name, preset_id in profile.presets.items():
                if preset_id not in STANDARD_PRESETS:
                    raise ValueError(f"Profile {profile_id} references unknown preset: {preset_id}")

            # Check that eager variants are valid
            for variant_name in profile.default_eager_variants:
                if variant_name not in profile.presets:
                    raise ValueError(f"Profile {profile_id} has invalid eager variant: {variant_name}")

        return True
    except Exception:
        return False


def get_transformation_for_variant(profile_id: PresetProfile, variant_name: str) -> str:
    """Get transformation string for a specific variant in a profile"""
    profile = get_profile_by_id(profile_id)

    if variant_name not in profile.presets:
        raise ValueError(f"Variant {variant_name} not found in profile {profile_id}")

    preset_id = profile.presets[variant_name]
    preset = get_preset_by_id(preset_id)

    return preset.transformation


# Validate configuration on module import
if not validate_preset_configuration():
    raise RuntimeError("Invalid preset configuration detected")