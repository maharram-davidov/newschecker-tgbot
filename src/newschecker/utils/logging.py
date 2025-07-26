import logging
import json
import time
import uuid
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
from logging.handlers import RotatingFileHandler
import threading

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record):
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'operation'):
            log_entry['operation'] = record.operation
        if hasattr(record, 'duration'):
            log_entry['duration_ms'] = record.duration
        if hasattr(record, 'error'):
            log_entry['error'] = str(record.error)
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)

class PerformanceLogger:
    """Logger for performance metrics and monitoring."""
    
    def __init__(self):
        self.metrics = {}
        self.lock = threading.Lock()
    
    def record_operation(self, operation: str, duration: float, success: bool = True, **kwargs):
        """Record operation performance metrics."""
        with self.lock:
            if operation not in self.metrics:
                self.metrics[operation] = {
                    'count': 0,
                    'total_duration': 0.0,
                    'avg_duration': 0.0,
                    'min_duration': float('inf'),
                    'max_duration': 0.0,
                    'success_count': 0,
                    'error_count': 0
                }
            
            metric = self.metrics[operation]
            metric['count'] += 1
            metric['total_duration'] += duration
            metric['avg_duration'] = metric['total_duration'] / metric['count']
            metric['min_duration'] = min(metric['min_duration'], duration)
            metric['max_duration'] = max(metric['max_duration'], duration)
            
            if success:
                metric['success_count'] += 1
            else:
                metric['error_count'] += 1
    
    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics."""
        with self.lock:
            if operation:
                return self.metrics.get(operation, {})
            return self.metrics.copy()
    
    def reset_metrics(self, operation: Optional[str] = None):
        """Reset performance metrics."""
        with self.lock:
            if operation:
                if operation in self.metrics:
                    del self.metrics[operation]
            else:
                self.metrics.clear()

class EnhancedLogger:
    """Enhanced logging system with structured logging and performance monitoring."""
    
    def __init__(self, name: str = 'newschecker'):
        self.logger = logging.getLogger(name)
        self.performance_logger = PerformanceLogger()
        self.request_context = threading.local()
        
        # Configure logger if not already configured
        if not self.logger.handlers:
            self._setup_logger()
    
    def _setup_logger(self):
        """Setup logger with multiple handlers."""
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatters
        structured_formatter = StructuredFormatter()
        simple_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler with simple format
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        self.logger.addHandler(console_handler)
        
        # Create logs directory if it doesn't exist
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # Main log file with structured format
        main_handler = RotatingFileHandler(
            log_dir / 'newschecker.log',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        main_handler.setLevel(logging.DEBUG)
        main_handler.setFormatter(structured_formatter)
        self.logger.addHandler(main_handler)
        
        # Error log file
        error_handler = RotatingFileHandler(
            log_dir / 'errors.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(structured_formatter)
        self.logger.addHandler(error_handler)
        
        # Performance log file
        perf_handler = RotatingFileHandler(
            log_dir / 'performance.log',
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        perf_handler.setLevel(logging.INFO)
        perf_handler.setFormatter(structured_formatter)
        
        # Create performance logger
        perf_logger = logging.getLogger(f'{self.logger.name}.performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
    
    def set_request_id(self, request_id: Optional[str] = None):
        """Set request ID for current thread context."""
        if request_id is None:
            request_id = str(uuid.uuid4())
        self.request_context.request_id = request_id
        return request_id
    
    def get_request_id(self) -> Optional[str]:
        """Get current request ID."""
        return getattr(self.request_context, 'request_id', None)
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with context information."""
        extra = {}
        
        # Add request ID if available
        request_id = self.get_request_id()
        if request_id:
            extra['request_id'] = request_id
        
        # Add any additional context
        if kwargs:
            extra['extra_data'] = kwargs
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message."""
        extra = kwargs.copy()
        if error:
            extra['error'] = str(error)
            extra['error_type'] = type(error).__name__
            # Add traceback for exceptions
            extra['traceback'] = traceback.format_exc()
        
        self._log_with_context(logging.ERROR, message, **extra)
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message."""
        extra = kwargs.copy()
        if error:
            extra['error'] = str(error)
            extra['error_type'] = type(error).__name__
            extra['traceback'] = traceback.format_exc()
        
        self._log_with_context(logging.CRITICAL, message, **extra)
    
    def log_user_action(self, user_id: int, action: str, data: Dict[str, Any]):
        """Log user action with structured data."""
        extra = {
            'user_id': user_id,
            'action': action,
            'action_data': data
        }
        self._log_with_context(logging.INFO, f"User action: {action}", **extra)
    
    def log_performance(self, operation: str, duration: float, success: bool = True, **kwargs):
        """Log performance metrics."""
        self.performance_logger.record_operation(operation, duration, success, **kwargs)
        
        extra = {
            'operation': operation,
            'duration': duration,
            'success': success
        }
        extra.update(kwargs)
        
        perf_logger = logging.getLogger(f'{self.logger.name}.performance')
        perf_logger.info(f"Performance: {operation}", extra=extra)
    
    def log_security_event(self, event_type: str, user_id: int, details: Dict[str, Any]):
        """Log security-related events."""
        extra = {
            'security_event': event_type,
            'user_id': user_id,
            'security_details': details
        }
        self._log_with_context(logging.WARNING, f"Security event: {event_type}", **extra)
    
    def get_performance_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics."""
        return self.performance_logger.get_metrics(operation)

# Global enhanced logger instance
enhanced_logger = EnhancedLogger()

def performance_monitor(operation_name: str):
    """
    Decorator to monitor function performance.
    
    Args:
        operation_name: Name of the operation for metrics
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = enhanced_logger.set_request_id()
            success = True
            error = None
            
            try:
                enhanced_logger.debug(f"Starting operation: {operation_name}", 
                                    operation=operation_name)
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error = e
                enhanced_logger.error(f"Error in operation: {operation_name}", 
                                    error=e, operation=operation_name)
                raise
            finally:
                duration = (time.time() - start_time) * 1000  # Convert to milliseconds
                enhanced_logger.log_performance(operation_name, duration, success)
                
                enhanced_logger.debug(f"Completed operation: {operation_name}", 
                                    operation=operation_name, 
                                    duration_ms=duration,
                                    success=success)
        
        return wrapper
    return decorator

def log_startup_info():
    """Log application startup information."""
    enhanced_logger.info("NewsChecker application starting", 
                        startup_time=datetime.now().isoformat(),
                        python_version=sys.version,
                        platform=sys.platform)

def log_shutdown_info():
    """Log application shutdown information."""
    enhanced_logger.info("NewsChecker application shutting down", 
                        shutdown_time=datetime.now().isoformat()) 