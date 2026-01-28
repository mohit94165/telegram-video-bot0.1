import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import asyncio

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token from environment variable
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Send me a video URL and I\'ll download it for you!\n'
        'Supported sites: YouTube, Twitter, Instagram, TikTok, and many more.'
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    chat_id = update.message.chat_id
    
    # Send initial message
    status_msg = await update.message.reply_text('⏳ Processing your request...')
    
    try:
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'max_filesize': 50 * 1024 * 1024,  # 50MB limit for Telegram
        }
        
        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await status_msg.edit_text('⬇️ Downloading video...')
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            title = info.get('title', 'Video')
        
        # Check file size
        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:
            await status_msg.edit_text('❌ Video is too large (max 50MB for Telegram)')
            os.remove(filename)
            return
        
        # Upload to Telegram
        await status_msg.edit_text('⬆️ Uploading to Telegram...')
        with open(filename, 'rb') as video:
            await context.bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=title,
                supports_streaming=True
            )
        
        # Cleanup
        await status_msg.delete()
        os.remove(filename)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await status_msg.edit_text(f'❌ Error: {str(e)}')

def main():
    # Create downloads directory
    os.makedirs('downloads', exist_ok=True)
    
    # Create application
    application = Application.builder().token(TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Start bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
