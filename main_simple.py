#!/usr/bin/env python3
"""
Simplified Telegram YouTube to MP3 Bot - Testing Version
"""

import logging
import asyncio
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Check if BOT_TOKEN exists
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
    sys.exit(1)

def main():
    """Main function to test bot setup"""
    logger.info("Testing bot configuration...")
    logger.info(f"Bot token available: {'Yes' if BOT_TOKEN else 'No'}")
    
    try:
        # Test imports one by one
        logger.info("Testing imports...")
        
        # Try importing without conflicting packages
        sys.path.insert(0, str(Path('.pythonlibs/lib/python3.11/site-packages')))
        
        import telegram
        logger.info("✅ Base telegram import successful")
        
        from telegram.ext import Application
        logger.info("✅ Application import successful")
        
        app = Application.builder().token(BOT_TOKEN).build()
        logger.info("✅ Bot application created successfully")
        
        logger.info("🎉 Bot setup successful! Ready to start implementing improvements.")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        logger.error("Will proceed with fixing the package configuration...")

if __name__ == '__main__':
    main()