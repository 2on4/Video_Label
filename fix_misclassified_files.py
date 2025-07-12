#!/usr/bin/env python3
"""
Script to fix files that were incorrectly classified as extras and moved to Extras folders.
This script identifies files with episode patterns (S01E01, etc.) in Extras folders and moves them back to proper episode locations.
"""

import re
import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fix_misclassified.log'),
        logging.StreamHandler()
    ]
)

def detect_episode_pattern(filename: str) -> Optional[Dict]:
    """Detect episode pattern in filename and extract show, season, episode info."""
    # Pattern to match S01E01, S1E1, etc.
    episode_pattern = r'S(\d{1,2})E(\d{1,2})'
    match = re.search(episode_pattern, filename, re.IGNORECASE)
    
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))
        
        # Extract show name (everything before the episode pattern)
        show_name = filename[:match.start()].strip()
        # Clean up common separators
        show_name = re.sub(r'[_-]+$', '', show_name)
        
        return {
            'show_name': show_name,
            'season': season,
            'episode': episode,
            'pattern': match.group(0)
        }
    return None


def clean_filename(name: str) -> str:
    """Clean filename by replacing forbidden characters."""
    forbidden = r'[<>:\"|?*/]'
    return re.sub(forbidden, '-', name).strip()


def find_misclassified_files(target_dir: str) -> List[Dict]:
    """Find files in Extras folders that have episode patterns."""
    target_path = Path(target_dir)
    misclassified = []
    
    # Walk through all Extras folders
    for root, dirs, files in os.walk(target_path):
        root_path = Path(root)
        
        # Check if this is an Extras folder
        if root_path.name.lower() == 'extras':
            for file in files:
                file_path = root_path / file
                episode_info = detect_episode_pattern(file)
                
                if episode_info:
                    misclassified.append({
                        'file_path': file_path,
                        'episode_info': episode_info,
                        'extras_dir': root_path
                    })
                    logging.info(f"Found misclassified file: {file_path}")
    
    return misclassified


def determine_correct_location(file_info: Dict, target_dir: str) -> Dict:
    """Determine the correct location for a misclassified episode."""
    episode_info = file_info['episode_info']
    show_name = clean_filename(episode_info['show_name'])
    season = episode_info['season']
    episode = episode_info['episode']
    
    # Determine the correct directory structure
    season_str = f"Season {season:02d}"
    correct_dir = Path(target_dir) / "TV Shows" / show_name / season_str
    
    # Determine the correct filename
    ep_str = f"S{season:02d}E{episode:02d}"
    original_name = file_info['file_path'].name
    
    # Extract episode title if present (after the episode pattern)
    episode_pattern = episode_info['pattern']
    title_start = original_name.find(episode_pattern) + len(episode_pattern)
    episode_title = original_name[title_start:].strip()
    
    # Clean up episode title
    if episode_title:
        # Remove file extension for title extraction
        episode_title = re.sub(r'\.[^.]+$', '', episode_title)
        # Clean up separators
        episode_title = re.sub(r'^[_-]+', '', episode_title)
        episode_title = re.sub(r'[_-]+$', '', episode_title)
        
        if episode_title:
            title_part = f" - {clean_filename(episode_title)}"
        else:
            title_part = ""
    else:
        title_part = ""
    
    # Construct new filename
    new_filename = f"{show_name} - {ep_str}{title_part}{file_info['file_path'].suffix}"
    new_file_path = correct_dir / new_filename
    
    return {
        'correct_dir': correct_dir,
        'new_filename': new_filename,
        'new_file_path': new_file_path
    }


def fix_misclassified_files(target_dir: str, dry_run: bool = True) -> None:
    """Fix misclassified files by moving them to correct locations."""
    logging.info(f"Starting fix process for: {target_dir}")
    logging.info(f"Dry run mode: {dry_run}")
    
    # Find all misclassified files
    misclassified = find_misclassified_files(target_dir)
    
    if not misclassified:
        logging.info("No misclassified files found.")
        return
    
    logging.info(f"Found {len(misclassified)} misclassified files.")
    
    # Process each misclassified file
    for file_info in misclassified:
        try:
            correct_location = determine_correct_location(file_info, target_dir)
            
            logging.info(f"Processing: {file_info['file_path']}")
            logging.info(f"  -> Correct location: {correct_location['new_file_path']}")
            
            if not dry_run:
                # Create directory if it doesn't exist
                correct_location['correct_dir'].mkdir(parents=True, exist_ok=True)
                
                # Check if destination file already exists
                if correct_location['new_file_path'].exists():
                    logging.warning(f"Destination file already exists: {correct_location['new_file_path']}")
                    logging.warning(f"Skipping move to avoid overwrite.")
                    continue
                
                # Move the file
                shutil.move(str(file_info['file_path']), str(correct_location['new_file_path']))
                logging.info(f"Successfully moved: {file_info['file_path']} -> {correct_location['new_file_path']}")
                
                # Check if Extras directory is now empty and remove it if so
                extras_dir = file_info['extras_dir']
                if not any(extras_dir.iterdir()):
                    try:
                        extras_dir.rmdir()
                        logging.info(f"Removed empty Extras directory: {extras_dir}")
                    except Exception as e:
                        logging.warning(f"Failed to remove empty directory {extras_dir}: {e}")
            else:
                logging.info(f"[DRY RUN] Would move: {file_info['file_path']} -> {correct_location['new_file_path']}")
                
        except Exception as e:
            logging.error(f"Error processing {file_info['file_path']}: {e}")
    
    logging.info("Fix process completed.")


def main():
    """Main function with command line argument parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fix misclassified files in Extras folders')
    parser.add_argument('target_dir', help='Target directory containing TV Shows folder')
    parser.add_argument('--execute', action='store_true', help='Actually execute the moves (default is dry-run)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target_dir):
        logging.error(f"Target directory does not exist: {args.target_dir}")
        return
    
    fix_misclassified_files(args.target_dir, dry_run=not args.execute)


if __name__ == "__main__":
    main() 