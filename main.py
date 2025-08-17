#!/usr/bin/env python3
"""
Telegram YouTube to MP3 Bot
Main entry point for the bot application
"""

import logging
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import BOT_TOKEN
from bot.handlers import start_handler, help_handler, message_handler, button_callback_handler, error_handler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Reduce httpx logging verbosity
logging.getLogger("httpx").setLevel(logging.WARNING)

def main():
    """Main function to start the bot"""
    # Create the Application
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required")
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting YouTube to MP3 Bot...")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
