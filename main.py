#!/usr/bin/env python3
"""
Telegram YouTube to MP3 Bot
Main entry point for the bot application
"""

import logging
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
    # Create the Application with optimized settings for high concurrency
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is required")
    application = (Application.builder()
                  .token(BOT_TOKEN)
                  .concurrent_updates(True)  # Enable concurrent update processing
                  .pool_timeout(30)  # Connection pool timeout
                  .connection_pool_size(256)  # Increased connection pool
                  .get_updates_connect_timeout(60)  # Connection timeout
                  .get_updates_read_timeout(60)  # Read timeout
                  .get_updates_write_timeout(60)  # Write timeout
                  .get_updates_pool_timeout(30)  # Pool timeout
                  .build())
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_callback_handler))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot with unlimited concurrent processing
    logger.info("Starting YouTube to MP3 Bot with unlimited concurrency...")
    application.run_polling(
        allowed_updates=["message", "callback_query"],
        close_loop=False  # Keep loop open for better performance
    )

if __name__ == '__main__':
    main()
