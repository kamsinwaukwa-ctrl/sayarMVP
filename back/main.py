"""
Sayar WhatsApp Commerce Platform - FastAPI Backend
Main application entry point with OpenAPI v3 documentation and observability
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import API routers
from src.api.auth import router as auth_router
from src.api.merchants import router as merchants_router
from src.api.products import router as products_router
from src.api.delivery_rates import router as delivery_rates_router
from src.api.discounts import router as discounts_router
from src.api.health import router as health_router
from src.api.meta_feeds import router as meta_feeds_router
from src.api.payment_providers import router as payment_providers_router
from src.api.integrations import router as integrations_router
from src.api.meta_integrations import router as meta_integrations_router
from src.api.admin.reconciliation import router as admin_reconciliation_router
from src.api.admin.webhook_bootstrap import router as admin_webhook_router
from src.api.webhooks import router as webhooks_router

# Import observability components
from src.middleware.logging import LoggingMiddleware
from src.middleware.error_middleware import ErrorMiddleware
from src.utils.logger import log

# Import outbox worker
from src.workers.outbox_worker import start_worker, stop_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with structured logging and worker management"""
    # Startup
    log.info(
        "Application starting up",
        extra={
            "event_type": "app_startup",
            "version": os.getenv("APP_VERSION", "0.1.1"),
            "environment": os.getenv("ENV", "development"),
        },
    )

    # Start outbox worker if enabled
    # In split deployment: web service sets WORKER_ENABLED=false, worker service sets it to true
    worker_enabled = os.getenv("WORKER_ENABLED", "true").lower() == "true"
    if worker_enabled:
        log.info(
            "Starting outbox worker (embedded mode)",
            extra={
                "event_type": "worker_startup_init",
                "mode": "embedded_in_web",
            },
        )
        await start_worker()
    else:
        log.info(
            "Outbox worker disabled - running in web-only mode",
            extra={
                "event_type": "worker_disabled",
                "note": "Worker should be running in separate service",
            },
        )

    yield

    # Shutdown
    log.info("Application shutting down", extra={"event_type": "app_shutdown"})

    # Stop outbox worker if it was started
    if worker_enabled:
        log.info("Stopping outbox worker", extra={"event_type": "worker_shutdown_init"})
        await stop_worker()


# Create FastAPI app with OpenAPI configuration
app = FastAPI(
    title="Sayar API",
    description="""
    Sayar WhatsApp Commerce Platform API
    
    **Version:** 0.1.1
    
    Provides endpoints for authentication, merchants, products, delivery rates, and discounts.
    All endpoints require JWT authentication with merchant_id claim.
    
    **Changelog v0.1.1:**
    - Made WhatsApp phone number optional during user registration
    """,
    version="0.1.1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.usesayar.com", "description": "Production server"},
    ],
)


# Customize OpenAPI schema to add x-api-version
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )
    openapi_schema["info"]["x-api-version"] = "0.1.1"
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Configure middleware - order matters!
# 1. CORS middleware (FIRST - must run before any errors to ensure headers are set)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "https://app.usesayar.com",
        "https://usesayar.com",
    ],  # no '*'
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Error middleware (catches all exceptions)
include_debug = os.getenv("ENV", "development") == "development"
app.add_middleware(ErrorMiddleware, include_debug_info=include_debug)

# 3. Logging middleware (logs requests/responses)
app.add_middleware(LoggingMiddleware)

# 4. Connection handling middleware to prevent H11 protocol errors
from fastapi import Request
from fastapi.responses import Response
import asyncio

@app.middleware("http")
async def connection_handler(request: Request, call_next):
    """Handle connection drops gracefully to prevent H11 protocol errors"""
    try:
        # Add timeout to prevent hanging requests (only for HTTP requests)
        response = await asyncio.wait_for(call_next(request), timeout=60.0)
        return response
    except asyncio.TimeoutError:
        # Request timed out
        log.warning(
            "Request timeout",
            extra={
                "event_type": "request_timeout",
                "path": request.url.path,
                "method": request.method,
            }
        )
        return Response(status_code=504, content="Request timeout")
    except (ConnectionResetError, BrokenPipeError) as e:
        # Client disconnected, log and return empty response
        log.warning(
            "Client disconnected during request",
            extra={
                "event_type": "client_disconnect",
                "error_type": type(e).__name__,
                "path": request.url.path,
                "method": request.method,
            }
        )
        return Response(status_code=499)  # Client Closed Request
    except asyncio.CancelledError:
        # Task was cancelled (likely due to client disconnect)
        log.debug(
            "Request cancelled",
            extra={
                "event_type": "request_cancelled",
                "path": request.url.path,
                "method": request.method,
            }
        )
        return Response(status_code=499)  # Client Closed Request

# Global exception handler for HTTPException to add CORS headers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    from fastapi.responses import JSONResponse

    # Create response content
    content = {
        "detail": exc.detail
    }

    # Create response with CORS headers
    response = JSONResponse(
        content=content,
        status_code=exc.status_code,
    )

    # Add CORS headers manually if Origin header is present
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "https://app.usesayar.com",
        "https://usesayar.com",
    ]

    if origin and origin in allowed_origins:
        response.headers["access-control-allow-origin"] = origin
        response.headers["access-control-allow-credentials"] = "true"
        response.headers["vary"] = "Origin"

    return response

# Include observability routers first (no auth required)
app.include_router(health_router)

# Include public API routers (no auth required)
app.include_router(meta_feeds_router, prefix="/api/v1")
app.include_router(webhooks_router)  # Webhook endpoints (no auth - verified by signature)

# Include authenticated API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(merchants_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(delivery_rates_router, prefix="/api/v1")
app.include_router(discounts_router, prefix="/api/v1")
app.include_router(payment_providers_router, prefix="/api/v1")
app.include_router(meta_integrations_router, prefix="/api/v1")
app.include_router(integrations_router)
app.include_router(admin_reconciliation_router)
app.include_router(admin_webhook_router)  # Admin webhook bootstrap endpoints


@app.get("/")
async def root(request: Request):
    """Root endpoint with basic service information and test error handling"""
    # Handle test error cases
    if test_error := request.headers.get("X-Test-Error"):
        if test_error == "rate-limit":
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "30"},
            )
        elif test_error == "not-found":
            raise HTTPException(status_code=404, detail="Resource not found")

    return {
        "message": "Sayar WhatsApp Commerce API",
        "version": os.getenv("APP_VERSION", "0.1.1"),
        "status": "running",
        "docs": "/docs",
        "health": {
            "liveness": "/healthz",
            "readiness": "/readyz",
            "metrics": "/metrics",
        },
    }


# Development endpoints for testing error handling
if os.getenv("ENV", "development") == "development":
    from src.models.errors import RetryableError, AuthzError
    from src.utils.retry import retryable, RetryConfig
    from src.utils.circuit_breaker import circuit_breaker, CircuitBreakerConfig
    import asyncio
    import random

    @app.get("/dev/boom")
    async def dev_boom():
        """Trigger a synthetic 500 error for testing"""
        raise HTTPException(
            status_code=500, detail="Synthetic server error for testing"
        )

    @app.get("/dev/rate-limited")
    async def dev_rate_limited():
        """Trigger a synthetic rate limit error"""
        raise HTTPException(
            status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "30"}
        )

    @app.get("/dev/auth-error")
    async def dev_auth_error():
        """Trigger a synthetic authorization error"""
        raise AuthzError("Requires admin role for testing")

    # Global counter for flaky endpoint
    _flaky_attempts = 0

    @app.get("/dev/flaky")
    @retryable(config=RetryConfig(max_attempts=3, base_delay=0.1))
    async def dev_flaky():
        """Endpoint that succeeds on 3rd attempt for retry testing"""
        global _flaky_attempts
        _flaky_attempts += 1

        if _flaky_attempts < 3:
            raise RetryableError("test_service", f"Attempt {_flaky_attempts} failed")
        else:
            _flaky_attempts = 0  # Reset for next test
            return {"message": "Success after retries", "attempts": 3}

    @app.get("/dev/upstream-500")
    @circuit_breaker(
        "test_upstream", CircuitBreakerConfig(failure_threshold=3, recovery_timeout=10)
    )
    async def dev_upstream_500():
        """Endpoint that randomly fails for circuit breaker testing"""
        if random.random() < 0.8:  # 80% failure rate
            raise HTTPException(status_code=500, detail="Upstream service error")
        return {"message": "Upstream call succeeded"}


if __name__ == "__main__":
    # For development only
    port = int(os.getenv("PORT", 8000))  # Railway provides PORT env var
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "development") == "development",
        # Connection handling improvements
        timeout_keep_alive=30,  # Keep connections alive for 30 seconds
        timeout_graceful_shutdown=10,  # Graceful shutdown timeout
        limit_max_requests=1000,  # Restart worker after 1000 requests
        limit_concurrency=1000,  # Max concurrent connections
    )
