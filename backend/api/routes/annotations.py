from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
import logging

from ...services.annotation_service import AnnotationService
from ...models.schemas import Annotation, AnnotationCreate, AnnotationUpdate, UserFeedbackCreate
from ...models.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize annotation service
annotation_service = AnnotationService()

@router.post("/", response_model=Annotation)
async def create_annotation(
    annotation: AnnotationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new annotation
    """
    try:
        created_annotation = await annotation_service.create_annotation(
            annotation_data=annotation,
            db=db
        )
        
        return created_annotation
        
    except Exception as e:
        logger.error(f"Error creating annotation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating annotation: {str(e)}")

@router.get("/{annotation_id}", response_model=Annotation)
async def get_annotation(
    annotation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific annotation by ID
    """
    try:
        from ...models.models import Annotation as AnnotationModel
        
        annotation = db.query(AnnotationModel).filter(AnnotationModel.id == annotation_id).first()
        if not annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        return annotation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting annotation {annotation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting annotation: {str(e)}")

@router.put("/{annotation_id}", response_model=Annotation)
async def update_annotation(
    annotation_id: str,
    annotation_update: AnnotationUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an annotation
    """
    try:
        updated_annotation = await annotation_service.update_annotation(
            annotation_id=annotation_id,
            update_data=annotation_update,
            db=db
        )
        
        if not updated_annotation:
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        return updated_annotation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating annotation {annotation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating annotation: {str(e)}")

@router.delete("/{annotation_id}")
async def delete_annotation(
    annotation_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an annotation
    """
    try:
        success = await annotation_service.delete_annotation(
            annotation_id=annotation_id,
            db=db
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Annotation not found")
        
        return {"message": "Annotation deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting annotation {annotation_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting annotation: {str(e)}")

@router.get("/image/{image_id}")
async def get_image_annotations(
    image_id: str,
    z: Optional[int] = Query(None, description="Filter by zoom level"),
    x: Optional[int] = Query(None, description="Filter by x coordinate"),
    y: Optional[int] = Query(None, description="Filter by y coordinate"),
    annotation_type: Optional[str] = Query(None, description="Filter by annotation type"),
    db: Session = Depends(get_db)
):
    """
    Get all annotations for an image with optional filters
    """
    try:
        annotations = await annotation_service.get_annotations(
            image_id=image_id,
            db=db,
            z=z,
            x=x,
            y=y
        )
        
        # Apply additional filters
        if annotation_type:
            annotations = [a for a in annotations if a.annotation_type == annotation_type]
        
        return {
            "image_id": image_id,
            "annotations": [annotation.dict() for annotation in annotations],
            "count": len(annotations)
        }
        
    except Exception as e:
        logger.error(f"Error getting annotations for image {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting annotations: {str(e)}")

@router.get("/image/{image_id}/stats")
async def get_annotation_stats(
    image_id: str,
    db: Session = Depends(get_db)
):
    """
    Get annotation statistics for an image
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
        logger.error(f"Error getting annotation stats for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting annotation stats: {str(e)}")

@router.post("/feedback")
async def submit_feedback(
    feedback: UserFeedbackCreate,
    db: Session = Depends(get_db)
):
    """
    Submit user feedback for annotations or ML results
    """
    try:
        from ...models.models import UserFeedback as UserFeedbackModel
        
        user_feedback = UserFeedbackModel(
            image_id=feedback.image_id,
            tile_coordinates=feedback.tile_coordinates,
            feedback_type=feedback.feedback_type,
            content=feedback.content,
            user_id=feedback.user_id
        )
        
        db.add(user_feedback)
        db.commit()
        db.refresh(user_feedback)
        
        return {
            "message": "Feedback submitted successfully",
            "feedback_id": user_feedback.id
        }
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error submitting feedback: {str(e)}")

@router.get("/feedback/{image_id}")
async def get_feedback(
    image_id: str,
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    db: Session = Depends(get_db)
):
    """
    Get user feedback for an image
    """
    try:
        from ...models.models import UserFeedback as UserFeedbackModel
        
        query = db.query(UserFeedbackModel).filter(UserFeedbackModel.image_id == image_id)
        
        if feedback_type:
            query = query.filter(UserFeedbackModel.feedback_type == feedback_type)
        
        feedback_items = query.all()
        
        return {
            "image_id": image_id,
            "feedback": [
                {
                    "id": item.id,
                    "feedback_type": item.feedback_type,
                    "content": item.content,
                    "created_at": item.created_at.isoformat()
                }
                for item in feedback_items
            ],
            "count": len(feedback_items)
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting feedback: {str(e)}")

@router.get("/export/{image_id}")
async def export_annotations(
    image_id: str,
    format: str = Query("json", description="Export format: json, coco"),
    db: Session = Depends(get_db)
):
    """
    Export annotations in various formats
    """
    try:
        export_data = await annotation_service.export_annotations(
            image_id=image_id,
            db=db,
            format=format
        )
        
        return export_data
        
    except Exception as e:
        logger.error(f"Error exporting annotations for {image_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error exporting annotations: {str(e)}")
