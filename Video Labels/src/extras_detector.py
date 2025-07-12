import re
from pathlib import Path
from typing import Optional, Dict, List
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
}

EXTRA_FOLDERS = ['extras', 'bonus', 'specials', 'behind the scenes', 'featurettes']


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


def is_extra_by_location(path: Path) -> Optional[str]:
    """Detect if file is in an extras folder by location."""
    for part in path.parts:
        if part.lower() in EXTRA_FOLDERS:
            return part.capitalize()
    return None


def classify_extra(file_path: Path, duration: Optional[float] = None) -> Optional[Dict]:
    """
    Classify a file as extra content, returning its type and details if applicable.
    Uses keyword, location, and AI-based detection.
    """
    # 1. Check for episode patterns first - if it looks like an episode, it's probably not an extra
    if detect_episode_pattern(file_path.name):
        return None
    
    # 2. Keyword-based detection
    extra_type = detect_extra_type(file_path.name)
    if extra_type:
        return {'is_extra': True, 'extra_type': extra_type, 'method': 'keyword'}

    # 3. Location-based detection
    location_type = is_extra_by_location(file_path)
    if location_type:
        return {'is_extra': True, 'extra_type': location_type, 'method': 'location'}

    # 4. Duration-based detection (only as fallback, and more conservative)
    if duration is not None and duration < 300:  # less than 5 minutes (more conservative)
        return {'is_extra': True, 'extra_type': 'Short', 'method': 'duration'}

    # 5. AI-based detection (fallback)
    ai_meta = identify_media(file_path.name)
    if ai_meta.get('type') == 'extra' or ai_meta.get('is_special'):
        return {'is_extra': True, 'extra_type': ai_meta.get('extra_type', 'Special'), 'method': 'ai', 'ai_meta': ai_meta}

    return None 