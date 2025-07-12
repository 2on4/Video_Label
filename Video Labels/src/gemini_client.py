import google.generativeai as genai
import json
from typing import Dict, Any, List
from config import API_KEY
from logger import logging
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from google.generativeai.types import GenerationConfig

configure(api_key=API_KEY)
model = GenerativeModel('gemini-2.5-pro')  # Use Gemini 2.5 Pro model

def identify_media_batch(filenames: List[str]) -> List[Dict[str, Any]]:
    """Identify media types and metadata for multiple files in a single request.
    
    Args:
        filenames: List of video filenames to analyze.
    
    Returns:
        List of metadata dictionaries for each file.
    
    Raises:
        Exception: On API failure.
    """
    if not filenames:
        return []
    
    # Create a comprehensive prompt for batch analysis
    files_text = "\n".join([f"{i+1}. {filename}" for i, filename in enumerate(filenames)])
    
    prompt = f"""
    Analyze these video filenames and identify their media type and metadata.
    
    Files to analyze:
    {files_text}
    
    For each file, determine if it's a TV show episode, movie, or unknown.
    Return a JSON array where each element corresponds to the file at the same index:
    [
        {{
            "type": "tv" or "movie" or "unknown",
            "name": str,
            "year": int (for movie, optional),
            "season": int (for tv, optional),
            "episode": int (for tv),
            "episode_title": str (optional),
            "is_special": bool (default false)
        }},
        ...
    ]
    
    Guidelines:
    - For TV shows: Extract show name, season, episode number, and episode title
    - For episode titles: 
        * First check if the episode title is present in the filename
        * If not in filename, use your knowledge of TV shows to provide the actual episode title
        * For example: "The Bear S01E01" should have episode_title "System"
        * Episode titles should be the actual episode names, not generic descriptions
    - For movies: Extract movie name and year if present
    - For remakes/reboots: Add disambiguation like "(US)" or "(2020)"
    - For specials: Set is_special to true and use S00EXX format
    - For unknown files: Set type to "unknown" and leave other fields empty
    - Handle various filename formats (dots, dashes, underscores, etc.)
    - Be consistent with naming conventions
    - IMPORTANT: Always try to provide actual episode titles, not generic "Episode X" descriptions
    """
    
    try:
        response = model.generate_content(
            prompt,
            generation_config=GenerationConfig(response_mime_type="application/json")
        )
        data = json.loads(response.text)
        
        # Ensure we get a list back and it matches the number of input files
        if not isinstance(data, list):
            logging.error(f"Expected list response, got {type(data)}")
            return [{"type": "unknown"} for _ in filenames]
        
        # Pad or truncate to match input length
        while len(data) < len(filenames):
            data.append({"type": "unknown"})
        
        if len(data) > len(filenames):
            data = data[:len(filenames)]
        
        return data
        
    except Exception as e:
        logging.error(f"API error for batch analysis: {e}")
        return [{"type": "unknown"} for _ in filenames]

def identify_media(filename: str) -> Dict[str, Any]:
    """Legacy function for single file identification - now uses batch processing.
    
    Args:
        filename: Video filename.
    
    Returns:
        Dict with metadata.
    """
    # For backward compatibility, wrap single file in batch
    results = identify_media_batch([filename])
    return results[0] if results else {"type": "unknown"} 