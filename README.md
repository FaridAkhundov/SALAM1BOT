# YouTube to MP3 Telegram Bot

Telegram bot that converts YouTube videos to MP3 files with search capabilities.

## Requirements

### System Dependencies
- Python 3.11+
- FFmpeg (required for audio conversion)

### Installation

1. Install FFmpeg:
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install ffmpeg
   
   # macOS
   brew install ffmpeg
   
   # Windows
   # Download from https://ffmpeg.org/download.html
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variable:
   ```bash
   export BOT_TOKEN="your_telegram_bot_token_here"
   ```

4. Run the bot:
   ```bash
   python main.py
   ```

## Features
- YouTube to MP3 conversion
- Search functionality
- Embedded thumbnails
- Azerbaijani interface
- Unlimited concurrent downloads

## Environment Variables
- `BOT_TOKEN` (required): Your Telegram bot token from @BotFather

## YouTube Cookie Support (Optional but Recommended)

If you encounter "Please sign in" errors, add YouTube cookies:

1. Export cookies using browser extension or yt-dlp
2. Save as `cookies.txt` in project root
3. Bot will automatically use cookies if file exists

See `SETUP.md` for detailed cookie setup instructions.

## External Server Deployment

For deployment on VPS/cloud servers, see `SETUP.md` for complete setup guide including:
- System requirements
- Cookie configuration
- Systemd service setup
- Docker deployment
