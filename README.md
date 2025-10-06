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
