from pathlib import Path
from typing import List
from config import VIDEO_EXTENSIONS

def scan_videos(directory: str) -> List[Path]:
    """Recursively scan for video files.
    
    Args:
        directory: Source directory.
    
    Returns:
        List of video file paths.
    
    Raises:
        ValueError: If directory invalid.
    """
    path = Path(directory)
    if not path.is_dir():
        raise ValueError(f"Invalid directory: {directory}")
    return [f for f in path.rglob('*') if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS] 