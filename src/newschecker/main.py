#!/usr/bin/env python3
"""
NewsChecker - Main Entry Point

This is the main entry point for the NewsChecker application.
It provides options to run the Telegram bot, web interface, or both.
"""

import sys
import argparse
import asyncio
import logging
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.newschecker.config.settings import config
from src.newschecker.utils.logging import enhanced_logger, log_startup_info, log_shutdown_info
from src.newschecker.utils.rate_limiting import initialize_rate_limiter

def setup_logging():
    """Setup application logging."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_bot():
    """Run the Telegram bot."""
    try:
        from src.newschecker.bot.handlers import BotApplication
        
        log_startup_info()
        enhanced_logger.info("Starting Telegram bot...")
        
        # Initialize rate limiter with admin users
        initialize_rate_limiter(config.ADMIN_USER_IDS)
        
        # Create and run bot application
        bot_app = BotApplication()
        bot_app.run()
        
    except KeyboardInterrupt:
        enhanced_logger.info("Bot shutdown requested by user")
    except Exception as e:
        enhanced_logger.critical("Critical error in bot", error=e)
        raise
    finally:
        log_shutdown_info()

def run_web():
    """Run the web interface."""
    try:
        from src.newschecker.web.app import create_app
        
        log_startup_info()
        enhanced_logger.info("Starting web interface...")
        
        # Create Flask app
        app = create_app()
        
        # Run the web server
        app.run(
            host=config.WEB_HOST,
            port=config.WEB_PORT,
            debug=config.WEB_DEBUG
        )
        
    except KeyboardInterrupt:
        enhanced_logger.info("Web server shutdown requested by user")
    except Exception as e:
        enhanced_logger.critical("Critical error in web server", error=e)
        raise
    finally:
        log_shutdown_info()

def run_both():
    """Run both bot and web interface."""
    import threading
    
    enhanced_logger.info("Starting both bot and web interface...")
    
    # Start web server in a separate thread
    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()
    
    # Run bot in main thread
    run_bot()

def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(
        description='NewsChecker - AI-powered news verification system'
    )
    
    parser.add_argument(
        'mode',
        choices=['bot', 'web', 'both'],
        help='Run mode: bot (Telegram bot), web (web interface), or both'
    )
    
    parser.add_argument(
        '--config-check',
        action='store_true',
        help='Check configuration and exit'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Override log level'
    )
    
    args = parser.parse_args()
    
    # Override log level if specified
    if args.log_level:
        config.LOG_LEVEL = args.log_level
    
    # Setup logging
    setup_logging()
    
    # Configuration check
    if args.config_check:
        enhanced_logger.info("Checking configuration...")
        
        try:
            # Validate configuration
            if config.validate_config():
                enhanced_logger.info("Configuration is valid")
                print("Configuration Summary:")
                summary = config.get_summary()
                for key, value in summary.items():
                    print(f"  {key}: {value}")
                sys.exit(0)
            else:
                enhanced_logger.error("Configuration validation failed")
                sys.exit(1)
        except Exception as e:
            enhanced_logger.error(f"❌ Configuration error: {e}")
            sys.exit(1)
    
    # Run the appropriate mode
    try:
        if args.mode == 'bot':
            run_bot()
        elif args.mode == 'web':
            run_web()
        elif args.mode == 'both':
            run_both()
    except Exception as e:
        enhanced_logger.critical(f"Application failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 