from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from typing import Optional, Dict, Any
import asyncio
import logging
import traceback

from .services.tile_service import TileService
from .services.ml_service import MLService
from .services.cache_service import CacheService
from .services.annotation_service import AnnotationService
from .models.database import get_db
from .api.routes import tiles, metadata, annotations, ml_inference
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NASA Deep Zoom AI Platform",
    description="AI-enhanced deep zoom platform for NASA imagery with ML-powered super-resolution, denoising, and feature detection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "msg": str(exc)},
    )

# Initialize services
tile_service = TileService()
ml_service = MLService()
cache_service = CacheService()
annotation_service = AnnotationService()

# Include API routes
app.include_router(tiles.router, prefix="/api/tiles", tags=["tiles"])
app.include_router(metadata.router, prefix="/api/metadata", tags=["metadata"])
app.include_router(annotations.router, prefix="/api/annotations", tags=["annotations"])
app.include_router(ml_inference.router, prefix="/api/ml", tags=["ml"])

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("Starting NASA Deep Zoom AI Platform...")
    
    # Initialize ML models
    await ml_service.initialize_models()
    logger.info("ML models initialized")
    
    # Initialize cache
    await cache_service.initialize()
    logger.info("Cache service initialized")
    
    # Initialize database
    await annotation_service.initialize()
    logger.info("Annotation service initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down NASA Deep Zoom AI Platform...")
    await cache_service.close()
    await ml_service.cleanup()

@app.get("/")
async def root():
    return {
        "message": "NASA Deep Zoom AI Platform",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "ml_service": await ml_service.health_check(),
        "cache_service": await cache_service.health_check(),
        "annotation_service": await annotation_service.health_check()
    }

# Mount static files for serving tiles
if os.path.exists("tiles"):
    app.mount("/tiles", StaticFiles(directory="tiles"), name="tiles")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
