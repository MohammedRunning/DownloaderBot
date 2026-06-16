import asyncio
from downloader import download_video_async

async def test():
    try:
        res = await download_video_async(
            "https://www.instagram.com/reel/DZkoVwVMq96/",
            "temp_downloads",
            lambda s: print("Progress:", s)
        )
        print("Success:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
