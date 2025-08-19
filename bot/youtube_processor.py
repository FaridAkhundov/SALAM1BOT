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

            # Enhanced yt-dlp options with anti-detection measures
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
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
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
                    embedded_file_path = self._embed_thumbnail_with_ffmpeg(file_path, thumbnail_path, title)
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
    
    def _embed_thumbnail_with_ffmpeg(self, mp3_path: str, thumbnail_path: str, title: str) -> str:
        try:
            import subprocess
            
            base_name = os.path.splitext(mp3_path)[0]
            embedded_path = f"{base_name}_embedded.mp3"
            
            # Convert WebP to JPEG for better MP3 compatibility and resize for smaller file
            if thumbnail_path.lower().endswith('.webp') or thumbnail_path.lower().endswith('.png'):
                jpeg_path = thumbnail_path.replace('.webp', '.jpg').replace('.png', '.jpg')
                try:
                    # Convert and resize to 300x300 for better compatibility and smaller size
                    subprocess.run(['ffmpeg', '-i', thumbnail_path, '-vf', 'scale=300:300:force_original_aspect_ratio=decrease,pad=300:300:(ow-iw)/2:(oh-ih)/2', '-q:v', '3', '-y', jpeg_path], 
                                 capture_output=True, timeout=60, check=True)
                    if os.path.exists(jpeg_path):
                        thumbnail_path = jpeg_path
                        logger.info(f"Converted thumbnail to JPEG: {jpeg_path}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to convert thumbnail to JPEG: {e}")
            elif thumbnail_path.lower().endswith('.jpg') or thumbnail_path.lower().endswith('.jpeg'):
                # Resize existing JPEG for consistency
                resized_path = thumbnail_path.replace('.jpg', '_resized.jpg').replace('.jpeg', '_resized.jpg')
                try:
                    subprocess.run(['ffmpeg', '-i', thumbnail_path, '-vf', 'scale=300:300:force_original_aspect_ratio=decrease,pad=300:300:(ow-iw)/2:(oh-ih)/2', '-q:v', '3', '-y', resized_path], 
                                 capture_output=True, timeout=60, check=True)
                    if os.path.exists(resized_path):
                        thumbnail_path = resized_path
                        logger.info(f"Resized thumbnail: {resized_path}")
                except subprocess.CalledProcessError as e:
                    logger.warning(f"Failed to resize thumbnail: {e}")
            
            # FFmpeg command to embed thumbnail into MP3 with maximum device compatibility
            cmd = [
                'ffmpeg', '-i', mp3_path, '-i', thumbnail_path,
                '-map', '0:a', '-map', '1:v',
                '-c:a', 'copy',  # Copy audio without re-encoding
                '-c:v', 'mjpeg',   # Use MJPEG for better device compatibility
                '-disposition:v', 'attached_pic',  # Mark as attached picture
                '-id3v2_version', '3',  # Use ID3v2.3 for maximum compatibility
                '-write_id3v1', '1',    # Also write ID3v1 for older devices
                '-y', embedded_path
            ]
            
            logger.info(f"Running FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            
            if result.returncode == 0 and os.path.exists(embedded_path):
                logger.info(f"FFmpeg embedding successful. Output size: {os.path.getsize(embedded_path)} bytes")
                return embedded_path
            else:
                error_msg = result.stderr.decode() if result.stderr else 'Unknown error'
                logger.error(f"FFmpeg thumbnail embedding failed. Return code: {result.returncode}, Error: {error_msg}")
                return mp3_path
                
        except Exception as e:
            logger.error(f"Exception during thumbnail embedding: {e}")
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
