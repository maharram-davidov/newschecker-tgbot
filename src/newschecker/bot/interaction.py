import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes

# Import from new structure
from ..core.database import db

logger = logging.getLogger(__name__)

class UserInteraction:
    def __init__(self):
        pass
    
    @staticmethod
    async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show main interaction menu"""
        keyboard = [
            [KeyboardButton("📰 Xəbər Analizi"), KeyboardButton("📊 Mənim Statistikam")],
            [KeyboardButton("❓ Kömək"), KeyboardButton("⚙️ Ayarlar")],
            [KeyboardButton("📚 Necə İstifadə Etmək Olar")]
        ]
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=False
        )
        
        await update.message.reply_text(
            "🎯 **Əsas Menyu**\n\n"
            "Aşağıdakı seçimlərdən birini seçin:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_analysis_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show analysis type options"""
        keyboard = [
            [InlineKeyboardButton("📝 Mətn Analizi", callback_data="analysis_text")],
            [InlineKeyboardButton("🔗 Link Analizi", callback_data="analysis_link")],
            [InlineKeyboardButton("🖼️ Şəkil Analizi", callback_data="analysis_image")],
            [InlineKeyboardButton("🔙 Geri", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📰 **Xəbər Analizi Növləri**\n\n"
            "Hansı növ analiz etmək istəyirsiniz?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_user_stats_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics menu"""
        user_id = update.effective_user.id
        
        try:
            user_stats = db.get_user_stats(user_id)
            user_history = db.get_user_history(user_id, limit=5)
            
            if user_stats:
                stats_text = f"""📊 **Sizin Statistikalarınız**

🔢 Ümumi analizlər: {user_stats['total_analyses']}
📅 İlk analiz: {user_stats['first_analysis_date']}
📅 Son analiz: {user_stats['last_analysis_date']}
⭐ Orta etibarlılıq xalı: {user_stats.get('average_credibility_score', 0):.1f}

📋 **Son 5 Analiz:**"""
                
                for i, analysis in enumerate(user_history, 1):
                    stats_text += f"\n{i}. {analysis['news_type']} - {analysis['credibility_score']}/10"
                
                keyboard = [
                    [InlineKeyboardButton("📈 Ətraflı Statistika", callback_data="detailed_stats")],
                    [InlineKeyboardButton("🔙 Əsas Menyu", callback_data="back_to_menu")]
                ]
            else:
                stats_text = """📊 **Sizin Statistikalarınız**

🔢 Hələ heç bir analiz etməmisiniz.
💡 İlk xəbərinizi analiz etmək üçün "📰 Xəbər Analizi" seçin!"""
                
                keyboard = [
                    [InlineKeyboardButton("📰 İlk Analizi Başlat", callback_data="analysis_text")],
                    [InlineKeyboardButton("🔙 Əsas Menyu", callback_data="back_to_menu")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing user stats: {e}")
            await update.message.reply_text("❌ Statistikalarınızı yükləməkdə xəta baş verdi.")
    
    @staticmethod
    async def show_help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help menu"""
        help_text = """❓ **Kömək və Məlumat**

🤖 **Bot haqqında:**
Bu bot xəbərlərin doğruluğunu AI vasitəsilə analiz edir.

📝 **İstifadə qaydası:**
1. Xəbər mətni, linki və ya şəkli göndərin
2. Bot avtomatik analiz edəcək
3. Etibarlılıq xalı və təfərrüatlı hesabat alacaqsınız

⭐ **Etibarlılıq Xalları:**
• 8-10: Yüksək Etibarlı 🟢
• 6-7.9: Etibarlı 🔵  
• 4-5.9: Orta 🟡
• 2-3.9: Şübhəli 🟠
• 0-1.9: Etibarsız 🔴

🔍 **Analiz Parametrləri:**
• Mənbə etibarlılığı
• Məzmun keyfiyyəti
• Dil istifadəsi
• Faktiki doğrulama
• Zaman uyğunluğu"""
        
        keyboard = [
            [InlineKeyboardButton("📋 Ətraflı Təlimat", callback_data="detailed_help")],
            [InlineKeyboardButton("🔙 Əsas Menyu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show settings menu"""
        settings_text = """⚙️ **Tənzimləmələr**

🔔 **Bildirişlər:** Aktiv
🌐 **Dil:** Azərbaycan dili
📊 **Statistika:** Aktiv
🔒 **Məxfilik:** Yüksək

💡 **Qeyd:** Tənzimləmələr hazırda əl ilə dəyişdirilə bilməz.
Gələcək versiyalarda əlavə seçimlər əlavə ediləcək."""
        
        keyboard = [
            [InlineKeyboardButton("🔙 Əsas Menyu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def show_tutorial(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tutorial"""
        tutorial_text = """📚 **Necə İstifadə Etmək Olar**

🎯 **Addım-addım təlimat:**

1️⃣ **Xəbər göndərin:**
   • Mətn yazın və ya yapışdırın
   • Link göndərin
   • Şəkil yükləyin

2️⃣ **Analizi gözləyin:**
   • Bot xəbəri analiz edəcək (30-60 saniyə)
   • Müxtəlif mənbələrlə yoxlayacaq

3️⃣ **Nəticəni oxuyun:**
   • Etibarlılıq xalı (0-10)
   • Təfərrüatlı analiz
   • Tövsiyələr

💡 **Tövsiyələr:**
• Uzun mətnlər daha yaxşı analiz olunur
• Rəsmi mənbələr üstünlük təşkil edir
• Şübhəli xəbərləri paylaşmayın"""
        
        keyboard = [
            [InlineKeyboardButton("📰 İndi Sınayın", callback_data="analysis_text")],
            [InlineKeyboardButton("🔙 Əsas Menyu", callback_data="back_to_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(tutorial_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def handle_text_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text-based menu interactions"""
        text = update.message.text.strip()
        
        if text == "📰 Xəbər Analizi":
            await UserInteraction.show_analysis_options(update, context)
            return True
        elif text == "📊 Mənim Statistikam":
            await UserInteraction.show_user_stats_menu(update, context)
            return True
        elif text == "❓ Kömək":
            await UserInteraction.show_help_menu(update, context)
            return True
        elif text == "⚙️ Ayarlar":
            await UserInteraction.show_settings_menu(update, context)
            return True
        elif text == "📚 Necə İstifadə Etmək Olar":
            await UserInteraction.show_tutorial(update, context)
            return True
        
        return False
    
    @staticmethod
    async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "back_to_menu":
            # Edit the message to show main menu text
            await query.edit_message_text(
                "🎯 **Əsas Menyu**\n\n"
                "Aşağıdakı düymələrdən birini seçin və ya mətn yazın:",
                parse_mode='Markdown'
            )
            # Show main menu
            await UserInteraction.show_main_menu(query, context)
        
        elif callback_data == "analysis_text":
            await query.edit_message_text(
                "📝 **Mətn Analizi**\n\n"
                "Zəhmət olmasa analiz etmək istədiyiniz xəbər mətnini yazın:",
                parse_mode='Markdown'
            )
        
        elif callback_data == "analysis_link":
            await query.edit_message_text(
                "🔗 **Link Analizi**\n\n"
                "Zəhmət olmasa analiz etmək istədiyiniz xəbər linkini göndərin:",
                parse_mode='Markdown'
            )
        
        elif callback_data == "analysis_image":
            await query.edit_message_text(
                "🖼️ **Şəkil Analizi**\n\n"
                "Zəhmət olmasa analiz etmək istədiyiniz xəbər şəklini göndərin:",
                parse_mode='Markdown'
            )
        
        elif callback_data == "detailed_stats":
            user_id = query.from_user.id
            try:
                user_stats = db.get_user_stats(user_id)
                user_history = db.get_user_history(user_id, limit=10)
                
                if user_stats:
                    detailed_text = f"""📈 **Ətraflı Statistika**

👤 **İstifadəçi:** {user_id}
🔢 **Ümumi analizlər:** {user_stats['total_analyses']}
📅 **İlk analiz tarixi:** {user_stats['first_analysis_date']}
📅 **Son analiz tarixi:** {user_stats['last_analysis_date']}
⭐ **Orta etibarlılıq xalı:** {user_stats.get('average_credibility_score', 0):.2f}

📊 **Son 10 Analiz:**"""
                    
                    for i, analysis in enumerate(user_history, 1):
                        detailed_text += f"\n{i}. {analysis['analyzed_date'][:10]} - {analysis['news_type']} ({analysis['credibility_score']}/10)"
                    
                    keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="back_to_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await query.edit_message_text(detailed_text, reply_markup=reply_markup, parse_mode='Markdown')
                else:
                    await query.edit_message_text("❌ Statistika məlumatı tapılmadı.")
            except Exception as e:
                logger.error(f"Error showing detailed stats: {e}")
                await query.edit_message_text("❌ Ətraflı statistika yükləməkdə xəta.")
        
        elif callback_data == "detailed_help":
            detailed_help = """📋 **Ətraflı Təlimat**

🔍 **Analiz Prosesi:**
Bot aşağıdaki addımları izləyir:
1. Mətn təmizləmə və normallaşdırma
2. Mənbə identifikasiyası
3. Rəsmi mənbələrlə yoxlama
4. AI ilə məzmun analizi
5. Etibarlılıq hesablama

📊 **Qiymətləndirmə Kriteyaları:**
• **Mənbə etibarlılığı (35%):** Rəsmi mənbələr, tanınmış KİV
• **Məzmun keyfiyyəti (25%):** Struktur, dil keyfiyyəti
• **Dil istifadəsi (20%):** Bitərəflik, manipulyasiya
• **Faktiki doğrulama (15%):** Digər mənbələrlə uyğunluq
• **Aktualıq (5%):** Zaman uyğunluğu

⚠️ **Məhdudiyyətlər:**
• AI sistemi 100% dəqiq deyil
• Həmişə digər mənbələrlə də yoxlayın
• Şübhəli xəbərləri paylaşmayın"""
            
            keyboard = [[InlineKeyboardButton("🔙 Geri", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(detailed_help, reply_markup=reply_markup, parse_mode='Markdown')
        
        else:
            # Unknown callback, go back to menu
            await query.edit_message_text("❌ Naməlum seçim. Əsas menyuya qayıdılır...")
            await UserInteraction.show_main_menu(query, context) 