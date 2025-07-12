from configparser import ConfigParser
from typing import Dict

config = ConfigParser()
config.read('config/config.ini')

API_KEY: str = config['gemini']['api_key']

DEFAULT_SOURCE: str = config['paths']['default_source']
DEFAULT_TARGET: str = config['paths']['default_target']

DRY_RUN: bool = config.getboolean('settings', 'dry_run')
MAX_WORKERS: int = config.getint('settings', 'max_workers')

VIDEO_EXTENSIONS: set = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.flv'}

def get_config(section: str, key: str) -> str:
    """Get a config value with error handling.
    
    Args:
        section: Config section.
        key: Config key.
    
    Returns:
        Value as string.
    
    Raises:
        KeyError: If section or key not found.
    """
    try:
        return config[section][key]
    except KeyError:
        raise ValueError(f"Config key '{key}' not found in section '{section}'.") 