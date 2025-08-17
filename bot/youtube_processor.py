"""
YouTube video download and MP3 conversion processor
"""

import os
import asyncio
import logging
from pathlib import Path
import yt_dlp
from config import (
    TEMP_DIR, MAX_FILE_SIZE_BYTES, DOWNLOAD_TIMEOUT, 
    AUDIO_QUALITY, AUDIO_FORMAT, ERROR_MESSAGES
)

logger = logging.getLogger(__name__)

class YouTubeProcessor:
    """Handles YouTube video downloading and MP3 conversion"""
    
    def __init__(self):
        """Initialize the processor"""
        # Create temp directory if it doesn't exist
        Path(TEMP_DIR).mkdir(exist_ok=True)
        self.progress_callback = None
        
        # Configure yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
            'extractaudio': True,
            'audioformat': AUDIO_FORMAT,
            'audioquality': AUDIO_QUALITY,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': AUDIO_FORMAT,
                'preferredquality': AUDIO_QUALITY,
            }],
            'quiet': True,
            'no_warnings': True,
            # Add options to handle YouTube's anti-bot measures
            'cookiefile': None,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {'http': lambda n: min(4 ** n, 60)},
            'socket_timeout': 30,
        }
    
    async def download_and_convert(self, url: str) -> dict:
        """
        Download YouTube video and convert to MP3
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Result containing success status, file path, and metadata
        """
        try:
            # Run the download in a thread with a simpler approach
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._download_video, url)
            return result
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return {
                "success": False,
                "error": ERROR_MESSAGES["download_failed"]
            }
    
    def _download_video(self, url: str) -> dict:
        """
        Synchronous download function to run in executor
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Result containing success status, file path, and metadata
        """
        try:
            logger.info(f"Starting download for URL: {url}")
            


            # Simplified options for better reliability
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,  # Only download single video, not playlist
                'quiet': False,  # Enable output for debugging
                'no_warnings': False,
                'socket_timeout': 15,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'extractor_retries': 1,  # Reduce retries for faster failure
                'fragment_retries': 1,
            }
            
            logger.info("Creating yt-dlp instance...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info first
                logger.info("Extracting video information...")
                try:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        logger.info(f"Video info extraction completed: {info.get('title', 'Unknown')}")
                    else:
                        logger.error("Video info extraction returned None")
                except Exception as extract_error:
                    logger.error(f"Failed to extract video info: {extract_error}")
                    raise extract_error
                
                # Check if video is available
                if not info:
                    logger.error("Failed to extract video information")
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["download_failed"]
                    }
                
                # Get video metadata
                title = info.get('title', 'Unknown Title')
                uploader = info.get('uploader', 'Unknown Artist')
                duration = info.get('duration', 0)
                
                logger.info(f"Video info - Title: {title}, Duration: {duration}s, Uploader: {uploader}")
                
                # Estimate file size (rough approximation)
                estimated_size = duration * 24000  # ~192kbps in bytes per second
                if estimated_size > MAX_FILE_SIZE_BYTES:
                    logger.error(f"File too large: estimated {estimated_size} bytes")
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["file_too_large"]
                    }
                
                # Download and convert
                logger.info("Starting download and conversion...")
                ydl.download([url])
                    
                logger.info("Download completed, looking for converted file...")
                
                # Find the converted file
                file_path = self._find_converted_file(title)
                if not file_path or not os.path.exists(file_path):
                    logger.error(f"Converted file not found. Expected pattern: {title}")
                    # List files in temp directory for debugging
                    temp_files = os.listdir(TEMP_DIR) if os.path.exists(TEMP_DIR) else []
                    logger.error(f"Files in temp directory: {temp_files}")
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["conversion_failed"]
                    }
                
                logger.info(f"Found converted file: {file_path}")
                
                # Check actual file size
                file_size = os.path.getsize(file_path)
                if file_size > MAX_FILE_SIZE_BYTES:
                    logger.error(f"File too large after conversion: {file_size} bytes")
                    os.remove(file_path)
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["file_too_large"]
                    }
                
                logger.info(f"Conversion successful! File size: {file_size} bytes")
                return {
                    "success": True,
                    "file_path": file_path,
                    "title": title,
                    "uploader": uploader,
                    "duration": duration,
                    "file_size": file_size
                }
                
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": ERROR_MESSAGES["download_failed"]
            }
    
    async def search_youtube(self, query: str, max_results: int = 24) -> list:
        """
        Search YouTube for videos by query
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return (max 24 for 3 pages)
            
        Returns:
            list: List of video dictionaries with title, url, and uploader
        """
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._search_youtube_sync, query, max_results)
            return result
        except Exception as e:
            logger.error(f"Error searching YouTube for '{query}': {str(e)}")
            return []
    
    def _search_youtube_sync(self, query: str, max_results: int = 24) -> list:
        """
        Synchronous YouTube search function to run in executor
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            list: List of video dictionaries
        """
        try:
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Don't download, just get metadata
                'default_search': 'ytsearch',
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                # Search for videos
                search_query = f"ytsearch{max_results}:{query}"
                search_results = ydl.extract_info(search_query, download=False)
                
                videos = []
                if search_results and 'entries' in search_results:
                    for entry in search_results['entries']:
                        if entry:
                            video_id = entry.get('id', '')
                            # Skip if no video ID or if it's a playlist/channel
                            if not video_id or len(video_id) != 11:
                                continue
                            
                            # Basic filtering for obviously problematic entries
                            title = entry.get('title', 'Unknown Title')
                            if not title or title in ['[Deleted video]', '[Private video]', 'Deleted video', 'Private video']:
                                continue
                                
                            videos.append({
                                'title': title,
                                'url': f"https://www.youtube.com/watch?v={video_id}",
                                'uploader': entry.get('uploader', 'Unknown Artist'),
                                'duration': entry.get('duration', 0),
                                'id': video_id
                            })
                
                logger.info(f"Found {len(videos)} videos for query: {query}")
                return videos
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []

    def _find_converted_file(self, title: str) -> str:
        """
        Find the converted MP3 file
        
        Args:
            title (str): Video title
            
        Returns:
            str: Path to the MP3 file
        """
        # Clean title for filename matching
        clean_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        # Look for files in temp directory
        temp_path = Path(TEMP_DIR)
        
        # Try exact match first
        exact_match = temp_path / f"{clean_title}.{AUDIO_FORMAT}"
        if exact_match.exists():
            return str(exact_match)
        
        # Look for any MP3 files that might match
        for file_path in temp_path.glob(f"*.{AUDIO_FORMAT}"):
            if clean_title.lower() in file_path.stem.lower():
                return str(file_path)
        
        # Return the most recent MP3 file as fallback
        mp3_files = list(temp_path.glob(f"*.{AUDIO_FORMAT}"))
        if mp3_files:
            return str(max(mp3_files, key=os.path.getctime))
        
        return ""
