import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram Bot Token
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Admin User IDs
    ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x]
    
    # Max file size for Telegram (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Download path
    DOWNLOAD_PATH = "downloads"
    
    # Supported domains
    SUPPORTED_DOMAINS = [
        "youtube.com",
        "youtu.be",
        "twitter.com",
        "x.com",
        "tiktok.com",
        "instagram.com",
        "facebook.com",
        "reddit.com",
        "vimeo.com",
        "dailymotion.com",
        "twitch.tv"
    ]
    
    # Premium features
    PREMIUM_USERS = []
    PREMIUM_MAX_SIZE = 200 * 1024 * 1024  # 200MB for premium
