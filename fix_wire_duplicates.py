#!/usr/bin/env python3
"""
Script to fix duplicate and quality issues with The Wire organization.
This script handles:
- Duplicate episodes (both .mkv and .mp4 versions)
- Better quality assessment when ffprobe fails
- Proper duplicate resolution
- File structure issues
"""

import re
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
import subprocess

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_wire_duplicates.log'),
        logging.StreamHandler()
    ]
)

def get_file_size(path: Path) -> int:
    """Get file size in bytes."""
    try:
        return path.stat().st_size
    except Exception:
        return 0

def get_video_quality(path: Path) -> Tuple[int, bool]:
    """Get video quality and playability, with fallback to file size."""
    try:
        # Try to get resolution using ffprobe
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', str(path)],
            capture_output=True, text=True, check=True, timeout=10
        )
        width, height = map(int, result.stdout.strip().split('x'))
        quality = width * height
        
        # Check if file is playable
        playable_result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
             '-of', 'default=noprint_wrappers=1:nokey=1', str(path)],
            capture_output=True, text=True, check=True, timeout=10
        )
        duration = float(playable_result.stdout.strip())
        playable = duration > 0
        
        return quality, playable
    except Exception as e:
        logging.warning(f"ffprobe failed for {path}: {e}")
        # Fallback to file size
        file_size = get_file_size(path)
        return file_size, True  # Assume playable if we can't check

def detect_episode_info(filename: str) -> Optional[Dict]:
    """Detect episode information from filename."""
    # Pattern to match S01E01, S1E1, etc.
    episode_pattern = r'S(\d{1,2})E(\d{1,2})'
    match = re.search(episode_pattern, filename, re.IGNORECASE)
    
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        
        # Extract episode title if present
        title_start = match.end()
        episode_title = filename[title_start:].strip()
        # Clean up episode title
        episode_title = re.sub(r'\.[^.]+$', '', episode_title)  # Remove extension
        episode_title = re.sub(r'^[_-]+', '', episode_title)  # Remove leading separators
        episode_title = re.sub(r'[_-]+$', '', episode_title)  # Remove trailing separators
        
        return {
            'season': season,
            'episode': episode,
            'title': episode_title if episode_title else None
        }
    return None

def find_duplicate_episodes(target_dir: str) -> Dict[str, List[Path]]:
    """Find duplicate episodes in The Wire directories."""
    target_path = Path(target_dir)
    duplicates = {}
    
    # Walk through TV Shows/The Wire directory
    wire_path = target_path / "TV Shows" / "The Wire"
    if not wire_path.exists():
        logging.warning(f"The Wire directory not found: {wire_path}")
        return duplicates
    
    # Scan all season directories
    for season_dir in wire_path.iterdir():
        if season_dir.is_dir() and season_dir.name.startswith("Season"):
            for file_path in season_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in ['.mkv', '.mp4']:
                    episode_info = detect_episode_info(file_path.name)
                    if episode_info:
                        key = f"S{episode_info['season']:02d}E{episode_info['episode']:02d}"
                        if key not in duplicates:
                            duplicates[key] = []
                        duplicates[key].append(file_path)
    
    # Filter to only episodes with duplicates
    return {k: v for k, v in duplicates.items() if len(v) > 1}

def resolve_duplicates(duplicates: Dict[str, List[Path]], dry_run: bool = True) -> None:
    """Resolve duplicate episodes by keeping the best version."""
    for episode_key, files in duplicates.items():
        logging.info(f"Processing duplicates for {episode_key}:")
        
        # Sort files by quality and playability
        file_qualities = []
        for file_path in files:
            quality, playable = get_video_quality(file_path)
            file_qualities.append({
                'path': file_path,
                'quality': quality,
                'playable': playable,
                'size': get_file_size(file_path)
            })
            logging.info(f"  {file_path.name}: quality={quality}, playable={playable}, size={file_path.stat().st_size}")
        
        # Sort by playability first, then quality, then size
        file_qualities.sort(key=lambda x: (not x['playable'], -x['quality'], -x['size']))
        
        # Keep the best file, remove the rest
        best_file = file_qualities[0]
        files_to_remove = file_qualities[1:]
        
        logging.info(f"  Keeping: {best_file['path'].name}")
        
        if not dry_run:
            for file_info in files_to_remove:
                try:
                    file_info['path'].unlink()
                    logging.info(f"  Removed: {file_info['path'].name}")
                except Exception as e:
                    logging.error(f"  Failed to remove {file_info['path'].name}: {e}")
        else:
            for file_info in files_to_remove:
                logging.info(f"  [DRY RUN] Would remove: {file_info['path'].name}")

def find_orphaned_files(target_dir: str) -> List[Path]:
    """Find files that are in the wrong location (e.g., in source directories)."""
    target_path = Path(target_dir)
    orphaned = []
    
    # Look for files in the original source structure
    source_patterns = [
        target_path / "The Wire" / "Season 1",
        target_path / "The Wire" / "The.Wire.S01.2160p.x265.10bit.DTS-HD.MA.5.1[TheUpscaler]",
        target_path / "The Wire" / "The.Wire.S02.2160p.x265.10bit.DTS-HD.MA.5.1[TheUpscaler]",
        target_path / "The Wire" / "The.Wire.S03.2160p.x265.10bit.DTS-HD.MA.5.1[TheUpscaler]",
        target_path / "The Wire" / "The.Wire.S05.2160p.x265.10bit.DTS-HD.MA.5.1[TheUpscaler]",
    ]
    
    for pattern in source_patterns:
        if pattern.exists():
            for file_path in pattern.rglob("*.mkv"):
                if file_path.is_file():
                    orphaned.append(file_path)
            for file_path in pattern.rglob("*.mp4"):
                if file_path.is_file():
                    orphaned.append(file_path)
    
    return orphaned

def fix_wire_organization(target_dir: str, dry_run: bool = True) -> None:
    """Main function to fix The Wire organization issues."""
    logging.info(f"Starting Wire organization fix for: {target_dir}")
    logging.info(f"Dry run mode: {dry_run}")
    
    # 1. Find and resolve duplicate episodes
    duplicates = find_duplicate_episodes(target_dir)
    if duplicates:
        logging.info(f"Found {len(duplicates)} episodes with duplicates")
        resolve_duplicates(duplicates, dry_run)
    else:
        logging.info("No duplicate episodes found")
    
    # 2. Find orphaned files
    orphaned = find_orphaned_files(target_dir)
    if orphaned:
        logging.info(f"Found {len(orphaned)} orphaned files")
        for file_path in orphaned:
            logging.info(f"  Orphaned: {file_path}")
            if not dry_run:
                try:
                    file_path.unlink()
                    logging.info(f"  Removed orphaned file: {file_path}")
                except Exception as e:
                    logging.error(f"  Failed to remove {file_path}: {e}")
            else:
                logging.info(f"  [DRY RUN] Would remove orphaned file: {file_path}")
    else:
        logging.info("No orphaned files found")
    
    # 3. Clean up empty directories
    if not dry_run:
        cleanup_empty_dirs(Path(target_dir))
    
    logging.info("Wire organization fix completed.")

def cleanup_empty_dirs(root: Path):
    """Recursively remove empty directories."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        if not any(path.iterdir()):
            try:
                path.rmdir()
                logging.info(f"Removed empty directory: {path}")
            except Exception as e:
                logging.warning(f"Failed to remove {path}: {e}")

def main():
    """Main function with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix The Wire organization issues')
    parser.add_argument('target_dir', help='Target directory containing TV Shows folder')
    parser.add_argument('--execute', action='store_true', help='Actually execute the fixes (default is dry-run)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target_dir):
        logging.error(f"Target directory does not exist: {args.target_dir}")
        return
    
    fix_wire_organization(args.target_dir, dry_run=not args.execute)

if __name__ == "__main__":
    main() 