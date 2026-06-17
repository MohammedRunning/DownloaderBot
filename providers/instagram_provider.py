import os
import uuid
import asyncio
import logging
import yt_dlp
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class InstagramProvider(BaseProvider):
    async def download(self, url: str, download_dir: str, progress_callback=None) -> dict:
        """
        Downloads an Instagram video. Implements the fallback system.
        """
        methods = [
            (self._download_primary, "المصدر الأول (yt-dlp الأساسي)"),
            (self._download_fallback, "المصدر الثاني (yt-dlp البديل)")
        ]
        
        last_error = None
        for method, name in methods:
            try:
                logger.info(f"Trying Instagram download using: {name}")
                return await method(url, download_dir, progress_callback)
            except Exception as e:
                logger.warning(f"Instagram download method '{name}' failed: {e}")
                last_error = e
                
        raise last_error or RuntimeError("فشلت جميع طرق تحميل الفيديو من إنستقرام.")

    async def _download_primary(self, url: str, download_dir: str, progress_callback=None) -> dict:
        return await self._run_ytdl(url, download_dir, progress_callback, {
            'format': 'best[ext=mp4]/best',
            'nocheckcertificate': True,
        })

    async def _download_fallback(self, url: str, download_dir: str, progress_callback=None) -> dict:
        # Fallback uses generic format and different mobile User-Agent to bypass potential rate limit blocks
        return await self._run_ytdl(url, download_dir, progress_callback, {
            'format': 'best',
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.9',
                'Referer': 'https://www.google.com/',
            }
        })

    async def _run_ytdl(self, url: str, download_dir: str, progress_callback=None, extra_opts=None) -> dict:
        loop = asyncio.get_running_loop()
        
        def thread_safe_callback(status):
            if progress_callback:
                loop.call_soon_threadsafe(progress_callback, status)
                
        return await asyncio.to_thread(self._ytdl_sync, url, download_dir, thread_safe_callback, extra_opts)

    def _ytdl_sync(self, url: str, download_dir: str, progress_callback=None, extra_opts=None) -> dict:
        os.makedirs(download_dir, exist_ok=True)
        unique_id = str(uuid.uuid4())
        outtmpl = os.path.join(download_dir, f"{unique_id}_%(title).100s.%(ext)s")
        
        downloading_triggered = False
        def ytdl_hook(d):
            nonlocal downloading_triggered
            if d['status'] == 'downloading' and not downloading_triggered:
                downloading_triggered = True
                if progress_callback:
                    try:
                        progress_callback('downloading')
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': outtmpl,
            'merge_output_format': 'mp4',
            'quiet': True,
            'no_warnings': True,
            'playlist_items': '1',
            'progress_hooks': [ytdl_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,video/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.instagram.com/',
            },
        }
        
        if extra_opts:
            ydl_opts.update(extra_opts)
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                logger.error(f"yt-dlp extraction failed: {str(e)}")
                raise RuntimeError(f"فشل استخراج المنشور من إنستقرام: {str(e)}")
                
            video_info = info
            if 'entries' in info and info['entries']:
                video_info = info['entries'][0]
                
            duration = video_info.get('duration')
            width = video_info.get('width')
            height = video_info.get('height')
            title = video_info.get('title') or video_info.get('description')
            
            # Search for downloaded file
            downloaded_file = None
            for file in os.listdir(download_dir):
                if file.startswith(unique_id):
                    full_path = os.path.abspath(os.path.join(download_dir, file))
                    if os.path.isfile(full_path) and not file.endswith(('.part', '.ytdl')):
                        downloaded_file = full_path
                        break
            
            if not downloaded_file or not os.path.exists(downloaded_file):
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                for ext in ['.mp4', '.mkv', '.webm', '.3gp']:
                    alternative_path = base + ext
                    if os.path.exists(alternative_path):
                        downloaded_file = os.path.abspath(alternative_path)
                        break
                if not downloaded_file and os.path.exists(filename):
                    downloaded_file = os.path.abspath(filename)
                    
            if downloaded_file and os.path.exists(downloaded_file):
                return {
                    'file_path': downloaded_file,
                    'duration': int(duration) if duration else None,
                    'width': int(width) if width else None,
                    'height': int(height) if height else None,
                    'title': title
                }
                
            raise FileNotFoundError("لم يتم العثور على الملف المحمل بعد اكتمال التنزيل.")
