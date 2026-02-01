import os
import logging
from PIL import Image
import io
import httpx
import hashlib
from typing import Optional, List, Dict, Any
from ..config import settings
from .ml_service import ml_service
from .cache_service import cache_service

logger = logging.getLogger(__name__)

class TileService:
    def __init__(self):
        self.ml_service = ml_service
        self.cache_service = cache_service
        self.http_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        self.source_image_cache = {} # In-memory cache for full source images during active sessions

    async def _fetch_original_tile(self, image_id: str, z: int, x: int, y: int) -> Optional[bytes]:
        """
        Internal method to fetch the original, unprocessed tile from disk.
        Used by the ML inference engine.
        """
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "public"))
        
        possible_paths = [
            os.path.join(base_dir, f"{image_id}_files", str(z), f"{x}_{y}.jpg"),
            os.path.join(base_dir, f"{image_id}_files", str(z), f"{x}_{y}.png"),
            os.path.join(base_dir, "tiles", image_id, str(z), f"{x}_{y}.jpg"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "rb") as f:
                    return f.read()
        return None
        
    async def get_tile(
        self,
        image_id: str,
        z: int,
        x: int,
        y: int,
        enhance: bool = False,
        labels: bool = False,
        confidence_threshold: float = 0.5
    ) -> Optional[bytes]:
        """
        Get an image tile with optional ML enhancement and labeling.
        """
        # Generate a unique cache key based on all parameters
        cache_key = f"{image_id}:{z}:{x}:{y}:e{enhance}:l{labels}:c{confidence_threshold}"
        
        # 1. Try to get from cache
        if not self.cache_service.connected:
            await self.cache_service.initialize()
            
        cached_tile = await self.cache_service.get_tile(cache_key)
        if cached_tile:
            logger.debug(f"Cache hit for tile: {cache_key}")
            return cached_tile
            
        # 2. Find the source tile on disk
        # We look in the root public directory where DZI files are stored
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "public"))
        
        # Common DZI tile patterns
        possible_paths = [
            os.path.join(base_dir, f"{image_id}_files", str(z), f"{x}_{y}.jpg"),
            os.path.join(base_dir, f"{image_id}_files", str(z), f"{x}_{y}.png"),
            os.path.join(base_dir, "tiles", image_id, str(z), f"{x}_{y}.jpg"),
        ]
        
        tile_path = None
        for path in possible_paths:
            if os.path.exists(path):
                tile_path = path
                break
                
        if not tile_path:
            logger.warning(f"Tile not found for {image_id} at z={z}, x={x}, y={y}")
            return None
            
        # 3. Process the tile
        try:
            image = Image.open(tile_path)
            
            # Ensure ML models are initialized
            if not self.ml_service.models_loaded:
                await self.ml_service.initialize_models()
            
            # Apply enhancements
            if enhance:
                logger.debug(f"Applying AI enhancement to tile {image_id}/{z}/{x}/{y}")
                image = await self.ml_service.super_resolve(image)
                image = await self.ml_service.denoise(image)
                
            # Apply labels
            if labels:
                logger.debug(f"Adding AI labels to tile {image_id}/{z}/{x}/{y}")
                image = await self.ml_service.add_labels(image, confidence_threshold)
                
            # Convert back to bytes
            img_byte_arr = io.BytesIO()
            # If it was a PNG originally, we might want to keep that or convert everything to JPEG for speed
            save_format = 'JPEG' if image.mode != 'RGBA' else 'PNG'
            image.save(img_byte_arr, format=save_format, quality=85)
            tile_data = img_byte_arr.getvalue()
            
            # 4. Store in cache
            await self.cache_service.set_tile(cache_key, tile_data)
            
            return tile_data
            
        except Exception as e:
            logger.error(f"Error processing tile {tile_path}: {str(e)}")
            return None

    async def get_iiif_info(self, image_url: str) -> Dict[str, Any]:
        """
        Generate IIIF info.json for an external image URL.
        This allows OpenSeadragon to treat any image as a deep-zoom source.
        """
        try:
            # 1. Get image dimensions
            image = await self._get_full_image(image_url)
            if not image:
                raise Exception("Could not load source image")
            
            width, height = image.size
            
            import math
            max_level = math.ceil(math.log2(max(width, height)))
            
            # Simple hash for ID
            image_id = hashlib.md5(image_url.encode()).hexdigest()
            
            return {
                "@context": "http://iiif.io/api/image/2/context.json",
                "@id": f"{settings.nasa_api_key}/proxy/{image_id}", # settings.nasa_api_key is used as placeholder for API BASE URL in proxy context
                "protocol": "http://iiif.io/api/image",
                "width": width,
                "height": height,
                "maxLevel": max_level,
                "tiles": [
                    {
                        "width": 256,
                        "scaleFactors": [2**i for i in range(max_level + 1)]
                    }
                ],
                "profile": [
                    "http://iiif.io/api/image/2/level2.json"
                ]
            }
        except Exception as e:
            logger.error(f"Error generating IIIF info: {str(e)}")
            return {}

    async def get_dynamic_tile(
        self,
        image_url: str,
        z: int,
        x: int,
        y: int,
        tile_size: int = 256,
        enhance: bool = False,
        labels: bool = False,
        confidence_threshold: float = 0.5,
        quality: int = 90
    ) -> Optional[bytes]:
        """
        Dynamically crop a tile from a full image and apply AI enhancement.
        Fixes pixel tearing by providing high-res tiles on demand.
        """
        try:
            # 1. Load full image
            full_image = await self._get_full_image(image_url)
            if not full_image:
                return None
            
            width, height = full_image.size
            
            # 2. Calculate maxLevel
            import math
            max_level = math.ceil(math.log2(max(width, height)))
            
            # 3. Hash URL for cache key
            url_hash = hashlib.md5(image_url.encode()).hexdigest()
            cache_key = f"dyn:{url_hash}:{z}:{x}:{y}:e{enhance}:l{labels}:c{confidence_threshold}:q{quality}"
            
            # 4. Check cache
            if not self.cache_service.connected:
                await self.cache_service.initialize()
            
            cached_tile = await self.cache_service.get_tile(cache_key)
            if cached_tile:
                return cached_tile
            
            # 5. Calculate crop area based on OSD level system
            # OSD Deep Zoom Level 0 is the smallest (1x1 or close)
            # Max level is the full res image.
            # Scale at level z is 1 / 2^(max_level - z)
            scale = 2 ** (max_level - z)
            
            # Tile size in terms of full-res pixels
            full_res_tile_size = tile_size * scale
            
            left = x * full_res_tile_size
            top = y * full_res_tile_size
            right = min(left + full_res_tile_size, width)
            bottom = min(top + full_res_tile_size, height)
            
            if left >= width or top >= height or right <= left or bottom <= top:
                logger.debug(f"Tile out of bounds: {x},{y} at z={z} (scale {scale})")
                return None
            
            # Crop the high-res region
            tile_image = full_image.crop((int(left), int(top), int(right), int(bottom)))
            
            # Resize the cropped region to the requested tile size (or proportional)
            # This ensures OSD gets exactly what it expects for its grid
            target_w = int((right - left) / scale)
            target_h = int((bottom - top) / scale)
            
            # Safety check for tiny crops
            target_w = max(1, target_w)
            target_h = max(1, target_h)
            
            tile_image = tile_image.resize((target_w, target_h), Image.LANCZOS)
            
            # 6. Enhance
            if not self.ml_service.models_loaded:
                await self.ml_service.initialize_models()
                
            if enhance:
                # Apply enhancement to the tile
                tile_image = await self.ml_service.super_resolve(tile_image)
                tile_image = await self.ml_service.denoise(tile_image)
                # Keep it high quality
            
            if labels:
                tile_image = await self.ml_service.add_labels(tile_image, confidence_threshold)
            
            # 7. Save and Cache
            img_byte_arr = io.BytesIO()
            tile_image.save(img_byte_arr, format='JPEG', quality=quality)
            tile_data = img_byte_arr.getvalue()
            
            await self.cache_service.set_tile(cache_key, tile_data)
            return tile_data
            
        except Exception as e:
            logger.error(f"Error in dynamic tiling: {str(e)}")
            return None

    async def _get_full_image(self, url: str) -> Optional[Image.Image]:
        """Fetch and cache full source image in memory for tiling"""
        # 1. Attempt to resolve NASA thumbnails to originals
        actual_url = url
        if "nasa.gov" in url and ("~thumb" in url or "~mobile" in url):
            try:
                # Extract NASA ID from URL
                # e.g., https://.../image/PIA12345/PIA12345~thumb.jpg
                parts = url.split('/')
                nasa_id = None
                for i, part in enumerate(parts):
                    if part == 'image' and i + 1 < len(parts):
                        nasa_id = parts[i+1]
                        break
                
                if nasa_id:
                    logger.info(f"Resolving NASA original for {nasa_id}")
                    asset_resp = await self.http_client.get(f"https://images-api.nasa.gov/asset/{nasa_id}")
                    if asset_resp.status_code == 200:
                        assets = asset_resp.json()
                        links = [item['href'] for item in assets['collection']['items']]
                        # Prioritize ~orig.jpg
                        orig = next((l for l in links if "~orig" in l and l.lower().endswith(('.jpg', '.jpeg', '.png'))), None)
                        if orig:
                            actual_url = orig
                            logger.info(f"Resolved to original: {actual_url}")
            except Exception as e:
                logger.warning(f"Failed to resolve NASA original, using provided URL: {str(e)}")

        if actual_url in self.source_image_cache:
            return self.source_image_cache[actual_url]
        
        try:
            logger.info(f"Fetching full image from {actual_url}")
            # Use a more aggressive timeout for the individual image fetch
            # to prevent the whole tiling engine from hanging.
            response = await self.http_client.get(actual_url, timeout=10.0)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                # Convert to RGB if necessary
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                    
                # Keep only a few images in memory
                if len(self.source_image_cache) > 3:
                    self.source_image_cache.pop(next(iter(self.source_image_cache)))
                self.source_image_cache[actual_url] = image
                return image
            elif actual_url != url:
                # If we tried the original and it failed, fallback to the thumbnail
                logger.warning(f"Failed to fetch original, falling back to thumbnail: {url}")
                return await self._get_full_image(url)
            else:
                logger.error(f"Failed to fetch image: {response.status_code}")
                return None
        except httpx.TimeoutException:
            if actual_url != url:
                logger.warning(f"Timeout fetching original {actual_url}, falling back to thumbnail {url}")
                return await self._get_full_image(url)
            logger.error(f"Timeout fetching source image {actual_url}")
            return None
        except Exception as e:
            logger.error(f"Error fetching source image: {str(e)}")
            return None

    async def precompute_tiles(
        self,
        image_id: str,
        zoom_levels: List[int],
        enhance: bool = True
    ) -> Dict[str, Any]:
        """
        Placeholder for precomputing tiles for fixed zoom levels.
        """
        logger.info(f"Started precomputation for image {image_id}, zooms: {zoom_levels}")
        return {
            "status": "success",
            "message": "Precomputation task queued",
            "image_id": image_id,
            "processed_zooms": zoom_levels
        }

# Global instance
tile_service = TileService()
