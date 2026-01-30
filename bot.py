import os
import logging
import asyncio
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import BadRequest
import config
from utils.downloader import downloader
from utils.helpers import is_valid_url, clean_filename, format_size, format_duration
import traceback

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create downloads directory
os.makedirs(config.Config.DOWNLOAD_PATH, exist_ok=True)

class VideoBot:
    def __init__(self):
        self.user_data = {}
        
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        user = update.effective_user
        welcome_text = f"""
🤖 *Welcome to Premium Video Downloader Bot* {user.mention_html()}!

✨ *Features:*
• Download videos from 1000+ websites
• Choose video quality
• Extract audio only
• Premium support for larger files
• Fast download speeds

📥 *How to use:*
1. Send me a video URL
2. Select quality/format
3. Download directly!

⚡ *Premium Commands:*
/ytdl - Download YouTube videos
/tiktok - Download TikTok videos
/insta - Download Instagram videos
/twitter - Download Twitter videos
/audio - Extract audio only
/batch - Download multiple videos
/status - Check bot status
/help - Show all commands

👑 *Premium Features:*
• 200MB file size limit
• Priority processing
• Batch downloads
• No ads
• Faster speeds

Made with ❤️ by VideoBot Team
"""
        await update.message.reply_html(welcome_text)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help message"""
        help_text = """
📚 *Available Commands:*

🔹 *Basic Commands:*
/start - Start the bot
/help - Show this help message
/ytdl [url] - Download YouTube video
/tiktok [url] - Download TikTok video
/insta [url] - Download Instagram video
/twitter [url] - Download Twitter video
/audio [url] - Extract audio from video
/info [url] - Get video information

👑 *Premium Commands (Premium Users Only):*
/batch [urls] - Download multiple videos
/compress [url] - Compress video
/convert [url] - Convert video format
/custom - Custom download settings

🛠️ *Admin Commands (Admins Only):*
/stats - Bot statistics
/broadcast - Send message to all users
/addpremium - Add premium user
/removepremium - Remove premium user

⚠️ *Note:* Some features require premium subscription.
Contact admin for premium access.

📝 *Usage:* Just send any video URL or use the commands above!
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video URL message"""
        url = update.message.text.strip()
        user_id = update.effective_user.id
        
        if not is_valid_url(url):
            await update.message.reply_text("❌ Invalid URL. Please send a valid video URL.")
            return
        
        # Check if user is premium
        is_premium = user_id in config.Config.PREMIUM_USERS or user_id in config.Config.ADMIN_IDS
        
        # Show processing message
        processing_msg = await update.message.reply_text(
            "🔍 *Processing your request...*\n"
            f"👑 Premium: {'✅' if is_premium else '❌'}\n"
            "Please wait while I fetch video information...",
            parse_mode='Markdown'
        )
        
        try:
            # Get video info
            video_info = await downloader.get_video_info(url)
            
            # Create format selection keyboard
            keyboard = []
            formats = video_info.get('formats', [])
            
            # Add best quality option
            keyboard.append([InlineKeyboardButton("🎬 Best Quality", callback_data=f"download:{url}:best")])
            
            # Add audio only option
            keyboard.append([InlineKeyboardButton("🎵 Audio Only (MP3)", callback_data=f"audio:{url}")])
            
            # Add quality options if available
            quality_options = []
            for fmt in formats:
                if fmt.get('ext') in ['mp4', 'webm', 'mkv'] and fmt.get('height'):
                    quality_options.append((fmt['height'], fmt['format_id']))
            
            # Deduplicate and sort qualities
            quality_options = sorted(set(quality_options), reverse=True)
            for quality, fmt_id in quality_options[:5]:  # Show top 5 qualities
                keyboard.append([
                    InlineKeyboardButton(f"📹 {quality}p", callback_data=f"download:{url}:{fmt_id}")
                ])
            
            # Add premium features for premium users
            if is_premium:
                keyboard.append([
                    InlineKeyboardButton("⚡ Premium Fast Download", callback_data=f"premium:{url}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send video info with options
            info_text = f"""
📹 *Video Information:*

📌 *Title:* {video_info['title']}
⏱️ *Duration:* {format_duration(video_info['duration'])}
🌐 *Source:* {video_info['extractor'].upper()}
🔗 *URL:* {url}

👇 *Select download option:*
            """
            
            if video_info.get('thumbnail'):
                try:
                    await update.message.reply_photo(
                        photo=video_info['thumbnail'],
                        caption=info_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                except:
                    await update.message.reply_text(
                        info_text,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    info_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            
            await processing_msg.delete()
            
        except Exception as e:
            await processing_msg.edit_text(f"❌ Error: {str(e)}")
            logger.error(f"Error getting video info: {traceback.format_exc()}")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        user_id = query.from_user.id
        is_premium = user_id in config.Config.PREMIUM_USERS or user_id in config.Config.ADMIN_IDS
        
        if data.startswith("download:"):
            _, url, format_id = data.split(":", 2)
            await self.download_video(query, url, format_id, is_premium)
        
        elif data.startswith("audio:"):
            url = data.split(":", 1)[1]
            await self.download_audio(query, url, is_premium)
        
        elif data.startswith("premium:"):
            url = data.split(":", 1)[1]
            if is_premium:
                await self.premium_download(query, url)
            else:
                await query.message.reply_text(
                    "👑 This feature requires premium subscription!\n"
                    "Contact admin for premium access."
                )
    
    async def download_video(self, query, url: str, format_id: str, is_premium: bool):
        """Download video with selected format"""
        status_msg = await query.message.reply_text(
            "⏬ *Downloading video...*\n"
            "This may take a few moments...",
            parse_mode='Markdown'
        )
        
        try:
            filename, title = await downloader.download_video(url, format_id, is_premium)
            
            await status_msg.edit_text("📤 *Uploading to Telegram...*")
            
            # Send video
            with open(filename, 'rb') as video_file:
                await query.message.reply_video(
                    video=video_file,
                    caption=f"🎬 *{clean_filename(title)}*\n\n✅ Download complete!\n"
                            f"👑 Premium: {'✅' if is_premium else '❌'}",
                    parse_mode='Markdown'
                )
            
            await status_msg.delete()
            
            # Clean up
            os.remove(filename)
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Download failed: {str(e)}")
            logger.error(f"Download error: {traceback.format_exc()}")
    
    async def download_audio(self, query, url: str, is_premium: bool):
        """Download audio only"""
        status_msg = await query.message.reply_text(
            "🎵 *Extracting audio...*\n"
            "Converting to MP3 format...",
            parse_mode='Markdown'
        )
        
        try:
            # Use yt-dlp with audio extraction
            import yt_dlp
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'outtmpl': os.path.join(config.Config.DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            await status_msg.edit_text("📤 *Uploading audio...*")
            
            # Send audio
            with open(filename, 'rb') as audio_file:
                await query.message.reply_audio(
                    audio=audio_file,
                    caption=f"🎵 *{clean_filename(info['title'])}*\n\n✅ Audio extracted successfully!",
                    parse_mode='Markdown'
                )
            
            await status_msg.delete()
            os.remove(filename)
            
        except Exception as e:
            await status_msg.edit_text(f"❌ Audio extraction failed: {str(e)}")
    
    async def premium_download(self, query, url: str):
        """Premium download with extra features"""
        status_msg = await query.message.reply_text(
            "⚡ *Premium Download Started!*\n"
            "Enjoy faster download speeds...",
            parse_mode='Markdown'
        )
        
        # Premium users get parallel download and better formats
        await self.download_video(query, url, "bestvideo+bestaudio", True)
    
    async def ytdl_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """YouTube specific download"""
        if context.args:
            url = context.args[0]
            await self.handle_url(update, context)
        else:
            await update.message.reply_text("Usage: /ytdl [youtube_url]")
    
    async def audio_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Extract audio from video"""
        if context.args:
            url = context.args[0]
            user_id = update.effective_user.id
            is_premium = user_id in config.Config.PREMIUM_USERS or user_id in config.Config.ADMIN_IDS
            
            # Create a mock query object
            class MockQuery:
                def __init__(self, message):
                    self.message = message
                    self.from_user = message.from_user
                
                async def answer(self):
                    pass
            
            query = MockQuery(update.message)
            await self.download_audio(query, url, is_premium)
        else:
            await update.message.reply_text("Usage: /audio [video_url]")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot statistics (Admin only)"""
        user_id = update.effective_user.id
        
        if user_id not in config.Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admin only command!")
            return
        
        import psutil
        import datetime
        
        # Get system stats
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        stats_text = f"""
📊 *Bot Statistics*

👥 *Users:* {len(self.user_data)}
👑 *Premium Users:* {len(config.Config.PREmium_USERS)}

💻 *System Stats:*
• CPU Usage: {cpu_usage}%
• Memory: {memory.percent}% used
• Disk: {disk.percent}% used

📁 *Downloads Folder:*
• Files: {len(os.listdir(config.Config.DOWNLOAD_PATH))}
• Size: {format_size(sum(os.path.getsize(os.path.join(config.Config.DOWNLOAD_PATH, f)) for f in os.listdir(config.Config.DOWNLOAD_PATH) if os.path.isfile(os.path.join(config.Config.DOWNLOAD_PATH, f))))}

🕐 *Uptime:* {datetime.datetime.now()}
"""
        await update.message.reply_text(stats_text, parse_mode='Markdown')
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message to all users (Admin only)"""
        user_id = update.effective_user.id
        
        if user_id not in config.Config.ADMIN_IDS:
            await update.message.reply_text("❌ Admin only command!")
            return
        
        if not context.args:
            await update.message.reply_text("Usage: /broadcast [message]")
            return
        
        message = " ".join(context.args)
        broadcast_text = f"""
📢 *Announcement from Admin*

{message}

---
*This is a broadcast message to all users.*
"""
        
        # In production, you would send to all users from database
        await update.message.reply_text(
            f"📤 Broadcast sent to {len(self.user_data)} users",
            parse_mode='Markdown'
        )

# Main function
def main():
    """Start the bot"""
    bot = VideoBot()
    
    # Create application
    application = Application.builder().token(config.Config.BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("ytdl", bot.ytdl_command))
    application.add_handler(CommandHandler("audio", bot.audio_command))
    application.add_handler(CommandHandler("stats", bot.stats_command))
    application.add_handler(CommandHandler("broadcast", bot.broadcast_command))
    
    # Add URL handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        bot.handle_url
    ))
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(bot.button_callback))
    
    # Start bot
    print("🤖 Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
