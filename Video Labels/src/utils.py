import re
from pathlib import Path
import subprocess
from typing import Optional
import logging
import hashlib

def clean_filename(name: str) -> str:
    """Clean filename by replacing forbidden characters.
    
    Args:
        name: Original name.
    
    Returns:
        Cleaned name.
    
    Examples:
        >>> clean_filename('bad:name?*')
        'bad-name--'
    """
    forbidden = r'[<>:\"|?*/]'
    return re.sub(forbidden, '-', name).strip()

def get_quality(path: Path) -> int:
    """Get video quality metric (resolution area or file size fallback).
    
    Args:
        path: File path.
    
    Returns:
        Quality score.
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(path)],
            capture_output=True, text=True, check=True
        )
        width, height = map(int, result.stdout.strip().split('x'))
        return width * height
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError):
        logging.warning(f"ffprobe failed for {path}; using file size.")
        return path.stat().st_size 

def get_file_hash(path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of a file for duplicate detection."""
    hasher = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(chunk_size):
            hasher.update(chunk)
    return hasher.hexdigest()


def is_file_playable(path: Path) -> bool:
    """Check if a video file is playable using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            capture_output=True, text=True, check=True
        )
        duration = float(result.stdout.strip())
        return duration > 0
    except Exception:
        return False


def get_video_duration(path: Path) -> float:
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            capture_output=True, text=True, check=True
        )
        return float(result.stdout.strip())
    except Exception:
        return 0.0 