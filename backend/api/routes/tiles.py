from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import logging

from ...services.tile_service import TileService
from ...models.schemas import TileRequest
from ...models.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

# Use shared global instance
from ...services.tile_service import tile_service

@router.get("/{image_id}/{z}/{x}/{y}")
async def get_tile(
    image_id: str,
    z: int,
    x: int,
    y: int,
    enhance: bool = Query(False, description="Apply ML enhancement"),
    labels: bool = Query(False, description="Overlay feature labels"),
    confidence_threshold: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence for labels"),
    db: Session = Depends(get_db)
):
    """
    Get a tile with optional ML enhancement
    
    - **image_id**: Unique identifier for the image
    - **z**: Zoom level
    - **x**: X coordinate
    - **y**: Y coordinate
    - **enhance**: Whether to apply ML enhancement (super-resolution, denoising)
    - **labels**: Whether to overlay detected features
    - **confidence_threshold**: Minimum confidence for displaying labels
    """
    try:
        tile_data = await tile_service.get_tile(
            image_id=image_id,
            z=z,
            x=x,
            y=y,
            enhance=enhance,
            labels=labels,
            confidence_threshold=confidence_threshold
        )
        
        if not tile_data:
            raise HTTPException(status_code=404, detail="Tile not found")
        
        return Response(
            content=tile_data,
            media_type="image/jpeg",
            headers={
                "Cache-Control": "public, max-age=3600",
                "X-Tile-Enhanced": str(enhance),
                "X-Tile-Labels": str(labels)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tile {image_id}/{z}/{x}/{y}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing tile: {str(e)}")

@router.get("/proxy/info.json")
async def get_proxy_info(url: str, db: Session = Depends(get_db)):
    """
    Get IIIF info.json for an external image URL
    """
    try:
        info = await tile_service.get_iiif_info(url)
        if not info:
            raise HTTPException(status_code=400, detail="Could not retrieve image info")
        return info
    except Exception as e:
        logger.error(f"Error proxying info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/proxy/tile")
async def get_proxy_tile(
    url: str,
    z: int = Query(...),
    x: int = Query(...),
    y: int = Query(...),
    enhance: bool = Query(False),
    labels: bool = Query(False),
    confidence_threshold: float = Query(0.5),
    quality: int = Query(90),
    db: Session = Depends(get_db)
):
    """
    Serve a dynamic tile for an external image URL
    """
    try:
        tile_data = await tile_service.get_dynamic_tile(
            image_url=url,
            z=z,
            x=x,
            y=y,
            enhance=enhance,
            labels=labels,
            confidence_threshold=confidence_threshold
        )
        
        if not tile_data:
            raise HTTPException(status_code=404, detail="Tile generation failed")
            
        return Response(
            content=tile_data,
            media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )
    except Exception as e:
        logger.error(f"Error proxying tile: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/precompute")
async def precompute_tiles(
    image_id: str,
    zoom_levels: list[int] = Query(..., description="Zoom levels to precompute"),
    enhance: bool = Query(True, description="Whether to apply enhancement"),
    db: Session = Depends(get_db)
):
    """
    Precompute tiles for an image at specified zoom levels
    """
    try:
        results = await tile_service.precompute_tiles(
            image_id=image_id,
            zoom_levels=zoom_levels,
            enhance=enhance
        )
        
        return {
            "message": "Tile precomputation started",
            "image_id": image_id,
            "zoom_levels": zoom_levels,
            "enhance": enhance,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error precomputing tiles for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error precomputing tiles: {str(e)}")

@router.delete("/{image_id}/cache")
async def clear_tile_cache(image_id: str, db: Session = Depends(get_db)):
    """
    Clear cache for all tiles of an image
    """
    try:
        await tile_service.cache_service.invalidate_image(image_id)
        
        return {
            "message": f"Cache cleared for image {image_id}",
            "image_id": image_id
        }
        
    except Exception as e:
        logger.error(f"Error clearing cache for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")

@router.get("/{image_id}/cache/stats")
async def get_cache_stats(image_id: str, db: Session = Depends(get_db)):
    """
    Get cache statistics for an image
    """
    try:
        stats = await tile_service.cache_service.get_cache_stats()
        
        return {
            "image_id": image_id,
            "cache_stats": stats
        }
        
    except Exception as e:
        logger.error(f"Error getting cache stats for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting cache stats: {str(e)}")
