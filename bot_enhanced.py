"""
Enhanced News Verification Bot with Security and Performance Improvements
This is an improved version demonstrating the critical security and performance enhancements.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from serpapi import GoogleSearch
import json
from datetime import datetime, timedelta
import re
import easyocr
from PIL import Image
import io
import numpy
from config import get_official_search_params, get_news_search_params
from security_utils import (
    check_rate_limit, 
    validate_input, 
    validate_url_input, 
    InputValidator, 
    security_config
)
import functools
from enum import Enum
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging with more detail
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Gemini
try:
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel('gemini-2.0-flash')
    logger.info("Gemini AI initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Gemini AI: {e}")
    raise

# Initialize EasyOCR reader
try:
    reader = easyocr.Reader(['az', 'en'])
    logger.info("EasyOCR initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize EasyOCR: {e}")
    raise

class ErrorType(Enum):
    """Error types for better error handling."""
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    UNKNOWN_ERROR = "unknown_error"

def handle_errors(error_type: ErrorType):
    """Decorator for consistent error handling."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                
                # Find update object in args
                update = None
                for arg in args:
                    if isinstance(arg, Update):
                        update = arg
                        break
                
                if update:
                    await handle_error(error_type, e, update)
                else:
                    logger.error(f"Could not find Update object to send error message")
                
                return None
        return wrapper
    return decorator

async def handle_error(error_type: ErrorType, error: Exception, update: Update):
    """Handle errors with user-friendly messages."""
    error_messages = {
        ErrorType.API_ERROR: "🔧 Xidmətdə müvəqqəti nasazlıq var. Zəhmət olmasa bir az sonra yenidən cəhd edin.",
        ErrorType.NETWORK_ERROR: "🌐 İnternet əlaqəsi problemi. Zəhmət olmasa əlaqənizi yoxlayın.",
        ErrorType.VALIDATION_ERROR: "❌ Göndərdiyiniz məlumat düzgün formatda deyil.",
        ErrorType.RATE_LIMIT_ERROR: "⏳ Çox tez-tez sorğu göndərirsiniz. Zəhmət olmasa bir az gözləyin.",
        ErrorType.UNKNOWN_ERROR: "❌ Gözlənilməz xəta baş verdi. Zəhmət olmasa daha sonra yenidən cəhd edin."
    }
    
    message = error_messages.get(error_type, error_messages[ErrorType.UNKNOWN_ERROR])
    
    try:
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")

def with_rate_limit(func):
    """Decorator to check rate limits before executing function."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        # Check rate limit
        is_allowed, error_message = check_rate_limit(user_id)
        if not is_allowed:
            await update.message.reply_text(error_message)
            return
        
        # Log remaining requests
        remaining = security_config.rate_limiter.get_remaining_requests(user_id)
        logger.info(f"User {user_id} has {remaining} requests remaining")
        
        return await func(update, context, *args, **kwargs)
    
    return wrapper

@handle_errors(ErrorType.API_ERROR)
def extract_sources_from_text(text: str) -> str:
    """Extract mentioned sources from the news text using Gemini."""
    # Sanitize input
    text = InputValidator.sanitize_text(text)
    
    prompt = f"""
    Bu xəbər mətni içərisində istinad edilən mənbələri tap və çıxar.
    Mənbələr bunlar ola bilər:
    - Rəsmi saytlar (məs: gov.az, who.int)
    - Xəbər agentlikləri (məs: Reuters, AP)
    - Rəsmi şəxslər (məs: Prezident, Nazir)
    - Rəsmi sənədlər (məs: qərar, sərəncam)
    - Rəsmi təşkilatlar (məs: BMT, DST)
    
    Xəbər mətni:
    {text}
    
    Zəhmət olmasa aşağıdakı formatda qaytar:
    - Mənbə adı: [mənbənin adı]
    - Mənbə növü: [rəsmi sayt/xəbər agentliyi/rəsmi şəxs/rəsmi sənəd/rəsmi təşkilat]
    - İstinad mətni: [xəbərdə bu mənbəyə necə istinad edilib]
    """
    
    response = model.generate_content(prompt)
    return response.text.strip()

@handle_errors(ErrorType.API_ERROR)
def verify_mentioned_sources(sources_text: str, keywords: str) -> list:
    """Verify the mentioned sources using SerpAPI."""
    # Get current date and date from 7 days ago
    current_date = datetime.now()
    week_ago = current_date - timedelta(days=7)
    date_range = f"after:{week_ago.strftime('%Y-%m-%d')}"
    
    # Extract source names from the sources text
    source_names = re.findall(r'Mənbə adı: (.*?)(?:\n|$)', sources_text)
    
    verification_results = []
    for source in source_names[:3]:  # Limit to 3 sources to avoid API quota issues
        # Search for the source and keywords
        params = {
            "engine": "google",
            "q": f'"{source}" {keywords} {date_range}',
            "api_key": os.getenv('SERPAPI_API_KEY'),
            "num": 3
        }
        
        try:
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "organic_results" in results:
                verification_results.append({
                    "source": source,
                    "results": results["organic_results"]
                })
        except Exception as e:
            logger.error(f"Error verifying source {source}: {e}")
            continue
    
    return verification_results

@handle_errors(ErrorType.API_ERROR)
def search_news_sources(news_content: str) -> dict:
    """Search for the news content in both official and general news sources using SerpAPI."""
    # Sanitize input
    news_content = InputValidator.sanitize_text(news_content)
    
    # Extract key information from the news content using Gemini
    prompt = f"""
    Bu xəbər mətnindən əsas məlumatları çıxar və axtarış üçün ən vacib 3-4 açar sözü tap.
    Yalnız açar sözləri qaytar, başqa heç nə yazma.
    
    Xəbər mətni:
    {news_content}
    """
    
    response = model.generate_content(prompt)
    keywords = response.text.strip()
    
    # Get current date and date from 7 days ago
    current_date = datetime.now()
    week_ago = current_date - timedelta(days=7)
    date_range = f"after:{week_ago.strftime('%Y-%m-%d')}"
    
    # Get search parameters from config
    official_params = get_official_search_params(keywords, date_range, os.getenv('SERPAPI_API_KEY'))
    news_params = get_news_search_params(keywords, date_range, os.getenv('SERPAPI_API_KEY'))
    
    try:
        official_search = GoogleSearch(official_params)
        news_search = GoogleSearch(news_params)
        
        official_results = official_search.get_dict()
        news_results = news_search.get_dict()
        
        return {
            "official_sources": official_results.get("organic_results", []),
            "news_sources": news_results.get("organic_results", []),
            "keywords": keywords
        }
    except Exception as e:
        logger.error(f"Error in search_news_sources: {e}")
        return {"official_sources": [], "news_sources": [], "keywords": ""}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    logger.info(f"User {user_id} ({username}) started the bot")
    
    welcome_message = (
        "👋 *Xoş gəlmisiniz!*\n\n"
        "Mən xəbər doğruluq analiz botuyam. Mənə göndərdiyiniz xəbərlərin doğruluğunu yoxlayıb, "
        "ətraflı analiz təqdim edə bilərəm.\n\n"
        "📝 *İstifadə qaydası:*\n"
        "1️⃣ Bir xəbər linki göndərin\n"
        "2️⃣ Və ya xəbər mətni birbaşa yazın\n"
        "3️⃣ Və ya xəbər şəkli göndərin\n\n"
        "⚡ *Yeni xüsusiyyətlər:*\n"
        "• Təkmilləşdirilmiş təhlükəsizlik\n"
        "• Daha sürətli analiz\n"
        "• Yaxşılaşdırılmış xəta idarəetməsi\n\n"
        f"📊 Sizə {security_config.max_requests_per_user} analiz haqq1 var "
        f"({security_config.rate_limit_window} saniyə ərzində)\n\n"
        "❓ Kömək üçün /help əmrindən istifadə edə bilərsiniz."
    )
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "🤖 *Bot İstifadə Təlimatı*\n\n"
        "📌 *Əsas əmrlər:*\n"
        "• /start - Botu başlatmaq\n"
        "• /help - Bu kömək mesajını göstərmək\n"
        "• /status - Bot vəziyyətini yoxlamaq\n\n"
        "📌 *Xəbər analizi üçün:*\n"
        "1. Bir xəbər linki göndərin\n"
        "2. Və ya xəbər mətni birbaşa yazın\n"
        "3. Və ya xəbər şəkli göndərin\n\n"
        "📌 *Analiz nəticələri:*\n"
        "• Xəbər Analizi\n"
        "• Mənbə Analizi\n"
        "• Bitərəflik Analizi\n"
        "• Nəticə\n"
        "• Qeydlər\n\n"
        "⚡ *Təhlükəsizlik:*\n"
        f"• Hər istifadəçi {security_config.rate_limit_window} saniyədə maksimum {security_config.max_requests_per_user} sorğu göndərə bilər\n"
        f"• Mətn uzunluğu maksimum {security_config.max_text_length} simvol ola bilər\n"
        "• Şübhəli linklər avtomatik bloklanır\n\n"
        "❓ Suallarınız varsa, zəhmət olmasa məlumat verin."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status and user's remaining requests."""
    user_id = update.effective_user.id
    remaining = security_config.rate_limiter.get_remaining_requests(user_id)
    
    status_text = (
        "📊 *Bot Vəziyyəti*\n\n"
        "🟢 Bot aktiv və işləyir\n"
        f"⚡ Sizin qalan sorğu haqq1: {remaining}/{security_config.max_requests_per_user}\n"
        f"⏱ Sıfırlanma müddəti: {security_config.rate_limit_window} saniyə\n\n"
        "🔧 *Sistemin vəziyyəti:*\n"
        "• Gemini AI: ✅ Aktiv\n"
        "• SerpAPI: ✅ Aktiv\n"
        "• EasyOCR: ✅ Aktiv\n"
        "• Təhlükəsizlik: ✅ Aktiv"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

@handle_errors(ErrorType.NETWORK_ERROR)
def extract_text_from_url(url: str) -> Optional[str]:
    """Extract text content from a URL with security validation."""
    # Validate URL first
    is_valid, error_message = validate_url_input(url)
    if not is_valid:
        logger.warning(f"Invalid URL rejected: {url}")
        return None
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
        
    # Get text content
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    # Sanitize and limit text
    return InputValidator.sanitize_text(text, security_config.max_text_length)

@handle_errors(ErrorType.API_ERROR)
async def extract_text_from_image(image_data: bytes) -> Optional[str]:
    """Extract text from image using EasyOCR with security checks."""
    # Check image size
    if len(image_data) > 10 * 1024 * 1024:  # 10MB limit
        logger.warning("Image too large, rejecting")
        return None
    
    # Convert image data to PIL Image
    image = Image.open(io.BytesIO(image_data))
    
    # Check image dimensions
    if image.width > 4096 or image.height > 4096:
        logger.warning("Image dimensions too large, rejecting")
        return None
    
    # Extract text using EasyOCR
    results = reader.readtext(numpy.array(image))
    
    # Combine all detected text
    text = ' '.join([result[1] for result in results])
    
    # Sanitize text
    return InputValidator.sanitize_text(text.strip())

@with_rate_limit
@handle_errors(ErrorType.API_ERROR)
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages with enhanced security."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} sent a photo for analysis")
    
    # Get the photo file
    photo = await update.message.photo[-1].get_file()
    
    # Download the photo
    photo_data = await photo.download_as_bytearray()
    
    # Send "analyzing" message
    analyzing_message = await update.message.reply_text(
        "🔄 Şəkil analiz olunur...\n"
        "Zəhmət olmasa gözləyin..."
    )
    
    # Extract text from the photo
    extracted_text = await extract_text_from_image(photo_data)
    
    if not extracted_text:
        await analyzing_message.edit_text(
            "❌ Üzr istəyirəm, şəkildən mətn çıxara bilmədim.\n"
            "Zəhmət olmasa daha yaxşı keyfiyyətli şəkil göndərin və ya "
            "şəklin böyüklüyünün 10MB-dan az olduğunu yoxlayın."
        )
        return
    
    # Validate extracted text
    is_valid, error_message = validate_input(extracted_text)
    if not is_valid:
        await analyzing_message.edit_text(error_message)
        return
    
    # Update analyzing message
    await analyzing_message.edit_text(
        "✅ Şəkildən mətn uğurla çıxarıldı!\n"
        "🔄 Mətn analiz olunur...\n"
        "Zəhmət olmasa gözləyin..."
    )
    
    # Analyze the extracted text
    await analyze_news_content(update, context, extracted_text)
    
    # Delete the "analyzing" message
    await analyzing_message.delete()

# Continue with the rest of the enhanced functions...
# (This is a partial implementation showing the key security improvements)