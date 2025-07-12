"""
Cached utility functions for Video Labels Organizer.

This module provides cached versions of expensive operations like:
- ffprobe metadata extraction
- Quality assessments
- File hash calculations
- AI classifications

All functions integrate with the MetadataCache system for performance optimization.
"""

import subprocess
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
import time

from .metadata_cache import get_global_cache, MetadataCache
from .logger import logging as logger


def get_cached_quality(path: Path, cache: Optional[MetadataCache] = None) -> int:
    """
    Get video quality metric with caching.
    
    Args:
        path: File path
        cache: Optional cache instance (uses global cache if None)
        
    Returns:
        Quality score (resolution area or file size fallback)
    """
    if cache is None:
        cache = get_global_cache()
    
    # Try to get from cache first
    cached = cache.get_metadata(path, "quality")
    if cached is not None:
        return cached.get('quality', 0)
    
    # Extract quality information
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(path)],
            capture_output=True, text=True, check=True, timeout=30
        )
        width, height = map(int, result.stdout.strip().split('x'))
        quality = width * height
        
        # Cache the result
        cache.set_metadata(path, {'quality': quality, 'width': width, 'height': height}, "quality")
        
        return quality
        
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, subprocess.TimeoutExpired):
        # Fallback to file size
        quality = path.stat().st_size
        cache.set_metadata(path, {'quality': quality, 'method': 'file_size'}, "quality")
        logger.warning(f"ffprobe failed for {path}; using file size.")
        return quality


def get_cached_file_hash(path: Path, chunk_size: int = 8192, cache: Optional[MetadataCache] = None) -> str:
    """
    Compute SHA256 hash of a file with caching.
    
    Args:
        path: File path
        chunk_size: Chunk size for reading
        cache: Optional cache instance
        
    Returns:
        SHA256 hash string
    """
    if cache is None:
        cache = get_global_cache()
    
    # Try to get from cache first
    cached = cache.get_metadata(path, "hash")
    if cached is not None:
        return cached.get('hash', '')
    
    # Calculate hash
    try:
        hasher = hashlib.sha256()
        with open(path, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()
        
        # Cache the result
        cache.set_metadata(path, {'hash': file_hash}, "hash")
        
        return file_hash
        
    except Exception as e:
        logger.error(f"Error calculating hash for {path}: {e}")
        return ""


def is_cached_file_playable(path: Path, cache: Optional[MetadataCache] = None) -> bool:
    """
    Check if a video file is playable with caching.
    
    Args:
        path: File path
        cache: Optional cache instance
        
    Returns:
        True if file is playable
    """
    if cache is None:
        cache = get_global_cache()
    
    # Try to get from cache first
    cached = cache.get_metadata(path, "playable")
    if cached is not None:
        return cached.get('playable', False)
    
    # Check playability
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            capture_output=True, text=True, check=True, timeout=30
        )
        duration = float(result.stdout.strip())
        playable = duration > 0
        
        # Cache the result
        cache.set_metadata(path, {'playable': playable, 'duration': duration}, "playable")
        
        return playable
        
    except Exception as e:
        logger.error(f"Error checking playability for {path}: {e}")
        cache.set_metadata(path, {'playable': False, 'error': str(e)}, "playable")
        return False


def get_cached_video_duration(path: Path, cache: Optional[MetadataCache] = None) -> float:
    """
    Get video duration with caching.
    
    Args:
        path: File path
        cache: Optional cache instance
        
    Returns:
        Duration in seconds
    """
    if cache is None:
        cache = get_global_cache()
    
    # Try to get from cache first
    cached = cache.get_metadata(path, "duration")
    if cached is not None:
        return cached.get('duration', 0.0)
    
    # Get duration
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            capture_output=True, text=True, check=True, timeout=30
        )
        duration = float(result.stdout.strip())
        
        # Cache the result
        cache.set_metadata(path, {'duration': duration}, "duration")
        
        return duration
        
    except Exception as e:
        logger.error(f"Error getting duration for {path}: {e}")
        cache.set_metadata(path, {'duration': 0.0, 'error': str(e)}, "duration")
        return 0.0


def get_comprehensive_metadata(path: Path, cache: Optional[MetadataCache] = None) -> Dict[str, Any]:
    """
    Get comprehensive metadata for a video file in a single ffprobe call.
    
    Args:
        path: File path
        cache: Optional cache instance
        
    Returns:
        Dictionary with all metadata (duration, quality, playable, etc.)
    """
    if cache is None:
        cache = get_global_cache()
    
    # Try to get from cache first
    cached = cache.get_metadata(path, "comprehensive")
    if cached is not None:
        return cached
    
    # Extract comprehensive metadata
    try:
        cmd = [
            'ffprobe', '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,duration',
            '-show_entries', 'format=duration,size',
            '-of', 'json',
            str(path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
        data = json.loads(result.stdout)
        
        streams = data.get('streams', [])
        format_info = data.get('format', {})
        
        # Extract video stream info
        width = height = duration = None
        if streams:
            stream = streams[0]
            width = stream.get('width')
            height = stream.get('height')
            duration = stream.get('duration')
        
        # Fallback to format duration
        if not duration:
            duration = format_info.get('duration')
        
        # Calculate quality and playability
        quality = (width * height) if width and height else path.stat().st_size
        playable = duration is not None and float(duration) > 0
        file_size = format_info.get('size')
        
        metadata = {
            'duration': float(duration) if duration else 0.0,
            'quality': quality,
            'playable': playable,
            'width': width,
            'height': height,
            'file_size': file_size,
            'path': str(path)
        }
        
        # Cache the result
        cache.set_metadata(path, metadata, "comprehensive")
        
        return metadata
        
    except Exception as e:
        logger.error(f"Error extracting comprehensive metadata for {path}: {e}")
        # Fallback metadata
        fallback_metadata = {
            'duration': 0.0,
            'quality': path.stat().st_size,
            'playable': False,
            'error': str(e),
            'path': str(path)
        }
        cache.set_metadata(path, fallback_metadata, "comprehensive")
        return fallback_metadata


def batch_get_metadata(file_paths: List[Path], cache: Optional[MetadataCache] = None) -> Dict[Path, Dict[str, Any]]:
    """
    Get metadata for multiple files with caching optimization.
    
    Args:
        file_paths: List of file paths
        cache: Optional cache instance
        
    Returns:
        Dictionary mapping file paths to metadata
    """
    if cache is None:
        cache = get_global_cache()
    
    results = {}
    
    for file_path in file_paths:
        # Try cache first
        cached = cache.get_metadata(file_path, "comprehensive")
        if cached is not None:
            results[file_path] = cached
        else:
            # Extract fresh metadata
            metadata = get_comprehensive_metadata(file_path, cache)
            results[file_path] = metadata
    
    return results


def cache_ai_classification(file_path: Path, ai_metadata: Dict[str, Any], cache: Optional[MetadataCache] = None) -> bool:
    """
    Cache AI classification results.
    
    Args:
        file_path: File path
        ai_metadata: AI analysis results
        cache: Optional cache instance
        
    Returns:
        True if successfully cached
    """
    if cache is None:
        cache = get_global_cache()
    
    return cache.set_metadata(file_path, ai_metadata, "ai", ttl=86400)  # 24 hour TTL


def get_cached_ai_classification(file_path: Path, cache: Optional[MetadataCache] = None) -> Optional[Dict[str, Any]]:
    """
    Get cached AI classification results.
    
    Args:
        file_path: File path
        cache: Optional cache instance
        
    Returns:
        Cached AI metadata or None
    """
    if cache is None:
        cache = get_global_cache()
    
    return cache.get_metadata(file_path, "ai")


def invalidate_file_cache(file_path: Path, cache: Optional[MetadataCache] = None) -> int:
    """
    Invalidate all cached entries for a file.
    
    Args:
        file_path: File path
        cache: Optional cache instance
        
    Returns:
        Number of entries removed
    """
    if cache is None:
        cache = get_global_cache()
    
    return cache.invalidate_file(file_path)


def get_cache_stats(cache: Optional[MetadataCache] = None) -> Dict[str, Any]:
    """
    Get cache performance statistics.
    
    Args:
        cache: Optional cache instance
        
    Returns:
        Cache statistics dictionary
    """
    if cache is None:
        cache = get_global_cache()
    
    return cache.get_stats()


def export_cache_stats(file_path: Optional[Path] = None, cache: Optional[MetadataCache] = None) -> None:
    """
    Export cache statistics to JSON file.
    
    Args:
        file_path: Output file path (optional)
        cache: Optional cache instance
    """
    if cache is None:
        cache = get_global_cache()
    
    cache.export_stats(file_path)


# Performance monitoring decorator
def monitor_cache_performance(func):
    """Decorator to monitor cache performance for functions."""
    def wrapper(*args, **kwargs):
        cache = get_global_cache()
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            
            # Log performance
            elapsed = time.time() - start_time
            stats = cache.get_stats()
            logger.debug(f"{func.__name__} completed in {elapsed:.3f}s, cache hit rate: {stats['hit_rate']:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            raise
    
    return wrapper


# Example usage with performance monitoring
@monitor_cache_performance
def get_optimized_metadata(file_path: Path) -> Dict[str, Any]:
    """
    Get optimized metadata with caching and performance monitoring.
    
    Args:
        file_path: File path
        
    Returns:
        Comprehensive metadata dictionary
    """
    return get_comprehensive_metadata(file_path) 