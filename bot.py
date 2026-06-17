import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Import our downloader module
from downloader import download_video_async, INSTAGRAM_URL_PATTERN, TIKTOK_URL_PATTERN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8154863289:AAE42WonCOFHEJGudn_hEWzJD4a8mSsc3Nw"

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
    logger.error("BOT_TOKEN is missing or not set in the environment variables.")
    raise ValueError("الرجاء ضبط BOT_TOKEN في ملف .env لتشغيل البوت.")

# Load optional proxy setting (renamed to BOT_PROXY to avoid conflict with global env variables)
BOT_PROXY = os.getenv("BOT_PROXY")

# Initialize Bot and Dispatcher (with proxy support if configured)
if BOT_PROXY:
    from aiogram.client.session.aiohttp import AiohttpSession
    session = AiohttpSession(proxy=BOT_PROXY)
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    logger.info(f"Bot initialized using proxy: {BOT_PROXY}")
else:
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    
dp = Dispatcher()

# Directory to temporarily store downloaded videos
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_downloads")

def clean_temp_directory():
    """
    Cleans up the temp_downloads directory to free space on startup or shutdown.
    """
    if os.path.exists(TEMP_DIR):
        logger.info("Cleaning up temporary downloads directory...")
        for file in os.listdir(TEMP_DIR):
            file_path = os.path.join(TEMP_DIR, file)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    logger.debug(f"Deleted temp file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to delete temp file {file_path} during startup cleanup: {e}")

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """
    Handler for /start command. Welcomes the user and explains how to use the bot.
    """
    welcome_text = (
        "👋 **أهلاً بك في بوت تحميل فيديوهات إنستقرام وتيك توك!**\n\n"
        "وظيفة البوت بسيطة جداً وسريعة:\n"
        "1. أرسل لي أي رابط فيديو من إنستقرام (Reel, Post) أو تيك توك.\n"
        "2. وسأقوم بتحميل الفيديو وإرساله لك مباشرة بجودة عالية. 📥\n\n"
        "⚡ **المنصات المدعومة:**\n"
        "• Instagram (Reels, Posts, Videos)\n"
        "• TikTok (Videos, Share links, Short links)\n\n"
        "أرسل الرابط الآن للبدء! 👇"
    )
    await message.reply(welcome_text)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """
    Handler for /help command.
    """
    help_text = (
        "💡 **طريقة الاستخدام:**\n"
        "قم بنسخ رابط الفيديو من تطبيق إنستقرام أو تيك توك وأرسله هنا مباشرة.\n\n"
        "**أمثلة على الروابط المقبولة:**\n"
        "• `https://www.instagram.com/reel/xxxx/`\n"
        "• `https://vt.tiktok.com/xxxx/` أو `https://www.tiktok.com/@user/video/xxxx`\n\n"
        "⚠️ **ملاحظة:** البوت يدعم الفيديوهات العامة فقط. الحسابات الخاصة (Private) قد لا تعمل."
    )
    await message.reply(help_text)

@dp.message()
async def handle_media_links(message: types.Message):
    """
    Core handler that detects and processes Instagram and TikTok links.
    """
    text = message.text or ""
    
    # Search for Instagram or TikTok URL in the message
    insta_match = INSTAGRAM_URL_PATTERN.search(text)
    tiktok_match = TIKTOK_URL_PATTERN.search(text)
    
    if not insta_match and not tiktok_match:
        # If private chat, guide the user. Otherwise, ignore messages in groups
        if message.chat.type == "private":
            await message.reply(
                "❌ عذراً، لم أجد رابط إنستقرام أو تيك توك صالح في رسالتك.\n"
                "يرجى إرسال رابط فيديو صالح للبدء."
            )
        return
        
    # Use the matched URL
    url = (insta_match or tiktok_match).group(0)
    
    # 1. Status: Extraction
    progress_msg = await message.reply("📥 جاري استخراج الفيديو...")
    
    # Progress callback to switch to "⬇️ جاري التحميل..." once yt-dlp starts the download stream
    async def on_download_start(status):
        if status == 'downloading':
            try:
                await progress_msg.edit_text("⬇️ جاري التحميل...")
            except Exception as e:
                logger.debug(f"Failed to edit progress message: {e}")
                
    downloaded_info = None
    
    try:
        # 2. Download the video asynchronously
        downloaded_info = await download_video_async(url, TEMP_DIR, on_download_start)
        
        # 3. Status: Sending
        try:
            await progress_msg.edit_text("📤 جاري الإرسال...")
        except Exception as e:
            logger.debug(f"Failed to edit progress message: {e}")
            
        file_path = downloaded_info['file_path']
        
        # Check size of the file (Telegram Bot API upload limit for bots is 50MB)
        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            await progress_msg.edit_text(
                "⚠️ **عذراً، حجم الفيديو يتجاوز 50 ميجابايت.**\n"
                "تمنع سياسة تيليجرام البوتات من إرسال ملفات تزيد عن 50 ميجابايت."
            )
            # Delete file
            if os.path.exists(file_path):
                os.remove(file_path)
            return

        # Send the video file
        video_input = FSInputFile(file_path)
        caption = f"🎬 **تم التحميل بنجاح!**\n\n🤖 البوت: @{(await bot.get_me()).username}"
        
        await message.reply_video(
            video=video_input,
            caption=caption,
            duration=downloaded_info.get('duration'),
            width=downloaded_info.get('width'),
            height=downloaded_info.get('height'),
            supports_streaming=True
        )
        
        # Delete progress message after successful delivery
        try:
            await progress_msg.delete()
        except Exception as e:
            logger.debug(f"Failed to delete progress message: {e}")
            
    except Exception as e:
        logger.error(f"Error handling media download: {e}")
        try:
            await progress_msg.edit_text(f"❌ **حدث خطأ أثناء تحميل الفيديو:**\n\n`{str(e)}`")
        except Exception as edit_err:
            logger.error(f"Failed to update progress message with error: {edit_err}")
            
    finally:
        # 4. Clean up downloaded temp file
        if downloaded_info and 'file_path' in downloaded_info:
            file_path = downloaded_info['file_path']
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
                except Exception as cleanup_err:
                    logger.error(f"Failed to delete temp file {file_path}: {cleanup_err}")

async def main():
    # Perform cleanup on startup
    clean_temp_directory()
    
    logger.info("Starting Telegram Bot...")
    try:
        await dp.start_polling(bot)
    finally:
        # Perform cleanup on shutdown
        clean_temp_directory()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
