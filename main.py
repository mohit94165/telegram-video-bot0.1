import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yt_dlp

# Set up logging to see errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Get token from environment variables (for security)
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Send me a video link (YouTube, Instagram, TikTok, etc.), and I'll download it for you!"
    )

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    status_msg = await context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Downloading...")

    # Unique filename based on update ID to prevent conflicts
    file_name = f"video_{update.update_id}.mp4"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',  # Download best quality mp4
        'outtmpl': file_name,            # Save as our filename
        'quiet': True,
    }

    try:
        # 1. Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info.get('title', 'Video')

        # 2. Send the video to the user
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text="⬆️ Uploading...")
        
        with open(file_name, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=video_file,
                caption=f"🎥 {video_title}",
                supports_streaming=True
            )
        
        # 3. Cleanup: Delete the file after sending
        os.remove(file_name)
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)

    except Exception as e:
        error_text = str(e)
        if "File is too big" in error_text:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text="❌ Error: File is too large for Telegram (Limit is 50MB).")
        else:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text="❌ Failed to download. Invalid link or private video.")
        
        # Clean up if file was created but upload failed
        if os.path.exists(file_name):
            os.remove(file_name)

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN is missing!")
    else:
        application = ApplicationBuilder().token(TOKEN).build()
        
        # Handlers
        application.add_handler(CommandHandler('start', start))
        application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), download_video))
        
        application.run_polling()
