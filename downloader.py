import os
import re
import uuid
import asyncio
import logging
import yt_dlp

logger = logging.getLogger(__name__)

# Regex pattern to match standard Instagram video, reel, and post URLs
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv|share/reel)/([A-Za-z0-9_-]+)",
    re.IGNORECASE
)

def is_valid_instagram_url(url: str) -> bool:
    """
    Checks if the given URL is a valid Instagram video, reel, or post URL.
    """
    return bool(INSTAGRAM_URL_PATTERN.match(url))

def download_instagram_video(url: str, download_dir: str, progress_callback=None) -> dict:
    """
    Synchronous function to download an Instagram video using yt-dlp.
    Returns a dictionary containing video metadata and file path.
    """
    os.makedirs(download_dir, exist_ok=True)
    
    unique_id = str(uuid.uuid4())
    outtmpl = os.path.join(download_dir, f"{unique_id}_%(title).100s.%(ext)s")
    
    # Flag to ensure the downloading callback is only called once
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
        # Select best pre-merged format (video+audio in one file) to avoid requiring ffmpeg for merging
        'format': 'best[ext=mp4]/best',
        'outtmpl': outtmpl,
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'playlist_items': '1',  # Only download the first item
        'progress_hooks': [ytdl_hook],
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,video/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.instagram.com/',
        },
    }
    
    logger.info(f"Starting download for URL: {url} with unique ID: {unique_id}")
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except Exception as e:
            logger.error(f"yt-dlp extraction failed: {str(e)}")
            raise RuntimeError(f"فشل استخراج الفيديو من الرابط. قد يكون الحساب خاصاً أو تم حظر الطلب.")
        
        video_info = info
        if 'entries' in info and info['entries']:
            video_info = info['entries'][0]
            
        duration = video_info.get('duration')
        width = video_info.get('width')
        height = video_info.get('height')
        title = video_info.get('title') or video_info.get('description')
        
        # Search the directory for any file matching the unique_id
        downloaded_file = None
        for file in os.listdir(download_dir):
            if file.startswith(unique_id):
                full_path = os.path.abspath(os.path.join(download_dir, file))
                if os.path.isfile(full_path) and not file.endswith(('.part', '.ytdl')):
                    downloaded_file = full_path
                    break
        
        # Fallback to prepare_filename
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
            logger.info(f"Successfully downloaded file: {downloaded_file}")
            return {
                'file_path': downloaded_file,
                'duration': int(duration) if duration else None,
                'width': int(width) if width else None,
                'height': int(height) if height else None,
                'title': title
            }
            
        raise FileNotFoundError("لم يتم العثور على الملف المحمل بعد اكتمال التنزيل.")

async def download_video_async(url: str, download_dir: str, progress_callback=None) -> dict:
    """
    Asynchronous wrapper that runs the blocking yt-dlp downloader in a separate thread.
    Passes a thread-safe wrapper callback to update download progress.
    """
    loop = asyncio.get_running_loop()
    
    def thread_safe_callback(status):
        if progress_callback:
            loop.call_soon_threadsafe(progress_callback, status)
            
    return await asyncio.to_thread(download_instagram_video, url, download_dir, thread_safe_callback)
