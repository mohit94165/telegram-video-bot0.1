import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# Set up logging to see errors in the console
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# 1. The Download Function
def download_video(url):
    """
    Downloads the video from the given URL using yt-dlp.
    Returns the filename of the downloaded video.
    """
    # Options for yt-dlp
    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # Try to get MP4, or best available
        'outtmpl': '%(id)s.%(ext)s',     # Name the file using the video ID
        'quiet': True,                   # Don't print too much to logs
        'noplaylist': True,              # Download only single video, not playlist
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        print(f"Error downloading: {e}")
        return None

# 2. The Message Handler
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_url = update.message.text
    
    # Check if text looks like a URL
    if not user_url.startswith("http"):
        await update.message.reply_text("Please send a valid video link starting with http or https.")
        return

    status_msg = await update.message.reply_text("⏳ Downloading video... please wait.")

    # Run the download in a separate thread so the bot doesn't freeze
    loop =  os.get_running_loop()
    # We use run_in_executor because downloading is a blocking operation
    filename = await loop.run_in_executor(None, download_video, user_url)

    if filename and os.path.exists(filename):
        try:
            # Check file size (Telegram limit is 50MB for bots)
            file_size = os.path.getsize(filename)
            limit_mb = 50 * 1024 * 1024 # 50 MB in bytes

            if file_size > limit_mb:
                await status_msg.edit_text(f"❌ Video is too large ({file_size / (1024*1024):.2f} MB). Telegram bots are limited to 50MB uploads.")
            else:
                await status_msg.edit_text("Uploading to Telegram...")
                await context.bot.send_video(chat_id=update.effective_chat.id, video=open(filename, 'rb'))
                await status_msg.delete()
        except Exception as e:
            await status_msg.edit_text(f"❌ Error sending video: {e}")
        finally:
            # Cleanup: Delete the file after sending (or failing)
            if os.path.exists(filename):
                os.remove(filename)
    else:
        await status_msg.edit_text("❌ Could not download video. The link might be invalid or unsupported.")

# 3. Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me a video link and I will try to download it for you.")

# Main Execution
if __name__ == '__main__':
    # Get the token from environment variables (for security)
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN not found in environment variables.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    # Filter to handle text messages that are not commands
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(start_handler)
    application.add_handler(message_handler)

    print("Bot is running...")
    application.run_polling()
