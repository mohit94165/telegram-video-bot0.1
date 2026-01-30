import yt_dlp
import os
from typing import Dict, Tuple
import asyncio
from config import Config

class VideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best',
            'outtmpl': os.path.join(Config.DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
    
    async def get_video_info(self, url: str) -> Dict:
        """Get video information without downloading"""
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'formats': info.get('formats', []),
                    'thumbnail': info.get('thumbnail', ''),
                    'webpage_url': info.get('webpage_url', url),
                    'extractor': info.get('extractor', 'generic')
                }
            except Exception as e:
                raise Exception(f"Error getting video info: {str(e)}")
    
    async def download_video(self, url: str, format_id: str = None, is_premium: bool = False) -> Tuple[str, str]:
        """Download video with optional format selection"""
        opts = self.ydl_opts.copy()
        if format_id:
            opts['format'] = format_id
        
        with yt_dlp.YoutubeDL(opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                # Check file size
                file_size = os.path.getsize(filename)
                max_size = Config.PREMIUM_MAX_SIZE if is_premium else Config.MAX_FILE_SIZE
                
                if file_size > max_size:
                    os.remove(filename)
                    raise Exception(f"File too large ({file_size//1024//1024}MB). Max allowed: {max_size//1024//1024}MB")
                
                return filename, info.get('title', 'video')
            except Exception as e:
                raise Exception(f"Download failed: {str(e)}")

downloader = VideoDownloader()
