from pathlib import Path
from typing import List, Dict, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from file_scanner import scan_videos
from gemini_client import identify_media_batch
from utils import clean_filename, get_quality, get_file_hash, is_file_playable
from logger import logging, log_operation
from config import MAX_WORKERS
from extras_detector import classify_extra
from utils import get_video_duration
import os
import re

def get_proposed_changes(source: str, target: str, progress_callback: Optional[Callable[[int], None]] = None) -> List[Dict]:
    """Get proposed changes without executing them.
    
    Args:
        source: Source directory.
        target: Target directory.
        progress_callback: Function to update progress (int percent).
    
    Returns:
        List of proposed changes with metadata.
    """
    try:
        files: List[Path] = scan_videos(source)
        total = len(files)
        if total == 0:
            logging.info("No videos found.")
            return []
        
        # Update progress for scanning
        if progress_callback:
            progress_callback(10)
        
        # Extract filenames for batch processing
        filenames = [file.name for file in files]
        
        # Single batch request to AI for all files
        logging.info(f"Analyzing {len(filenames)} files in batch...")
        metadatas = identify_media_batch(filenames)
        
        # Update progress after AI analysis
        if progress_callback:
            progress_callback(50)
        
        # Generate proposed changes
        proposed_changes = []
        processed = 0
        
        for file, meta in zip(files, metadatas):
            # --- Extra content detection ---
            duration = get_video_duration(file)
            extra_info = classify_extra(file, duration)
            # --- TV/movie distinction improvement ---
            filename = file.name
            folder = file.parent.name
            # Try to classify by pattern first
            tv_patterns = [
                r"S\d{1,2}E\d{1,2}",  # S01E01
                r"Season[ ._-]?\d{1,2}",
                r"Episode[ ._-]?\d{1,2}",
                r"\d{1,2}x\d{1,2}",  # 1x01
            ]
            movie_patterns = [
                r"\(\d{4}\)",  # (2020)
                r"\d{4}[ ._-]1080p",  # 2020 1080p
                r"\d{4}[ ._-]720p",
            ]
            is_tv = any(re.search(p, filename, re.IGNORECASE) or re.search(p, folder, re.IGNORECASE) for p in tv_patterns)
            is_movie = any(re.search(p, filename, re.IGNORECASE) or re.search(p, folder, re.IGNORECASE) for p in movie_patterns)
            # If AI/ML disagrees with pattern, log ambiguity
            if meta['type'] == 'unknown':
                if is_tv:
                    meta['type'] = 'tv'
                    logging.info(f"Pattern-based override: {file} classified as TV (was unknown)")
                elif is_movie:
                    meta['type'] = 'movie'
                    logging.info(f"Pattern-based override: {file} classified as Movie (was unknown)")
                else:
                    logging.warning(f"Ambiguous file needs user input: {file}")
                    meta['needs_user_input'] = True
            else:
                if is_tv and meta['type'] != 'tv':
                    logging.warning(f"Ambiguity: {file} pattern looks like TV but AI/ML says {meta['type']}")
                if is_movie and meta['type'] != 'movie':
                    logging.warning(f"Ambiguity: {file} pattern looks like Movie but AI/ML says {meta['type']}")
            # --- End TV/movie distinction improvement ---
            
            if meta['type'] == 'unknown':
                logging.warning(f"Skipping unknown: {file}")
                processed += 1
                if progress_callback:
                    progress_callback(50 + int((processed / total) * 40))
                continue
            
            # Only process as main content if NOT classified as extra
            clean_show = clean_filename(meta['name'])
            if meta['type'] == 'movie':
                year = meta.get('year', '')
                name = f"{clean_show} ({year})" if year else clean_show
                new_dir = Path(target) / "Movies" / name
                new_file = new_dir / f"{name}{file.suffix}"
                episode_info = f"Movie ({year})" if year else "Movie"
            else:  # tv
                ep_str = f"S{meta.get('season', 0):02d}E{meta['episode']:02d}"
                episode_title = meta.get('episode_title')
                title = f" - {clean_filename(episode_title)}" if episode_title and episode_title.strip() else ""
                new_filename = f"{clean_show} - {ep_str}{title}{file.suffix}"
                
                # Only treat as special if explicitly marked AND not already classified as extra
                if meta.get('is_special', False) and not (extra_info and extra_info['is_extra']):
                    new_dir = Path(target) / "TV Shows" / "Specials"
                    episode_info = f"Special {ep_str}"
                else:
                    season_str = f"Season {meta.get('season', 1):02d}"
                    new_dir = Path(target) / "TV Shows" / clean_show / season_str
                    episode_info = f"Season {meta.get('season', 1)} Episode {meta['episode']}"
                    if episode_title and episode_title.strip():
                        episode_info += f" - {episode_title}"
                
                new_file = new_dir / new_filename
            
            proposed_changes.append({
                'original': str(file),
                'new_path': str(new_file),
                'show_name': clean_show,
                'episode_info': episode_info,
                'type': meta['type'],
                'metadata': meta
            })
            
            processed += 1
            if progress_callback:
                progress_callback(50 + int((processed / total) * 40))
        
        # Final progress update
        if progress_callback:
            progress_callback(100)
        
        return proposed_changes
        
    except Exception as e:
        logging.error(f"Error getting proposed changes: {e}")
        raise

def remove_empty_dirs(root: Path, preserve: List[str] = ["Extras"]):
    """Recursively remove empty directories, preserving important ones."""
    for dirpath, dirnames, filenames in os.walk(root, topdown=False):
        path = Path(dirpath)
        # Skip preserved directories
        if path.name in preserve:
            continue
        # If directory is empty
        if not any(Path(dirpath).iterdir()):
            try:
                path.rmdir()
                logging.info(f"Removed empty directory: {path}")
            except Exception as e:
                logging.warning(f"Failed to remove {path}: {e}")

def organize_files(source: str, target: str, dry_run: bool = True, progress_callback: Optional[Callable[[int], None]] = None) -> None:
    """Organize video files into media server structure.
    
    Args:
        source: Source directory.
        target: Target directory.
        dry_run: If True, preview only.
        progress_callback: Function to update progress (int percent).
    """
    try:
        files: List[Path] = scan_videos(source)
        total = len(files)
        if total == 0:
            logging.info("No videos found.")
            return
        
        # Update progress for scanning
        if progress_callback:
            progress_callback(10)
        
        # Extract filenames for batch processing
        filenames = [file.name for file in files]
        
        # Single batch request to AI for all files
        logging.info(f"Analyzing {len(filenames)} files in batch...")
        metadatas = identify_media_batch(filenames)
        
        # Update progress after AI analysis
        if progress_callback:
            progress_callback(50)
        
        # Process results
        processed = 0
        # Track extras for numbering
        extras_counter = {}
        for file, meta in zip(files, metadatas):
            # --- Extra content detection ---
            duration = get_video_duration(file)
            extra_info = classify_extra(file, duration)
            # --- TV/movie distinction improvement ---
            filename = file.name
            folder = file.parent.name
            # Try to classify by pattern first
            tv_patterns = [
                r"S\d{1,2}E\d{1,2}",  # S01E01
                r"Season[ ._-]?\d{1,2}",
                r"Episode[ ._-]?\d{1,2}",
                r"\d{1,2}x\d{1,2}",  # 1x01
            ]
            movie_patterns = [
                r"\(\d{4}\)",  # (2020)
                r"\d{4}[ ._-]1080p",  # 2020 1080p
                r"\d{4}[ ._-]720p",
            ]
            is_tv = any(re.search(p, filename, re.IGNORECASE) or re.search(p, folder, re.IGNORECASE) for p in tv_patterns)
            is_movie = any(re.search(p, filename, re.IGNORECASE) or re.search(p, folder, re.IGNORECASE) for p in movie_patterns)
            # If AI/ML disagrees with pattern, log ambiguity
            if meta['type'] == 'unknown':
                if is_tv:
                    meta['type'] = 'tv'
                    logging.info(f"Pattern-based override: {file} classified as TV (was unknown)")
                elif is_movie:
                    meta['type'] = 'movie'
                    logging.info(f"Pattern-based override: {file} classified as Movie (was unknown)")
                else:
                    logging.warning(f"Ambiguous file needs user input: {file}")
                    meta['needs_user_input'] = True
            else:
                if is_tv and meta['type'] != 'tv':
                    logging.warning(f"Ambiguity: {file} pattern looks like TV but AI/ML says {meta['type']}")
                if is_movie and meta['type'] != 'movie':
                    logging.warning(f"Ambiguity: {file} pattern looks like Movie but AI/ML says {meta['type']}")
            # --- End TV/movie distinction improvement ---
            
            if extra_info and extra_info['is_extra']:
                show_name = meta.get('name') or file.parent.parent.name
                season = meta.get('season') if 'season' in meta else None
                clean_show = clean_filename(show_name)
                extra_type = clean_filename(extra_info['extra_type'])
                output_base = clean_filename(extra_info.get('output_base', extra_type))
                key = (clean_show, season, extra_type)
                extras_counter[key] = extras_counter.get(key, 0) + 1
                number = extras_counter[key]
                if season:
                    season_str = f"Season {season:02d}"
                    extras_dir = Path(target) / "TV Shows" / clean_show / season_str / "Extras"
                    base_name = f"{clean_show} - S{season:02d} - {output_base}"
                    logging.info(f"[MOVE] Placing extra/featurette: {file} -> {extras_dir} (show: {clean_show}, season: {season}, type: {extra_type})")
                else:
                    extras_dir = Path(target) / "TV Shows" / clean_show / "Extras"
                    base_name = f"{clean_show} - {output_base}"
                    logging.warning(f"[MOVE] Placing extra/featurette with no season: {file} -> {extras_dir} (show: {clean_show}, type: {extra_type})")
                if number > 1:
                    base_name += f" {number}"
                new_file = extras_dir / f"{base_name}{file.suffix}"
                logging.info(f"Proposed extra: {file} -> {new_file}")
                if not dry_run:
                    extras_dir.mkdir(parents=True, exist_ok=True)
                    # Duplicate detection for extras
                    if new_file.exists():
                        # Compare hashes
                        src_hash = get_file_hash(file)
                        dst_hash = get_file_hash(new_file)
                        if src_hash == dst_hash:
                            logging.info(f"Duplicate extra detected (identical hash): {file} == {new_file}")
                        else:
                            logging.warning(f"Duplicate extra detected (different hash): {file} != {new_file}")
                    else:
                        file.rename(new_file)
                    log_operation({"original": str(file), "new": str(new_file)})
                processed += 1
                if progress_callback:
                    progress_callback(50 + int((processed / total) * 40))
                continue
            
            # Only process as main content if NOT classified as extra
            clean_show = clean_filename(meta['name'])
            if meta['type'] == 'movie':
                year = meta.get('year', '')
                name = f"{clean_show} ({year})" if year else clean_show
                new_dir = Path(target) / "Movies" / name
                new_file = new_dir / f"{name}{file.suffix}"
            else:  # tv
                ep_str = f"S{meta.get('season', 0):02d}E{meta['episode']:02d}"
                episode_title = meta.get('episode_title')
                title = f" - {clean_filename(episode_title)}" if episode_title and episode_title.strip() else ""
                new_filename = f"{clean_show} - {ep_str}{title}{file.suffix}"
                
                # Only treat as special if explicitly marked AND not already classified as extra
                if meta.get('is_special', False) and not (extra_info and extra_info['is_extra']):
                    new_dir = Path(target) / "TV Shows" / "Specials"
                else:
                    season_str = f"Season {meta.get('season', 1):02d}"
                    new_dir = Path(target) / "TV Shows" / clean_show / season_str
                
                new_file = new_dir / new_filename
            
            logging.info(f"Proposed: {file} -> {new_file}")
            
            if not dry_run:
                # Main content duplicate detection
                if new_file.exists():
                    src_hash = get_file_hash(file)
                    dst_hash = get_file_hash(new_file)
                    if src_hash == dst_hash:
                        logging.info(f"Duplicate main content (identical): {file} == {new_file}, removing source.")
                        file.unlink()
                        processed += 1
                        if progress_callback:
                            progress_callback(50 + int((processed / total) * 40))
                        continue
                    src_quality = get_quality(file)
                    dst_quality = get_quality(new_file)
                    src_playable = is_file_playable(file)
                    dst_playable = is_file_playable(new_file)
                    if (src_playable and not dst_playable) or (src_quality > dst_quality):
                        logging.info(f"Replacing lower quality or unplayable main content: {new_file}")
                        new_file.unlink()
                    else:
                        logging.info(f"Skipping duplicate main content (better or equal exists): {file}")
                        file.unlink()
                        processed += 1
                        if progress_callback:
                            progress_callback(50 + int((processed / total) * 40))
                        continue
                
                new_dir.mkdir(parents=True, exist_ok=True)
                file.rename(new_file)
                log_operation({"original": str(file), "new": str(new_file)})
            
            processed += 1
            if progress_callback:
                progress_callback(50 + int((processed / total) * 40))
        
        # Final progress update
        if progress_callback:
            progress_callback(100)
        
        # At the end, cleanup empty directories
        if not dry_run:
            remove_empty_dirs(Path(source))
    
    except Exception as e:
        logging.error(f"Organization error: {e}")
        raise 