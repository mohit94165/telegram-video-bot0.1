import os
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
import yt_dlp

BOT_TOKEN = os.getenv("8508688706:AAHu1wJTzcklvb9Ijp5dMkrC3U0qXxIBIHA")

async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not url.startswith("http"):
        await update.message.reply_text("Send a valid video link.")
        return

    await update.message.reply_text("Downloading video...")

    ydl_opts = {
        'outtmpl': 'video.%(ext)s',
        'format': 'mp4',
        'noplaylist': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for file in os.listdir():
            if file.startswith("video."):
                await update.message.reply_document(document=open(file, 'rb'))
                os.remove(file)
                break

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

app = ApplicationBuilder().token(8508688706:AAHu1wJTzcklvb9Ijp5dMkrC3U0qXxIBIHA).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
app.run_polling()
