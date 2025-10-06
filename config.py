# Bot configuration

import os

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")

MAX_FILE_SIZE_MB = 49  # Maximum possible for Telegram (49.5MB limit)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
DOWNLOAD_TIMEOUT = 600  # Increased to 10 minutes for large files
TEMP_DIR = "temp_downloads"
RATE_LIMIT_SECONDS = 0  # Completely disabled - unlimited requests
AUDIO_QUALITY = "192"
AUDIO_FORMAT = "mp3"

# YouTube Cookies (optional - helps bypass restrictions)
YOUTUBE_COOKIES = os.getenv("YOUTUBE_COOKIES", None)
COOKIES_FILE = "cookies.txt" if os.path.exists("cookies.txt") else None

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
• Telegram limitlərinə görə 49MB-dan böyük fayllar göndərilə bilməz.
• Limitsiz istifadə - istənilən qədər mahnı yükləyə bilərsiniz
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
• Maksimum fayl ölçüsü: 49MB (Telegram limiti)
• Məhdudiyyət: YOX - Limitsiz istifadə
• Yalnız YouTube mahnıları

*Problem yaşayırsınız?*
YouTube linkinizin etibarlı olduğundan və mahnının ictimai əlçatan olduğundan əmin olun.
"""

ERROR_MESSAGES = {
    "invalid_url": "❌ Yanlış YouTube linki. Zəhmət olmasa etibarlı YouTube linki göndərin.",
    "download_failed": "❌ Mahnı yüklənə bilmədi. Zəhmət olmasa linki yoxlayın və yenidən cəhd edin.",
    "file_too_large": f"❌ Fayl çox böyükdür ({MAX_FILE_SIZE_MB}MB-dan çox). Telegram bu qədər böyük faylları dəstəkləmir.",
    "conversion_failed": "❌ Mahnı MP3-ə çevrilə bilmədi. Zəhmət olmasa yenidən cəhd edin.",
    "general_error": "❌ Xəta baş verdi. Zəhmət olmasa sonra yenidən cəhd edin.",
    "connection_error": "❌ İnternet bağlantısı problemi. Bir neçə dəqiqə gözləyin və yenidən cəhd edin.",
    "timeout_error": "❌ Zaman aşımı baş verdi. Video çox böyük ola bilər. Yenidən cəhd edin.",
    "search_failed": "❌ Axtarış uğursuz oldu. İnternet bağlantınızı yoxlayın və yenidən cəhd edin."
}
