from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class AnnotationBase(BaseModel):
    image_id: str
    tile_coordinates: Dict[str, int] = Field(..., description="Tile coordinates: {z, x, y}")
    annotation_type: str = Field(..., description="Type of annotation: crater, lava_flow, etc.")
    geometry: Dict[str, Any] = Field(..., description="Geometry data (GeoJSON format)")
    properties: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    user_id: Optional[str] = None

class AnnotationCreate(AnnotationBase):
    pass

class AnnotationUpdate(BaseModel):
    annotation_type: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)

class Annotation(AnnotationBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TileMetadataBase(BaseModel):
    image_id: str
    z: int
    x: int
    y: int
    enhanced: str
    model_version: Optional[str] = None
    processing_time: Optional[float] = None
    confidence_scores: Optional[Dict[str, float]] = None
    features_detected: Optional[List[Dict[str, Any]]] = None

class TileMetadataCreate(TileMetadataBase):
    pass

class TileMetadata(TileMetadataBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ImageMetadataBase(BaseModel):
    image_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    nasa_id: Optional[str] = None
    source_url: Optional[str] = None
    iiif_url: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None
    zoom_levels: Optional[List[int]] = None
    enhanced_available: str = "false"

class ImageMetadataCreate(ImageMetadataBase):
    pass

class ImageMetadata(ImageMetadataBase):
    id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserFeedbackBase(BaseModel):
    image_id: str
    tile_coordinates: Dict[str, int]
    feedback_type: str = Field(..., description="Type of feedback: correction, improvement, bug_report")
    content: str
    user_id: Optional[str] = None

class UserFeedbackCreate(UserFeedbackBase):
    pass

class UserFeedback(UserFeedbackBase):
    id: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class MLInferenceRequest(BaseModel):
    image_id: str
    z: int
    x: int
    y: int
    operations: List[str] = Field(..., description="List of operations: sr, denoise, segment, classify")
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)

class MLInferenceResponse(BaseModel):
    success: bool
    processing_time: float
    model_versions: Dict[str, str]
    confidence_scores: Dict[str, float]
    features_detected: List[Dict[str, Any]]
    error: Optional[str] = None

class TileRequest(BaseModel):
    image_id: str
    z: int
    x: int
    y: int
    enhance: bool = False
    labels: bool = False
    confidence_threshold: float = Field(0.5, ge=0.0, le=1.0)

class ComparisonRequest(BaseModel):
    image_id: str
    z: int
    x: int
    y: int
    original: bool = True
    enhanced: bool = True

class PrecomputeRequest(BaseModel):
    image_id: str
    image_url: Optional[str] = None
    zoom_levels: List[int]
    operations: Optional[List[str]] = None
