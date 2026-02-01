import torch
import torch.nn as nn
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
import logging
from typing import Dict, List, Tuple, Optional, Any
import asyncio
from pathlib import Path
import json

from ..config import settings

logger = logging.getLogger(__name__)

class MLService:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() and settings.gpu_enabled else "cpu")
        self.models = {}
        self.models_loaded = False
        self.batch_size = settings.batch_size
        
    async def initialize_models(self):
        """Initialize all ML models"""
        try:
            logger.info(f"Initializing ML models on device: {self.device}")
            
            # Initialize super-resolution model
            await self._load_sr_model()
            
            # Initialize denoising model
            await self._load_denoising_model()
            
            # Initialize segmentation model
            await self._load_segmentation_model()
            
            # Initialize classification model
            await self._load_classification_model()
            
            self.models_loaded = True
            logger.info("All ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ML models: {str(e)}")
            raise
    
    async def _load_sr_model(self):
        """Load Real-ESRGAN super-resolution model"""
        try:
            from realesrgan import RealESRGANer
            from basicsr.archs.rrdbnet_arch import RRDBNet
            
            # Load Real-ESRGAN model
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
            self.models['sr'] = RealESRGANer(
                scale=4,
                model_path='models/RealESRGAN_x4plus.pth',
                model=model,
                tile=0,
                tile_pad=10,
                pre_pad=0,
                half=True if self.device.type == 'cuda' else False
            )
            logger.info("Super-resolution model loaded")
            
        except Exception as e:
            logger.warning(f"Could not load Real-ESRGAN model: {str(e)}")
            # Fallback to simple upscaling
            self.models['sr'] = None
    
    async def _load_denoising_model(self):
        """Load denoising model"""
        try:
            # For now, use OpenCV's denoising
            # In production, load a trained denoising model
            self.models['denoise'] = 'opencv'
            logger.info("Denoising model loaded")
            
        except Exception as e:
            logger.warning(f"Could not load denoising model: {str(e)}")
            self.models['denoise'] = None
    
    async def _load_segmentation_model(self):
        """Load segmentation model for feature detection"""
        try:
            # Load a pre-trained segmentation model
            # For now, use a simple threshold-based approach
            # In production, load U-Net or Mask R-CNN
            self.models['segmentation'] = 'threshold'
            logger.info("Segmentation model loaded")
            
        except Exception as e:
            logger.warning(f"Could not load segmentation model: {str(e)}")
            self.models['segmentation'] = None
    
    async def _load_classification_model(self):
        """Load classification model for feature labeling"""
        try:
            # Load a pre-trained classification model
            # For now, use simple rule-based classification
            self.models['classification'] = 'rules'
            logger.info("Classification model loaded")
            
        except Exception as e:
            logger.warning(f"Could not load classification model: {str(e)}")
            self.models['classification'] = None
    
    async def super_resolve(self, image: Image.Image) -> Image.Image:
        """Apply super-resolution to image"""
        try:
            if not self.models_loaded or not self.models.get('sr'):
                # Improved fallback: High-quality Lanczos + Smart Sharpening
                upscaled = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
                
                # Apply subtle sharpening to the upscaled image to avoid blur
                from PIL import ImageFilter
                upscaled = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
                return upscaled
            
            # Convert PIL to numpy
            img_array = np.array(image)
            
            # Apply Real-ESRGAN
            sr_array, _ = self.models['sr'].enhance(img_array, outscale=2)
            
            # Convert back to PIL
            return Image.fromarray(sr_array)
            
        except Exception as e:
            logger.error(f"Error in super-resolution: {str(e)}")
            return image
    
    async def denoise(self, image: Image.Image) -> Image.Image:
        """Apply denoising to image"""
        try:
            # Convert PIL to numpy
            img_array = np.array(image)
            
            # Use Bilateral Filter for better edge preservation than fastNlMeans
            # d=9 (diameter), sigmaColor=75, sigmaSpace=75
            denoised = cv2.bilateralFilter(img_array, 9, 75, 75)
            
            # Optional: Apply slight adaptive thresholding or more advanced denoising if needed
            return Image.fromarray(denoised)
            
        except Exception as e:
            logger.error(f"Error in denoising: {str(e)}")
            return image
    
    async def add_labels(
        self, 
        image: Image.Image, 
        confidence_threshold: float = 0.5
    ) -> Image.Image:
        """Add feature labels to image"""
        try:
            if not self.models_loaded:
                return image
            
            # Create a copy for labeling
            labeled_image = image.copy()
            draw = ImageDraw.Draw(labeled_image)
            
            # Simple feature detection (replace with actual ML model)
            features = await self._detect_features(image, confidence_threshold)
            
            # Draw labels
            for feature in features:
                self._draw_feature_label(draw, feature)
            
            return labeled_image
            
        except Exception as e:
            logger.error(f"Error adding labels: {str(e)}")
            return image
    
    async def _detect_features(
        self, 
        image: Image.Image, 
        confidence_threshold: float
    ) -> List[Dict[str, Any]]:
        """Detect features in image"""
        try:
            # Convert to numpy for processing
            img_array = np.array(image)
            
            # Simple feature detection (replace with actual ML model)
            features = []
            
            # Detect craters using circular Hough transform
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            circles = cv2.HoughCircles(
                gray, cv2.HOUGH_GRADIENT, 1, 20,
                param1=50, param2=30, minRadius=5, maxRadius=50
            )
            
            if circles is not None:
                circles = np.round(circles[0, :]).astype("int")
                for (x, y, r) in circles:
                    features.append({
                        'type': 'crater',
                        'confidence': 0.8,
                        'bbox': [x-r, y-r, x+r, y+r],
                        'center': [x, y],
                        'radius': r
                    })
            
            # Filter by confidence threshold
            return [f for f in features if f['confidence'] >= confidence_threshold]
            
        except Exception as e:
            logger.error(f"Error detecting features: {str(e)}")
            return []
    
    def _draw_feature_label(self, draw: ImageDraw.Draw, feature: Dict[str, Any]):
        """Draw feature label on image"""
        try:
            bbox = feature['bbox']
            confidence = feature['confidence']
            feature_type = feature['type']
            
            # Draw bounding box
            draw.rectangle(bbox, outline='red', width=2)
            
            # Draw label
            label = f"{feature_type}: {confidence:.2f}"
            draw.text((bbox[0], bbox[1] - 20), label, fill='red')
            
        except Exception as e:
            logger.error(f"Error drawing feature label: {str(e)}")
    
    async def batch_process(
        self, 
        images: List[Image.Image], 
        operations: List[str]
    ) -> List[Image.Image]:
        """Process multiple images in batch"""
        try:
            results = []
            
            for i in range(0, len(images), self.batch_size):
                batch = images[i:i + self.batch_size]
                batch_results = []
                
                for img in batch:
                    processed_img = img
                    
                    if 'sr' in operations:
                        processed_img = await self.super_resolve(processed_img)
                    
                    if 'denoise' in operations:
                        processed_img = await self.denoise(processed_img)
                    
                    if 'labels' in operations:
                        processed_img = await self.add_labels(processed_img)
                    
                    batch_results.append(processed_img)
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in batch processing: {str(e)}")
            return images
    
    async def health_check(self) -> Dict[str, Any]:
        """Check ML service health"""
        return {
            "status": "healthy" if self.models_loaded else "unhealthy",
            "models_loaded": self.models_loaded,
            "device": str(self.device),
            "models": list(self.models.keys())
        }
    
    async def cleanup(self):
        """Cleanup ML models"""
        try:
            if hasattr(self, 'models'):
                for model in self.models.values():
                    if hasattr(model, 'cleanup'):
                        model.cleanup()
            logger.info("ML service cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up ML service: {str(e)}")

# Global instance
ml_service = MLService()
