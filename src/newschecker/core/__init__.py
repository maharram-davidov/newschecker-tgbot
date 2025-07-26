"""
Core module containing the main business logic.

This module contains:
- Credibility analysis engine
- Database operations
- Caching system
- Search functionality
- Text processing utilities
"""

from .analyzer import CredibilityAnalyzer
from .database import NewsDatabase
from .cache import NewsCache

__all__ = ['CredibilityAnalyzer', 'NewsDatabase', 'NewsCache'] 