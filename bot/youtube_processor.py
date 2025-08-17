"""
YouTube video download and MP3 conversion processor
"""

import os
import asyncio
import logging
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
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
        self.executor = ThreadPoolExecutor(max_workers=3)  # Support for multitasking
        
        # Configure optimized yt-dlp options with thumbnail support
        self.ydl_opts = {
            'format': 'bestaudio/best[filesize<45M]',  # Prioritize smaller files
            'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
            'writethumbnail': True,  # Download thumbnail
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': AUDIO_FORMAT,
                    'preferredquality': AUDIO_QUALITY,
                },
                {
                    'key': 'EmbedThumbnail',  # Embed thumbnail in audio file
                    'already_have_thumbnail': False,
                },
                {
                    'key': 'FFmpegMetadata',  # Add metadata support
                }
            ],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'extractor_retries': 1,  # Faster retries
            'fragment_retries': 1,   # Faster retries
            'socket_timeout': 15,    # Faster timeout
            'concurrent_fragment_downloads': 4,  # Speed up downloads
        }
    
    async def download_and_convert(self, url: str, progress_callback=None) -> dict:
        """
        Download YouTube video and convert to MP3 with real-time progress
        
        Args:
            url (str): YouTube video URL
            progress_callback: Callback function for progress updates
            
        Returns:
            dict: Result containing success status, file path, and metadata
        """
        try:
            # Store progress callback
            self.progress_callback = progress_callback
            
            # Run the download in thread pool for multitasking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.executor, self._download_video, url)
            return result
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return {
                "success": False,
                "error": ERROR_MESSAGES["download_failed"]
            }
    
    def _download_video(self, url: str) -> dict:
        """
        Synchronous download function to run in executor with real-time progress
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            dict: Result containing success status, file path, and metadata
        """
        try:
            logger.info(f"Starting download for URL: {url}")
            
            # Progress tracking variables
            self.download_progress = 0
            self.conversion_progress = 0
            
            def progress_hook(d):
                if d['status'] == 'downloading':
                    if d.get('total_bytes') or d.get('total_bytes_estimate'):
                        total = d.get('total_bytes') or d.get('total_bytes_estimate')
                        downloaded = d.get('downloaded_bytes', 0)
                        progress = min(99, int((downloaded / total) * 100))  # Cap at 99% until complete
                        self.download_progress = progress
                        
                        if self.progress_callback:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    self.progress_callback(f"📥 Mahnı yüklənir... ({progress}%)"),
                                    asyncio.get_event_loop()
                                )
                            except:
                                pass
                elif d['status'] == 'finished':
                    self.download_progress = 100
                    if self.progress_callback:
                        try:
                            asyncio.run_coroutine_threadsafe(
                                self.progress_callback("🔄 MP3-ə çevrilir..."),
                                asyncio.get_event_loop()
                            )
                        except:
                            pass

            # Enhanced options with optimized thumbnail support for speed
            ydl_opts = {
                'format': 'bestaudio/best[filesize<45M]',  # Prioritize smaller files
                'outtmpl': f'{TEMP_DIR}/%(title)s.%(ext)s',
                'writethumbnail': True,
                'writeinfojson': False,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    {
                        'key': 'EmbedThumbnail',
                        'already_have_thumbnail': False,
                    },
                    {
                        'key': 'FFmpegMetadata',  # Add metadata support
                    }
                ],
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                'quiet': True,  # Optimize for speed
                'no_warnings': True,  # Optimize for speed
                'socket_timeout': 10,  # Faster timeout
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'extractor_retries': 1,
                'fragment_retries': 1,
                'concurrent_fragment_downloads': 4,  # Speed up downloads
            }
            
            logger.info("Creating yt-dlp instance...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info first
                logger.info("Extracting video information...")
                info = ydl.extract_info(url, download=False)
                
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
                
                # Ensure download progress reaches 100%
                if self.progress_callback:
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.progress_callback("📥 Mahnı yüklənir... (100%)"),
                            asyncio.get_event_loop()
                        )
                        time.sleep(0.5)  # Brief pause to show 100%
                    except:
                        pass
                    
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
