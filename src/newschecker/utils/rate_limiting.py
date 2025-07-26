import time
import threading
from collections import defaultdict, deque
from typing import Dict, Tuple, Any, Optional
from functools import wraps
from datetime import datetime, timedelta

class RateLimiter:
    """
    Advanced rate limiting system with per-user and operation-specific limits.
    
    Features:
    - Sliding window rate limiting
    - Per-operation limits (text, URL, image analysis)
    - VIP user support with multipliers
    - Automatic cleanup of old entries
    - Thread-safe operations
    - Comprehensive statistics
    """
    
    def __init__(self):
        self.user_operations = defaultdict(lambda: defaultdict(deque))
        self.global_operations = defaultdict(deque)
        self.lock = threading.RLock()
        self.cleanup_interval = 300  # 5 minutes
        self.last_cleanup = time.time()
        
        # Rate limits per operation (requests per minute)
        self.operation_limits = {
            'text_analysis': 10,
            'url_analysis': 5, 
            'image_analysis': 3,
            'general': 15
        }
        
        # Global limits (total across all users)
        self.global_limits = {
            'text_analysis': 100,
            'url_analysis': 50,
            'image_analysis': 30,
            'general': 200
        }
        
        # VIP users (admin multiplier)
        self.vip_multiplier = 5
        self.vip_users = set()  # Will be populated from config
        
        # Window size in seconds
        self.window_size = 60
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'operations_count': defaultdict(int),
            'user_stats': defaultdict(lambda: {'requests': 0, 'blocked': 0})
        }
    
    def add_vip_user(self, user_id: int):
        """Add VIP user (admin user)."""
        with self.lock:
            self.vip_users.add(user_id)
    
    def remove_vip_user(self, user_id: int):
        """Remove VIP user."""
        with self.lock:
            self.vip_users.discard(user_id)
    
    def is_vip_user(self, user_id: int) -> bool:
        """Check if user is VIP."""
        return user_id in self.vip_users
    
    def _cleanup_old_entries(self):
        """Clean up old entries beyond the window."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - self.window_size
        
        # Clean user operations
        for user_id in list(self.user_operations.keys()):
            for operation in list(self.user_operations[user_id].keys()):
                queue = self.user_operations[user_id][operation]
                while queue and queue[0] < cutoff_time:
                    queue.popleft()
                
                # Remove empty queues
                if not queue:
                    del self.user_operations[user_id][operation]
            
            # Remove empty user entries
            if not self.user_operations[user_id]:
                del self.user_operations[user_id]
        
        # Clean global operations
        for operation in list(self.global_operations.keys()):
            queue = self.global_operations[operation]
            while queue and queue[0] < cutoff_time:
                queue.popleft()
            
            # Remove empty queues
            if not queue:
                del self.global_operations[operation]
        
        self.last_cleanup = current_time
    
    def _get_user_limit(self, user_id: int, operation: str) -> int:
        """Get rate limit for user and operation."""
        base_limit = self.operation_limits.get(operation, self.operation_limits['general'])
        
        if self.is_vip_user(user_id):
            return base_limit * self.vip_multiplier
        
        return base_limit
    
    def _get_global_limit(self, operation: str) -> int:
        """Get global rate limit for operation."""
        return self.global_limits.get(operation, self.global_limits['general'])
    
    def is_allowed(self, user_id: int, operation: str = 'general') -> Dict[str, Any]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            user_id: User identifier
            operation: Operation type ('text_analysis', 'url_analysis', 'image_analysis', 'general')
            
        Returns:
            Dict with 'allowed' boolean and additional info
        """
        with self.lock:
            current_time = time.time()
            self._cleanup_old_entries()
            
            # Update statistics
            self.stats['total_requests'] += 1
            self.stats['operations_count'][operation] += 1
            self.stats['user_stats'][user_id]['requests'] += 1
            
            # Check user-specific limit
            user_queue = self.user_operations[user_id][operation]
            user_limit = self._get_user_limit(user_id, operation)
            
            # Count requests in current window
            cutoff_time = current_time - self.window_size
            user_requests_in_window = sum(1 for timestamp in user_queue if timestamp > cutoff_time)
            
            if user_requests_in_window >= user_limit:
                self.stats['blocked_requests'] += 1
                self.stats['user_stats'][user_id]['blocked'] += 1
                
                # Calculate retry after time
                oldest_in_window = min((t for t in user_queue if t > cutoff_time), default=current_time)
                retry_after = self.window_size - (current_time - oldest_in_window)
                
                return {
                    'allowed': False,
                    'reason': 'user_limit_exceeded',
                    'limit': user_limit,
                    'current_count': user_requests_in_window,
                    'retry_after': max(0, retry_after),
                    'is_vip': self.is_vip_user(user_id)
                }
            
            # Check global limit
            global_queue = self.global_operations[operation]
            global_limit = self._get_global_limit(operation)
            global_requests_in_window = sum(1 for timestamp in global_queue if timestamp > cutoff_time)
            
            if global_requests_in_window >= global_limit:
                self.stats['blocked_requests'] += 1
                self.stats['user_stats'][user_id]['blocked'] += 1
                
                # Calculate retry after time
                oldest_in_window = min((t for t in global_queue if t > cutoff_time), default=current_time)
                retry_after = self.window_size - (current_time - oldest_in_window)
                
                return {
                    'allowed': False,
                    'reason': 'global_limit_exceeded',
                    'limit': global_limit,
                    'current_count': global_requests_in_window,
                    'retry_after': max(0, retry_after),
                    'is_vip': self.is_vip_user(user_id)
                }
            
            # Allow request and record it
            user_queue.append(current_time)
            global_queue.append(current_time)
            
            return {
                'allowed': True,
                'user_limit': user_limit,
                'user_remaining': user_limit - user_requests_in_window - 1,
                'global_limit': global_limit,
                'global_remaining': global_limit - global_requests_in_window - 1,
                'is_vip': self.is_vip_user(user_id)
            }
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get statistics for a specific user."""
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.window_size
            
            user_operations = self.user_operations.get(user_id, {})
            stats = {
                'user_id': user_id,
                'is_vip': self.is_vip_user(user_id),
                'operations': {}
            }
            
            for operation, limit in self.operation_limits.items():
                user_limit = self._get_user_limit(user_id, operation)
                queue = user_operations.get(operation, deque())
                current_count = sum(1 for timestamp in queue if timestamp > cutoff_time)
                
                stats['operations'][operation] = {
                    'limit': user_limit,
                    'current': current_count,
                    'remaining': max(0, user_limit - current_count)
                }
            
            # Add overall user statistics
            user_stats = self.stats['user_stats'][user_id]
            stats['total_requests'] = user_stats['requests']
            stats['blocked_requests'] = user_stats['blocked']
            
            return stats
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics."""
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - self.window_size
            
            global_stats = {
                'total_requests': self.stats['total_requests'],
                'blocked_requests': self.stats['blocked_requests'],
                'active_users': len(self.user_operations),
                'vip_users_count': len(self.vip_users),
                'operations': {}
            }
            
            for operation, limit in self.global_limits.items():
                queue = self.global_operations.get(operation, deque())
                current_count = sum(1 for timestamp in queue if timestamp > cutoff_time)
                
                global_stats['operations'][operation] = {
                    'limit': limit,
                    'current': current_count,
                    'remaining': max(0, limit - current_count),
                    'total_requests': self.stats['operations_count'][operation]
                }
            
            return global_stats
    
    def reset_user_limits(self, user_id: int, operation: Optional[str] = None):
        """Reset rate limits for a user."""
        with self.lock:
            if user_id in self.user_operations:
                if operation:
                    if operation in self.user_operations[user_id]:
                        self.user_operations[user_id][operation].clear()
                else:
                    del self.user_operations[user_id]
    
    def reset_global_limits(self, operation: Optional[str] = None):
        """Reset global rate limits."""
        with self.lock:
            if operation:
                if operation in self.global_operations:
                    self.global_operations[operation].clear()
            else:
                self.global_operations.clear()
    
    def update_limits(self, operation_limits: Optional[Dict[str, int]] = None, 
                     global_limits: Optional[Dict[str, int]] = None):
        """Update rate limits dynamically."""
        with self.lock:
            if operation_limits:
                self.operation_limits.update(operation_limits)
            if global_limits:
                self.global_limits.update(global_limits)

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit_check(operation: str = 'general'):
    """
    Decorator for rate limiting function calls.
    
    Args:
        operation: Operation type for rate limiting
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract user_id from args (assumes it's in Update object)
            user_id = None
            for arg in args:
                if hasattr(arg, 'effective_user') and hasattr(arg.effective_user, 'id'):
                    user_id = arg.effective_user.id
                    break
            
            if user_id is None:
                # If no user_id found, proceed without rate limiting
                return await func(*args, **kwargs)
            
            # Check rate limit
            rate_check = rate_limiter.is_allowed(user_id, operation)
            if not rate_check['allowed']:
                # Handle rate limit exceeded (this would be customized based on framework)
                return None
            
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract user_id from args
            user_id = None
            for arg in args:
                if hasattr(arg, 'effective_user') and hasattr(arg.effective_user, 'id'):
                    user_id = arg.effective_user.id
                    break
            
            if user_id is None:
                return func(*args, **kwargs)
            
            # Check rate limit
            rate_check = rate_limiter.is_allowed(user_id, operation)
            if not rate_check['allowed']:
                return None
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

def initialize_rate_limiter(admin_user_ids: list):
    """Initialize rate limiter with admin users."""
    for admin_id in admin_user_ids:
        rate_limiter.add_vip_user(admin_id) 