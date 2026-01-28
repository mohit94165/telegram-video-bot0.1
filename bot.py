import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")

user_quality = {}  # user ke liye quality save karega


# 🎬 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📥 Download Video", callback_data="download")],
        [InlineKeyboardButton("🎵 Audio Only", callback_data="audio")]
    ]
    await update.message.reply_text(
        "👋 Welcome!\nSend any video link.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# 🎯 BUTTON CLICK
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "download":
        keyboard = [
            [InlineKeyboardButton("360p", callback_data="360")],
            [InlineKeyboardButton("720p", callback_data="720")],
            [InlineKeyboardButton("1080p", callback_data="1080")]
        ]
        await query.edit_message_text(
            "Select video quality:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data in ["360", "720", "1080"]:
        user_quality[user_id] = query.data
        await query.edit_message_text("Now send video link 🔗")

    elif query.data == "audio":
        user_quality[user_id] = "audio"
        await query.edit_message_text("Send link for audio 🎵")


# 📊 PROGRESS HOOK
def progress_hook(d):
    if d['status'] == 'downloading':
        percent = d.get('_percent_str', '0%')
        print(f"Downloading: {percent}")


# 📥 DOWNLOAD FUNCTION
async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    user_id = update.message.from_user.id
    quality = user_quality.get(user_id, "720")

    if not url.startswith("http"):
        await update.message.reply_text("Send valid link.")
        return

    msg = await update.message.reply_text("Downloading... ⏳")

    if quality == "audio":
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': 'audio.%(ext)s',
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
            info = ydl.extract_info(url, download=True)

        file = None
        for f in os.listdir():
            if f.startswith("video.") or f.startswith("audio."):
                file = f
                break

        thumb = info.get("thumbnail")

        await msg.edit_text("Uploading... 🚀")

        if file:
            await update.message.reply_document(
                document=open(file, 'rb'),
                thumbnail=thumb if thumb else None
            )
            os.remove(file)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


# 🏁 RUN BOT
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))

print("Bot running...")
app.run_polling()
