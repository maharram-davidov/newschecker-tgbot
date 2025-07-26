import os
import logging
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, ContextTypes, ApplicationBuilder, CallbackQueryHandler
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime, timedelta
import re
import easyocr
from PIL import Image
import io
import numpy
from googleapiclient.discovery import build

# Import from new structure
from ..config.settings import config, get_official_search_params, get_news_search_params, NEWS_SOURCES, OFFICIAL_SOURCES, sanitize_input
from ..utils.logging import enhanced_logger, performance_monitor
from ..utils.rate_limiting import rate_limiter, rate_limit_check
from ..utils.security import security_validator, security_check, validate_image_file
from ..core.database import db
from ..core.cache import news_cache
from ..core.analyzer import credibility_analyzer

# Import from new structure
from .interaction import UserInteraction
from ..admin.commands import ADMIN_COMMANDS

class BotHandlers:
    """Main bot handlers class containing all Telegram bot functionality."""
    
    def __init__(self):
        """Initialize bot handlers and services."""
        self.setup_gemini()
        self.setup_ocr()
        self.search_service = self.get_google_search_service()
    
    def setup_gemini(self):
        """Configure Gemini AI."""
        genai.configure(api_key=config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        enhanced_logger.info("Gemini AI configured successfully")
    
    def setup_ocr(self):
        """Initialize EasyOCR reader."""
        try:
            self.reader = easyocr.Reader(['az', 'en'])
            enhanced_logger.info("EasyOCR initialized successfully")
        except Exception as e:
            enhanced_logger.error("Failed to initialize EasyOCR", error=e)
            self.reader = None
    
    def get_google_search_service(self):
        """Initialize and return Google Custom Search API service."""
        try:
            service = build("customsearch", "v1", developerKey=config.GOOGLE_API_KEY)
            enhanced_logger.debug("Google Search service initialized")
            return service
        except Exception as e:
            enhanced_logger.error("Error initializing Google Search service", error=e)
            return None

    @performance_monitor('google_search')
    def search_with_google(self, query, cx):
        """Search using Google Custom Search API with performance monitoring."""
        try:
            if not self.search_service:
                return {"items": []}

            enhanced_logger.debug(f"Sending request to Google Search API", query=query)
            result = self.search_service.cse().list(
                q=query,
                cx=cx,
                num=10,
                gl="az",
                hl="az"
            ).execute()

            enhanced_logger.debug(f"Received response from Google Search API", results_count=len(result.get("items", [])))
            return result
        except Exception as e:
            enhanced_logger.error("Error in search_with_google", error=e, query=query)
            return {"items": []}

    @performance_monitor('source_extraction')
    @security_check('text')
    def extract_sources_from_text(self, text):
        """Extract mentioned sources from the news text using Gemini with security validation."""
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
            
            response = self.model.generate_content(prompt)
            enhanced_logger.debug("Source extraction completed successfully")
            return response.text.strip()
        except Exception as e:
            enhanced_logger.error("Error in extract_sources_from_text", error=e)
            return ""

    @performance_monitor('source_verification')
    def verify_mentioned_sources(self, sources_text, keywords):
        """Verify the mentioned sources using Google Search API."""
        try:
            current_date = datetime.now()
            week_ago = current_date - timedelta(days=7)
            date_range = f"after:{week_ago.strftime('%Y-%m-%d')}"
            
            source_names = re.findall(r'Mənbə adı: (.*?)(?:\n|$)', sources_text)
            
            verification_results = []
            for source in source_names:
                params = {
                    "q": f'"{source}" {keywords} {date_range}',
                    "gl": "az",
                    "hl": "az",
                    "num": 3
                }
                
                search_results = self.search_with_google(params['q'], config.GOOGLE_CSE_ID)
                
                if "items" in search_results and search_results["items"]:
                    verification_results.append({
                        "source": source,
                        "results": search_results["items"]
                    })
            
            enhanced_logger.debug("Source verification completed", verified_sources=len(verification_results))
            return verification_results
        except Exception as e:
            enhanced_logger.error("Error in verify_mentioned_sources", error=e)
            return []

    @performance_monitor('news_search')
    def search_news_sources(self, news_content):
        """Search for the news content in both official and general news sources."""
        try:
            prompt = f"""
            Bu xəbər mətnindən əsas məlumatları çıxar və axtarış üçün ən vacib 3-4 açar sözü tap.
            Açar sözlər xəbərin əsas mövzusunu və ən vacib məlumatlarını əhatə etməlidir.
            Yalnız açar sözləri qaytar, başqa heç nə yazma.
            
            Xəbər mətni:
            {news_content}
            """
            
            response = self.model.generate_content(prompt)
            keywords = response.text.strip()
            enhanced_logger.debug("Keywords extracted", keywords=keywords)
            
            current_date = datetime.now()
            month_ago = current_date - timedelta(days=30)
            date_range = f"after:{month_ago.strftime('%Y-%m-%d')}"
            
            official_params = get_official_search_params(keywords, date_range, config.GOOGLE_API_KEY)
            news_params = get_news_search_params(keywords, date_range, config.GOOGLE_API_KEY)
            
            enhanced_logger.debug("Search parameters prepared", 
                                official_query=official_params['q'], 
                                news_query=news_params['q'])
            
            try:
                official_results = self.search_with_google(official_params['q'], config.GOOGLE_CSE_ID)
                enhanced_logger.debug("Official search completed", results_count=len(official_results.get("items", [])))
            except Exception as e:
                enhanced_logger.error("Error in official search", error=e)
                official_results = {"items": []}
            
            try:
                news_results = self.search_with_google(news_params['q'], config.GOOGLE_CSE_ID)
                enhanced_logger.debug("News search completed", results_count=len(news_results.get("items", [])))
            except Exception as e:
                enhanced_logger.error("Error in news search", error=e)
                news_results = {"items": []}
            
            official_sources = []
            if "items" in official_results and official_results["items"]:
                for result in official_results["items"]:
                    if any(source in result.get("link", "").lower() for source in OFFICIAL_SOURCES):
                        official_sources.append(result)
            
            news_sources = []
            if "items" in news_results and news_results["items"]:
                for result in news_results["items"]:
                    if any(source in result.get("link", "").lower() for source in NEWS_SOURCES):
                        news_sources.append(result)
            
            enhanced_logger.debug("Search filtering completed", 
                                official_sources=len(official_sources), 
                                news_sources=len(news_sources))
            
            return {
                "official_sources": official_sources,
                "news_sources": news_sources,
                "keywords": keywords
            }
            
        except Exception as e:
            enhanced_logger.error("Error in search_news_sources", error=e)
            return {"official_sources": [], "news_sources": [], "keywords": ""}

    @performance_monitor('url_extraction')
    @security_check('url')
    def extract_text_from_url(self, url):
        """Extract text content from a URL with security validation and caching."""
        try:
            cached_content = news_cache.get_cached_url_content(url)
            if cached_content:
                enhanced_logger.debug("Retrieved cached URL content", url=url[:50])
                return cached_content
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            content = sanitize_input(text, config.MAX_CONTENT_LENGTH)
            news_cache.cache_url_content(url, content)
            
            enhanced_logger.debug("URL content extracted successfully", url=url[:50], content_length=len(content))
            return content
        except Exception as e:
            enhanced_logger.error("Error extracting text from URL", error=e, url=url)
            return None

    @performance_monitor('image_processing')
    async def extract_text_from_image(self, image_data):
        """Extract text from image using EasyOCR with enhanced error handling."""
        if self.reader is None:
            enhanced_logger.error("EasyOCR reader not initialized")
            return None
            
        try:
            validation_result = validate_image_file(image_data, "uploaded_image.jpg")
            if not validation_result['safe']:
                enhanced_logger.warning("Image validation failed", errors=validation_result['errors'])
                return None
            
            image = Image.open(io.BytesIO(image_data))
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            results = self.reader.readtext(numpy.array(image))
            text = ' '.join([result[1] for result in results if result[2] > 0.5])
            
            enhanced_logger.debug("Text extraction from image completed", text_length=len(text))
            return text.strip()
        except Exception as e:
            enhanced_logger.error("Error in extract_text_from_image", error=e)
            return None

    def clean_markdown(self, text):
        """Clean text from problematic markdown characters."""
        text = text.replace('*', '')
        text = text.replace('_', '')
        text = text.replace('`', '')
        text = text.replace('[', '')
        text = text.replace(']', '')
        text = text.replace('(', '')
        text = text.replace(')', '')
        return text

    @performance_monitor('news_analysis')
    @rate_limit_check('text_analysis')
    async def analyze_news_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE, news_content: str):
        """Analyze the news content with enhanced features, security, and performance monitoring."""
        try:
            user_id = update.effective_user.id
            
            security_result = security_validator.validate_content(news_content, 'text')
            if not security_result['safe']:
                enhanced_logger.log_security_event('content_validation_failed', user_id, {
                    'errors': security_result['errors'],
                    'content_preview': news_content[:100]
                })
                await update.message.reply_text(
                    "❌ Göndərdiyiniz məzmun təhlükəsizlik yoxlamasından keçmədi.\n"
                    "Zəhmət olmasa başqa məzmun sınayın."
                )
                return
            
            news_content = security_result.get('sanitized_content', news_content)
            
            cached_analysis = news_cache.get_cached_analysis(news_content)
            if cached_analysis:
                enhanced_logger.debug("Using cached analysis", user_id=user_id)
                await update.message.reply_text(
                    "📋 Bu xəbər əvvəllər analiz edilmişdir. Saxlanmış nəticəni göstərirəm:\n\n" + 
                    cached_analysis
                )
                return
            
            duplicate_check = db.check_duplicate(news_content)
            if duplicate_check:
                enhanced_logger.debug("Using database duplicate", user_id=user_id)
                duplicate_message = f"""📋 Bu xəbər əvvəllər analiz edilmişdir:

📅 Analiz tarixi: {duplicate_check['analyzed_date']}
⭐ Etibarlılıq xalı: {duplicate_check['credibility_score']}/10

{duplicate_check['analysis_result']}"""
                await update.message.reply_text(duplicate_message)
                return
            
            enhanced_logger.log_user_action(user_id, 'analysis_started', {
                'content_type': 'text',
                'content_length': len(news_content)
            })
            
            mentioned_sources = self.extract_sources_from_text(news_content)
            search_results = self.search_news_sources(news_content)
            source_verification = self.verify_mentioned_sources(mentioned_sources, search_results["keywords"])
            credibility_analysis = credibility_analyzer.analyze_credibility(
                news_content, search_results, mentioned_sources
            )
            
            prompt = f"""
            Siz bir xəbər analiz mütəxəssisisiniz. Xəbərləri bitərəf və obyektiv şəkildə analiz edirsiniz.
            
            Aşağıdakı xəbəri analiz et və bu məlumatları istifadə edərək ətraflı bir analiz hazırla:
            
            Xəbər məzmunu:
            {news_content}
            
            Avtomatik etibarlılıq qiymətləndirməsi:
            - Ümumi xal: {credibility_analysis['final_score']}/10
            - Etibarlılıq səviyyəsi: {credibility_analysis['credibility_level']}
            - Xəbərdarlıq işarələri: {', '.join(credibility_analysis['warning_flags']) if credibility_analysis['warning_flags'] else 'Yoxdur'}
            
            Xəbərdə istinad edilən mənbələr:
            {mentioned_sources}
            
            Mənbələrin doğrulanması:
            {json.dumps(source_verification, indent=2, ensure_ascii=False) if source_verification else 'Xəbərdə istinad edilən mənbələr tapılmadı və ya doğrulanmadı.'}
            
            Rəsmi mənbələrdə tapılan məlumatlar:
            {json.dumps(search_results['official_sources'], indent=2, ensure_ascii=False) if search_results['official_sources'] else 'Rəsmi mənbələrdə bu xəbərlə əlaqəli məlumat tapılmadı.'}
            
            Digər xəbər mənbələrində tapılan məlumatlar:
            {json.dumps(search_results['news_sources'], indent=2, ensure_ascii=False) if search_results['news_sources'] else 'Digər xəbər mənbələrində bu xəbərlə əlaqəli məlumat tapılmadı.'}
            
            Zəhmət olmasa aşağıdakı formatda ətraflı bir analiz hazırla:
            
            📰 Xəbər Analizi
            [Burada xəbərin əsas məzmununu qısa şəkildə izah edin]
            
            🔍 Mənbə Analizi
            [Burada bütün mənbələri (xəbərdə istinad edilən, rəsmi və digər xəbər mənbələri) birlikdə analiz edin.]
            
            ⚖️ Bitərəflik Analizi
            [Xəbərin bitərəfliyini və mümkün tərəfli ifadələri izah edin]
            
            📊 Nəticə
            [Xəbərin ümumi qiymətləndirməsini və etibarlılıq səviyyəsini izah edin]
            
            📝 Qeydlər
            [Əgər varsa, əlavə qeydlər və xəbərdarlıqlar]
            """

            response = self.model.generate_content(prompt)
            analysis = response.text
            analysis = self.clean_markdown(analysis)
            
            enhanced_analysis = f"""{analysis}

🎯 **Avtomatik Etibarlılıq Qiymətləndirməsi**

⭐ Etibarlılıq xalı: {credibility_analysis['final_score']}/10
📋 Səviyyə: {credibility_analysis['credibility_level']}

{chr(10).join(credibility_analysis['warning_flags']) if credibility_analysis['warning_flags'] else '✅ Xəbərdarlıq işarəsi tapılmadı'}

💡 **Tövsiyələr:**
{chr(10).join(credibility_analysis['recommendations'])}"""

            news_cache.cache_analysis(news_content, enhanced_analysis)
            
            db.save_analysis(
                user_id=user_id,
                news_content=news_content,
                news_type='text',
                keywords=search_results.get('keywords', ''),
                mentioned_sources=mentioned_sources,
                official_sources=search_results.get('official_sources', []),
                news_sources=search_results.get('news_sources', []),
                analysis_result=enhanced_analysis,
                credibility_score=int(credibility_analysis['final_score'])
            )
            
            enhanced_logger.log_user_action(user_id, 'analysis_completed', {
                'credibility_score': credibility_analysis['final_score'],
                'warning_flags_count': len(credibility_analysis['warning_flags']),
                'official_sources_found': len(search_results.get('official_sources', [])),
                'news_sources_found': len(search_results.get('news_sources', []))
            })

            await update.message.reply_text(enhanced_analysis)

        except Exception as e:
            enhanced_logger.error("Error in analyze_news_content", error=e, user_id=user_id)
            await update.message.reply_text(
                "❌ Üzr istəyirəm, bir xəta baş verdi.\n"
                "Zəhmət olmasa daha sonra yenidən cəhd edin."
            )

    # Handler methods
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a welcome message when the /start command is issued."""
        user_id = update.effective_user.id
        
        enhanced_logger.log_user_action(user_id, 'start_command', {
            'username': update.effective_user.username,
            'first_name': update.effective_user.first_name
        })
        
        welcome_message = (
            "👋 *Xoş gəlmisiniz!*\n\n"
            "Mən xəbər doğruluq analiz botuyam. Mənə göndərdiyiniz xəbərlərin doğruluğunu yoxlayıb, "
            "ətraflı analiz təqdim edə bilərəm.\n\n"
            "📝 *İstifadə qaydası:*\n"
            "1️⃣ Bir xəbər linki göndərin\n"
            "2️⃣ Və ya xəbər mətni birbaşa yazın\n"
            "3️⃣ Və ya xəbər şəkli göndərin\n\n"
            "Mən sizə xəbərin doğruluğu haqqında ətraflı bir analiz təqdim edəcəyəm.\n\n"
            "❓ Kömək üçün /help əmrindən istifadə edə bilərsiniz."
        )

        await update.message.reply_text(welcome_message, parse_mode='Markdown')
        
        if UserInteraction:
            await UserInteraction.show_main_menu(update, context)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send a message when the command /help is issued."""
        user_id = update.effective_user.id
        
        enhanced_logger.log_user_action(user_id, 'help_command', {})
        
        help_text = (
            "🤖 *Bot İstifadə Təlimatı*\n\n"
            "📌 *Əsas əmrlər:*\n"
            "• /start - Botu başlatmaq\n"
            "• /help - Bu kömək mesajını göstərmək\n"
            "• /stats - Şəxsi statistikalarınızı görmək\n\n"
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
            "❓ Suallarınız varsa, zəhmət olmasa məlumat verin."
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages with rate limiting and security validation."""
        user_id = update.effective_user.id
        
        rate_check = rate_limiter.is_allowed(user_id, 'image_analysis')
        if not rate_check['allowed']:
            await update.message.reply_text(
                f"❌ Çox tez-tez şəkil göndərirsiniz. "
                f"Zəhmət olmasa {int(rate_check.get('retry_after', 60))} saniyə gözləyin."
            )
            return
        
        try:
            photo = await update.message.photo[-1].get_file()
            photo_data = await photo.download_as_bytearray()
            
            enhanced_logger.log_user_action(user_id, 'image_upload', {
                'file_size': len(photo_data),
                'file_id': photo.file_id
            })
            
            analyzing_message = await update.message.reply_text(
                "🔄 Şəkil analiz olunur...\n"
                "Zəhmət olmasa gözləyin..."
            )
            
            extracted_text = await self.extract_text_from_image(photo_data)
            
            if not extracted_text:
                await analyzing_message.edit_text(
                    "❌ Üzr istəyirəm, şəkildən mətn çıxara bilmədim.\n"
                    "Zəhmət olmasa daha yaxşı keyfiyyətli şəkil göndərin."
                )
                return
            
            await analyzing_message.edit_text(
                "✅ Şəkildən mətn uğurla çıxarıldı!\n"
                "🔄 Mətn analiz olunur...\n"
                "Zəhmət olmasa gözləyin..."
            )
            
            await self.analyze_news_content(update, context, extracted_text)
            await analyzing_message.delete()
            
        except Exception as e:
            enhanced_logger.error("Error in handle_photo", error=e, user_id=user_id)
            await update.message.reply_text(
                "❌ Üzr istəyirəm, şəkil emal edilərkən xəta baş verdi.\n"
                "Zəhmət olmasa daha sonra yenidən cəhd edin."
            )

    async def analyze_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages and analyze news with rate limiting and security."""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text
            
            if UserInteraction and await UserInteraction.handle_text_menu(update, context):
                return
            
            if message_text.startswith(('http://', 'https://')):
                rate_check = rate_limiter.is_allowed(user_id, 'url_analysis')
                operation = 'url_analysis'
            else:
                rate_check = rate_limiter.is_allowed(user_id, 'text_analysis')
                operation = 'text_analysis'
            
            if not rate_check['allowed']:
                await update.message.reply_text(
                    f"❌ Çox tez-tez analiz istəyi göndərirsiniz. "
                    f"Zəhmət olmasa {int(rate_check.get('retry_after', 60))} saniyə gözləyin."
                )
                return
            
            if message_text.startswith(('http://', 'https://')):
                analyzing_message = await update.message.reply_text(
                    "🔄 Link analiz olunur...\n"
                    "Zəhmət olmasa gözləyin..."
                )
                
                news_content = self.extract_text_from_url(message_text)
                if not news_content:
                    await analyzing_message.edit_text(
                        "❌ Üzr istəyirəm, bu linkdən məzmun çəkə bilmədim.\n"
                        "Zəhmət olmasa başqa bir link sınayın."
                    )
                    return
            else:
                analyzing_message = await update.message.reply_text(
                    "🔄 Mətn analiz olunur...\n"
                    "Zəhmət olmasa gözləyin..."
                )
                news_content = message_text

            await analyzing_message.edit_text(
                "✅ Məzmun uğurla əldə edildi!\n"
                "🔄 Xəbər analiz olunur...\n"
                "Zəhmət olmasa gözləyin..."
            )

            await self.analyze_news_content(update, context, news_content)
            await analyzing_message.delete()

        except Exception as e:
            enhanced_logger.error("Error in analyze_news", error=e, user_id=update.effective_user.id)
            await update.message.reply_text(
                "❌ Üzr istəyirəm, bir xəta baş verdi.\n"
                "Zəhmət olmasa daha sonra yenidən cəhd edin."
            )

    async def user_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics command."""
        user_id = update.effective_user.id
        
        try:
            user_stats = db.get_user_stats(user_id)
            rate_stats = rate_limiter.get_user_stats(user_id)
            
            if user_stats:
                stats_message = f"""📊 **Sizin Statistikalarınız**

🔢 Ümumi analizlər: {user_stats['total_analyses']}
📅 İlk analiz: {user_stats['first_analysis_date']}
📅 Son analiz: {user_stats['last_analysis_date']}

🚀 **Rate Limit Vəziyyəti:**
• Mətn analizi: {rate_stats['operations']['text_analysis']['remaining']}/{rate_stats['operations']['text_analysis']['limit']} qalıb
• URL analizi: {rate_stats['operations']['url_analysis']['remaining']}/{rate_stats['operations']['url_analysis']['limit']} qalıb
• Şəkil analizi: {rate_stats['operations']['image_analysis']['remaining']}/{rate_stats['operations']['image_analysis']['limit']} qalıb

💡 Siz artıq təcrübəli bir istifadəçisiniz! Davam edin."""
            else:
                stats_message = """📊 **Sizin Statistikalarınız**

🔢 Ümumi analizlər: 0
📅 Hələ heç bir analiz etməmisiniz.

💡 İlk xəbərinizi analiz etmək üçün bir xəbər göndərin!"""
            
            await update.message.reply_text(stats_message, parse_mode='Markdown')
            
            enhanced_logger.log_user_action(user_id, 'stats_viewed', {
                'has_previous_analyses': user_stats is not None
            })
            
        except Exception as e:
            enhanced_logger.error("Error in user_stats_command", error=e, user_id=user_id)
            await update.message.reply_text(
                "❌ Statistikalarınızı yükləyərkən xəta baş verdi."
            )


class BotApplication:
    """Main bot application class."""
    
    def __init__(self):
        """Initialize the bot application."""
        self.handlers = BotHandlers()
        self.application = None
    
    def setup_application(self):
        """Setup the Telegram application with handlers."""
        self.application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Add basic handlers
        self.application.add_handler(CommandHandler("start", self.handlers.start))
        self.application.add_handler(CommandHandler("help", self.handlers.help_command))
        self.application.add_handler(CommandHandler("stats", self.handlers.user_stats_command))
        
        # Add admin handlers if available
        for command, handler in ADMIN_COMMANDS.items():
            self.application.add_handler(CommandHandler(command, handler))
        
        # Add user interaction handlers if available
        if UserInteraction:
            self.application.add_handler(CallbackQueryHandler(UserInteraction.handle_button_callback))
        
        # Add content handlers
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handlers.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handlers.analyze_news))
        
        enhanced_logger.info("Bot application setup completed")
    
    def run(self):
        """Run the bot application."""
        if not self.application:
            self.setup_application()
        
        enhanced_logger.info("Starting NewsChecker bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES) 