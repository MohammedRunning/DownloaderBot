import yt_dlp
import sys

def test_opts(name, opts):
    print(f"\n--- Testing: {name} ---")
    url = "https://www.tiktok.com/@mrbeast/video/7376722839931325739"
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print("SUCCESS:", info.get("title"))
            return True
    except Exception as e:
        print("FAILED:", str(e)[:200])
        return False

# Test 1: Standard
test_opts("Standard", {
    'quiet': True,
    'no_warnings': True,
})

# Test 2: No impersonate (if yt-dlp allows it)
# In yt-dlp, we can try to override extractor args for tiktok
test_opts("No Impersonate via Extractor Args", {
    'quiet': True,
    'no_warnings': True,
    'extractor_args': {'tiktok': {'impersonate': []}}
})

# Test 3: Change User-Agent
test_opts("Custom User-Agent and headers", {
    'quiet': True,
    'no_warnings': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }
})

# Test 4: Disable certificate validation
test_opts("No check certificate", {
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True
})
