"""
Health check and metrics endpoints for Sayar WhatsApp Commerce Platform
Provides liveness (/healthz), readiness (/readyz), and metrics (/metrics) endpoints
"""

import os
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from ..database.connection import get_db
from ..utils.metrics import metrics_endpoint
from ..utils.logger import log


router = APIRouter(tags=["Observability"])


@router.get(
    "/healthz",
    summary="Liveness probe",
    description="Fast liveness check that doesn't depend on external services"
)
async def healthz() -> Dict[str, Any]:
    """
    Liveness probe - indicates if the application is running
    
    This endpoint should be fast and not depend on external services.
    Used by Kubernetes/Docker for liveness probes.
    
    Returns:
        Dict with status, timestamp, and version
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "service": "sayar-backend"
    }


@router.get(
    "/readyz",
    summary="Readiness probe", 
    description="Readiness check that verifies critical dependencies"
)
async def readyz(response: Response) -> Dict[str, Any]:
    """
    Readiness probe - indicates if the application can serve traffic
    
    This endpoint checks critical dependencies like database connectivity.
    Used by Kubernetes/Docker for readiness probes.
    
    Returns:
        Dict with status, timestamp, and dependency check results
    """
    checks = {}
    overall_healthy = True
    
    # Database connectivity check
    try:
        # Use dependency injection to get DB session
        async def check_db():
            async for db_session in get_db():
                try:
                    # Simple query to test connectivity
                    result = await db_session.execute(text("SELECT 1"))
                    result.fetchone()
                    return True
                except Exception as e:
                    log.error(f"Database health check failed: {e}")
                    return False
                finally:
                    await db_session.close()
        
        # Run DB check with timeout
        db_healthy = await asyncio.wait_for(check_db(), timeout=2.0)
        checks["database"] = "healthy" if db_healthy else "unhealthy"
        if not db_healthy:
            overall_healthy = False
            
    except asyncio.TimeoutError:
        checks["database"] = "timeout"
        overall_healthy = False
        log.error("Database health check timed out")
    except Exception as e:
        checks["database"] = "unhealthy"
        overall_healthy = False
        log.error(f"Database health check error: {e}")
    
    # Add more dependency checks here as needed
    # Example: Redis, external APIs, etc.
    
    result = {
        "status": "healthy" if overall_healthy else "unhealthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": checks
    }
    
    # Return 503 if any critical dependency is unhealthy
    if not overall_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return result


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Prometheus metrics endpoint for monitoring and alerting"
)
def metrics():
    """
    Prometheus metrics endpoint
    
    Returns metrics in Prometheus text format for scraping by monitoring systems.
    Can be disabled via METRICS_ENABLED environment variable.
    
    Returns:
        Response with Prometheus metrics or 404 if disabled
    """
    return metrics_endpoint()


@router.get(
    "/info",
    summary="Application information",
    description="General application information and build details"
)
async def info() -> Dict[str, Any]:
    """
    Application information endpoint
    
    Provides general application metadata, version info, and configuration.
    Useful for debugging and operational visibility.
    
    Returns:
        Dict with application information
    """
    return {
        "name": "Sayar WhatsApp Commerce Platform",
        "service": "sayar-backend",
        "version": os.getenv("APP_VERSION", "0.1.0"),
        "environment": os.getenv("ENV", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "features": {
            "metrics_enabled": os.getenv("METRICS_ENABLED", "true").lower() == "true",
            "json_logging": os.getenv("LOG_FORMAT", "json") == "json",
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
        },
        "endpoints": {
            "health_liveness": "/healthz",
            "health_readiness": "/readyz", 
            "metrics": "/metrics",
            "openapi": "/docs"
        }
    }