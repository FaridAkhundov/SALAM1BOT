# Xarici Serverdə Quraşdırma Təlimatı

Bu bot xarici serverdə (VPS, cloud server və s.) işləməsi üçün hazırlanıb.

## 1. Sistem Tələbləri

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip ffmpeg

# CentOS/RHEL
sudo yum install -y python3 python3-pip ffmpeg

# macOS
brew install python3 ffmpeg
```

## 2. Python Paketlərinin Quraşdırılması

```bash
# Virtual environment yaratmaq (tövsiyə olunur)
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# və ya
venv\Scripts\activate  # Windows

# Paketləri install et
pip install -r requirements.txt
```

## 3. Bot Token Konfiqurasiyası

```bash
# .env faylı yarat
echo "BOT_TOKEN=sizin_telegram_bot_token" > .env

# Və ya environment variable kimi əlavə et
export BOT_TOKEN="sizin_telegram_bot_token"
```

## 4. YouTube Cookie Problemi Həlli (VACİB!)

YouTube artıq bot detection istifadə edir. Əgər "Please sign in" xətası alırsınızsa, cookie lazımdır.

### Cookies Necə Əldə Etmək:

**Üsul 1: Browser Extension (Asan)**

1. Chrome və ya Firefox-da [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) extension-ı quraşdır
2. YouTube.com-a daxil ol
3. Extension ikonuna bas və "Export" düyməsini seç
4. `cookies.txt` faylını bot qovluğuna köçür

**Üsul 2: Browser DevTools**

1. YouTube.com-a daxil ol
2. F12 bas (DevTools)
3. Network tab-a get
4. Səhifəni yenilə (F5)
5. İstənilən request-ə klik et
6. Headers bölməsində "Cookie" başlığını tap və kopyala

**Üsul 3: yt-dlp-dən avtomatik (Ən asan)**

```bash
# Chrome-dan cookie götür
yt-dlp --cookies-from-browser chrome --cookies cookies.txt https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Firefox-dan cookie götür  
yt-dlp --cookies-from-browser firefox --cookies cookies.txt https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

### Cookies.txt Faylı Formatı:

```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	0	CONSENT	YES+
.youtube.com	TRUE	/	FALSE	1234567890	VISITOR_INFO1_LIVE	xxx
```

Cookie faylını bot qovluğuna `cookies.txt` adı ilə qoy.

## 5. Botu İşə Salma

```bash
# Birbaşa işə sal
python main.py

# Və ya background-da işlət (Linux)
nohup python main.py > bot.log 2>&1 &

# Və ya systemd service yarat (uzunmüddətli işləmə üçün)
```

## 6. Systemd Service Yaratma (Ubuntu/Debian)

Uzunmüddətli və avtomatik restart üçün:

```bash
# /etc/systemd/system/telegram-bot.service faylı yarat
sudo nano /etc/systemd/system/telegram-bot.service
```

Aşağıdakı məzmunu əlavə et:

```ini
[Unit]
Description=Telegram YouTube MP3 Bot
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/bot
Environment="BOT_TOKEN=your_bot_token"
ExecStart=/path/to/venv/bin/python /path/to/bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Sonra:

```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

## 7. Docker ilə İşlətmək

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Çalıştır:

```bash
docker build -t telegram-bot .
docker run -d --name telegram-bot -e BOT_TOKEN="your_token" telegram-bot
```

## Problemlər və Həllər

### YouTube "Sign in" xətası
- Cookie faylı əlavə et (bax yuxarıda)
- yt-dlp-ni yenilə: `pip install --upgrade yt-dlp`

### FFmpeg tapılmır
```bash
sudo apt-get install ffmpeg
# və ya
sudo yum install ffmpeg
```

### Rate limiting
- VPN istifadə et
- Proxy əlavə et
- IP address dəyiş

### Bot işləmir
- Log-lara bax: `tail -f bot.log`
- Bot token-ın düzgün olduğunu yoxla
- İnternet bağlantısını yoxla
