import asyncio
import aiohttp

async def test_tikwm_no_www(url):
    print(f"\n--- Testing TikWM (no www) ---")
    api_url = "https://tikwm.com/api/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            async with session.post(api_url, data={"url": url}) as resp:
                print("Status:", resp.status)
                res = await resp.json()
                print("Code:", res.get("code"))
                print("Msg:", res.get("msg"))
                if res.get("code") == 0:
                    print("Play link:", res.get("data", {}).get("play")[:50])
        except Exception as e:
            print("Error:", e)

async def test_tiklydown_no_ssl(url):
    print(f"\n--- Testing Tiklydown (no ssl verify) ---")
    api_url = "https://api.tiklydown.eu.org/api/download"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    # Disable SSL verification
    conn = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(headers=headers, connector=conn) as session:
        try:
            async with session.get(api_url, params={"url": url}) as resp:
                print("Status:", resp.status)
                res = await resp.json()
                print("ID field:", res.get("id"))
                video_url = res.get("video", {}).get("noWatermark")
                if not video_url:
                    video_url = res.get("video", {}).get("noWatermark2")
                print("Video no watermark:", video_url[:50] if video_url else None)
        except Exception as e:
            print("Error:", e)

async def main():
    tiktok_url = "https://www.tiktok.com/@tiktok/video/7106195220677561646"
    await test_tikwm_no_www(tiktok_url)
    await test_tiklydown_no_ssl(tiktok_url)

if __name__ == "__main__":
    asyncio.run(main())
