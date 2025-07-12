"""
Comprehensive metadata caching system for Video Labels Organizer.

This module provides intelligent caching for expensive operations like:
- ffprobe metadata extraction
- Quality assessments
- AI classifications
- File hash calculations

Features:
- File signature-based cache invalidation
- Thread-safe operations
- LRU eviction with size limits
- Graceful error handling and fallbacks
- Cache statistics and monitoring
"""

import hashlib
import pickle
import threading
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union, List
from dataclasses import dataclass, asdict
from collections import OrderedDict
import logging
import json
import subprocess

from .logger import logging as logger


@dataclass
class CacheEntry:
    """Represents a cached metadata entry."""
    file_signature: str
    metadata: Dict[str, Any]
    timestamp: float
    access_count: int = 0
    last_accessed: float = 0.0


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    errors: int = 0
    total_entries: int = 0
    cache_size_bytes: int = 0
    last_cleanup: float = 0.0


class MetadataCache:
    """
    Thread-safe metadata cache with file signature invalidation.
    
    Features:
    - MD5-based file signatures (path + size + mtime)
    - LRU eviction with configurable size limits
    - Automatic cache persistence
    - Comprehensive error handling
    - Performance monitoring
    """
    
    def __init__(
        self,
        cache_file: str = ".video_labels_cache.pkl",
        max_size_mb: int = 10,
        cleanup_interval: int = 3600,  # 1 hour
        enable_persistence: bool = True
    ):
        """
        Initialize the metadata cache.
        
        Args:
            cache_file: Cache file path
            max_size_mb: Maximum cache size in MB
            cleanup_interval: Cache cleanup interval in seconds
            enable_persistence: Whether to persist cache to disk
        """
        self.cache_file = Path(cache_file)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.cleanup_interval = cleanup_interval
        self.enable_persistence = enable_persistence
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Cache storage (OrderedDict for LRU)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Statistics
        self._stats = CacheStats()
        
        # Load existing cache
        self._load_cache()
        
        # Schedule cleanup
        self._last_cleanup = time.time()
        
        logger.info(f"MetadataCache initialized: max_size={max_size_mb}MB, cache_file={cache_file}")
    
    def _generate_file_signature(self, file_path: Path) -> str:
        """
        Generate MD5 signature for file based on path, size, and modification time.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash string
        """
        try:
            stat = file_path.stat()
            signature_data = f"{file_path}:{stat.st_size}:{stat.st_mtime_ns}"
            return hashlib.md5(signature_data.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to generate signature for {file_path}: {e}")
            # Fallback to path-only signature
            return hashlib.md5(str(file_path).encode('utf-8')).hexdigest()
    
    def _load_cache(self) -> None:
        """Load cache from disk with error handling."""
        if not self.enable_persistence or not self.cache_file.exists():
            return
        
        try:
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                
            if isinstance(data, dict) and 'cache' in data and 'stats' in data:
                self._cache = OrderedDict(data['cache'])
                self._stats = CacheStats(**data['stats'])
                logger.info(f"Loaded cache: {len(self._cache)} entries, {self._stats.hits} hits")
            else:
                logger.warning("Invalid cache file format, starting fresh")
                
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            # Backup corrupted cache file
            backup_file = self.cache_file.with_suffix('.bak')
            try:
                self.cache_file.rename(backup_file)
                logger.info(f"Backed up corrupted cache to {backup_file}")
            except Exception:
                pass
    
    def _save_cache(self) -> None:
        """Save cache to disk with error handling."""
        if not self.enable_persistence:
            return
        
        try:
            # Prepare data for serialization
            cache_data = dict(self._cache)
            stats_data = asdict(self._stats)
            
            data = {
                'cache': cache_data,
                'stats': stats_data,
                'version': '1.0',
                'timestamp': time.time()
            }
            
            # Write to temporary file first
            temp_file = self.cache_file.with_suffix('.tmp')
            with open(temp_file, 'wb') as f:
                pickle.dump(data, f)
            
            # Atomic move
            temp_file.replace(self.cache_file)
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _cleanup_cache(self) -> None:
        """Remove expired entries and enforce size limits."""
        current_time = time.time()
        
        # Check if cleanup is needed
        if current_time - self._last_cleanup < self.cleanup_interval:
            return
        
        self._last_cleanup = current_time
        
        # Calculate current cache size
        cache_size = sum(len(pickle.dumps(entry)) for entry in self._cache.values())
        
        # Remove entries if cache is too large
        while cache_size > self.max_size_bytes and self._cache:
            # Remove least recently used entry
            _, entry = self._cache.popitem(last=False)
            cache_size -= len(pickle.dumps(entry))
            self._stats.evictions += 1
        
        # Update statistics
        self._stats.total_entries = len(self._cache)
        self._stats.cache_size_bytes = cache_size
        self._stats.last_cleanup = current_time
        
        logger.debug(f"Cache cleanup: {len(self._cache)} entries, {cache_size} bytes")
    
    def get_metadata(self, file_path: Path, metadata_type: str = "general") -> Optional[Dict[str, Any]]:
        """
        Get cached metadata for a file.
        
        Args:
            file_path: Path to the file
            metadata_type: Type of metadata (general, quality, ai, etc.)
            
        Returns:
            Cached metadata or None if not found/invalid
        """
        with self._lock:
            try:
                # Generate file signature
                signature = self._generate_file_signature(file_path)
                
                # Check if file still exists
                if not file_path.exists():
                    return None
                
                # Look up in cache
                cache_key = f"{signature}:{metadata_type}"
                entry = self._cache.get(cache_key)
                
                if entry is None:
                    self._stats.misses += 1
                    return None
                
                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = time.time()
                
                # Move to end (LRU)
                self._cache.move_to_end(cache_key)
                
                self._stats.hits += 1
                logger.debug(f"Cache hit for {file_path} ({metadata_type})")
                
                return entry.metadata.copy()
                
            except Exception as e:
                self._stats.errors += 1
                logger.error(f"Error getting metadata for {file_path}: {e}")
                return None
    
    def set_metadata(
        self,
        file_path: Path,
        metadata: Dict[str, Any],
        metadata_type: str = "general",
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache metadata for a file.
        
        Args:
            file_path: Path to the file
            metadata: Metadata to cache
            metadata_type: Type of metadata
            ttl: Time to live in seconds (None = no expiration)
            
        Returns:
            True if successfully cached
        """
        with self._lock:
            try:
                # Generate file signature
                signature = self._generate_file_signature(file_path)
                
                # Check TTL if specified
                if ttl is not None:
                    metadata['_expires_at'] = time.time() + ttl
                
                # Create cache entry
                entry = CacheEntry(
                    file_signature=signature,
                    metadata=metadata,
                    timestamp=time.time(),
                    access_count=1,
                    last_accessed=time.time()
                )
                
                # Store in cache
                cache_key = f"{signature}:{metadata_type}"
                self._cache[cache_key] = entry
                
                # Move to end (LRU)
                self._cache.move_to_end(cache_key)
                
                # Cleanup if needed
                self._cleanup_cache()
                
                # Save to disk
                self._save_cache()
                
                logger.debug(f"Cached metadata for {file_path} ({metadata_type})")
                return True
                
            except Exception as e:
                self._stats.errors += 1
                logger.error(f"Error caching metadata for {file_path}: {e}")
                return False
    
    def invalidate_file(self, file_path: Path) -> int:
        """
        Invalidate all cached entries for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Number of entries removed
        """
        with self._lock:
            try:
                signature = self._generate_file_signature(file_path)
                removed_count = 0
                
                # Remove all entries for this file
                keys_to_remove = [
                    key for key in self._cache.keys()
                    if key.startswith(f"{signature}:")
                ]
                
                for key in keys_to_remove:
                    del self._cache[key]
                    removed_count += 1
                
                if removed_count > 0:
                    self._save_cache()
                    logger.debug(f"Invalidated {removed_count} entries for {file_path}")
                
                return removed_count
                
            except Exception as e:
                logger.error(f"Error invalidating cache for {file_path}: {e}")
                return 0
    
    def clear_cache(self) -> int:
        """
        Clear all cached entries.
        
        Returns:
            Number of entries removed
        """
        with self._lock:
            try:
                count = len(self._cache)
                self._cache.clear()
                self._stats = CacheStats()
                
                # Remove cache file
                if self.cache_file.exists():
                    self.cache_file.unlink()
                
                logger.info(f"Cleared cache: {count} entries removed")
                return count
                
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        with self._lock:
            stats = asdict(self._stats)
            stats.update({
                'hit_rate': self._stats.hits / (self._stats.hits + self._stats.misses) if (self._stats.hits + self._stats.misses) > 0 else 0,
                'total_entries': len(self._cache),
                'cache_size_mb': self._stats.cache_size_bytes / (1024 * 1024),
                'max_size_mb': self.max_size_bytes / (1024 * 1024)
            })
            return stats
    
    def export_stats(self, file_path: Optional[Path] = None) -> None:
        """Export cache statistics to JSON file."""
        stats = self.get_stats()
        
        if file_path is None:
            file_path = Path("cache_stats.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(stats, f, indent=2)
            logger.info(f"Cache statistics exported to {file_path}")
        except Exception as e:
            logger.error(f"Failed to export cache statistics: {e}")


# Convenience functions for common metadata types
def cache_ffprobe_metadata(cache: MetadataCache, file_path: Path, metadata: Dict[str, Any]) -> bool:
    """Cache ffprobe metadata."""
    return cache.set_metadata(file_path, metadata, "ffprobe")

def get_cached_ffprobe_metadata(cache: MetadataCache, file_path: Path) -> Optional[Dict[str, Any]]:
    """Get cached ffprobe metadata."""
    return cache.get_metadata(file_path, "ffprobe")

def cache_ai_metadata(cache: MetadataCache, file_path: Path, metadata: Dict[str, Any]) -> bool:
    """Cache AI analysis metadata."""
    return cache.set_metadata(file_path, metadata, "ai")

def get_cached_ai_metadata(cache: MetadataCache, file_path: Path) -> Optional[Dict[str, Any]]:
    """Get cached AI analysis metadata."""
    return cache.get_metadata(file_path, "ai")

def cache_quality_metadata(cache: MetadataCache, file_path: Path, metadata: Dict[str, Any]) -> bool:
    """Cache quality assessment metadata."""
    return cache.set_metadata(file_path, metadata, "quality")

def get_cached_quality_metadata(cache: MetadataCache, file_path: Path) -> Optional[Dict[str, Any]]:
    """Get cached quality assessment metadata."""
    return cache.get_metadata(file_path, "quality")


# Global cache instance
_global_cache: Optional[MetadataCache] = None
_cache_lock = threading.Lock()


def get_global_cache() -> MetadataCache:
    """Get or create global cache instance."""
    global _global_cache
    
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = MetadataCache()
    
    return _global_cache


def clear_global_cache() -> int:
    """Clear the global cache."""
    global _global_cache
    
    if _global_cache is not None:
        return _global_cache.clear_cache()
    return 0 