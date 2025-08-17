"""
Telegram bot command and message handlers
"""

import asyncio
import logging
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from config import WELCOME_MESSAGE, HELP_MESSAGE, ERROR_MESSAGES, RATE_LIMIT_SECONDS
from bot.youtube_processor import YouTubeProcessor
from bot.utils import is_valid_youtube_url, cleanup_temp_files, clean_youtube_url

logger = logging.getLogger(__name__)

# Simple in-memory rate limiting storage
user_last_request = {}

# Store search results for pagination
user_search_results = {}

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    await update.message.reply_text(
        WELCOME_MESSAGE,
        parse_mode='Markdown'
    )

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command"""
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode='Markdown'
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages - both YouTube URLs and song search queries"""
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # Check rate limiting
    if user_id in user_last_request:
        time_diff = datetime.now() - user_last_request[user_id]
        if time_diff.total_seconds() < RATE_LIMIT_SECONDS:
            await update.message.reply_text(ERROR_MESSAGES["rate_limited"])
            return
    
    # Update last request time
    user_last_request[user_id] = datetime.now()
    
    # Check if message is a YouTube URL
    if is_valid_youtube_url(message_text):
        # Clean URL to remove playlist parameters
        clean_url = clean_youtube_url(message_text)
        await process_youtube_url(update, context, clean_url)
    else:
        # Treat as song search query
        await process_song_search(update, context, message_text)

async def process_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    """Process YouTube URL for download"""
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Send processing message
    processing_msg = await update.message.reply_text("🔄 Sorğunuz emal olunur...")
    
    try:
        # Initialize YouTube processor
        processor = YouTubeProcessor()
        
        # Real-time progress callback
        async def update_progress(message):
            try:
                await processing_msg.edit_text(message)
            except Exception as e:
                logger.debug(f"Progress update error: {e}")

        # Start download with real-time progress
        result = await processor.download_and_convert(url, progress_callback=update_progress)
        
        if not result["success"]:
            await processing_msg.edit_text(result["error"])
            return
        
        # Update progress for upload
        await processing_msg.edit_text("📤 Köçürülür...")
        
        # Send the MP3 file
        with open(result["file_path"], 'rb') as audio_file:
            # Clean title by removing channel/uploader name from beginning
            clean_title = result["title"]
            uploader = result["uploader"]
            
            # Remove uploader/channel name from the beginning of title if present
            if uploader and clean_title.startswith(uploader):
                # Remove uploader name and any following separator (-, –, |, etc.)
                clean_title = clean_title[len(uploader):].strip()
                # Remove common separators from the beginning
                for sep in ['-', '–', '|', ':', '•']:
                    if clean_title.startswith(sep):
                        clean_title = clean_title[1:].strip()
                        break
            
            # Send audio with clean title and embedded thumbnail
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=audio_file,
                title=clean_title,
                duration=result["duration"],
                performer=uploader if uploader and uploader != "Unknown Artist" else None
            )
        
        # Update progress after successful upload
        await processing_msg.edit_text("✅ Köçürüldü!")
        
        # Clean up the file immediately after upload
        cleanup_temp_files([result["file_path"]])
        
        # Delete processing message after a moment
        await asyncio.sleep(1)
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        await processing_msg.edit_text(ERROR_MESSAGES["general_error"])

async def process_song_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    """Process song search query and display paginated results"""
    user_id = update.effective_user.id
    
    # Send typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    # Send searching message
    searching_msg = await update.message.reply_text("🔍 Mahnılar axtarılır...")
    
    try:
        # Initialize YouTube processor
        processor = YouTubeProcessor()
        
        # Search for videos
        search_results = await processor.search_youtube(query, max_results=24)
        
        if not search_results:
            await searching_msg.edit_text("❌ Heç bir mahnı tapılmadı. Fərqli axtarış sözü sınayın.")
            return
        
        # Store search results for pagination
        user_search_results[user_id] = search_results
        
        # Create paginated keyboard for first page
        keyboard = create_paginated_keyboard(search_results, page=0, user_id=user_id)
        
        await searching_msg.edit_text(
            f"🎵 *{query}* üçün {len(search_results)} mahnı tapıldı\n\nSəhifə 1/3 - Mahnı seçin:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error searching for '{query}': {str(e)}")
        await searching_msg.edit_text(ERROR_MESSAGES["general_error"])

def create_paginated_keyboard(results: list, page: int, user_id: int) -> InlineKeyboardMarkup:
    """Create paginated inline keyboard with song buttons"""
    buttons = []
    start_idx = page * 8
    end_idx = min(start_idx + 8, len(results))
    
    # Add song buttons (8 per page)
    for i in range(start_idx, end_idx):
        song = results[i]
        # Truncate title if too long for button
        display_title = song['title'][:50] + "..." if len(song['title']) > 50 else song['title']
        buttons.append([InlineKeyboardButton(
            f"🎵 {display_title}",
            callback_data=f"song_{user_id}_{i}"
        )])
    
    # Add navigation buttons
    nav_buttons = []
    total_pages = min(3, (len(results) + 7) // 8)  # Max 3 pages
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Əvvəlki", callback_data=f"page_{user_id}_{page-1}"))
    
    if page < total_pages - 1 and page < 2:  # Max 3 pages (0, 1, 2)
        nav_buttons.append(InlineKeyboardButton("Növbəti ➡️", callback_data=f"page_{user_id}_{page+1}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(buttons)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("song_"):
            # Handle song selection
            _, cb_user_id, song_idx = callback_data.split("_")
            cb_user_id = int(cb_user_id)
            song_idx = int(song_idx)
            
            # Verify user owns this search
            if cb_user_id != user_id or user_id not in user_search_results:
                await query.edit_message_text("❌ Bu axtarış sessiyası bitib. Zəhmət olmasa yenidən axtarın.")
                return
            
            # Get selected song
            search_results = user_search_results[user_id]
            if song_idx >= len(search_results):
                await query.edit_message_text("❌ Yanlış seçim. Zəhmət olmasa yenidən axtarın.")
                return
            
            selected_song = search_results[song_idx]
            
            # Update message to show processing
            await query.edit_message_text(f"🔄 Yüklənir: {selected_song['title']}")
            
            # Process the selected song
            await process_youtube_url_from_callback(query, context, selected_song['url'], selected_song['title'])
            
        elif callback_data.startswith("page_"):
            # Handle page navigation
            _, cb_user_id, page = callback_data.split("_")
            cb_user_id = int(cb_user_id)
            page = int(page)
            
            # Verify user owns this search
            if cb_user_id != user_id or user_id not in user_search_results:
                await query.edit_message_text("❌ Bu axtarış sessiyası bitib. Zəhmət olmasa yenidən axtarın.")
                return
            
            # Update keyboard for new page
            search_results = user_search_results[user_id]
            keyboard = create_paginated_keyboard(search_results, page, user_id)
            
            await query.edit_message_reply_markup(reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling button callback: {str(e)}")
        await query.edit_message_text(ERROR_MESSAGES["general_error"])

async def process_youtube_url_from_callback(query, context: ContextTypes.DEFAULT_TYPE, url: str, title: str) -> None:
    """Process YouTube URL from button callback"""
    try:
        # Initialize YouTube processor
        processor = YouTubeProcessor()
        
        # Simulated progress updates
        async def simulate_progress():
            try:
                progress_steps = [
                    (f"📥 Yüklənir: {title} (15.6%)", 1),
                    (f"📥 Yüklənir: {title} (31.2%)", 1.5),
                    (f"📥 Yüklənir: {title} (48.8%)", 1),
                    (f"📥 Yüklənir: {title} (64.3%)", 1.5),
                    (f"📥 Yüklənir: {title} (79.7%)", 1),
                    (f"📥 Hazırlanır: {title}", 0.5)
                ]
                
                for message, delay in progress_steps:
                    await asyncio.sleep(delay)
                    try:
                        await query.edit_message_text(message)
                    except:
                        break
            except Exception as e:
                logger.debug(f"Progress simulation error: {e}")

        # Start progress simulation and download simultaneously
        progress_task = asyncio.create_task(simulate_progress())
        result = await processor.download_and_convert(url)
        
        # Cancel progress simulation
        progress_task.cancel()
        
        if not result["success"]:
            error_msg = result["error"]
            # Check if it's a video unavailable error
            if "unavailable" in error_msg.lower() or "not available" in error_msg.lower():
                await query.edit_message_text(f"❌ Video əlçatan deyil: {title}\nZəhmət olmasa axtarış nəticələrindən başqa mahnı sınayın.")
            else:
                await query.edit_message_text(f"❌ Yüklənə bilmədi: {title}\n{error_msg}")
            return
        
        # Update progress for upload
        await query.edit_message_text(f"📤 Köçürülür: {title}")
        
        # Send the MP3 file
        with open(result["file_path"], 'rb') as audio_file:
            # Clean title by removing channel/uploader name from beginning
            clean_title = result["title"]
            uploader = result["uploader"]
            
            # Remove uploader/channel name from the beginning of title if present
            if uploader and clean_title.startswith(uploader):
                # Remove uploader name and any following separator (-, –, |, etc.)
                clean_title = clean_title[len(uploader):].strip()
                # Remove common separators from the beginning
                for sep in ['-', '–', '|', ':', '•']:
                    if clean_title.startswith(sep):
                        clean_title = clean_title[1:].strip()
                        break
            
            # Send audio with clean title only (no performer to avoid duplication)
            await context.bot.send_audio(
                chat_id=query.message.chat.id,
                audio=audio_file,
                title=clean_title,
                duration=result["duration"]
            )
        
        # Update final message
        await query.edit_message_text(f"✅ Köçürüldü: {title}")
        
        # Clean up the file immediately after upload
        cleanup_temp_files([result["file_path"]])
        
        # Clean up search results for this user
        user_id = query.from_user.id
        if user_id in user_search_results:
            del user_search_results[user_id]
        
    except Exception as e:
        logger.error(f"Error processing URL from callback {url}: {str(e)}")
        # Check if it's a video unavailable error in the exception
        if "unavailable" in str(e).lower() or "not available" in str(e).lower():
            await query.edit_message_text(f"❌ Video əlçatan deyil: {title}\nZəhmət olmasa axtarış nəticələrindən başqa mahnı sınayın.")
        else:
            await query.edit_message_text(f"❌ Yüklənmə xətası: {title}")

# Keep old function name for compatibility
url_handler = message_handler

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(ERROR_MESSAGES["general_error"])
