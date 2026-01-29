import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import asyncio

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
BOT_TOKEN = os.getenv('BOT_TOKEN')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        'Hi! Send me an xHamster video link and I will download it for you.\n\n'
        'Just paste the video URL and I\'ll process it!'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        'Send me an xHamster video link and I will download it for you.\n\n'
        'Supported format: https://xhamster.com/videos/...'
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download video from xHamster link."""
    url = update.message.text.strip()
    
    # Check if the URL is from xHamster
    if 'xhamster' not in url.lower():
        await update.message.reply_text(
            'Please send a valid xHamster video link.'
        )
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text('Processing your video... ⏳')
    
    try:
        # Create downloads directory if it doesn't exist
        download_dir = 'downloads'
        os.makedirs(download_dir, exist_ok=True)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(download_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        # Download video info first
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'video')
            
            await processing_msg.edit_text(f'Downloading: {video_title}... 📥')
            
            # Download the video
            ydl.download([url])
            
            # Find the downloaded file
            filename = ydl.prepare_filename(info)
            
            if not os.path.exists(filename):
                raise FileNotFoundError(f"Downloaded file not found: {filename}")
            
            file_size = os.path.getsize(filename)
            
            # Telegram file size limit is 50MB for bots (2GB for premium users)
            if file_size > 50 * 1024 * 1024:
                await processing_msg.edit_text(
                    f'❌ Video is too large ({file_size / (1024*1024):.1f}MB). '
                    f'Telegram bot limit is 50MB.'
                )
                os.remove(filename)
                return
            
            await processing_msg.edit_text('Uploading to Telegram... 📤')
            
            # Send the video
            with open(filename, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=video_title,
                    supports_streaming=True
                )
            
            # Delete the processing message
            await processing_msg.delete()
            
            # Clean up - delete the downloaded file
            os.remove(filename)
            
    except yt_dlp.utils.DownloadError as e:
        await processing_msg.edit_text(
            f'❌ Error downloading video: {str(e)}\n\n'
            'Please make sure the link is valid and the video is accessible.'
        )
        logger.error(f"Download error: {e}")
    
    except Exception as e:
        await processing_msg.edit_text(
            f'❌ An error occurred: {str(e)}'
        )
        logger.error(f"Error: {e}", exc_info=True)

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))
    
    # Start the bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
