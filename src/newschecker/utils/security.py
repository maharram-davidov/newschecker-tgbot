import re
import logging
import hashlib
import mimetypes
from urllib.parse import urlparse
from typing import Dict, List, Any, Optional, Union
from functools import wraps

class SecurityValidator:
    """Enhanced security validation and sanitization system."""
    
    def __init__(self):
        self.blocked_domains = {
            'bit.ly', 'tinyurl.com', 't.co', 'goo.gl', 'ow.ly',
            'buff.ly', 'adf.ly', 'linktr.ee', 'short.link',
            'malicious-site.com', 'phishing-example.com'
        }
        
        self.malicious_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'vbscript:',
            r'data:text/html',
            r'on\w+\s*=',  # Event handlers like onclick, onload
            r'eval\s*\(',
            r'document\.cookie',
            r'window\.location',
            r'<iframe[^>]*>',
            r'<embed[^>]*>',
            r'<object[^>]*>',
        ]
        
        self.compiled_patterns = [re.compile(pattern, re.IGNORECASE | re.DOTALL) 
                                for pattern in self.malicious_patterns]
        
        # File signature mapping (magic bytes)
        self.file_signatures = {
            b'\xFF\xD8\xFF': '.jpg',
            b'\x89\x50\x4E\x47': '.png',
            b'\x47\x49\x46\x38': '.gif',
            b'\x42\x4D': '.bmp',
            b'RIFF': '.webp',  # WEBP files start with RIFF
        }
        
        self.max_content_length = 5000
        self.max_url_length = 2048
        self.max_image_size = 5 * 1024 * 1024  # 5MB
        
    def validate_content(self, content: str, content_type: str = 'text') -> Dict[str, Any]:
        """
        Comprehensive content validation.
        
        Args:
            content: The content to validate
            content_type: Type of content ('text', 'url', 'html')
            
        Returns:
            Dict with validation results
        """
        result = {
            'safe': True,
            'errors': [],
            'warnings': [],
            'sanitized_content': content,
            'security_score': 100
        }
        
        if not content:
            result['errors'].append('Empty content')
            result['safe'] = False
            return result
        
        # Length validation
        if len(content) > self.max_content_length:
            result['warnings'].append(f'Content length exceeds {self.max_content_length} characters')
            result['sanitized_content'] = content[:self.max_content_length] + '...'
            result['security_score'] -= 10
        
        # Malicious pattern detection
        malicious_found = []
        for i, pattern in enumerate(self.compiled_patterns):
            if pattern.search(content):
                malicious_found.append(self.malicious_patterns[i])
        
        if malicious_found:
            result['errors'].extend([f'Malicious pattern detected: {pattern}' for pattern in malicious_found])
            result['safe'] = False
            result['security_score'] -= 50
        
        # Content-specific validation
        if content_type == 'url':
            url_validation = self._validate_url_security(content)
            result['errors'].extend(url_validation['errors'])
            result['warnings'].extend(url_validation['warnings'])
            if not url_validation['safe']:
                result['safe'] = False
                result['security_score'] -= 30
        
        # Sanitize content
        result['sanitized_content'] = self._sanitize_content(result['sanitized_content'])
        
        return result
    
    def _validate_url_security(self, url: str) -> Dict[str, Any]:
        """Validate URL for security threats."""
        result = {'safe': True, 'errors': [], 'warnings': []}
        
        try:
            parsed = urlparse(url)
            
            # Scheme validation
            if parsed.scheme not in ['http', 'https']:
                result['errors'].append(f'Invalid URL scheme: {parsed.scheme}')
                result['safe'] = False
            
            # Domain validation
            domain = parsed.netloc.lower()
            if any(blocked in domain for blocked in self.blocked_domains):
                result['errors'].append(f'Blocked domain detected: {domain}')
                result['safe'] = False
            
            # Length validation
            if len(url) > self.max_url_length:
                result['warnings'].append(f'URL length exceeds {self.max_url_length} characters')
            
            # Suspicious patterns in URL
            suspicious_patterns = ['%00', '../', '..\\', 'file://', 'ftp://']
            for pattern in suspicious_patterns:
                if pattern in url.lower():
                    result['errors'].append(f'Suspicious pattern in URL: {pattern}')
                    result['safe'] = False
            
        except Exception as e:
            result['errors'].append(f'URL parsing error: {str(e)}')
            result['safe'] = False
        
        return result
    
    def _sanitize_content(self, content: str) -> str:
        """Sanitize content by removing dangerous elements."""
        if not content:
            return ""
        
        # Remove null bytes and control characters
        content = ''.join(char for char in content if ord(char) >= 32 or char in '\n\r\t')
        
        # Remove potential XSS patterns
        for pattern in self.compiled_patterns:
            content = pattern.sub('', content)
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        return content
    
    def validate_image_file(self, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Validate uploaded image file for security.
        
        Args:
            file_data: Raw file bytes
            filename: Original filename
            
        Returns:
            Dict with validation results
        """
        result = {
            'safe': True,
            'errors': [],
            'warnings': [],
            'file_type': None,
            'size': len(file_data)
        }
        
        # Size validation
        if len(file_data) > self.max_image_size:
            result['errors'].append(f'File size exceeds {self.max_image_size} bytes')
            result['safe'] = False
            return result
        
        # Magic byte validation
        detected_type = self._detect_file_type(file_data)
        if not detected_type:
            result['errors'].append('Unable to detect file type or unsupported format')
            result['safe'] = False
            return result
        
        result['file_type'] = detected_type
        
        # MIME type validation
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type and not mime_type.startswith('image/'):
            result['warnings'].append(f'MIME type mismatch: {mime_type}')
        
        # Additional security checks
        if self._has_embedded_threats(file_data):
            result['errors'].append('Embedded threats detected in file')
            result['safe'] = False
        
        return result
    
    def _detect_file_type(self, file_data: bytes) -> Optional[str]:
        """Detect file type based on magic bytes."""
        for signature, file_type in self.file_signatures.items():
            if file_data.startswith(signature):
                return file_type
        
        # Additional checks for WEBP
        if file_data.startswith(b'RIFF') and b'WEBP' in file_data[:12]:
            return '.webp'
        
        return None
    
    def _has_embedded_threats(self, file_data: bytes) -> bool:
        """Check for embedded threats in file."""
        # Convert to string for pattern matching (ignore encoding errors)
        try:
            file_content = file_data.decode('utf-8', errors='ignore')
            
            # Check for suspicious patterns
            threat_patterns = [
                'javascript:', '<script', 'eval(', 'document.cookie',
                'window.location', '<iframe', '<embed', '<object'
            ]
            
            for pattern in threat_patterns:
                if pattern.lower() in file_content.lower():
                    return True
                    
        except Exception:
            pass  # Ignore decoding errors for binary files
        
        return False
    
    def get_content_hash(self, content: Union[str, bytes]) -> str:
        """Generate secure hash of content for duplicate detection."""
        if isinstance(content, str):
            content = content.encode('utf-8')
        
        return hashlib.sha256(content).hexdigest()
    
    def log_security_event(self, event_type: str, user_id: int, details: Dict[str, Any]):
        """Log security-related events."""
        log_entry = {
            'event_type': event_type,
            'user_id': user_id,
            'timestamp': logging.Formatter().formatTime(logging.LogRecord(
                name='security', level=logging.WARNING, pathname='', lineno=0,
                msg='', args=(), exc_info=None
            )),
            'details': details
        }
        
        logging.warning(f"Security Event: {log_entry}")

# Global security validator instance
security_validator = SecurityValidator()

def security_check(content_type: str = 'text'):
    """
    Decorator for functions that need security validation.
    
    Args:
        content_type: Type of content to validate ('text', 'url', 'image')
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Find content argument (assumes first string argument is content)
            content = None
            for arg in args:
                if isinstance(arg, str) and len(arg) > 0:
                    content = arg
                    break
            
            if content:
                validation = security_validator.validate_content(content, content_type)
                if not validation['safe']:
                    logging.warning(f"Security validation failed for {func.__name__}: {validation['errors']}")
                    return None
            
            return func(*args, **kwargs)
        return wrapper
    return decorator

def validate_image_file(file_data: bytes, filename: str) -> Dict[str, Any]:
    """Convenience function for image validation."""
    return security_validator.validate_image_file(file_data, filename)

def get_xss_protection_headers() -> Dict[str, str]:
    """Get HTTP headers for XSS protection."""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    } 