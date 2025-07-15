"""
Security utilities for the News Verification Bot
Provides input validation, rate limiting, and security features.
"""

import re
import validators
from urllib.parse import urlparse
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class InputValidator:
    """Handles input validation and sanitization."""
    
    # Suspicious domains to block (can be expanded)
    BLOCKED_DOMAINS = {
        'malicious-site.com',
        'phishing.example',
        'scam.test',
        # Add more as needed
    }
    
    # File extensions that might be dangerous
    DANGEROUS_EXTENSIONS = {'.exe', '.bat', '.cmd', '.scr', '.com', '.pif'}
    
    @staticmethod
    def validate_url(url: str) -> tuple[bool, str]:
        """
        Validate URL for security and format.
        
        Args:
            url: URL to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not url:
            return False, "URL cannot be empty"
        
        # Basic URL validation
        if not validators.url(url):
            return False, "Invalid URL format"
        
        try:
            parsed = urlparse(url)
            
            # Check if domain is blocked
            if parsed.netloc.lower() in InputValidator.BLOCKED_DOMAINS:
                return False, "Domain is blocked for security reasons"
            
            # Block dangerous file extensions
            if any(parsed.path.lower().endswith(ext) for ext in InputValidator.DANGEROUS_EXTENSIONS):
                return False, "File type not allowed"
            
            # Block non-HTTP(S) protocols
            if parsed.scheme.lower() not in ['http', 'https']:
                return False, "Only HTTP and HTTPS URLs are allowed"
            
            # Block localhost and private IPs (basic check)
            if parsed.netloc.lower() in ['localhost', '127.0.0.1']:
                return False, "Local URLs are not allowed"
            
            return True, ""
            
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False, "URL validation failed"
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 10000) -> str:
        """
        Sanitize text input to prevent injection attacks.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove potential script injections
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'data:', '', text, flags=re.IGNORECASE)
        text = re.sub(r'vbscript:', '', text, flags=re.IGNORECASE)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Limit length
        text = text.strip()[:max_length]
        
        return text
    
    @staticmethod
    def validate_text_length(text: str, max_length: int = 10000) -> tuple[bool, str]:
        """
        Validate text length.
        
        Args:
            text: Text to validate
            max_length: Maximum allowed length
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not text:
            return False, "Text cannot be empty"
        
        if len(text) > max_length:
            return False, f"Text is too long (max {max_length} characters)"
        
        return True, ""

class RateLimiter:
    """Implements rate limiting per user."""
    
    def __init__(self, max_requests: int = 5, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> tuple[bool, Optional[int]]:
        """
        Check if user is allowed to make a request.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Tuple of (is_allowed, seconds_until_reset)
        """
        now = datetime.now()
        user_requests = self.requests[user_id]
        
        # Remove old requests outside the time window
        cutoff = now - timedelta(seconds=self.time_window)
        self.requests[user_id] = [req for req in user_requests if req > cutoff]
        
        # Check if limit exceeded
        if len(self.requests[user_id]) >= self.max_requests:
            # Calculate time until oldest request expires
            oldest_request = min(self.requests[user_id])
            reset_time = oldest_request + timedelta(seconds=self.time_window)
            seconds_until_reset = int((reset_time - now).total_seconds())
            return False, max(0, seconds_until_reset)
        
        # Add current request
        self.requests[user_id].append(now)
        return True, None
    
    def get_remaining_requests(self, user_id: int) -> int:
        """Get number of remaining requests for user."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.time_window)
        
        # Clean old requests
        if user_id in self.requests:
            self.requests[user_id] = [req for req in self.requests[user_id] if req > cutoff]
            return max(0, self.max_requests - len(self.requests[user_id]))
        
        return self.max_requests

class SecurityConfig:
    """Security configuration settings."""
    
    def __init__(self):
        import os
        
        # Rate limiting settings
        self.max_requests_per_user = int(os.getenv('MAX_REQUESTS_PER_USER', '5'))
        self.rate_limit_window = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        
        # Text limits
        self.max_text_length = int(os.getenv('MAX_TEXT_LENGTH', '10000'))
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=self.max_requests_per_user,
            time_window=self.rate_limit_window
        )

# Global security configuration instance
security_config = SecurityConfig()

def check_rate_limit(user_id: int) -> tuple[bool, Optional[str]]:
    """
    Check if user has exceeded rate limit.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        Tuple of (is_allowed, error_message)
    """
    is_allowed, seconds_until_reset = security_config.rate_limiter.is_allowed(user_id)
    
    if not is_allowed:
        remaining_time = seconds_until_reset or 60
        return False, (
            f"⏳ Çox tez-tez sorğu göndərirsiniz. "
            f"Zəhmət olmasa {remaining_time} saniyə gözləyin."
        )
    
    return True, None

def validate_input(text: str) -> tuple[bool, Optional[str]]:
    """
    Validate general text input.
    
    Args:
        text: Text to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = InputValidator.validate_text_length(
        text, 
        security_config.max_text_length
    )
    
    if not is_valid:
        return False, f"❌ {error}"
    
    return True, None

def validate_url_input(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL input.
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    is_valid, error = InputValidator.validate_url(url)
    
    if not is_valid:
        return False, f"❌ {error}"
    
    return True, None