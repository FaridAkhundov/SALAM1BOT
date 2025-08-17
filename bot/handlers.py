# Telegram bot handlers

import asyncio
import logging
import os
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from config import WELCOME_MESSAGE, HELP_MESSAGE, ERROR_MESSAGES, RATE_LIMIT_SECONDS
from bot.youtube_processor import YouTubeProcessor
from bot.utils import is_valid_youtube_url, cleanup_temp_files, clean_youtube_url

logger = logging.getLogger(__name__)

user_last_request = {}
user_search_results = {}
user_search_timestamps = {}  # Track when each search was created
user_search_sessions = {}     # Track session IDs to invalidate old searches

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME_MESSAGE, parse_mode='Markdown')

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_MESSAGE, parse_mode='Markdown')

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message or not update.message.text:
        return
        
    user_id = update.effective_user.id
    message_text = update.message.text.strip()
    
    # UNLIMITED MULTITASKING - No limits, no queues, fire-and-forget processing
    # Users can send 50+ downloads simultaneously without any restrictions
    
    # Create new search session if it's a song search (invalidates old searches)
    if not is_valid_youtube_url(message_text):
        # Generate new session ID to invalidate old search buttons
        import time
        new_session_id = time.time()
        user_search_sessions[user_id] = new_session_id
        user_search_timestamps[user_id] = datetime.now()
    
    # Process ALL requests concurrently - no limits, no waiting
    if is_valid_youtube_url(message_text):
        clean_url = clean_youtube_url(message_text)
        # Fire-and-forget: unlimited concurrent downloads
        asyncio.create_task(process_youtube_url(update, context, clean_url))
    else:
        # Fire-and-forget: unlimited concurrent searches  
        asyncio.create_task(process_song_search(update, context, message_text))

async def process_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str) -> None:
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    processing_msg = await update.message.reply_text("🎵 Mahnı hazırlanır...")
    
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
        
        # Send the MP3 file with thumbnail
        thumbnail_file = None
        try:
            # Check if we have a thumbnail file
            thumbnail_path = result.get("thumbnail_path")
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_file = open(thumbnail_path, 'rb')
            
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
                
                # Send audio with separate thumbnail file
                await context.bot.send_audio(
                    chat_id=update.effective_chat.id,
                    audio=audio_file,
                    thumbnail=thumbnail_file,
                    title=clean_title,
                    duration=result["duration"],
                    performer=uploader if uploader and uploader != "Unknown Artist" else None
                )
        finally:
            if thumbnail_file:
                thumbnail_file.close()
        
        # Update progress after successful upload
        await processing_msg.edit_text("✅ Köçürüldü!")
        
        # Clean up the files immediately after upload
        files_to_cleanup = [result["file_path"]]
        if result.get("thumbnail_path") and os.path.exists(result["thumbnail_path"]):
            files_to_cleanup.append(result["thumbnail_path"])
        cleanup_temp_files(files_to_cleanup)
        
        # Delete processing message after a moment
        await asyncio.sleep(1)
        await processing_msg.delete()
        
    except Exception as e:
        logger.error(f"Error processing URL {url}: {str(e)}")
        await processing_msg.edit_text(ERROR_MESSAGES["general_error"])

async def process_song_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
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
        
        # Store search results for pagination with timestamp and session ID
        current_session = datetime.now().timestamp()  # Use timestamp as unique session ID
        user_search_results[user_id] = search_results
        user_search_timestamps[user_id] = datetime.now()
        user_search_sessions[user_id] = current_session
        
        # Create paginated keyboard for first page with session ID
        keyboard = create_paginated_keyboard(search_results, page=0, user_id=user_id, session_id=current_session)
        
        await searching_msg.edit_text(
            f"🎵 *{query}* üçün {len(search_results)} mahnı tapıldı\n\nSəhifə 1/3 - Mahnı seçin:",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error searching for '{query}': {str(e)}")
        await searching_msg.edit_text(ERROR_MESSAGES["general_error"])

def create_paginated_keyboard(results: list, page: int, user_id: int, session_id: float) -> InlineKeyboardMarkup:
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
            callback_data=f"song_{user_id}_{i}_{session_id}"
        )])
    
    # Add navigation buttons
    nav_buttons = []
    total_pages = min(3, (len(results) + 7) // 8)  # Max 3 pages
    
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Əvvəlki", callback_data=f"page_{user_id}_{page-1}_{session_id}"))
    
    if page < total_pages - 1 and page < 2:  # Max 3 pages (0, 1, 2)
        nav_buttons.append(InlineKeyboardButton("Növbəti ➡️", callback_data=f"page_{user_id}_{page+1}_{session_id}"))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    
    return InlineKeyboardMarkup(buttons)

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    try:
        if callback_data.startswith("song_"):
            # Handle song selection
            parts = callback_data.split("_")
            if len(parts) < 4:  # Backward compatibility with old format
                _, cb_user_id, song_idx = parts
                cb_session_id = None
            else:
                _, cb_user_id, song_idx, cb_session_id = parts
                cb_session_id = float(cb_session_id)
            cb_user_id = int(cb_user_id)
            song_idx = int(song_idx)
            
            # Verify user owns this search and check session validity
            if cb_user_id != user_id or user_id not in user_search_results:
                await query.edit_message_text("❌ Bu axtarışın vaxtı keçib. Yenidən axtarış edin.")
                return
            
            # Check if this search session is still valid (not expired by newer search)
            if cb_session_id and user_id in user_search_sessions:
                current_session = user_search_sessions[user_id]
                # If user has made a new search, invalidate old buttons
                if cb_session_id != current_session:
                    await query.edit_message_text("⏱️ Bu axtarışın vaxtı keçib - yeni axtarış edilib. Köhnə nəticələr artıq işləmir.")
                    return
            
            # Time-based expiry check (1 hour)
            if user_id in user_search_timestamps:
                current_search_time = user_search_timestamps[user_id]
                time_diff = datetime.now() - current_search_time
                if time_diff.total_seconds() > 3600:  # 1 hour expiry
                    await query.edit_message_text("⌛ Bu axtarışın müddəti bitib (1 saat). Yeni axtarış edin.")
                    return
            
            # Get selected song
            search_results = user_search_results[user_id]
            if song_idx >= len(search_results):
                await query.edit_message_text("❌ Yanlış seçim. Zəhmət olmasa yenidən axtarın.")
                return
            
            selected_song = search_results[song_idx]
            
            # Process the selected song with real-time progress
            await process_youtube_url_from_callback(query, context, selected_song['url'], selected_song['title'])
            
        elif callback_data.startswith("page_"):
            # Handle page navigation
            parts = callback_data.split("_")
            if len(parts) < 4:  # Backward compatibility with old format
                _, cb_user_id, page = parts
                cb_session_id = None
            else:
                _, cb_user_id, page, cb_session_id = parts
                cb_session_id = float(cb_session_id)
            cb_user_id = int(cb_user_id)
            page = int(page)
            
            # Verify user owns this search and check session validity  
            if cb_user_id != user_id or user_id not in user_search_results:
                await query.edit_message_text("❌ Bu səhifənin vaxtı keçib. Yenidən axtarış edin.")
                return
            
            # Check if this search session is still valid (not expired by newer search)
            if cb_session_id and user_id in user_search_sessions:
                current_session = user_search_sessions[user_id]
                # If user has made a new search, invalidate old buttons
                if cb_session_id != current_session:
                    await query.edit_message_text("⏱️ Bu səhifənin vaxtı keçib - yeni axtarış edilib. Köhnə səhifələr artıq işləmir.")
                    return
            
            # Time-based expiry check (1 hour)
            if user_id in user_search_timestamps:
                current_search_time = user_search_timestamps[user_id]
                time_diff = datetime.now() - current_search_time
                if time_diff.total_seconds() > 3600:  # 1 hour expiry
                    await query.edit_message_text("⌛ Bu səhifənin müddəti bitib (1 saat). Yeni axtarış edin.")
                    return
            
            # Update keyboard for new page
            search_results = user_search_results[user_id]
            # Get current session ID for this user
            current_session = user_search_sessions.get(user_id, 0)
            keyboard = create_paginated_keyboard(search_results, page, user_id, current_session)
            
            await query.edit_message_reply_markup(reply_markup=keyboard)
            
    except Exception as e:
        logger.error(f"Error handling button callback: {str(e)}")
        await query.edit_message_text(ERROR_MESSAGES["general_error"])

async def process_youtube_url_from_callback(query, context: ContextTypes.DEFAULT_TYPE, url: str, title: str) -> None:
    """Process YouTube URL from button callback"""
    try:
        # Start with initial processing message
        await query.edit_message_text("🎵 Mahnı hazırlanır...")
        
        # Initialize YouTube processor
        processor = YouTubeProcessor()
        
        # Real-time progress callback - same as direct URL downloads
        async def update_progress(message):
            try:
                await query.edit_message_text(message)
            except Exception as e:
                logger.debug(f"Progress update error: {e}")

        # Start download with real-time progress - same as direct downloads
        result = await processor.download_and_convert(url, progress_callback=update_progress)
        
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
        
        # Send the MP3 file with thumbnail  
        thumbnail_file = None
        try:
            # Check if we have a thumbnail file
            thumbnail_path = result.get("thumbnail_path")
            if thumbnail_path and os.path.exists(thumbnail_path):
                thumbnail_file = open(thumbnail_path, 'rb')
            
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
                
                # Send audio with separate thumbnail file
                await context.bot.send_audio(
                    chat_id=query.message.chat.id,
                    audio=audio_file,
                    thumbnail=thumbnail_file,
                    title=clean_title,
                    duration=result["duration"],
                    performer=uploader if uploader and uploader != "Unknown Artist" else None
                )
        finally:
            if thumbnail_file:
                thumbnail_file.close()
        
        # Update final message
        await query.edit_message_text(f"✅ Köçürüldü: {title}")
        
        # Clean up the files immediately after upload
        files_to_cleanup = [result["file_path"]]
        if result.get("thumbnail_path") and os.path.exists(result["thumbnail_path"]):
            files_to_cleanup.append(result["thumbnail_path"])
        cleanup_temp_files(files_to_cleanup)
        
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

url_handler = message_handler

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.message:
        await update.message.reply_text(ERROR_MESSAGES["general_error"])
