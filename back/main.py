"""
Sayar WhatsApp Commerce Platform - FastAPI Backend
Main application entry point with OpenAPI v3 documentation
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import os
from datetime import datetime

# Import API routers
from src.api.auth import router as auth_router
from src.api.merchants import router as merchants_router
from src.api.products import router as products_router
from src.api.delivery_rates import router as delivery_rates_router
from src.api.discounts import router as discounts_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("🚀 Sayar backend starting up...")
    yield
    # Shutdown
    print("🛑 Sayar backend shutting down...")


# Create FastAPI app with OpenAPI configuration
app = FastAPI(
    title="Sayar API",
    description="""
    Sayar WhatsApp Commerce Platform API
    
    **Version:** 0.1.0
    
    Provides endpoints for authentication, merchants, products, delivery rates, and discounts.
    All endpoints require JWT authentication with merchant_id claim.
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.sayar.example.com",
            "description": "Production server"
        }
    ]
)

# Configure CORS from environment variable
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(merchants_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(delivery_rates_router, prefix="/api/v1")
app.include_router(discounts_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Sayar WhatsApp Commerce API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "sayar-backend"
    }


@app.get("/api/v1/health")
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "api_version": "v1",
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # For development only
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )