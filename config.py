"""
Configuration settings for the Telegram YouTube to MP3 Bot
"""

import os

# Telegram Bot Token - get from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")

# File size limits (Telegram has 50MB limit)
MAX_FILE_SIZE_MB = 45  # Leave some buffer
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Download settings (optimized for speed)
DOWNLOAD_TIMEOUT = 45  # 45 seconds for faster timeout
TEMP_DIR = "temp_downloads"

# Rate limiting (simple per-user)
RATE_LIMIT_SECONDS = 0  # No rate limiting

# Audio quality settings
AUDIO_QUALITY = "192"  # 192 kbps
AUDIO_FORMAT = "mp3"

# Bot messages
WELCOME_MESSAGE = """
🎵 *YouTube-dan MP3 Çevirici Bot* 🎵

Xoş gəlmisiniz! Mən sizin üçün YouTube mahnılarını MP3 fayllarına çevirə bilərəm.

*Necə istifadə etmək:*
• Birbaşa yükləmək üçün YouTube mahnı linkini göndərin
• Mahnı adını yazın və nəticələrdən seçin
• Mən onu yükləyib MP3-ə çevirərəm
• Audio faylı alacaqsınız

*Əmrlər:*
/start - Bu xoş gəldin mesajını göstər
/help - Kömək və istifadə təlimatları

*Qeyd:* 
• Telegram limitlərinə görə 45MB-dan böyük fayllar göndərilə bilməz.
• Sözlüklə axtarılan mahnılar düzgün təqdim edilməyə bilər. Bu halda YouTube linki ilə atmağa cəhd edin.
"""

HELP_MESSAGE = """
🔧 *Kömək və Təlimatlar* 🔧

*Musiqi almağın iki yolu:*
1. *Birbaşa Link:* Dərhal yükləmək üçün YouTube linki göndərin
2. *Axtarış:* Hər hansı mahnı adı yazın və axtarış nəticələrindən seçin

*Dəstəklənən Linklər:*
• youtube.com/watch?v=...
• youtu.be/...
• m.youtube.com/watch?v=...

*Axtarış Xüsusiyyətləri:*
• Hər axtarışda 24-ə qədər nəticə
• Hər səhifədə 8 mahnı, maksimum 3 səhifə
• Əvvəlki/Növbəti düymələri ilə asan naviqasiya

*Xüsusiyyətlər:*
• Yüksək keyfiyyətli MP3 çevrilməsi (192 kbps)
• Avtomatik fayl təmizliyi
• Yanlış linklər üçün xəta idarəetməsi
• Fayl ölçüsü yoxlanması

*Məhdudiyyətlər:*
• Maksimum fayl ölçüsü: 45MB
• Məhdudiyyət: Hər istifadəçi üçün 30 saniyədə bir sorğu
• Yalnız YouTube mahnıları

*Problem yaşayırsınız?*
YouTube linkinizin etibarlı olduğundan və mahnının ictimai əlçatan olduğundan əmin olun.
"""

ERROR_MESSAGES = {
    "invalid_url": "❌ Yanlış YouTube linki. Zəhmət olmasa etibarlı YouTube linki göndərin.",
    "download_failed": "❌ Mahnı yüklənə bilmədi. Zəhmət olmasa linki yoxlayın və yenidən cəhd edin.",
    "file_too_large": f"❌ Fayl çox böyükdür ({MAX_FILE_SIZE_MB}MB-dan çox). Telegram bu qədər böyük faylları dəstəkləmir.",
    "conversion_failed": "❌ Mahnı MP3-ə çevrilə bilmədi. Zəhmət olmasa yenidən cəhd edin.",
    "rate_limited": "⏰ Çox tez sorğu göndərirsiniz, bir az gözləyin.",
    "general_error": "❌ Xəta baş verdi. Zəhmət olmasa sonra yenidən cəhd edin."
}
