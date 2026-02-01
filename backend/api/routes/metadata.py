from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import logging

from ...services.annotation_service import AnnotationService
from ...models.schemas import Annotation, ImageMetadata, TileMetadata
from ...models.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize annotation service
annotation_service = AnnotationService()

@router.get("/{image_id}/{z}/{x}/{y}")
async def get_tile_metadata(
    image_id: str,
    z: int,
    x: int,
    y: int,
    db: Session = Depends(get_db)
):
    """
    Get metadata for a specific tile including annotations and ML results
    """
    try:
        # Get annotations for this tile
        annotations = await annotation_service.get_annotations(
            image_id=image_id,
            db=db,
            z=z,
            x=x,
            y=y
        )
        
        # Get tile metadata from database
        tile_metadata = db.query(TileMetadata).filter(
            TileMetadata.image_id == image_id,
            TileMetadata.z == z,
            TileMetadata.x == x,
            TileMetadata.y == y
        ).first()
        
        return {
            "image_id": image_id,
            "tile_coordinates": {"z": z, "x": x, "y": y},
            "annotations": [annotation.dict() for annotation in annotations],
            "tile_metadata": tile_metadata.dict() if tile_metadata else None,
            "annotation_count": len(annotations)
        }
        
    except Exception as e:
        logger.error(f"Error getting tile metadata {image_id}/{z}/{x}/{y}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting tile metadata: {str(e)}")

@router.get("/{image_id}/annotations")
async def get_image_annotations(
    image_id: str,
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    db: Session = Depends(get_db)
):
    """
    Get all annotations for an image with optional filters
    """
    try:
        annotations = await annotation_service.get_annotations(
            image_id=image_id,
            db=db
        )
        
        # Apply filters
        if annotation_type:
            annotations = [a for a in annotations if a.annotation_type == annotation_type]
        
        if min_confidence is not None:
            annotations = [a for a in annotations if a.confidence and a.confidence >= min_confidence]
        
        return {
            "image_id": image_id,
            "annotations": [annotation.dict() for annotation in annotations],
            "count": len(annotations)
        }
        
    except Exception as e:
        logger.error(f"Error getting annotations for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting annotations: {str(e)}")

@router.get("/{image_id}/stats")
async def get_image_stats(
    image_id: str,
    db: Session = Depends(get_db)
):
    """
    Get statistics for an image including annotation counts and ML metrics
    """
    try:
        stats = await annotation_service.get_annotation_stats(
            image_id=image_id,
            db=db
        )
        
        return {
            "image_id": image_id,
            "stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting stats for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")

@router.get("/search")
async def search_metadata(
    query: str = Query(..., description="Search query"),
    image_id: Optional[str] = Query(None, description="Filter by image ID"),
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    db: Session = Depends(get_db)
):
    """
    Search annotations and metadata
    """
    try:
        annotations = await annotation_service.search_annotations(
            db=db,
            query=query,
            image_id=image_id,
            annotation_type=annotation_type,
            min_confidence=min_confidence
        )
        
        return {
            "query": query,
            "results": [annotation.dict() for annotation in annotations],
            "count": len(annotations)
        }
        
    except Exception as e:
        logger.error(f"Error searching metadata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching metadata: {str(e)}")

@router.get("/{image_id}/export")
async def export_metadata(
    image_id: str,
    format: str = Query("json", description="Export format: json, coco"),
    db: Session = Depends(get_db)
):
    """
    Export metadata and annotations in various formats
    """
    try:
        export_data = await annotation_service.export_annotations(
            image_id=image_id,
            db=db,
            format=format
        )
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting metadata for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting metadata: {str(e)}")

@router.get("/models/versions")
async def get_model_versions():
    """
    Get information about available ML models and their versions
    """
    try:
        # This would typically come from the ML service
        models = {
            "super_resolution": {
                "name": "Real-ESRGAN",
                "version": "1.0.0",
                "description": "Super-resolution model for enhancing image clarity"
            },
            "denoising": {
                "name": "DnCNN",
                "version": "1.0.0", 
                "description": "Denoising model for cleaning space imagery"
            },
            "segmentation": {
                "name": "U-Net",
                "version": "1.0.0",
                "description": "Semantic segmentation for feature detection"
            },
            "classification": {
                "name": "ResNet",
                "version": "1.0.0",
                "description": "Feature classification model"
            }
        }
        
        return {
            "models": models,
            "last_updated": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(f"Error getting model versions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting model versions: {str(e)}")
