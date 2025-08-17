# Overview

This is a Telegram bot that converts YouTube videos to MP3 files with advanced music search capabilities. The bot interface is fully localized in Azerbaijani language. Users can either send YouTube URLs for direct download or search for songs by name. The bot displays search results in paginated inline keyboards (8 songs per page, up to 3 pages) for easy selection. It downloads videos, extracts audio, converts to MP3 format, and sends the audio file back via Telegram. The bot includes rate limiting, file size validation, and comprehensive error handling with user-friendly Azerbaijani messages.

# User Preferences

Preferred communication style: Simple, everyday language.
Bot Interface Language: Azerbaijani (all user-facing messages, commands, and responses)
Rate Limiting: Disabled (user requested removal of 30-second limit on 2025-08-10)
Progress Display: UPDATED (2025-08-17) - Real-time progress tracking that reaches 100% before proceeding
User Interface Notes: Search limitations notice moved from /help to /start command
Language Updates: Changed "Video" to "Mahnı" in all user-facing messages (2025-08-10)
URL Cleaning: Added automatic playlist parameter removal from YouTube URLs (2025-08-10)
Title Cleaning: Remove channel/uploader names from audio file titles to avoid duplication (2025-08-10)
Thumbnail Support: ADDED (2025-08-17) - Songs now include embedded thumbnails without extra text
Multitasking: IMPLEMENTED (2025-08-17) - Concurrent processing for multiple users
Code Cleanup: COMPLETED (2025-08-17) - Removed unnecessary code parts while maintaining functionality

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