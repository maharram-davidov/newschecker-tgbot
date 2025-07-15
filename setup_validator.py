#!/usr/bin/env python3
"""
Setup Validation Script for News Verification Bot
Run this script to validate your configuration before starting the bot.
"""

import os
import sys
from dotenv import load_dotenv
import requests
import google.generativeai as genai
from serpapi import GoogleSearch

def check_env_file():
    """Check if .env file exists and has required variables."""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("   Please copy .env.template to .env and fill in your API keys")
        return False
    
    load_dotenv()
    
    required_vars = ['TELEGRAM_BOT_TOKEN', 'GEMINI_API_KEY', 'SERPAPI_API_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f'your_{var.lower()}_here':
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing or invalid environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Environment file validation passed")
    return True

def validate_telegram_token():
    """Validate Telegram bot token."""
    try:
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        response = requests.get(f'https://api.telegram.org/bot{token}/getMe', timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Telegram bot validation passed - Bot: {bot_info['result']['first_name']}")
            return True
        else:
            print("❌ Invalid Telegram bot token")
            return False
    except Exception as e:
        print(f"❌ Telegram validation failed: {e}")
        return False

def validate_gemini_api():
    """Validate Google Gemini API key."""
    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        response = model.generate_content("Test message")
        print("✅ Gemini API validation passed")
        return True
    except Exception as e:
        print(f"❌ Gemini API validation failed: {e}")
        return False

def validate_serpapi():
    """Validate SerpAPI key."""
    try:
        search = GoogleSearch({
            "q": "test",
            "api_key": os.getenv('SERPAPI_API_KEY'),
            "num": 1
        })
        results = search.get_dict()
        
        if "error" in results:
            print(f"❌ SerpAPI validation failed: {results['error']}")
            return False
        
        print("✅ SerpAPI validation passed")
        return True
    except Exception as e:
        print(f"❌ SerpAPI validation failed: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    try:
        import telegram
        import google.generativeai
        import requests
        import beautifulsoup4
        import serpapi
        import easyocr
        import PIL
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("   Run: pip install -r requirements.txt")
        return False

def main():
    """Run all validation checks."""
    print("🔍 Validating News Verification Bot Setup...\n")
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file),
        ("Telegram Bot Token", validate_telegram_token),
        ("Gemini API Key", validate_gemini_api),
        ("SerpAPI Key", validate_serpapi)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"Checking {check_name}...")
        if not check_func():
            all_passed = False
        print()
    
    if all_passed:
        print("🎉 All checks passed! Your bot is ready to run.")
        print("   Start the bot with: python bot.py")
    else:
        print("⚠️  Some checks failed. Please fix the issues above before starting the bot.")
        sys.exit(1)

if __name__ == "__main__":
    main()