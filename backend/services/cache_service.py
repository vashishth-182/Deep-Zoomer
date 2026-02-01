import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Any
import hashlib
import pickle

from ..config import settings

logger = logging.getLogger(__name__)

class CacheService:
    def __init__(self):
        self.redis_client = None
        self.connected = False
        self.memory_cache = {} # Fallback for when Redis is unavailable
        
    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            self.connected = True
            logger.info("Cache service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing cache service: {str(e)}")
            self.connected = False
    
    async def get_tile(self, cache_key: str) -> Optional[bytes]:
        """Get tile from cache (Redis or Memory fallback)"""
        try:
            if self.connected:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    return cached_data
            
            # Memory fallback
            return self.memory_cache.get(cache_key)
            
        except Exception as e:
            logger.error(f"Error getting tile from cache: {str(e)}")
            return self.memory_cache.get(cache_key)
    
    async def set_tile(self, cache_key: str, tile_data: bytes, ttl: int = None):
        """Set tile in cache (Redis and/or Memory fallback)"""
        try:
            # Memory fallback
            self.memory_cache[cache_key] = tile_data
            if len(self.memory_cache) > 200: # Simple LRU-ish cleanup
                self.memory_cache.pop(next(iter(self.memory_cache)))

            if self.connected:
                ttl = ttl or settings.cache_ttl
                await self.redis_client.setex(cache_key, ttl, tile_data)
            
        except Exception as e:
            logger.error(f"Error setting tile in cache: {str(e)}")
    
    async def get_metadata(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get metadata from cache"""
        try:
            if not self.connected:
                return None
            
            cached_data = await self.redis_client.get(f"meta:{cache_key}")
            if cached_data:
                return json.loads(cached_data)
            return None
            
        except Exception as e:
            logger.error(f"Error getting metadata from cache: {str(e)}")
            return None
    
    async def set_metadata(self, cache_key: str, metadata: Dict[str, Any], ttl: int = None):
        """Set metadata in cache"""
        try:
            if not self.connected:
                return
            
            ttl = ttl or settings.cache_ttl
            await self.redis_client.setex(
                f"meta:{cache_key}", 
                ttl, 
                json.dumps(metadata)
            )
            
        except Exception as e:
            logger.error(f"Error setting metadata in cache: {str(e)}")
    
    async def invalidate_tile(self, image_id: str, z: int, x: int, y: int):
        """Invalidate specific tile cache"""
        try:
            if not self.connected:
                return
            
            # Generate pattern for all variations of this tile
            pattern = f"{image_id}:{z}:{x}:{y}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for tile {image_id}/{z}/{x}/{y}")
                
        except Exception as e:
            logger.error(f"Error invalidating tile cache: {str(e)}")
    
    async def invalidate_image(self, image_id: str):
        """Invalidate all tiles for an image"""
        try:
            if not self.connected:
                return
            
            pattern = f"{image_id}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for image {image_id}")
                
        except Exception as e:
            logger.error(f"Error invalidating image cache: {str(e)}")
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            if not self.connected:
                return {"status": "disconnected"}
            
            info = await self.redis_client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0)
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"status": "error", "error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache service health"""
        try:
            if not self.connected:
                return {"status": "disconnected"}
            
            await self.redis_client.ping()
            return {"status": "healthy"}
            
        except Exception as e:
            logger.error(f"Cache health check failed: {str(e)}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Close Redis connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.connected = False
                logger.info("Cache service closed")
        except Exception as e:
            logger.error(f"Error closing cache service: {str(e)}")

# Global instance
cache_service = CacheService()
