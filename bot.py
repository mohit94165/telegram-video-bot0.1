import os
import logging
import tempfile
import asyncio
from typing import Optional
from urllib.parse import urlparse

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
import yt_dlp

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Telegram limit for bots)
ALLOWED_DOMAINS = ['youtube.com', 'youtu.be', 'twitter.com', 'x.com', 'tiktok.com', 
                  'instagram.com', 'facebook.com', 'reddit.com', 'vimeo.com', 'dailymotion.com']

class VideoDownloaderBot:
    def __init__(self):
        self.session = None
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a welcome message when the command /start is issued."""
        user = update.effective_user
        welcome_text = f"""
👋 Hello {user.first_name}!

I'm a Video Downloader Bot. Send me a video link and I'll download it for you!

📋 **Supported Platforms:**
• YouTube
• Instagram
• TikTok
• Twitter/X
• Facebook
• Reddit
• Vimeo
• Dailymotion

⚠️ **Limitations:**
• Max file size: 50MB
• Video must be publicly accessible

🚀 **How to use:**
Just send me a valid video URL!
        """
        await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a help message."""
        help_text = """
📖 **Help Guide**

Send me a video URL from any supported platform.
I'll download it and send it back to you.

📝 **Example links:**
• YouTube: https://youtube.com/watch?v=...
• Instagram: https://instagram.com/reel/...
• TikTok: https://tiktok.com/@user/video/...

⚙️ **Commands:**
/start - Start the bot
/help - Show this help message
/about - Bot information

🔧 **Note:**
Some videos might be restricted or require login. I can only download publicly available videos.
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    async def about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show about information."""
        about_text = """
🤖 **Video Downloader Bot**
Version: 1.0.0

This bot downloads videos from various platforms using yt-dlp.

📦 **Features:**
• Support for multiple platforms
• Automatic format selection
• Compress large videos
• Fast and reliable

🛠 **Built with:**
• python-telegram-bot
• yt-dlp
• aiohttp

⚡ **Hosted on Railway**
        """
        await update.message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)
        
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and from allowed domain."""
        try:
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                domain = result.netloc.lower()
                return any(allowed in domain for allowed in ALLOWED_DOMAINS)
        except:
            return False
        return False
        
    async def download_video(self, url: str) -> Optional[str]:
        """Download video using yt-dlp."""
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        ydl_opts = {
            'format': 'best[filesize<50M]',
            'outtmpl': temp_path,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info and os.path.exists(temp_path):
                    file_size = os.path.getsize(temp_path)
                    if file_size > MAX_FILE_SIZE:
                        # Try to get a smaller version
                        ydl_opts['format'] = 'worst[filesize<50M]'
                        with yt_dlp.YoutubeDL(ydl_opts) as ydl_small:
                            ydl_small.extract_info(url, download=True)
                    return temp_path
        except Exception as e:
            logger.error(f"Download error: {e}")
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            return None
            
        return None
        
    async def handle_video_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming video links."""
        url = update.message.text.strip()
        
        if not self.is_valid_url(url):
            await update.message.reply_text(
                "❌ Invalid URL or unsupported platform.\n"
                "Please send a valid video URL from supported platforms.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Send processing message
        processing_msg = await update.message.reply_text(
            "⏳ Processing your request...\n"
            "Downloading video..."
        )
        
        try:
            # Download video
            video_path = await asyncio.to_thread(self.download_video, url)
            
            if not video_path or not os.path.exists(video_path):
                await processing_msg.edit_text("❌ Failed to download video. It might be private or unavailable.")
                return
                
            file_size = os.path.getsize(video_path)
            
            if file_size > MAX_FILE_SIZE:
                await processing_msg.edit_text(
                    f"❌ Video is too large ({file_size/1024/1024:.1f}MB).\n"
                    f"Telegram bot limit is {MAX_FILE_SIZE/1024/1024:.0f}MB."
                )
                os.unlink(video_path)
                return
                
            # Update status
            await processing_msg.edit_text("📤 Uploading to Telegram...")
            
            # Send video
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"✅ Downloaded successfully!\n📁 Size: {file_size/1024/1024:.1f}MB",
                    supports_streaming=True
                )
                
            await processing_msg.edit_text("✅ Done!")
            
        except Exception as e:
            logger.error(f"Error: {e}")
            await processing_msg.edit_text(f"❌ Error: {str(e)}")
            
        finally:
            # Cleanup
            if 'video_path' in locals() and video_path and os.path.exists(video_path):
                try:
                    os.unlink(video_path)
                except:
                    pass
                    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors."""
        logger.error(f"Exception while handling an update: {context.error}")
        
        if update and isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again later."
            )

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
        
    bot = VideoDownloaderBot()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("about", bot.about))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_video_link))
    
    # Register error handler
    application.add_error_handler(bot.error_handler)
    
    # Start bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
