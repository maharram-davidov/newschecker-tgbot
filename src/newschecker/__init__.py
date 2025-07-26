"""
NewsChecker - AI-powered news verification system for Azerbaijani content.

This package provides comprehensive news analysis capabilities including:
- Text analysis and credibility scoring
- URL content extraction and verification
- Image text extraction using OCR
- Source verification and cross-referencing
- Multi-language support with focus on Azerbaijani content
"""

__version__ = "1.0.0"
__author__ = "NewsChecker Team"
__description__ = "AI-powered news verification system"

# Core imports for package-level access
from .core.analyzer import CredibilityAnalyzer
from .core.database import NewsDatabase
from .core.cache import NewsCache
from .config.settings import config

__all__ = [
    'CredibilityAnalyzer',
    'NewsDatabase', 
    'NewsCache',
    'config'
] 