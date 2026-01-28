import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_quality = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 Download Video", callback_data="download")],
        [InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data="audio")]
    ]
    await update.message.reply_text(
        "👋 Send video link after selecting option.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "download":
        keyboard = [
            [InlineKeyboardButton("360p", callback_data="360")],
            [InlineKeyboardButton("720p", callback_data="720")],
            [InlineKeyboardButton("1080p", callback_data="1080")]
        ]
        await query.edit_message_text("Select quality:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data in ["360", "720", "1080"]:
        user_quality[uid] = query.data
        await query.edit_message_text("Now send video link 🔗")

    elif query.data == "audio":
        user_quality[uid] = "audio"
        await query.edit_message_text("Send link for MP3 🎵")


def progress_hook(d):
    if d['status'] == 'downloading':
        print("Downloading...", d.get('_percent_str', '0%'))


async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    uid = update.message.from_user.id
    quality = user_quality.get(uid, "720")

    if not url.startswith("http"):
        await update.message.reply_text("Send valid link.")
        return

    msg = await update.message.reply_text("Downloading... ⏳")

    if quality == "audio":
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'progress_hooks': [progress_hook]
        }
    else:
        ydl_opts = {
            'format': f'bestvideo[height<={quality}]+bestaudio/best',
            'outtmpl': 'video.%(ext)s',
            'merge_output_format': 'mp4',
            'progress_hooks': [progress_hook]
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        await msg.edit_text("Uploading... 🚀")

        for f in os.listdir():
            if f.startswith("video.") or f.endswith(".mp3"):
                await update.message.reply_document(document=open(f, 'rb'))
                os.remove(f)
                break

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))

print("Bot running...")
app.run_polling()
