import os
import logging
from dotenv import load_dotenv
import re
from urllib.parse import urlparse
from typing import Optional, Dict, Any, List

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class for NewsChecker application."""
    
    def __init__(self):
        """Initialize configuration with environment variables."""
        self._validate_environment()
        
        # Core API configurations
        self.TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
        self.GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
        self.GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        self.GOOGLE_CSE_ID = os.getenv('GOOGLE_CSE_ID')
        
        # Model and AI configurations
        self.GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
        self.GEMINI_TEMPERATURE = float(os.getenv('GEMINI_TEMPERATURE', '0.3'))
        
        # Security configurations
        self.MAX_CONTENT_LENGTH = int(os.getenv('MAX_CONTENT_LENGTH', '5000'))
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        self.MAX_IMAGE_SIZE = int(os.getenv('MAX_IMAGE_SIZE', '5242880'))  # 5MB
        
        # Rate limiting configurations
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds
        self.MAX_REQUESTS_PER_MINUTE = int(os.getenv('MAX_REQUESTS_PER_MINUTE', '10'))
        self.MAX_URL_REQUESTS_PER_MINUTE = int(os.getenv('MAX_URL_REQUESTS_PER_MINUTE', '5'))
        self.MAX_IMAGE_REQUESTS_PER_MINUTE = int(os.getenv('MAX_IMAGE_REQUESTS_PER_MINUTE', '3'))
        
        # Database configurations
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'news_checker.db')
        self.CACHE_TTL_HOURS = int(os.getenv('CACHE_TTL_HOURS', '2'))
        
        # Logging configurations
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FILE = os.getenv('LOG_FILE', 'newschecker.log')
        self.LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '10485760'))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Performance configurations
        self.ENABLE_PERFORMANCE_MONITORING = os.getenv('ENABLE_PERFORMANCE_MONITORING', 'true').lower() == 'true'
        self.METRICS_COLLECTION_INTERVAL = int(os.getenv('METRICS_COLLECTION_INTERVAL', '300'))  # 5 minutes
        
        # Feature flags
        self.ENABLE_CACHING = os.getenv('ENABLE_CACHING', 'true').lower() == 'true'
        self.ENABLE_RATE_LIMITING = os.getenv('ENABLE_RATE_LIMITING', 'true').lower() == 'true'
        self.ENABLE_SECURITY_VALIDATION = os.getenv('ENABLE_SECURITY_VALIDATION', 'true').lower() == 'true'
        
        # Admin configurations
        self.ADMIN_USER_IDS = self._parse_admin_users()
        self.ADMIN_RATE_MULTIPLIER = int(os.getenv('ADMIN_RATE_MULTIPLIER', '5'))
        
        # Web interface configurations
        self.WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
        self.WEB_PORT = int(os.getenv('WEB_PORT', '5000'))
        self.WEB_DEBUG = os.getenv('WEB_DEBUG', 'false').lower() == 'true'
        
    def _validate_environment(self):
        """Validate that all required environment variables are present."""
        required_vars = [
            'TELEGRAM_BOT_TOKEN',
            'GEMINI_API_KEY', 
            'GOOGLE_API_KEY',
            'GOOGLE_CSE_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
    def _parse_admin_users(self) -> List[int]:
        """Parse admin user IDs from environment variable."""
        admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
        if not admin_ids_str:
            return []
        
        try:
            return [int(uid.strip()) for uid in admin_ids_str.split(',') if uid.strip()]
        except ValueError:
            logging.warning("Invalid ADMIN_USER_IDS format. Expected comma-separated integers.")
            return []
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration (without sensitive data)."""
        return {
            'gemini_model': self.GEMINI_MODEL,
            'max_content_length': self.MAX_CONTENT_LENGTH,
            'request_timeout': self.REQUEST_TIMEOUT,
            'rate_limiting_enabled': self.ENABLE_RATE_LIMITING,
            'caching_enabled': self.ENABLE_CACHING,
            'security_validation_enabled': self.ENABLE_SECURITY_VALIDATION,
            'performance_monitoring_enabled': self.ENABLE_PERFORMANCE_MONITORING,
            'admin_users_count': len(self.ADMIN_USER_IDS),
            'web_host': self.WEB_HOST,
            'web_port': self.WEB_PORT
        }
    
    def validate_config(self) -> bool:
        """Validate configuration values are reasonable."""
        issues = []
        
        if self.MAX_CONTENT_LENGTH <= 0:
            issues.append("MAX_CONTENT_LENGTH must be positive")
        
        if self.REQUEST_TIMEOUT <= 0:
            issues.append("REQUEST_TIMEOUT must be positive")
        
        if self.RATE_LIMIT_WINDOW <= 0:
            issues.append("RATE_LIMIT_WINDOW must be positive")
        
        if issues:
            logging.error(f"Configuration validation failed: {'; '.join(issues)}")
            return False
        
        return True

# Create global config instance
config = Config()

# News Sources Configuration
NEWS_SOURCES = [
    "trend.az", "axar.az", "apa.az", "azernews.az", "news.az", 
    "milli.az", "oxu.az", "azeribaycan24.com", "moderator.az", "yenisabah.az"
]

OFFICIAL_SOURCES = [
    "gov.az", "president.az", "mfa.gov.az", "economy.gov.az", "who.int",
    "un.org", "council.europa.eu", "europa.eu", "osce.org"
]

def get_official_search_params(keywords: str, date_range: str, api_key: str) -> Dict[str, str]:
    """Get search parameters for official sources."""
    return {
        "q": f'site:gov.az OR site:president.az OR site:mfa.gov.az OR site:who.int "{keywords}" {date_range}',
        "gl": "az",
        "hl": "az",
        "num": 5
    }

def get_news_search_params(keywords: str, date_range: str, api_key: str) -> Dict[str, str]:
    """Get search parameters for news sources."""
    sites = " OR ".join([f"site:{source}" for source in NEWS_SOURCES])
    return {
        "q": f'({sites}) "{keywords}" {date_range}',
        "gl": "az", 
        "hl": "az",
        "num": 10
    }

def validate_url(url: str) -> bool:
    """Validate if URL is properly formatted and safe."""
    if not url:
        return False
    
    try:
        result = urlparse(url)
        if not result.scheme or not result.netloc:
            return False
        
        # Check for allowed schemes
        if result.scheme not in ['http', 'https']:
            return False
        
        # Basic security checks
        if any(dangerous in url.lower() for dangerous in ['javascript:', 'data:', 'vbscript:']):
            return False
        
        return True
    except Exception:
        return False

def sanitize_input(text: str, max_length: Optional[int] = None) -> str:
    """Sanitize user input by removing potentially dangerous content."""
    if not text:
        return ""
    
    # Remove null bytes and control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length if specified
    if max_length and len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text

def get_file_extension(filename: str) -> str:
    """Get file extension from filename."""
    return os.path.splitext(filename.lower())[1]

def is_allowed_file_type(filename: str, allowed_extensions: Optional[List[str]] = None) -> bool:
    """Check if file type is allowed."""
    if not allowed_extensions:
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    
    extension = get_file_extension(filename)
    return extension in allowed_extensions 