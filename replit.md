# Overview

This is a Telegram bot that converts YouTube videos to MP3 files with advanced music search capabilities. The bot interface is fully localized in Azerbaijani language. Users can either send YouTube URLs for direct download or search for songs by name. The bot displays search results in paginated inline keyboards (8 songs per page, up to 3 pages) for easy selection. It downloads videos, extracts audio, converts to MP3 format, and sends the audio file back via Telegram. The bot includes rate limiting, file size validation, and comprehensive error handling with user-friendly Azerbaijani messages.

## Migration Status
**COMPLETED (2025-08-19):** Successfully migrated from Replit Agent to standard Replit environment. All package conflicts between `telegram` and `python-telegram-bot` packages resolved, dependencies installed correctly. Bot is ready to run once BOT_TOKEN is configured.

**Final Migration Update (2025-08-17):** Migration completely finalized. Resolved all package conflicts between `telegram` and `python-telegram-bot` packages. Bot successfully starts and runs without errors. All dependencies properly installed and configured.

**VERIFIED (2025-08-18):** Bot fully operational with scheduler started and application running. Successfully resolved all ModuleNotFoundError issues with telegram package imports. Migration from Replit Agent to standard environment 100% complete and ready for production use.

**THUMBNAIL ENHANCEMENT (2025-08-18):** Added EmbedThumbnail processor to properly embed thumbnails into MP3 files for better compatibility with phone music players. This ensures thumbnails are preserved when audio files are downloaded to devices.

**THUMBNAIL FIX ADVANCED (2025-08-18):** Implemented manual FFmpeg thumbnail embedding as post-processing step to ensure album art is properly embedded into MP3 files. Uses direct FFmpeg commands with ID3v2.3 metadata for maximum phone compatibility.

**THUMBNAIL FORMAT FIX (2025-08-18):** Fixed MP3 thumbnail embedding by converting WebP thumbnails to JPEG format since MP3 containers don't support WebP images. Added automatic format conversion for better compatibility.

**CODE OPTIMIZATION (2025-08-18):** Cleaned and optimized codebase by removing unused parameters, excessive logging, redundant error handling, and non-functional features. Streamlined download and search processes while maintaining core functionality.

**ENHANCED (2025-08-17):** Added unlimited multitasking - users can now send 50+ downloads simultaneously. Improved session management messages in Azerbaijani for expired search results.

**PROGRESS TRACKING UNIFIED (2025-08-17):** All download types (direct URL and search results) now use real-time progress tracking instead of simulated progress. Consistent experience across all download methods.

**UI MESSAGES IMPROVED (2025-08-17):** Changed processing messages from "Sorğunuz emal olunur..." to "🎵 Mahnı hazırlanır..." for better user experience. Fixed RuntimeWarning issues in progress callback system.

**PROGRESS TRACKING ENHANCED (2025-08-17):** Fixed real-time progress tracking - now shows actual download percentages like "📥 Yüklənir.. (23%)", "📥 Yüklənir.. (67%)", "📥 Yüklənir.. (99%)". Progress stops at 99% and proceeds directly to upload without showing 100% or completion messages.

**TITLE PRESERVATION FIXED (2025-08-17):** Fixed title preservation issue - audio files now maintain their original YouTube titles exactly as they appear, without any cleaning or modification. User requested to preserve original song names.

**METADATA ENHANCEMENT (2025-08-17):** Added FFmpegMetadata processor to properly embed title and metadata into MP3 files. This ensures proper title display in Telegram audio messages with correct metadata.

# User Preferences

Preferred communication style: Simple, everyday language.
Bot Interface Language: Azerbaijani (all user-facing messages, commands, and responses)
Rate Limiting: COMPLETELY DISABLED (user requested unlimited access on 2025-08-17) - No waiting, no queues
Progress Display: UNIFIED (2025-08-17) - Real-time progress tracking for ALL download types (direct URLs and search results) that reaches 100% before proceeding
User Interface Notes: Search limitations notice moved from /help to /start command
Language Updates: Changed "Video" to "Mahnı" in all user-facing messages (2025-08-10)
URL Cleaning: Added automatic playlist parameter removal from YouTube URLs (2025-08-10)
Title Cleaning: Remove channel/uploader names from audio file titles to avoid duplication (2025-08-10)
Thumbnail Support: UPDATED (2025-08-17) - Songs now include embedded thumbnails with FFmpegMetadata support
Performance Optimization: ADDED (2025-08-17) - Optimized download speed with concurrent fragments and faster timeouts
UI Cleanup: COMPLETED (2025-08-17) - Removed extra caption text from audio messages for cleaner interface
Thumbnail Fix: COMPLETED (2025-08-17) - Fixed thumbnail issue by removing EmbedThumbnail processor and using separate thumbnail files for better Telegram compatibility
Multitasking: UNLIMITED (2025-08-17) - 50+ concurrent downloads, 25+ concurrent searches, no queues, fire-and-forget processing
Code Cleanup: COMPLETED (2025-08-17) - Removed docstrings, comments, and unnecessary code while maintaining full functionality
Session Management: ENHANCED (2025-08-17) - When users start new searches, old search result buttons show "session expired" message instead of processing outdated requests
Expired Session Messages: IMPROVED (2025-08-17) - User-friendly Azerbaijani messages when old search buttons are clicked: "Bu axtarışın vaxtı keçib"

# System Architecture

## Bot Framework
- **Technology**: Built using `python-telegram-bot` library for handling Telegram Bot API interactions
- **Architecture Pattern**: Handler-based event-driven system with separate modules for different concerns
- **Entry Point**: `main.py` sets up the application, registers handlers, and starts polling for updates

## Message Processing Pipeline
- **Command Handlers**: Separate handlers for `/start` and `/help` commands that display informational messages
- **Smart Message Handler**: Intelligently processes text messages, distinguishing between YouTube URLs and song search queries
- **Music Search System**: Provides YouTube search functionality with paginated inline keyboards (8 results per page, maximum 3 pages)
- **Callback Query Handler**: Manages user interactions with inline keyboard buttons for song selection and page navigation
- **Error Handler**: Global error handling for graceful failure management

## Rate Limiting System
- **Implementation**: Simple in-memory dictionary storing user ID and last request timestamp
- **Policy**: No rate limiting (RATE_LIMIT_SECONDS = 0) - disabled per user request on 2025-08-10
- **Storage**: Ephemeral storage that resets when bot restarts

## Media Processing Engine
- **Library**: Uses `yt-dlp` (YouTube downloader) with `noplaylist=True` for single video extraction, search functionality, and `FFmpeg` for audio conversion
- **Search Capabilities**: YouTube search with configurable result limits (up to 24 results per query)
- **Quality Settings**: Fixed 192 kbps MP3 output format for consistent file sizes
- **File Management**: Temporary file system with immediate cleanup after successful upload to users
- **Size Constraints**: 45MB file size limit (5MB buffer under Telegram's 50MB limit)
- **User Session Management**: In-memory storage for search results with user-specific pagination states

## Configuration Management
- **Environment Variables**: Bot token retrieved from environment for security
- **Centralized Config**: All settings, limits, and messages stored in `config.py` for easy modification
- **Default Values**: Fallback values provided for development environments

## File System Organization
- **Modular Structure**: Separate modules for handlers, utilities, and YouTube processing
- **Temporary Storage**: Local `temp_downloads` directory for intermediate files
- **Cleanup Strategy**: Automatic file deletion after successful upload or on errors

## Error Handling Strategy
- **Validation Layer**: URL format validation and automatic playlist parameter cleaning before processing begins  
- **Timeout Protection**: 5-minute download timeout to prevent hanging processes
- **User Feedback**: Descriptive error messages for different failure scenarios
- **Resource Management**: Guaranteed cleanup of temporary files even on failures
- **URL Cleaning**: Automatic extraction of video ID from playlist URLs to ensure single video download

# External Dependencies

## Telegram Bot API
- **Service**: Official Telegram Bot API for message handling and file uploads
- **Authentication**: Bot token-based authentication
- **Limitations**: 50MB file upload limit, polling-based message retrieval

## YouTube Data Access
- **Library**: `yt-dlp` for video metadata extraction and download
- **Capabilities**: Supports multiple YouTube URL formats and video qualities
- **Audio Extraction**: Handles format conversion from video containers

## Media Processing
- **Tool**: FFmpeg for audio format conversion and quality adjustment
- **Usage**: Post-processing pipeline within yt-dlp for MP3 conversion
- **Quality Control**: Bitrate normalization to 192 kbps

## Python Runtime Environment
- **Core Libraries**: `asyncio` for asynchronous operations, `logging` for monitoring
- **File System**: Local storage for temporary file management
- **Process Management**: Subprocess handling for media conversion tools