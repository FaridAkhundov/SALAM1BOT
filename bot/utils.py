"""
Utility functions for the Telegram YouTube to MP3 bot
"""

import os
import re
import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)

def is_valid_youtube_url(url: str) -> bool:
    """
    Check if a URL is a valid YouTube URL
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid YouTube URL, False otherwise
    """
    youtube_patterns = [
        r'https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtu\.be/[\w-]+',
        r'https?://(?:www\.)?m\.youtube\.com/watch\?v=[\w-]+',
        r'https?://(?:www\.)?youtube\.com/embed/[\w-]+',
        r'https?://(?:www\.)?youtube\.com/v/[\w-]+',
    ]
    
    for pattern in youtube_patterns:
        if re.match(pattern, url.strip()):
            return True
    
    return False

def cleanup_temp_files(file_paths: List[str] = None) -> None:
    """
    Clean up temporary files
    
    Args:
        file_paths (List[str], optional): Specific files to delete.
                                        If None, cleans all temp files.
    """
    try:
        if file_paths:
            # Delete specific files
            for file_path in file_paths:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted temp file: {file_path}")
        else:
            # Clean all files in temp directory older than 1 hour
            from config import TEMP_DIR
            import time
            
            temp_path = Path(TEMP_DIR)
            if not temp_path.exists():
                return
            
            current_time = time.time()
            for file_path in temp_path.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > 3600:  # 1 hour
                        file_path.unlink()
                        logger.info(f"Cleaned old temp file: {file_path}")
                        
    except Exception as e:
        logger.error(f"Error cleaning temp files: {str(e)}")

def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format
    
    Args:
        size_bytes (int): Size in bytes
        
    Returns:
        str: Formatted size string
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage
    
    Args:
        filename (str): Original filename
        
    Returns:
        str: Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    return filename or "audio"

def get_video_id_from_url(url: str) -> str:
    """
    Extract video ID from YouTube URL
    
    Args:
        url (str): YouTube URL
        
    Returns:
        str: Video ID or empty string if not found
    """
    patterns = [
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtu\.be/([^?]+)',
        r'youtube\.com/embed/([^?]+)',
        r'youtube\.com/v/([^?]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return ""

def clean_youtube_url(url: str) -> str:
    """
    Clean YouTube URL to remove playlist parameters and other unnecessary parts
    
    Args:
        url (str): Original YouTube URL (may contain playlist, timestamp, etc.)
        
    Returns:
        str: Clean YouTube URL with only the video ID
    """
    # Extract video ID
    video_id = get_video_id_from_url(url)
    if not video_id:
        return url  # Return original if can't extract ID
    
    # Return clean URL
    return f"https://www.youtube.com/watch?v={video_id}"
