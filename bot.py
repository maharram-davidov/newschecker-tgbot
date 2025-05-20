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

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize EasyOCR reader
reader = easyocr.Reader(['az', 'en'])

def extract_sources_from_text(text):
    """Extract mentioned sources from the news text using Gemini."""
    try:
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
    except Exception as e:
        logger.error(f"Error in extract_sources_from_text: {e}")
        return ""

def verify_mentioned_sources(sources_text, keywords):
    """Verify the mentioned sources using SerpAPI."""
    try:
        # Get current date and date from 7 days ago
        current_date = datetime.now()
        week_ago = current_date - timedelta(days=7)
        date_range = f"after:{week_ago.strftime('%Y-%m-%d')}"
        
        # Extract source names from the sources text
        source_names = re.findall(r'Mənbə adı: (.*?)(?:\n|$)', sources_text)
        
        verification_results = []
        for source in source_names:
            # Search for the source and keywords
            params = {
                "engine": "google",
                "q": f'"{source}" {keywords} {date_range}',
                "api_key": os.getenv('SERPAPI_API_KEY'),
                "num": 3
            }
            
            search = GoogleSearch(params)
            results = search.get_dict()
            
            if "organic_results" in results:
                verification_results.append({
                    "source": source,
                    "results": results["organic_results"]
                })
        
        return verification_results
    except Exception as e:
        logger.error(f"Error in verify_mentioned_sources: {e}")
        return []

def search_news_sources(news_content):
    """Search for the news content in both official and general news sources using SerpAPI."""
    try:
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
    welcome_message = (
        "Salam! Mən xəbər doğruluq analiz botuyam. 👋\n\n"
        "Mənə bir xəbər linki və ya xəbər mətni göndərə bilərsiniz. "
        "Mən də xəbərin doğruluğunu analiz edib sizə məlumat verəcəyəm.\n\n"
        "İstifadə qaydası:\n"
        "1. Bir xəbər linki göndərin\n"
        "2. Və ya xəbər mətni birbaşa yazın\n"
        "3. Mən sizə xəbərin doğruluğu haqqında ətraflı bir analiz təqdim edəcəyəm."
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /help is issued."""
    help_text = (
        "Bot İstifadə Təlimatı:\n\n"
        "1. Bir xəbər linki göndərin və ya xəbər mətni yazın\n"
        "2. Bot avtomatik olaraq xəbəri analiz edəcək\n"
        "3. Sizə xəbərin doğruluğu haqqında ətraflı bir hesabat təqdim olunacaq\n\n"
        "İstifadə nümunəsi:\n"
        "- Bir xəbər linki yapışdırın\n"
        "- Və ya 'Azərbaycanda yeni bir texnologiya şirkəti yaradıldı' kimi bir xəbər mətni yazın"
    )
    await update.message.reply_text(help_text)

def extract_text_from_url(url):
    """Extract text content from a URL."""
    try:
        response = requests.get(url)
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
        
        return text[:4000]  # Limit text length
    except Exception as e:
        logger.error(f"Error extracting text from URL: {e}")
        return None

async def extract_text_from_image(image_data):
    """Extract text from image using EasyOCR."""
    try:
        # Convert image data to PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Extract text using EasyOCR
        results = reader.readtext(numpy.array(image))
        
        # Combine all detected text
        text = ' '.join([result[1] for result in results])
        
        return text.strip()
    except Exception as e:
        logger.error(f"Error in extract_text_from_image: {e}")
        return None

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages."""
    try:
        # Get the photo file
        photo = await update.message.photo[-1].get_file()
        
        # Download the photo
        photo_data = await photo.download_as_bytearray()
        
        # Extract text from the photo
        extracted_text = await extract_text_from_image(photo_data)
        
        if not extracted_text:
            await update.message.reply_text("Üzr istəyirəm, şəkildən mətn çıxara bilmədim. Zəhmət olmasa daha yaxşı keyfiyyətli şəkil göndərin.")
            return
        
        # Send "analyzing" message
        analyzing_message = await update.message.reply_text("Şəkildən çıxarılan mətn analiz olunur... 🤔")
        
        # Analyze the extracted text
        await analyze_news_content(update, context, extracted_text)
        
        # Delete the "analyzing" message
        await analyzing_message.delete()
        
    except Exception as e:
        logger.error(f"Error in handle_photo: {e}")
        await update.message.reply_text("Üzr istəyirəm, şəkil emal edilərkən xəta baş verdi. Zəhmət olmasa daha sonra yenidən cəhd edin.")

async def analyze_news_content(update: Update, context: ContextTypes.DEFAULT_TYPE, news_content: str):
    """Analyze the news content."""
    try:
        # Extract and verify mentioned sources
        mentioned_sources = extract_sources_from_text(news_content)
        
        # Search in news sources
        search_results = search_news_sources(news_content)
        
        # Verify mentioned sources
        source_verification = verify_mentioned_sources(mentioned_sources, search_results["keywords"])
        
        # Prepare the prompt for Gemini
        prompt = f"""
        Siz bir xəbər analiz mütəxəssisisiniz. Xəbərləri bitərəf və obyektiv şəkildə analiz edirsiniz.
        
        Aşağıdakı xəbəri analiz et və bu məlumatları istifadə edərək ətraflı bir analiz hazırla:
        
        Xəbər məzmunu:
        {news_content}
        
        Xəbərdə istinad edilən mənbələr:
        {mentioned_sources}
        
        Mənbələrin doğrulanması:
        {json.dumps(source_verification, indent=2, ensure_ascii=False) if source_verification else 'Xəbərdə istinad edilən mənbələr tapılmadı və ya doğrulanmadı.'}
        
        Rəsmi mənbələrdə tapılan məlumatlar:
        {json.dumps(search_results['official_sources'], indent=2, ensure_ascii=False) if search_results['official_sources'] else 'Rəsmi mənbələrdə bu xəbərlə əlaqəli məlumat tapılmadı.'}
        
        Digər xəbər mənbələrində tapılan məlumatlar:
        {json.dumps(search_results['news_sources'], indent=2, ensure_ascii=False) if search_results['news_sources'] else 'Digər xəbər mənbələrində bu xəbərlə əlaqəli məlumat tapılmadı.'}
        
        Zəhmət olmasa aşağıdakı formatda ətraflı bir analiz hazırla:
        
        Xəbər Analizi:
        
        [Burada xəbərin əsas məzmununu qısa şəkildə izah edin]
        
        Mənbə Analizi:
        [Burada bütün mənbələri (xəbərdə istinad edilən, rəsmi və digər xəbər mənbələri) birlikdə analiz edin. 
        Hər bir mənbənin etibarlılığını, doğruluğunu və xəbərlə uyğunluğunu izah edin. 
        Mənbələr arasında uyğunluq və ya ziddiyyətləri qeyd edin]
        
        Bitərəflik Analizi:
        [Xəbərin bitərəfliyini və mümkün tərəfli ifadələri izah edin]
        
        Nəticə:
        [Xəbərin ümumi qiymətləndirməsini və etibarlılıq səviyyəsini izah edin]
        
        Qeydlər:
        [Əgər varsa, əlavə qeydlər və xəbərdarlıqlar]
        """

        # Get analysis from Gemini
        response = model.generate_content(prompt)
        analysis = response.text

        # Send the analysis
        await update.message.reply_text(analysis)

    except Exception as e:
        logger.error(f"Error in analyze_news_content: {e}")
        await update.message.reply_text("Üzr istəyirəm, bir xəta baş verdi. Zəhmət olmasa daha sonra yenidən cəhd edin.")

async def analyze_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages and analyze news."""
    try:
        # Get the message text
        message_text = update.message.text
        
        # Check if it's a URL
        if message_text.startswith(('http://', 'https://')):
            news_content = extract_text_from_url(message_text)
            if not news_content:
                await update.message.reply_text("Üzr istəyirəm, bu linkdən məzmun çəkə bilmədim. Zəhmət olmasa başqa bir link sınayın.")
                return
        else:
            news_content = message_text

        # Send "analyzing" message
        analyzing_message = await update.message.reply_text("Xəbər analiz olunur... 🤔")

        # Analyze the news content
        await analyze_news_content(update, context, news_content)

        # Delete the "analyzing" message
        await analyzing_message.delete()

    except Exception as e:
        logger.error(f"Error in analyze_news: {e}")
        await update.message.reply_text("Üzr istəyirəm, bir xəta baş verdi. Zəhmət olmasa daha sonra yenidən cəhd edin.")

def main():
    """Start the bot."""
    # Create the Application
    application = ApplicationBuilder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_news))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 