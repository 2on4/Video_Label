import re
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from gemini_client import identify_media

# List of known extra content keywords and their types
EXTRA_KEYWORDS = {
    'behind the scenes': 'Behind the Scenes',
    'featurette': 'Featurette',
    'deleted scene': 'Deleted Scene',
    'interview': 'Interview',
    'bloopers': 'Bloopers',
    'trailer': 'Trailer',
    'recap': 'Recap',
    'preview': 'Preview',
    'promo': 'Promo',
    'gag reel': 'Gag Reel',
    'making of': 'Making Of',
    'outtakes': 'Outtakes',
    'short': 'Short',
    'special': 'Special',
    'music video': 'Music Video',
    'documentary': 'Documentary',
    'webisode': 'Webisode',
    'mini-episode': 'Mini-Episode',
    'series overview': 'Series Overview',
    'season recap': 'Season Recap',
    'newsreel': 'Newsreels',
}

EXTRA_FOLDERS = ['extras', 'bonus', 'specials', 'behind the scenes', 'featurettes', 'newsreels']


def detect_episode_pattern(filename: str) -> bool:
    """Detect if filename contains episode pattern (S01E01, etc.)."""
    episode_pattern = r'S\d{1,2}E\d{1,2}'
    return bool(re.search(episode_pattern, filename, re.IGNORECASE))


def detect_extra_type(filename: str) -> Optional[str]:
    """Detect extra type from filename using keywords."""
    name = filename.lower()
    for keyword, extra_type in EXTRA_KEYWORDS.items():
        if keyword in name:
            return extra_type
    return None


def is_extra_by_location(path: Path) -> Optional[Tuple[str, Optional[str]]]:
    """
    Detect if file is in an extras folder by location.
    Returns (folder_type, subfolder) if found.
    """
    parts = [p.lower() for p in path.parts]
    for idx, part in enumerate(parts):
        if part in EXTRA_FOLDERS:
            # If there's a subfolder (e.g. Featurettes/Newsreels), return it
            subfolder = None
            if idx + 1 < len(parts):
                subfolder = parts[idx + 1] if parts[idx + 1] not in EXTRA_FOLDERS else None
            return (part.capitalize(), subfolder.capitalize() if subfolder else None)
    return None


def classify_extra(file_path: Path, duration: Optional[float] = None) -> Optional[Dict]:
    """
    Classify a file as extra content, returning its type, group, and recommended output base name.
    Uses keyword, location, and AI-based detection. Featurettes and Newsreels are uniquely named.
    Returns dict with keys: is_extra, extra_type, group, output_base, method, [ai_meta]
    """
    # 1. Check for episode patterns first - if it looks like an episode, it's probably not an extra
    if detect_episode_pattern(file_path.name):
        return None

    # 2. Keyword-based detection
    extra_type = detect_extra_type(file_path.name)
    group = None
    method = 'keyword'
    if extra_type:
        # Featurette and Newsreels get special handling
        if extra_type.lower() in ('featurette', 'newsreels'):
            group = extra_type if extra_type.lower() == 'featurette' else 'Newsreels'
            output_base = f"{file_path.stem}"
            return {
                'is_extra': True,
                'extra_type': extra_type,
                'group': group,
                'output_base': output_base,
                'method': method
            }
        else:
            output_base = extra_type
            return {
                'is_extra': True,
                'extra_type': extra_type,
                'group': None,
                'output_base': output_base,
                'method': method
            }

    # 3. Location-based detection
    location_info = is_extra_by_location(file_path)
    if location_info:
        folder_type, subfolder = location_info
        # Featurettes/Newsreels subfolder logic
        if folder_type.lower() in ('featurettes', 'newsreels'):
            group = folder_type
            if subfolder:
                output_base = f"{group} - {subfolder} - {file_path.stem}"
            else:
                output_base = f"{group} - {file_path.stem}"
            return {
                'is_extra': True,
                'extra_type': folder_type,
                'group': group,
                'output_base': output_base,
                'method': 'location'
            }
        else:
            output_base = folder_type
            return {
                'is_extra': True,
                'extra_type': folder_type,
                'group': None,
                'output_base': output_base,
                'method': 'location'
            }

    # 4. Duration-based detection (only as fallback, and more conservative)
    if duration is not None and duration < 300:  # less than 5 minutes (more conservative)
        return {
            'is_extra': True,
            'extra_type': 'Short',
            'group': None,
            'output_base': 'Short',
            'method': 'duration'
        }

    # 5. AI-based detection (fallback)
    ai_meta = identify_media(file_path.name)
    if ai_meta.get('type') == 'extra' or ai_meta.get('is_special'):
        ai_type = ai_meta.get('extra_type', ai_meta.get('type', 'Special'))
        group = ai_type if ai_type.lower() in ('featurette', 'newsreels') else None
        if group:
            output_base = f"{file_path.stem}"
        else:
            output_base = ai_type
        return {
            'is_extra': True,
            'extra_type': ai_type,
            'group': group,
            'output_base': output_base,
            'method': 'ai',
            'ai_meta': ai_meta
        }

    return None 