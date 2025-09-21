"""
Admin API endpoints for Cloudinary preset management
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.cloudinary import (
    PresetTestRequest,
    PresetTestResult,
    PresetManagementResponse,
    PresetListResponse,
    PresetStatsResponse,
    PresetProfileStatsResponse,
    PresetProfile
)
from ...models.errors import APIError, ErrorCode
from ...services.cloudinary_service import CloudinaryService
from ...integrations.cloudinary_client import CloudinaryClient
from ...config.cloudinary_presets import (
    STANDARD_PRESETS,
    PRESET_PROFILES,
    QUALITY_TARGETS,
    get_preset_by_id,
    get_profile_by_id,
    validate_preset_configuration
)
from ...auth.dependencies import get_current_admin_user
from ...models.sqlalchemy_models import Merchant

router = APIRouter(prefix="/api/v1/admin/cloudinary/presets", tags=["admin", "cloudinary", "presets"])


@router.get("/", response_model=PresetManagementResponse)
async def list_presets(
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    List all available Cloudinary transformation presets
    """
    try:
        presets_data = []

        for preset_id, preset in STANDARD_PRESETS.items():
            preset_data = {
                "id": preset.id,
                "name": preset.name,
                "description": preset.description,
                "transformation": preset.transformation,
                "use_cases": [uc.value for uc in preset.use_cases],
                "eager": preset.eager,
                "enabled": preset.enabled,
                "sort_order": preset.sort_order,
                "constraints": {
                    "max_width": preset.constraints.max_width,
                    "max_height": preset.constraints.max_height,
                    "min_quality": preset.constraints.min_quality,
                    "max_file_size_kb": preset.constraints.max_file_size_kb,
                    "maintain_aspect_ratio": preset.constraints.maintain_aspect_ratio
                },
                "quality_targets": QUALITY_TARGETS["file_size_kb"].get(preset_id, {})
            }
            presets_data.append(preset_data)

        return PresetManagementResponse(
            success=True,
            data={"presets": presets_data}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list presets: {str(e)}"
        )


@router.get("/profiles", response_model=PresetManagementResponse)
async def list_preset_profiles(
    admin_user: Merchant = Depends(get_current_admin_user)
):
    """
    List all available preset profiles
    """
    try:
        profiles_data = []

        for profile_id, profile in PRESET_PROFILES.items():
            profile_data = {
                "id": profile.profile_id.value,
                "name": profile.name,
                "description": profile.description,
                "presets": profile.presets,
                "default_eager_variants": profile.default_eager_variants,
                "recommended_for": profile.recommended_for
            }
            profiles_data.append(profile_data)

        return PresetManagementResponse(
            success=True,
            data={"profiles": profiles_data}
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list profiles: {str(e)}"
        )


@router.post("/test", response_model=PresetTestResult)
async def test_preset(
    request: PresetTestRequest,
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Test a preset transformation with a sample image
    """
    try:
        # Validate preset exists
        if request.preset_id not in STANDARD_PRESETS:
            raise HTTPException(
                status_code=404,
                detail=f"Preset {request.preset_id} not found"
            )

        cloudinary_client = CloudinaryClient()
        result = cloudinary_client.test_preset_transformation(
            preset_id=request.preset_id,
            test_image_url=request.test_image_url
        )

        return result

    except APIError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test preset: {str(e)}"
        )


@router.get("/stats", response_model=List[PresetStatsResponse])
async def get_preset_statistics(
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    preset_id: Optional[str] = Query(None, description="Filter by preset ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get preset usage statistics
    """
    try:
        cloudinary_service = CloudinaryService(db)

        if merchant_id:
            # Get stats for specific merchant
            from uuid import UUID
            merchant_uuid = UUID(merchant_id)
            stats = cloudinary_service.get_preset_statistics(
                merchant_id=merchant_uuid,
                preset_id=preset_id,
                days=days
            )
        else:
            # Get global stats (admin only feature)
            # This would require a different method for aggregated stats
            # For now, return empty list
            stats = []

        # Convert to response format
        response_stats = []
        for stat in stats:
            preset_config = STANDARD_PRESETS.get(stat["preset_id"])
            if preset_config:
                response_stats.append(PresetStatsResponse(
                    preset_id=stat["preset_id"],
                    name=preset_config.name,
                    transformation=preset_config.transformation,
                    use_cases=preset_config.use_cases,
                    eager=preset_config.eager,
                    stats={
                        "preset_id": stat["preset_id"],
                        "usage_count": stat["usage_count"],
                        "avg_file_size_kb": stat["avg_file_size_kb"],
                        "avg_processing_time_ms": stat["avg_processing_time_ms"],
                        "quality_score_avg": stat["quality_score_avg"],
                        "last_used_at": stat["last_used_at"]
                    }
                ))

        return response_stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.get("/stats/profiles", response_model=List[PresetProfileStatsResponse])
async def get_profile_statistics(
    merchant_id: Optional[str] = Query(None, description="Filter by merchant ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get preset profile usage statistics
    """
    try:
        cloudinary_service = CloudinaryService(db)

        profile_stats = []
        for profile_id, profile_config in PRESET_PROFILES.items():

            if merchant_id:
                from uuid import UUID
                merchant_uuid = UUID(merchant_id)

                # Get stats for all presets in this profile
                preset_stats = []
                total_usage = 0
                total_processing_time = []

                for variant_name, preset_id in profile_config.presets.items():
                    stats = cloudinary_service.get_preset_statistics(
                        merchant_id=merchant_uuid,
                        preset_id=preset_id,
                        days=days
                    )

                    for stat in stats:
                        preset_config = STANDARD_PRESETS.get(stat["preset_id"])
                        if preset_config:
                            preset_stats.append(PresetStatsResponse(
                                preset_id=stat["preset_id"],
                                name=preset_config.name,
                                transformation=preset_config.transformation,
                                use_cases=preset_config.use_cases,
                                eager=preset_config.eager,
                                stats={
                                    "preset_id": stat["preset_id"],
                                    "usage_count": stat["usage_count"],
                                    "avg_file_size_kb": stat["avg_file_size_kb"],
                                    "avg_processing_time_ms": stat["avg_processing_time_ms"],
                                    "quality_score_avg": stat["quality_score_avg"],
                                    "last_used_at": stat["last_used_at"]
                                }
                            ))

                            total_usage += stat["usage_count"]
                            if stat["avg_processing_time_ms"]:
                                total_processing_time.append(stat["avg_processing_time_ms"])

                avg_processing_time = sum(total_processing_time) // len(total_processing_time) if total_processing_time else None

                profile_stats.append(PresetProfileStatsResponse(
                    profile_id=profile_id,
                    name=profile_config.name,
                    description=profile_config.description,
                    total_usage=total_usage,
                    avg_processing_time_ms=avg_processing_time,
                    presets=preset_stats
                ))

        return profile_stats

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get profile statistics: {str(e)}"
        )


@router.get("/validate", response_model=PresetManagementResponse)
async def validate_presets(
    admin_user: Merchant = Depends(get_current_admin_user)
):
    """
    Validate all preset configurations
    """
    try:
        validation_result = validate_preset_configuration()

        return PresetManagementResponse(
            success=validation_result,
            data={
                "valid": validation_result,
                "message": "All presets are valid" if validation_result else "Some presets have validation errors",
                "presets_count": len(STANDARD_PRESETS),
                "profiles_count": len(PRESET_PROFILES)
            }
        )

    except Exception as e:
        return PresetManagementResponse(
            success=False,
            data={
                "valid": False,
                "message": f"Validation failed: {str(e)}",
                "error": str(e)
            }
        )


@router.get("/health", response_model=PresetManagementResponse)
async def check_preset_health(
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Check health of preset system and Cloudinary integration
    """
    try:
        cloudinary_service = CloudinaryService(db)

        # Check Cloudinary health
        cloudinary_health = cloudinary_service.health_check()

        # Check preset configuration
        config_valid = validate_preset_configuration()

        # Check database connectivity for stats
        try:
            db.execute("SELECT 1 FROM cloudinary_preset_stats LIMIT 1")
            db_healthy = True
        except Exception:
            db_healthy = False

        return PresetManagementResponse(
            success=cloudinary_health["configured"] and config_valid and db_healthy,
            data={
                "cloudinary": cloudinary_health,
                "preset_config_valid": config_valid,
                "database_healthy": db_healthy,
                "presets_available": len(STANDARD_PRESETS),
                "profiles_available": len(PRESET_PROFILES)
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )


@router.get("/performance", response_model=PresetManagementResponse)
async def get_performance_metrics(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    admin_user: Merchant = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics for preset system
    """
    try:
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query aggregated performance data
        query = """
        SELECT
            preset_id,
            COUNT(*) as total_merchants,
            SUM(usage_count) as total_usage,
            AVG(avg_file_size_kb) as overall_avg_size,
            AVG(avg_processing_time_ms) as overall_avg_time,
            AVG(quality_score_avg) as overall_avg_quality
        FROM cloudinary_preset_stats
        WHERE last_used_at >= %s OR last_used_at IS NULL
        GROUP BY preset_id
        ORDER BY total_usage DESC
        """

        result = db.execute(query, [cutoff_date]).fetchall()

        performance_data = []
        for row in result:
            preset_config = STANDARD_PRESETS.get(row[0])
            if preset_config:
                target_size = QUALITY_TARGETS["file_size_kb"].get(row[0], {}).get("target", 0)
                performance_data.append({
                    "preset_id": row[0],
                    "preset_name": preset_config.name,
                    "total_merchants": row[1],
                    "total_usage": row[2],
                    "avg_file_size_kb": round(row[3], 1) if row[3] else None,
                    "avg_processing_time_ms": round(row[4], 1) if row[4] else None,
                    "avg_quality_score": round(row[5], 1) if row[5] else None,
                    "target_file_size_kb": target_size,
                    "size_efficiency": round((target_size / row[3]) * 100, 1) if row[3] and target_size else None
                })

        return PresetManagementResponse(
            success=True,
            data={
                "period_days": days,
                "performance_metrics": performance_data,
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance metrics: {str(e)}"
        )