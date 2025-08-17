#!/usr/bin/env python3
"""
Test script to check if imports work correctly
"""

try:
    print("Testing python-telegram-bot imports...")
    
    # Test basic telegram import first
    import telegram
    print("✅ telegram base import successful")
    
    # Test specific imports
    from telegram import Update
    print("✅ telegram.Update import successful")
    
    from telegram.ext import Application
    print("✅ telegram.ext.Application import successful")
    
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    print("✅ telegram.ext handlers and filters imports successful")
    
    print("Testing yt-dlp import...")
    import yt_dlp
    print("✅ yt-dlp import successful")
    
    print("Testing ffmpeg-python import...")
    import ffmpeg
    print("✅ ffmpeg-python import successful")
    
    print("\n🎉 All imports successful! The bot should work.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    exit(1)