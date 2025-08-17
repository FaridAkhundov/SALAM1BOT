# YouTube video processor

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
    
    def __init__(self):
        Path(TEMP_DIR).mkdir(exist_ok=True)
        self.progress_callback = None
        # Maximum workers for unlimited concurrency - supports 100+ simultaneous operations
        self.download_executor = ThreadPoolExecutor(max_workers=50, thread_name_prefix="download")
        self.search_executor = ThreadPoolExecutor(max_workers=25, thread_name_prefix="search")
        # Connection pooling for better performance
        self.session_pool = {}
    
    async def download_and_convert(self, url: str, progress_callback=None) -> dict:
        try:
            # Store progress callback and event loop
            self.progress_callback = progress_callback
            self.main_loop = asyncio.get_running_loop()
            logger.info(f"Stored main loop reference: {self.main_loop}")
            
            # Use dedicated download executor with high concurrency
            result = await self.main_loop.run_in_executor(self.download_executor, self._download_video, url)
            return result
            
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return {
                "success": False,
                "error": ERROR_MESSAGES["download_failed"]
            }
    
    def _download_video(self, url: str) -> dict:
        try:
            logger.info(f"Starting download for URL: {url}")
            
            def progress_hook(d):
                try:
                    if d['status'] == 'downloading':
                        if d.get('total_bytes') or d.get('total_bytes_estimate'):
                            total = d.get('total_bytes') or d.get('total_bytes_estimate')
                            downloaded = d.get('downloaded_bytes', 0)
                            progress = min(99, int((downloaded / total) * 100))
                            
                            # Log progress for debugging
                            logger.info(f"Download progress: {progress}%")
                            
                            if self.progress_callback and hasattr(self, 'main_loop') and self.main_loop:
                                try:
                                    # Schedule callback on main loop
                                    future = asyncio.run_coroutine_threadsafe(
                                        self.progress_callback(f"📥 Yüklənir ({progress}%)"),
                                        self.main_loop
                                    )
                                    # Don't wait for result to avoid blocking
                                except Exception as e:
                                    logger.error(f"Progress callback failed: {e}")
                    elif d['status'] == 'finished':
                        logger.info("Download finished - 100%")
                        if self.progress_callback and hasattr(self, 'main_loop') and self.main_loop:
                            try:
                                future = asyncio.run_coroutine_threadsafe(
                                    self.progress_callback("📥 Yüklənir (100%)"),
                                    self.main_loop
                                )
                            except Exception as e:
                                logger.error(f"Finished callback failed: {e}")
                except Exception as e:
                    logger.error(f"Progress hook error: {e}")

            # High-performance options optimized for concurrent downloads
            ydl_opts = {
                'format': 'bestaudio/best[filesize<45M]',
                'outtmpl': f'{TEMP_DIR}/%(epoch)s_%(id)s_%(title)s.%(ext)s',  # Unique names to prevent conflicts
                'writethumbnail': True,
                'writeinfojson': False,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    }
                ],
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                # Optimized for high concurrency
                'socket_timeout': 30,
                'read_timeout': 30,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'extractor_retries': 2,
                'fragment_retries': 2,
                'concurrent_fragment_downloads': 8,  # Doubled for faster downloads
                'geo_bypass': True,
                'geo_bypass_country': 'US',
                # Connection pooling and keepalive
                'keepvideo': False,
                'throttled_rate': None,  # No throttling for max speed
            }
            
            logger.info("Creating yt-dlp instance...")
            # Create fresh instance for each download to avoid conflicts
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            try:
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
                
                # Show final completion message
                if self.progress_callback and hasattr(self, 'main_loop') and self.main_loop:
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.progress_callback("✅ Hazır"),
                            self.main_loop
                        )
                        time.sleep(0.3)  # Brief pause to show completion
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")
                    
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
                
                # Find thumbnail file
                thumbnail_path = self._find_thumbnail_file(title)
                logger.info(f"Looking for thumbnail with title: {title}")
                logger.info(f"Found thumbnail path: {thumbnail_path}")
                
                logger.info(f"Conversion successful! File size: {file_size} bytes")
                return {
                    "success": True,
                    "file_path": file_path,
                    "title": title,
                    "uploader": uploader,
                    "duration": duration,
                    "file_size": file_size,
                    "thumbnail_path": thumbnail_path
                }
            finally:
                # Clean up yt-dlp instance
                try:
                    ydl.close()
                except:
                    pass
                
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": ERROR_MESSAGES["download_failed"]
            }
    
    async def search_youtube(self, query: str, max_results: int = 24) -> list:
        try:
            # Use dedicated search executor for concurrent search operations
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(self.search_executor, self._search_youtube_sync, query, max_results)
            return result
        except Exception as e:
            logger.error(f"Error searching YouTube for '{query}': {str(e)}")
            return []
    
    def _search_youtube_sync(self, query: str, max_results: int = 24) -> list:
        try:
            # High-performance search options for concurrent operations
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Don't download, just get metadata
                'default_search': 'ytsearch',
                'socket_timeout': 15,
                'read_timeout': 15,
                'geo_bypass': True,
                'geo_bypass_country': 'US',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
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
    
    def _find_thumbnail_file(self, title: str) -> str:
        temp_path = Path(TEMP_DIR)
        if not temp_path.exists():
            logger.info("Temp directory does not exist")
            return None
            
        # List all files in temp directory for debugging
        all_files = list(temp_path.glob("*"))
        logger.info(f"All files in temp directory: {[f.name for f in all_files]}")
        
        # Look for common thumbnail extensions
        for ext in ['.webp', '.jpg', '.jpeg', '.png']:
            # Look for exact match first
            exact_file = temp_path / f"{title}{ext}"
            if exact_file.exists():
                logger.info(f"Found exact thumbnail match: {exact_file}")
                return str(exact_file)
            
            # Look for files containing the title or similar pattern
            for file_path in temp_path.glob(f"*{ext}"):
                logger.info(f"Checking thumbnail file: {file_path.name}")
                # Check if title is in filename (more flexible matching)
                if any(word.lower() in file_path.stem.lower() for word in title.split() if len(word) > 3):
                    logger.info(f"Found thumbnail match: {file_path}")
                    return str(file_path)
        
        # Just grab any thumbnail file as last resort
        thumbnail_files = []
        for ext in ['.webp', '.jpg', '.jpeg', '.png']:
            thumbnail_files.extend(temp_path.glob(f"*{ext}"))
        
        if thumbnail_files:
            # Return the most recent thumbnail
            newest_thumb = max(thumbnail_files, key=lambda f: f.stat().st_mtime)
            logger.info(f"Using newest thumbnail as fallback: {newest_thumb}")
            return str(newest_thumb)
        
        logger.info("No thumbnail file found")
        return None
