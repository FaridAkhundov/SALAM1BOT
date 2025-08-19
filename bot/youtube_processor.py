# YouTube video processor

import os
import asyncio
import logging
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import yt_dlp
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, ID3NoHeaderError
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
                            
                            # Update progress callback every 1 second instead of every log
                            if not hasattr(self, '_last_progress_update') or not hasattr(self, '_last_progress_value'):
                                self._last_progress_update = 0
                                self._last_progress_value = -1
                            
                            import time
                            current_time = time.time()
                            
                            # Update progress every 1 second or when progress changes significantly
                            if (current_time - self._last_progress_update >= 1.0 or 
                                progress - self._last_progress_value >= 5):
                                
                                self._last_progress_update = current_time
                                self._last_progress_value = progress
                                
                                if self.progress_callback and hasattr(self, 'main_loop') and self.main_loop:
                                    try:
                                        # Schedule callback on main loop
                                        future = asyncio.run_coroutine_threadsafe(
                                            self.progress_callback(f"📥 Yüklənir.. ({progress}%)"),
                                            self.main_loop
                                        )
                                        # Don't wait for result to avoid blocking
                                    except Exception as e:
                                        logger.error(f"Progress callback failed: {e}")
                    elif d['status'] == 'finished':
                        # Final update when download completes
                        if self.progress_callback and hasattr(self, 'main_loop') and self.main_loop:
                            try:
                                asyncio.run_coroutine_threadsafe(
                                    self.progress_callback("📥 Yüklənir.. (99%)"),
                                    self.main_loop
                                )
                            except Exception as e:
                                logger.error(f"Final progress callback failed: {e}")
                except Exception as e:
                    logger.error(f"Progress hook error: {e}")

            # Enhanced yt-dlp options with advanced anti-detection measures
            ydl_opts = {
                'format': 'bestaudio/best[filesize<45M]',
                'outtmpl': f'{TEMP_DIR}/%(epoch)s_%(id)s_%(title)s.%(ext)s',
                'writethumbnail': True,
                'writeinfojson': False,
                'postprocessors': [
                    {
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '192',
                    },
                    {
                        'key': 'FFmpegMetadata',
                        'add_metadata': True,
                    },
                ],
                'progress_hooks': [progress_hook],
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 120,
                'read_timeout': 120,
                'extractor_retries': 5,
                'fragment_retries': 5,
                'retries': 3,
                'concurrent_fragment_downloads': 4,
                'keepvideo': False,
                # Advanced anti-bot detection measures
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                },
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],  # Skip problematic formats
                        'player_skip': ['configs'],  # Skip player configs that may trigger detection
                    }
                },
                # Use browser-like behavior
                'cookies_from_browser': ('chrome',),  # Try to use Chrome cookies if available
                'age_limit': 0,  # Don't skip age-restricted content
                'ignoreerrors': False,  # Don't ignore errors, handle them properly
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except (yt_dlp.utils.ExtractorError, yt_dlp.utils.DownloadError) as e:
                    error_msg = str(e)
                    if any(phrase in error_msg for phrase in [
                        "Sign in to confirm you're not a bot",
                        "The following content is not available on this app",
                        "Watch on the latest version of YouTube"
                    ]):
                        # Try fallback options for YouTube restrictions
                        logger.warning(f"YouTube restriction encountered: {error_msg[:100]}...")
                        logger.warning("Trying fallback extraction methods...")
                        
                        # Try different user agents and configurations
                        fallback_configs = [
                            # Standard web browser
                            {
                                **ydl_opts,
                                'http_headers': {
                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                                    'Accept': '*/*',
                                    'Accept-Language': 'en-US,en;q=0.9',
                                    'Sec-Fetch-Mode': 'navigate',
                                },
                                'extractor_args': {
                                    'youtube': {
                                        'player_client': ['android', 'web'],
                                        'skip': ['hls'],
                                    }
                                },
                            },
                            # Mobile user agent
                            {
                                **ydl_opts,
                                'http_headers': {
                                    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36',
                                },
                                'extractor_args': {
                                    'youtube': {
                                        'player_client': ['android'],
                                    }
                                },
                            },
                            # Minimal configuration with no cookies
                            {
                                'format': 'bestaudio/best[filesize<45M]',
                                'outtmpl': f'{TEMP_DIR}/%(epoch)s_%(id)s_%(title)s.%(ext)s',
                                'writethumbnail': True,
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
                                'http_headers': {
                                    'User-Agent': 'yt-dlp/2025.08.11',
                                },
                                'extractor_args': {
                                    'youtube': {
                                        'player_client': ['android'],
                                    }
                                },
                            },
                            # Ultra minimal - no postprocessors
                            {
                                'format': 'bestaudio',
                                'outtmpl': f'{TEMP_DIR}/%(epoch)s_%(id)s_%(title)s.%(ext)s',
                                'noplaylist': True,
                                'quiet': True,
                                'extractor_args': {
                                    'youtube': {
                                        'player_client': ['android'],
                                    }
                                },
                            }
                        ]
                        
                        info = None
                        successful_config = None
                        
                        for i, config in enumerate(fallback_configs):
                            try:
                                logger.info(f"Trying fallback configuration {i+1}/{len(fallback_configs)}...")
                                with yt_dlp.YoutubeDL(config) as fallback_ydl:
                                    info = fallback_ydl.extract_info(url, download=False)
                                    successful_config = config
                                    logger.info(f"✓ Fallback configuration {i+1} successful!")
                                    break
                            except Exception as fallback_error:
                                logger.warning(f"✗ Fallback {i+1} failed: {str(fallback_error)[:100]}")
                                continue
                        
                        if not info:
                            raise e  # Re-raise original error if all fallbacks fail
                            
                    else:
                        raise e
                
                if not info:
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["download_failed"]
                    }
                
                title = info.get('title', 'Unknown Title')
                uploader = info.get('uploader', 'Unknown Artist')
                duration = info.get('duration', 0)
                
                estimated_size = duration * 24000
                if estimated_size > MAX_FILE_SIZE_BYTES:
                    return {
                        "success": False,
                        "error": ERROR_MESSAGES["file_too_large"]
                    }
                
                # Use the same configuration for download that worked for extraction
                if 'successful_config' in locals() and successful_config:
                    logger.info("Using successful fallback configuration for download...")
                    with yt_dlp.YoutubeDL(successful_config) as download_ydl:
                        download_ydl.download([url])
                else:
                    ydl.download([url])
            
            file_path = self._find_converted_file(title)
            if not file_path or not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": ERROR_MESSAGES["conversion_failed"]
                }
            
            file_size = os.path.getsize(file_path)
            if file_size > MAX_FILE_SIZE_BYTES:
                os.remove(file_path)
                return {
                    "success": False,
                    "error": ERROR_MESSAGES["file_too_large"]
                }
            
            thumbnail_path = self._find_thumbnail_file(title)
            
            # Always try manual thumbnail embedding for better compatibility  
            if thumbnail_path and os.path.exists(thumbnail_path):
                try:
                    logger.info(f"Attempting thumbnail embedding for: {title}")
                    embedded_file_path = self._embed_thumbnail_with_mutagen(file_path, thumbnail_path, title)
                    if embedded_file_path and os.path.exists(embedded_file_path) and embedded_file_path != file_path:
                        # Check if embedded file is valid and has reasonable size
                        embedded_size = os.path.getsize(embedded_file_path)
                        if embedded_size > 1000:  # At least 1KB
                            os.remove(file_path)
                            file_path = embedded_file_path
                            file_size = embedded_size
                            logger.info(f"Successfully embedded thumbnail for: {title}")
                        else:
                            logger.warning("Embedded file too small, keeping original")
                            if os.path.exists(embedded_file_path):
                                os.remove(embedded_file_path)
                    else:
                        logger.warning("Thumbnail embedding failed or returned same file")
                except Exception as e:
                    logger.warning(f"Manual thumbnail embedding failed: {e}")
            else:
                logger.warning(f"No thumbnail found for: {title}")
            
            return {
                "success": True,
                "file_path": file_path,
                "title": title,
                "uploader": uploader,
                "duration": duration,
                "file_size": file_size,
                "thumbnail_path": thumbnail_path
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
            search_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,
                'default_search': 'ytsearch',
                'socket_timeout': 60,
                'read_timeout': 60,
                # Anti-bot measures for search
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.5',
                },
                'extractor_args': {
                    'youtube': {
                        'skip': ['hls', 'dash'],
                        'player_skip': ['configs'],
                    }
                },
            }
            
            with yt_dlp.YoutubeDL(search_opts) as ydl:
                search_query = f"ytsearch{max_results}:{query}"
                search_results = ydl.extract_info(search_query, download=False)
                
                videos = []
                if search_results and 'entries' in search_results:
                    for entry in search_results['entries']:
                        if entry and entry.get('id') and len(entry.get('id', '')) == 11:
                            title = entry.get('title', 'Unknown Title')
                            if title and title not in ['[Deleted video]', '[Private video]']:
                                videos.append({
                                    'title': title,
                                    'url': f"https://www.youtube.com/watch?v={entry['id']}",
                                    'uploader': entry.get('uploader', 'Unknown Artist'),
                                    'duration': entry.get('duration', 0),
                                    'id': entry['id']
                                })
                
                return videos
                
        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return []
    
    def _embed_thumbnail_with_mutagen(self, mp3_path: str, thumbnail_path: str, title: str) -> str:
        """
        Embed thumbnail using Mutagen library with ID3v2.3 for maximum device compatibility.
        This method works perfectly on Xiaomi 13T Pro, Samsung Music, iPhone, VLC, etc.
        """
        try:
            import shutil
            
            base_name = os.path.splitext(mp3_path)[0]
            embedded_path = f"{base_name}_embedded.mp3"
            
            # Convert and optimize thumbnail for best device compatibility
            optimized_thumbnail = f"{base_name}_thumbnail.jpg"
            
            # Convert any format to JPEG and resize to 300x300 for device compatibility
            try:
                cmd_convert = [
                    'ffmpeg', '-y',         # Overwrite output
                    '-i', thumbnail_path,   # Input thumbnail (any format)
                    '-vf', 'scale=300:300:force_original_aspect_ratio=decrease,pad=300:300:(ow-iw)/2:(oh-ih)/2:color=white',
                    '-q:v', '2',            # High quality JPEG
                    '-pix_fmt', 'yuv420p',  # Standard pixel format
                    '-f', 'mjpeg',          # Force MJPEG format
                    optimized_thumbnail     # Output JPEG file
                ]
                
                result = subprocess.run(cmd_convert, capture_output=True, timeout=60, check=True)
                if os.path.exists(optimized_thumbnail) and os.path.getsize(optimized_thumbnail) > 1000:
                    thumbnail_path = optimized_thumbnail
                    logger.info(f"Optimized thumbnail created: {optimized_thumbnail}")
                else:
                    logger.warning("Thumbnail optimization failed, using original")
                    
            except subprocess.CalledProcessError as e:
                logger.warning(f"Thumbnail optimization failed: {e}")
            
            # Copy original MP3 file
            shutil.copy2(mp3_path, embedded_path)
            
            # Read thumbnail image data
            with open(thumbnail_path, 'rb') as img_file:
                img_data = img_file.read()
            
            # Load MP3 file with Mutagen
            try:
                audio = MP3(embedded_path, ID3=ID3)
            except ID3NoHeaderError:
                # Add ID3 header if it doesn't exist
                audio = MP3(embedded_path)
                audio.add_tags()
            
            # Clear any existing album art
            audio.tags.delall('APIC')
            
            # Add album art with ID3v2.3 format - this is the key for device compatibility
            audio.tags.add(
                APIC(
                    encoding=3,        # UTF-8 encoding
                    mime='image/jpeg', # MIME type for JPEG
                    type=3,            # Front cover (type 3)
                    desc='Cover',      # Description
                    data=img_data      # Image data
                )
            )
            
            # Force save as ID3v2.3 (most compatible version)
            audio.tags.update_to_v23()
            audio.save(v2_version=3, v23_sep='/')
            
            logger.info(f"✓ Mutagen ID3v2.3 + APIC embedding successful for: {title}")
            
            if os.path.exists(embedded_path):
                original_size = os.path.getsize(mp3_path)
                embedded_size = os.path.getsize(embedded_path)
                logger.info(f"File size: {original_size} → {embedded_size} bytes")
                
                # Clean up optimized thumbnail if we created one
                if optimized_thumbnail != thumbnail_path and os.path.exists(optimized_thumbnail):
                    os.remove(optimized_thumbnail)
                
                return embedded_path
            else:
                logger.warning(f"Embedded file not created: {embedded_path}")
                return mp3_path
                
        except Exception as e:
            logger.error(f"Exception during FFmpeg thumbnail embedding: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return mp3_path

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
            return None
        
        for ext in ['.webp', '.jpg', '.jpeg', '.png']:
            for file_path in temp_path.glob(f"*{ext}"):
                if any(word.lower() in file_path.stem.lower() for word in title.split() if len(word) > 3):
                    return str(file_path)
        
        thumbnail_files = []
        for ext in ['.webp', '.jpg', '.jpeg', '.png']:
            thumbnail_files.extend(temp_path.glob(f"*{ext}"))
        
        if thumbnail_files:
            return str(max(thumbnail_files, key=lambda f: f.stat().st_mtime))
        
        return None
