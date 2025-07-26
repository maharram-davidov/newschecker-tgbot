import pytest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config_loading():
    """Test that configuration loads successfully"""
    try:
        from config import config, OFFICIAL_SOURCES, NEWS_SOURCES
        
        # Test that configuration object exists
        assert config is not None
        
        # Test that required sources are defined
        assert len(OFFICIAL_SOURCES) > 0
        assert len(NEWS_SOURCES) > 0
        
        # Test specific known sources
        assert "gov.az" in OFFICIAL_SOURCES
        assert "bbc.com" in NEWS_SOURCES
        
    except ImportError as e:
        pytest.fail(f"Failed to import config: {e}")

def test_database_initialization():
    """Test that database initializes successfully"""
    try:
        from database import NewsDatabase
        
        # Create test database
        test_db = NewsDatabase(":memory:")  # Use in-memory database for testing
        
        # Test that database is created
        assert test_db is not None
        assert test_db.db_path == ":memory:"
        
    except ImportError as e:
        pytest.fail(f"Failed to import database: {e}")

def test_cache_manager():
    """Test cache manager functionality"""
    try:
        from cache_manager import CacheManager
        
        # Create test cache
        cache = CacheManager(default_ttl=60)
        
        # Test basic cache operations
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        
        # Test non-existent key
        assert cache.get("non_existent") is None
        
        # Test cache stats
        stats = cache.get_stats()
        assert "total_entries" in stats
        
    except ImportError as e:
        pytest.fail(f"Failed to import cache_manager: {e}")

def test_credibility_analyzer():
    """Test credibility analyzer functionality"""
    try:
        from credibility_analyzer import CredibilityAnalyzer
        
        analyzer = CredibilityAnalyzer()
        
        # Test basic analysis
        test_content = "Bu gün Azərbaycan Prezidenti mühüm açıqlama etdi."
        mock_sources = {"official_sources": [], "news_sources": []}
        mock_mentioned = "Prezident açıqlaması"
        
        result = analyzer.analyze_credibility(test_content, mock_sources, mock_mentioned)
        
        # Verify result structure
        assert "final_score" in result
        assert "credibility_level" in result
        assert "warning_flags" in result
        assert "recommendations" in result
        
        # Score should be between 0 and 10
        assert 0 <= result["final_score"] <= 10
        
    except ImportError as e:
        pytest.fail(f"Failed to import credibility_analyzer: {e}")

def test_utility_functions():
    """Test utility functions from config"""
    try:
        from config import validate_url, sanitize_input, get_file_extension
        
        # Test URL validation
        assert validate_url("https://www.example.com") is True
        assert validate_url("not-a-url") is False
        
        # Test input sanitization
        dirty_input = "<script>alert('test')</script>Normal text"
        clean_input = sanitize_input(dirty_input)
        assert "<script>" not in clean_input
        assert "Normal text" in clean_input
        
        # Test file extension extraction
        assert get_file_extension("test.jpg") == "jpg"
        assert get_file_extension("document.pdf") == "pdf"
        assert get_file_extension("noextension") == ""
        
    except ImportError as e:
        pytest.fail(f"Failed to import utility functions: {e}")

def test_search_params_generation():
    """Test search parameters generation"""
    try:
        from config import get_official_search_params, get_news_search_params
        
        # Test parameters
        keywords = "test news"
        date_range = "after:2024-01-01"
        api_key = "test_key"
        
        # Test official search params
        official_params = get_official_search_params(keywords, date_range, api_key)
        assert "q" in official_params
        assert "gl" in official_params
        assert "hl" in official_params
        assert official_params["gl"] == "az"
        
        # Test news search params
        news_params = get_news_search_params(keywords, date_range, api_key)
        assert "q" in news_params
        assert "safe" in news_params
        assert news_params["safe"] == "active"
        
    except ImportError as e:
        pytest.fail(f"Failed to import search functions: {e}")

if __name__ == "__main__":
    pytest.main([__file__]) 