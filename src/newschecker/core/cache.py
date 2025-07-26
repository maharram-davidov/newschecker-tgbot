import hashlib
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
import logging

class NewsCache:
    """
    Advanced caching system for news analysis results with TTL and intelligent eviction.
    
    Features:
    - TTL-based expiration
    - Different cache types with different TTLs
    - Thread-safe operations
    - Memory usage tracking
    - Cache hit/miss statistics
    - Intelligent eviction policies
    """
    
    def __init__(self, max_memory_mb: int = 100):
        """
        Initialize the cache system.
        
        Args:
            max_memory_mb: Maximum memory usage in MB
        """
        self.cache = {}
        self.access_times = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'memory_usage_bytes': 0
        }
        
        # TTL configurations (in seconds)
        self.ttl_config = {
            'analysis': 7200,      # 2 hours for analysis results
            'search': 1800,        # 30 minutes for search results
            'url_content': 3600,   # 1 hour for URL content
            'source_verification': 1800,  # 30 minutes for source verification
            'user_stats': 300,     # 5 minutes for user statistics
            'default': 1800        # 30 minutes default
        }
        
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.lock = threading.RLock()
        self.logger = logging.getLogger(__name__)
        
        # Start cleanup thread
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """Start background thread for cache cleanup."""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(300)  # Run every 5 minutes
                    with self.lock:
                        self._cleanup_expired()
                        self._enforce_memory_limit()
                except Exception as e:
                    self.logger.error(f"Error in cache cleanup: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
    
    def _generate_key(self, content: Union[str, Dict], cache_type: str = 'default') -> str:
        """Generate cache key from content."""
        if isinstance(content, dict):
            content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        else:
            content_str = str(content)
        
        # Create hash of content + cache type
        hash_input = f"{cache_type}:{content_str}".encode('utf-8')
        return hashlib.sha256(hash_input).hexdigest()
    
    def _calculate_size(self, value: Any) -> int:
        """Estimate memory size of cached value."""
        try:
            if isinstance(value, dict):
                return len(json.dumps(value, ensure_ascii=False).encode('utf-8'))
            elif isinstance(value, str):
                return len(value.encode('utf-8'))
            else:
                return len(str(value).encode('utf-8'))
        except Exception:
            return 1024  # Default estimate
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        expiry_time = cache_entry.get('expiry_time')
        if expiry_time is None:
            return False
        return time.time() > expiry_time
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            self._remove_entry(key)
            self.cache_stats['evictions'] += 1
        
        if expired_keys:
            self.logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def _enforce_memory_limit(self):
        """Enforce memory limit by evicting LRU entries."""
        if self.cache_stats['memory_usage_bytes'] <= self.max_memory_bytes:
            return
        
        # Sort entries by access time (LRU first)
        sorted_entries = sorted(
            self.access_times.items(),
            key=lambda x: x[1]
        )
        
        evicted_count = 0
        for key, _ in sorted_entries:
            if self.cache_stats['memory_usage_bytes'] <= self.max_memory_bytes * 0.8:
                break
            
            if key in self.cache:
                self._remove_entry(key)
                evicted_count += 1
                self.cache_stats['evictions'] += 1
        
        if evicted_count > 0:
            self.logger.debug(f"Evicted {evicted_count} entries due to memory limit")
    
    def _remove_entry(self, key: str):
        """Remove entry and update memory usage."""
        if key in self.cache:
            entry = self.cache[key]
            entry_size = entry.get('size', 0)
            self.cache_stats['memory_usage_bytes'] -= entry_size
            del self.cache[key]
        
        if key in self.access_times:
            del self.access_times[key]
    
    def set(self, content: Union[str, Dict], value: Any, cache_type: str = 'default', 
            custom_ttl: Optional[int] = None) -> bool:
        """
        Store value in cache.
        
        Args:
            content: Content to generate key from
            value: Value to cache
            cache_type: Type of cache for TTL determination
            custom_ttl: Custom TTL in seconds (overrides cache_type TTL)
            
        Returns:
            True if stored successfully, False otherwise
        """
        try:
            with self.lock:
                key = self._generate_key(content, cache_type)
                entry_size = self._calculate_size(value)
                
                # Check if adding this entry would exceed memory limit
                if (self.cache_stats['memory_usage_bytes'] + entry_size > self.max_memory_bytes and
                    key not in self.cache):
                    self._enforce_memory_limit()
                    
                    # If still too large after cleanup, reject the entry
                    if self.cache_stats['memory_usage_bytes'] + entry_size > self.max_memory_bytes:
                        self.logger.warning(f"Cannot cache entry: would exceed memory limit")
                        return False
                
                # Remove existing entry if updating
                if key in self.cache:
                    self._remove_entry(key)
                
                # Determine TTL
                ttl = custom_ttl if custom_ttl is not None else self.ttl_config.get(cache_type, self.ttl_config['default'])
                expiry_time = time.time() + ttl if ttl > 0 else None
                
                # Store entry
                self.cache[key] = {
                    'value': value,
                    'cache_type': cache_type,
                    'created_time': time.time(),
                    'expiry_time': expiry_time,
                    'size': entry_size,
                    'access_count': 0
                }
                
                self.access_times[key] = time.time()
                self.cache_stats['memory_usage_bytes'] += entry_size
                self.cache_stats['sets'] += 1
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error setting cache: {e}")
            return False
    
    def get(self, content: Union[str, Dict], cache_type: str = 'default') -> Optional[Any]:
        """
        Retrieve value from cache.
        
        Args:
            content: Content to generate key from
            cache_type: Type of cache
            
        Returns:
            Cached value if exists and not expired, None otherwise
        """
        try:
            with self.lock:
                key = self._generate_key(content, cache_type)
                
                if key not in self.cache:
                    self.cache_stats['misses'] += 1
                    return None
                
                entry = self.cache[key]
                
                # Check if expired
                if self._is_expired(entry):
                    self._remove_entry(key)
                    self.cache_stats['misses'] += 1
                    return None
                
                # Update access time and count
                self.access_times[key] = time.time()
                entry['access_count'] += 1
                self.cache_stats['hits'] += 1
                
                return entry['value']
                
        except Exception as e:
            self.logger.error(f"Error getting from cache: {e}")
            self.cache_stats['misses'] += 1
            return None
    
    def cache_analysis(self, content: str, analysis_result: str) -> bool:
        """Cache analysis result for news content."""
        return self.set(content, analysis_result, 'analysis')
    
    def get_cached_analysis(self, content: str) -> Optional[str]:
        """Get cached analysis result."""
        return self.get(content, 'analysis')
    
    def cache_search_results(self, query: str, results: Dict[str, Any]) -> bool:
        """Cache search results."""
        return self.set(query, results, 'search')
    
    def get_cached_search_results(self, query: str) -> Optional[Dict[str, Any]]:
        """Get cached search results."""
        return self.get(query, 'search')
    
    def cache_url_content(self, url: str, content: str) -> bool:
        """Cache URL content."""
        return self.set(url, content, 'url_content')
    
    def get_cached_url_content(self, url: str) -> Optional[str]:
        """Get cached URL content."""
        return self.get(url, 'url_content')
    
    def cache_source_verification(self, source_info: Dict[str, Any], verification_result: Dict[str, Any]) -> bool:
        """Cache source verification results."""
        return self.set(source_info, verification_result, 'source_verification')
    
    def get_cached_source_verification(self, source_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached source verification results."""
        return self.get(source_info, 'source_verification')
    
    def invalidate(self, content: Union[str, Dict], cache_type: str = 'default') -> bool:
        """
        Invalidate specific cache entry.
        
        Args:
            content: Content to generate key from
            cache_type: Type of cache
            
        Returns:
            True if entry was removed, False if not found
        """
        try:
            with self.lock:
                key = self._generate_key(content, cache_type)
                if key in self.cache:
                    self._remove_entry(key)
                    return True
                return False
        except Exception as e:
            self.logger.error(f"Error invalidating cache: {e}")
            return False
    
    def clear(self, cache_type: Optional[str] = None):
        """
        Clear cache entries.
        
        Args:
            cache_type: If specified, only clear entries of this type. If None, clear all.
        """
        try:
            with self.lock:
                if cache_type is None:
                    # Clear all
                    self.cache.clear()
                    self.access_times.clear()
                    self.cache_stats['memory_usage_bytes'] = 0
                else:
                    # Clear specific type
                    keys_to_remove = []
                    for key, entry in self.cache.items():
                        if entry.get('cache_type') == cache_type:
                            keys_to_remove.append(key)
                    
                    for key in keys_to_remove:
                        self._remove_entry(key)
                
                self.logger.info(f"Cache cleared: {cache_type or 'all'}")
                
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.cache_stats['hits'] + self.cache_stats['misses']
            hit_rate = (self.cache_stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            # Get cache type distribution
            type_distribution = {}
            for entry in self.cache.values():
                cache_type = entry.get('cache_type', 'unknown')
                type_distribution[cache_type] = type_distribution.get(cache_type, 0) + 1
            
            return {
                'total_entries': len(self.cache),
                'memory_usage_mb': self.cache_stats['memory_usage_bytes'] / (1024 * 1024),
                'memory_limit_mb': self.max_memory_bytes / (1024 * 1024),
                'hit_rate_percent': round(hit_rate, 2),
                'hits': self.cache_stats['hits'],
                'misses': self.cache_stats['misses'],
                'sets': self.cache_stats['sets'],
                'evictions': self.cache_stats['evictions'],
                'type_distribution': type_distribution
            }
    
    def get_entry_info(self, content: Union[str, Dict], cache_type: str = 'default') -> Optional[Dict[str, Any]]:
        """Get information about a specific cache entry."""
        try:
            with self.lock:
                key = self._generate_key(content, cache_type)
                if key not in self.cache:
                    return None
                
                entry = self.cache[key]
                return {
                    'cache_type': entry.get('cache_type'),
                    'created_time': datetime.fromtimestamp(entry['created_time']).isoformat(),
                    'expiry_time': datetime.fromtimestamp(entry['expiry_time']).isoformat() if entry.get('expiry_time') else None,
                    'size_bytes': entry.get('size', 0),
                    'access_count': entry.get('access_count', 0),
                    'is_expired': self._is_expired(entry)
                }
        except Exception as e:
            self.logger.error(f"Error getting entry info: {e}")
            return None

# Global cache instance
news_cache = NewsCache() 