import asyncio
import os
import shutil
from downloader import download_video_async

async def test_platform(name: str, url: str):
    print(f"\n==========================================")
    print(f"Testing {name} with URL: {url}")
    print(f"==========================================")
    temp_dir = "test_downloads"
    try:
        res = await download_video_async(
            url,
            temp_dir,
            lambda s: print(f"[{name}] Progress update: {s}")
        )
        print(f"[{name}] SUCCESS!")
        print(f"[{name}] Details: {res}")
        # Clean up downloaded file
        file_path = res.get('file_path')
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            print(f"[{name}] Cleaned up downloaded file: {file_path}")
    except Exception as e:
        import traceback
        print(f"[{name}] FAILED!")
        traceback.print_exc()

async def main():
    # Instagram Reels Test URL
    insta_url = "https://www.instagram.com/reel/DZkoVwVMq96/"
    # TikTok Test URL (Official TikTok account public video)
    tiktok_url = "https://www.tiktok.com/@tiktok/video/7106195220677561646"

    await test_platform("Instagram", insta_url)
    await test_platform("TikTok", tiktok_url)
    
    # Clean up test download dir if empty
    if os.path.exists("test_downloads"):
        try:
            shutil.rmtree("test_downloads")
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())
