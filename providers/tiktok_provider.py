import os
import uuid
import asyncio
import logging
import aiohttp
import yt_dlp
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

class TikTokProvider(BaseProvider):
    async def download(self, url: str, download_dir: str, progress_callback=None) -> dict:
        """
        Downloads a TikTok video. Implements the fallback system.
        """
        methods = [
            (self._download_via_api, "المصدر الأول (TikWM API بدون علامة مائية)"),
            (self._download_via_ytdl, "المصدر الثاني (yt-dlp البديل)")
        ]
        
        last_error = None
        for method, name in methods:
            try:
                logger.info(f"Trying TikTok download using: {name}")
                return await method(url, download_dir, progress_callback)
            except Exception as e:
                logger.warning(f"TikTok download method '{name}' failed: {e}")
                last_error = e
                
        raise last_error or RuntimeError("فشلت جميع طرق تحميل الفيديو من تيك توك.")

    async def _download_via_api(self, url: str, download_dir: str, progress_callback=None) -> dict:
        api_url = "https://www.tikwm.com/api/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        
        logger.info(f"Querying TikWM API for URL: {url}")
        async with aiohttp.ClientSession(headers=headers) as session:
            # Query the API
            data = {"url": url}
            async with session.post(api_url, data=data, timeout=12) as response:
                if response.status != 200:
                    raise RuntimeError(f"TikWM API returned HTTP status {response.status}")
                
                result = await response.json()
                if result.get("code") != 0:
                    msg = result.get("msg") or "Unknown error"
                    raise RuntimeError(f"TikWM API Error: {msg}")
                
                video_data = result.get("data")
                if not video_data:
                    raise RuntimeError("No data found in TikWM API response.")
                
                play_url = video_data.get("play")
                if not play_url:
                    raise RuntimeError("Could not find watermark-free video play URL.")
                
                if not play_url.startswith("http"):
                    play_url = "https://www.tikwm.com" + play_url
                    
                duration = video_data.get("duration")
                title = video_data.get("title")
                
                # Trigger progress callback
                if progress_callback:
                    try:
                        progress_callback('downloading')
                    except Exception as e:
                        logger.error(f"Error in progress callback: {e}")
                
                # Download the file
                os.makedirs(download_dir, exist_ok=True)
                unique_id = str(uuid.uuid4())
                file_path = os.path.join(download_dir, f"{unique_id}_tiktok_no_wm.mp4")
                
                logger.info(f"Downloading no-watermark TikTok video from direct URL: {play_url}")
                async with session.get(play_url, timeout=30) as video_resp:
                    if video_resp.status != 200:
                        raise RuntimeError(f"Failed to download video file, status code: {video_resp.status}")
                    
                    with open(file_path, "wb") as f:
                        while True:
                            chunk = await video_resp.content.read(1024 * 64)
                            if not chunk:
                                break
                            f.write(chunk)
                            
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    logger.info(f"Successfully downloaded TikTok video without watermark: {file_path}")
                    return {
                        'file_path': os.path.abspath(file_path),
                        'duration': int(duration) if duration else None,
                        'width': None,
                        'height': None,
                        'title': title
                    }
                else:
                    if os.path.exists(file_path):
                        os.remove(file_path)
                    raise FileNotFoundError("Downloaded file is empty or not written successfully.")

    async def _download_via_ytdl(self, url: str, download_dir: str, progress_callback=None) -> dict:
        loop = asyncio.get_running_loop()
        
        def thread_safe_callback(status):
            if progress_callback:
                loop.call_soon_threadsafe(progress_callback, status)
                
        return await asyncio.to_thread(self._ytdl_sync, url, download_dir, thread_safe_callback)

    def _ytdl_sync(self, url: str, download_dir: str, progress_callback=None) -> dict:
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
                'Referer': 'https://www.tiktok.com/',
            },
        }
            
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=True)
            except Exception as e:
                logger.error(f"yt-dlp extraction failed: {str(e)}")
                raise RuntimeError(f"فشل استخراج المنشور من تيك توك: {str(e)}")
                
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
