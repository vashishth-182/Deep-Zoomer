import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from ..models.database import get_db
from ..models.schemas import Annotation, AnnotationCreate, AnnotationUpdate
from sqlalchemy.orm import Session
from sqlalchemy import and_

logger = logging.getLogger(__name__)

class AnnotationService:
    def __init__(self):
        self.initialized = False
        
    async def initialize(self):
        """Initialize annotation service"""
        try:
            # Initialize database tables
            from ..models.database import engine
            from ..models import models
            
            # Create tables
            models.Base.metadata.create_all(bind=engine)
            self.initialized = True
            logger.info("Annotation service initialized")
            
        except Exception as e:
            logger.error(f"Error initializing annotation service: {str(e)}")
            raise
    
    async def create_annotation(
        self, 
        annotation_data: AnnotationCreate,
        db: Session
    ) -> Annotation:
        """Create a new annotation"""
        try:
            annotation = Annotation(
                id=str(uuid.uuid4()),
                image_id=annotation_data.image_id,
                tile_coordinates=annotation_data.tile_coordinates,
                annotation_type=annotation_data.annotation_type,
                geometry=annotation_data.geometry,
                properties=annotation_data.properties,
                confidence=annotation_data.confidence,
                user_id=annotation_data.user_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(annotation)
            db.commit()
            db.refresh(annotation)
            
            logger.info(f"Created annotation {annotation.id}")
            return annotation
            
        except Exception as e:
            logger.error(f"Error creating annotation: {str(e)}")
            db.rollback()
            raise
    
    async def get_annotations(
        self, 
        image_id: str, 
        db: Session,
        z: Optional[int] = None, 
        x: Optional[int] = None, 
        y: Optional[int] = None
    ) -> List[Annotation]:
        """Get annotations for an image or specific tile"""
        try:
            query = db.query(Annotation).filter(Annotation.image_id == image_id)
            
            if z is not None and x is not None and y is not None:
                # Filter by tile coordinates - check if using SQLite or Postgres
                from ..models.database import engine
                if engine.url.drivername == 'sqlite':
                    # SQLite: fetch all and filter in memory OR use json_extract (standard SQLAlchemy handles this poorly across versions)
                    annotations = query.all()
                    return [
                        a for a in annotations 
                        if str(a.tile_coordinates.get('z')) == str(z) and 
                           str(a.tile_coordinates.get('x')) == str(x) and 
                           str(a.tile_coordinates.get('y')) == str(y)
                    ]
                else:
                    # Postgres-specific JSON filtering
                    query = query.filter(
                        and_(
                            Annotation.tile_coordinates['z'].astext == str(z),
                            Annotation.tile_coordinates['x'].astext == str(x),
                            Annotation.tile_coordinates['y'].astext == str(y)
                        )
                    )
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting annotations: {str(e)}")
            return []
    
    async def update_annotation(
        self, 
        annotation_id: str, 
        update_data: AnnotationUpdate,
        db: Session
    ) -> Optional[Annotation]:
        """Update an annotation"""
        try:
            annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
            if not annotation:
                return None
            
            # Update fields
            for field, value in update_data.dict(exclude_unset=True).items():
                setattr(annotation, field, value)
            
            annotation.updated_at = datetime.utcnow()
            
            db.commit()
            db.refresh(annotation)
            
            logger.info(f"Updated annotation {annotation_id}")
            return annotation
            
        except Exception as e:
            logger.error(f"Error updating annotation: {str(e)}")
            db.rollback()
            return None
    
    async def delete_annotation(self, annotation_id: str, db: Session) -> bool:
        """Delete an annotation"""
        try:
            annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
            if not annotation:
                return False
            
            db.delete(annotation)
            db.commit()
            
            logger.info(f"Deleted annotation {annotation_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting annotation: {str(e)}")
            db.rollback()
            return False
    
    async def get_annotation_stats(self, image_id: str, db: Session) -> Dict[str, Any]:
        """Get annotation statistics for an image"""
        try:
            total_annotations = db.query(Annotation).filter(Annotation.image_id == image_id).count()
            
            # Count by type
            type_counts = {}
            annotations = db.query(Annotation).filter(Annotation.image_id == image_id).all()
            for annotation in annotations:
                annotation_type = annotation.annotation_type
                type_counts[annotation_type] = type_counts.get(annotation_type, 0) + 1
            
            # Average confidence
            confidences = [a.confidence for a in annotations if a.confidence is not None]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            return {
                "total_annotations": total_annotations,
                "type_counts": type_counts,
                "average_confidence": avg_confidence,
                "confidence_range": {
                    "min": min(confidences) if confidences else 0,
                    "max": max(confidences) if confidences else 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting annotation stats: {str(e)}")
            return {}
    
    async def search_annotations(
        self, 
        db: Session,
        query: str, 
        image_id: Optional[str] = None,
        annotation_type: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[Annotation]:
        """Search annotations with filters"""
        try:
            query_obj = db.query(Annotation)
            
            if image_id:
                query_obj = query_obj.filter(Annotation.image_id == image_id)
            
            if annotation_type:
                query_obj = query_obj.filter(Annotation.annotation_type == annotation_type)
            
            if min_confidence is not None:
                query_obj = query_obj.filter(Annotation.confidence >= min_confidence)
            
            # Text search in properties
            if query:
                query_obj = query_obj.filter(
                    Annotation.properties.ilike(f"%{query}%")
                )
            
            annotations = query_obj.all()
            return annotations
            
        except Exception as e:
            logger.error(f"Error searching annotations: {str(e)}")
            return []
    
    async def export_annotations(
        self, 
        image_id: str, 
        db: Session,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export annotations in various formats"""
        try:
            annotations = await self.get_annotations(image_id, db=db)
            
            if format == "json":
                return {
                    "image_id": image_id,
                    "annotations": [
                        {
                            "id": a.id,
                            "type": a.annotation_type,
                            "geometry": a.geometry,
                            "properties": a.properties,
                            "confidence": a.confidence,
                            "created_at": a.created_at.isoformat(),
                            "updated_at": a.updated_at.isoformat()
                        }
                        for a in annotations
                    ]
                }
            elif format == "coco":
                # Convert to COCO format
                return self._convert_to_coco(annotations, image_id)
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Error exporting annotations: {str(e)}")
            return {}
    
    def _convert_to_coco(self, annotations: List[Annotation], image_id: str) -> Dict[str, Any]:
        """Convert annotations to COCO format"""
        try:
            coco_data = {
                "images": [{"id": 1, "file_name": f"{image_id}.jpg"}],
                "annotations": [],
                "categories": []
            }
            
            category_map = {}
            for i, annotation in enumerate(annotations):
                # Add category if not exists
                if annotation.annotation_type not in category_map:
                    category_id = len(category_map) + 1
                    category_map[annotation.annotation_type] = category_id
                    coco_data["categories"].append({
                        "id": category_id,
                        "name": annotation.annotation_type
                    })
                
                # Convert geometry to COCO bbox format
                if annotation.geometry and "bbox" in annotation.geometry:
                    bbox = annotation.geometry["bbox"]
                    coco_data["annotations"].append({
                        "id": i + 1,
                        "image_id": 1,
                        "category_id": category_map[annotation.annotation_type],
                        "bbox": bbox,
                        "area": bbox[2] * bbox[3],
                        "iscrowd": 0
                    })
            
            return coco_data
            
        except Exception as e:
            logger.error(f"Error converting to COCO format: {str(e)}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check annotation service health"""
        try:
            return {
                "status": "healthy" if self.initialized else "unhealthy",
                "initialized": self.initialized
            }
        except Exception as e:
            logger.error(f"Annotation service health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
