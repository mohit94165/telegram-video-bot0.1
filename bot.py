import os
import logging
import tempfile
import requests
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
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message"""
    await update.message.reply_text(
        "🎬 *Video Downloader Bot*\n\n"
        "Send me YouTube/TikTok/Instagram video link!\n\n"
        "Commands:\n"
        "/start - Start bot\n"
        "/help - Help guide",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    await update.message.reply_text(
        "📖 *How to use:*\n"
        "1. Copy video URL\n"
        "2. Send it to me\n"
        "3. I'll download and send it back\n\n"
        "✅ *Supported:*\n"
        "• YouTube\n"
        "• TikTok\n"
        "• Instagram\n"
        "• Twitter/X\n\n"
        "⚠️ *Limit:* Max 50MB",
        parse_mode=ParseMode.MARKDOWN
    )

def download_video_simple(url):
    """Download video - SIMPLE VERSION"""
    try:
        # Create temp file
        temp_file = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        # Download options
        ydl_opts = {
            'outtmpl': temp_path,
            'format': 'best[filesize<50M]/best',
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        # Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Check if file exists and size
        if os.path.exists(temp_path):
            size = os.path.getsize(temp_path)
            if size > 0 and size <= MAX_FILE_SIZE:
                return temp_path
            else:
                os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Download error: {e}")
        if os.path.exists(temp_path):
            os.remove(temp_path)
    return None

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video links"""
    message = update.message.text.strip()
    
    # Check if it's a URL
    if not (message.startswith('http://') or message.startswith('https://')):
        await update.message.reply_text("❌ Please send a valid video URL starting with http:// or https://")
        return
    
    # Send processing message
    status_msg = await update.message.reply_text("⏳ Downloading video...")
    
    try:
        # Download video
        video_path = download_video_simple(message)
        
        if not video_path:
            await status_msg.edit_text("❌ Failed to download. Video might be private or too large (>50MB).")
            return
        
        # Get file size
        file_size = os.path.getsize(video_path)
        
        # Send video
        await status_msg.edit_text("📤 Uploading to Telegram...")
        
        with open(video_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=f"✅ Downloaded!\nSize: {file_size/1024/1024:.1f}MB",
                supports_streaming=True,
                read_timeout=60,
                write_timeout=60,
                connect_timeout=60,
                pool_timeout=60
            )
        
        await status_msg.edit_text("✅ Done!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f"❌ Error: {str(e)[:100]}")
    
    finally:
        # Cleanup
        if 'video_path' in locals() and video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
            except:
                pass

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text("❌ Sorry, something went wrong. Try again!")
    except:
        pass

def main():
    """Start the bot"""
    if not BOT_TOKEN:
        print("❌ ERROR: BOT_TOKEN not found in .env file!")
        print("Please add: BOT_TOKEN=your_token_here to .env file")
        return
    
    print("🤖 Starting Video Downloader Bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    # Start bot
    app.run_polling()

if __name__ == '__main__':
    main()
