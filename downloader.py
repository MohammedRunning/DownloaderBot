import re
import logging
from providers.instagram_provider import InstagramProvider
from providers.tiktok_provider import TikTokProvider

logger = logging.getLogger(__name__)

# Regex pattern to match standard Instagram video, reel, and post URLs
INSTAGRAM_URL_PATTERN = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv|share/reel)/([A-Za-z0-9_-]+)",
    re.IGNORECASE
)

# Regex pattern to match TikTok video, short links, and share URLs
# Examples:
# https://www.tiktok.com/@username/video/1234567890
# https://vm.tiktok.com/ZS12345/
# https://vt.tiktok.com/ZS12345/
TIKTOK_URL_PATTERN = re.compile(
    r"https?://(?:www\.|vm\.|vt\.|v\.)?tiktok\.com/[A-Za-z0-9_@./?-]+",
    re.IGNORECASE
)

def is_valid_instagram_url(url: str) -> bool:
    """
    Checks if the given URL is a valid Instagram video, reel, or post URL.
    """
    return bool(INSTAGRAM_URL_PATTERN.search(url))

def is_valid_tiktok_url(url: str) -> bool:
    """
    Checks if the given URL is a valid TikTok URL.
    """
    return bool(TIKTOK_URL_PATTERN.search(url))

async def download_video_async(url: str, download_dir: str, progress_callback=None) -> dict:
    """
    Auto-detects the platform (Instagram or TikTok) and downloads using the respective provider.
    """
    if is_valid_instagram_url(url):
        logger.info(f"Detected Instagram URL: {url}")
        provider = InstagramProvider()
        return await provider.download(url, download_dir, progress_callback)
        
    elif is_valid_tiktok_url(url):
        logger.info(f"Detected TikTok URL: {url}")
        provider = TikTokProvider()
        return await provider.download(url, download_dir, progress_callback)
        
    else:
        raise ValueError("الرابط المكتوب غير مدعوم. يدعم البوت روابط Instagram و TikTok فقط.")
