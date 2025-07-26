"""
Bot commands module for basic command handling.

This module contains command handlers for the Telegram bot.
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

# Import from new structure
from ..utils.logging import enhanced_logger
from ..config.settings import config

logger = logging.getLogger(__name__)


class BotCommands:
    """Basic bot command handlers."""
    
    def __init__(self):
        """Initialize bot commands."""
        pass
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
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
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
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
    
    @staticmethod
    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /stats command."""
        user_id = update.effective_user.id
        
        try:
            from ..core.database import db
            from ..utils.rate_limiting import rate_limiter
            
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
            enhanced_logger.error("Error in stats_command", error=e, user_id=user_id)
            await update.message.reply_text(
                "❌ Statistikalarınızı yükləyərkən xəta baş verdi."
            ) 