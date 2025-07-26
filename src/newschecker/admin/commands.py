import logging
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timedelta
import json

# Import from new structure
from ..core.database import db
from ..core.cache import news_cache
from ..config.settings import config

logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in config.ADMIN_USER_IDS

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    try:
        # Database statistics
        db_stats = db.get_database_stats()
        
        # Cache statistics
        cache_stats = news_cache.get_stats()
        
        # Generate stats message
        stats_message = f"""📊 **Bot Statistikası**

🗄️ **Database:**
• Ümumi analizlər: {db_stats.get('total_analyses', 0)}
• Ümumi istifadəçilər: {db_stats.get('total_users', 0)}
• Orta etibarlılıq xalı: {db_stats.get('avg_credibility_score', 0):.1f}

💾 **Cache:**
• Aktiv girişlər: {cache_stats.get('total_entries', 0)}
• Yaddaş istifadəsi: {cache_stats.get('memory_usage_mb', 0):.2f} MB
• Cache hit rate: {cache_stats.get('hit_rate_percent', 0):.1f}%
• Evictions: {cache_stats.get('evictions', 0)}

📊 **Top İstifadəçilər:**"""
        
        # Add top users info
        top_users = db_stats.get('top_users', [])
        for i, user in enumerate(top_users[:5], 1):
            stats_message += f"\n{i}. User {user['user_id']}: {user['total_analyses']} analiz"
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in admin_stats: {e}")
        await update.message.reply_text("❌ Statistika yükləməkdə xəta baş verdi.")

async def admin_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get user information - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    try:
        if not context.args:
            await update.message.reply_text("📝 İstifadə: /adminuser <user_id>")
            return
        
        user_id = int(context.args[0])
        user_stats = db.get_user_stats(user_id)
        user_history = db.get_user_history(user_id, limit=5)
        
        if not user_stats:
            await update.message.reply_text(f"❌ User {user_id} tapılmadı.")
            return
        
        info_message = f"""👤 **İstifadəçi Məlumatı: {user_id}**

📊 **Statistika:**
• Ümumi analizlər: {user_stats['total_analyses']}
• İlk analiz: {user_stats['first_analysis_date']}
• Son analiz: {user_stats['last_analysis_date']}
• Orta etibarlılıq: {user_stats.get('average_credibility_score', 0):.1f}

📋 **Son Analizlər:**"""
        
        for analysis in user_history:
            info_message += f"\n• {analysis['analyzed_date']}: {analysis['news_type']} - {analysis['credibility_score']}/10"
        
        await update.message.reply_text(info_message, parse_mode='Markdown')
        
    except ValueError:
        await update.message.reply_text("❌ Yanlış user ID formatı.")
    except Exception as e:
        logger.error(f"Error in admin_user_info: {e}")
        await update.message.reply_text("❌ İstifadəçi məlumatı yükləməkdə xəta.")

async def admin_clear_cache(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear cache - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    try:
        cache_type = context.args[0] if context.args else None
        
        if cache_type:
            news_cache.clear(cache_type)
            await update.message.reply_text(f"✅ {cache_type} cache təmizləndi.")
        else:
            news_cache.clear()
            await update.message.reply_text("✅ Bütün cache təmizləndi.")
        
        logger.info(f"Admin {update.effective_user.id} cleared cache: {cache_type or 'all'}")
        
    except Exception as e:
        logger.error(f"Error in admin_clear_cache: {e}")
        await update.message.reply_text("❌ Cache təmizləməkdə xəta baş verdi.")

async def admin_export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export database data - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    try:
        # Get recent analyses for export
        from ..core.database import db
        
        # This is a simplified export - in production you'd want to create actual files
        stats = db.get_database_stats()
        export_info = {
            'export_date': datetime.now().isoformat(),
            'total_analyses': stats.get('total_analyses', 0),
            'total_users': stats.get('total_users', 0),
            'avg_credibility': stats.get('avg_credibility_score', 0)
        }
        
        await update.message.reply_text(
            f"📄 **Data Export Summary**\n\n"
            f"```json\n{json.dumps(export_info, indent=2, ensure_ascii=False)}\n```",
            parse_mode='Markdown'
        )
        
        logger.info(f"Admin {update.effective_user.id} exported data")
        
    except Exception as e:
        logger.error(f"Error in admin_export_data: {e}")
        await update.message.reply_text("❌ Data eksportunda xəta baş verdi.")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin help - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    help_text = """🛠️ **Admin Əmrləri**

📊 **Statistika:**
• /adminstats - Bot statistikası
• /adminuser <user_id> - İstifadəçi məlumatı

🔧 **İdarəetmə:**
• /adminclear [cache_type] - Cache təmizləmə
• /adminexport - Data eksportu
• /adminhelp - Bu kömək menyusu

💡 **Qeydlər:**
- Bütün əmrlər log edilir
- Cache növləri: analysis, search, url_content
- Export yalnız summary məlumat verir"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def admin_system_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show system information - Admin only"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Bu əmr yalnız adminlər üçündür.")
        return
    
    try:
        import psutil
        import sys
        
        system_info = f"""🖥️ **Sistem Məlumatı**

🐍 **Python:**
• Versiya: {sys.version.split()[0]}
• Platform: {sys.platform}

💾 **Yaddaş:**
• RAM istifadəsi: {psutil.virtual_memory().percent:.1f}%
• Disk istifadəsi: {psutil.disk_usage('/').percent:.1f}%

⚙️ **Konfigurasiya:**
• Log level: {config.LOG_LEVEL}
• Cache enabled: {config.ENABLE_CACHING}
• Rate limiting: {config.ENABLE_RATE_LIMITING}
• Performance monitoring: {config.ENABLE_PERFORMANCE_MONITORING}"""
        
        await update.message.reply_text(system_info, parse_mode='Markdown')
        
    except ImportError:
        await update.message.reply_text("⚠️ psutil paketi yüklənməyib. Əsas məlumat:")
        basic_info = f"""🖥️ **Əsas Sistem Məlumatı**

🐍 Python versiya: {sys.version.split()[0]}
⚙️ Cache aktiv: {config.ENABLE_CACHING}
📊 Monitoring aktiv: {config.ENABLE_PERFORMANCE_MONITORING}"""
        await update.message.reply_text(basic_info, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error in admin_system_info: {e}")
        await update.message.reply_text("❌ Sistem məlumatı yükləməkdə xəta.")

# Admin commands registry
ADMIN_COMMANDS = {
    'adminstats': admin_stats,
    'adminuser': admin_user_info,
    'adminclear': admin_clear_cache,
    'adminexport': admin_export_data,
    'adminhelp': admin_help,
    'adminsystem': admin_system_info,
} 