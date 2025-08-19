"""Monitoring and error handling system for 1xbet scraper.

This module provides comprehensive monitoring, logging, error handling,
and performance tracking for the scraping operations.
"""

import logging
import time
import traceback
import json
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from contextlib import contextmanager

from apify import Actor


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorType(str, Enum):
    """Error type enumeration."""
    NETWORK_ERROR = "network_error"
    PARSING_ERROR = "parsing_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT_ERROR = "timeout_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    CAPTCHA_ERROR = "captcha_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class PerformanceMetrics:
    """Performance metrics data class."""
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    requests_made: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    matches_extracted: int = 0
    data_size_bytes: int = 0
    average_request_time: float = 0.0
    peak_memory_usage: float = 0.0
    
    def calculate_duration(self):
        """Calculate duration if end_time is set."""
        if self.end_time:
            self.duration = self.end_time - self.start_time
    
    def calculate_averages(self):
        """Calculate average metrics."""
        if self.requests_made > 0:
            self.average_request_time = self.duration / self.requests_made if self.duration else 0.0


@dataclass
class ErrorRecord:
    """Error record data class."""
    timestamp: datetime
    error_type: ErrorType
    message: str
    details: Optional[str] = None
    url: Optional[str] = None
    match_id: Optional[str] = None
    traceback: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False


class ScrapingMonitor:
    """Comprehensive monitoring system for scraping operations."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.debug_mode = config.get('debug_mode', False)
        
        # Initialize logging
        self._setup_logging()
        
        # Performance tracking
        self.metrics = PerformanceMetrics(start_time=time.time())
        self.request_times: List[float] = []
        
        # Error tracking
        self.errors: List[ErrorRecord] = []
        self.error_counts: Dict[ErrorType, int] = {error_type: 0 for error_type in ErrorType}
        
        # Rate limiting
        self.last_request_time = 0.0
        self.request_delay = config.get('request_delay', 1.0)
        
        # Retry configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_delay = config.get('retry_delay', 5.0)
        
        # Memory tracking
        self.memory_samples: List[float] = []
        
        self.logger.info("ScrapingMonitor initialized")
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = logging.DEBUG if self.debug_mode else logging.INFO
        
        # Create logger
        self.logger = logging.getLogger('1xbet_scraper')
        self.logger.setLevel(log_level)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        
        # File handler
        log_file = Path('logs/scraper.log')
        log_file.parent.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    @contextmanager
    def track_request(self, url: str, operation: str = "request"):
        """Context manager to track individual requests."""
        start_time = time.time()
        self.metrics.requests_made += 1
        
        try:
            # Rate limiting
            self._apply_rate_limit()
            
            self.logger.debug(f"Starting {operation}: {url}")
            yield
            
            # Success tracking
            end_time = time.time()
            request_time = end_time - start_time
            self.request_times.append(request_time)
            self.metrics.successful_requests += 1
            
            self.logger.debug(f"Completed {operation} in {request_time:.2f}s: {url}")
            
        except Exception as e:
            # Error tracking
            end_time = time.time()
            request_time = end_time - start_time
            self.request_times.append(request_time)
            self.metrics.failed_requests += 1
            
            # Log and record error
            error_type = self._classify_error(e)
            self.record_error(error_type, str(e), url=url, details=traceback.format_exc())
            
            raise
        
        finally:
            self.last_request_time = time.time()
    
    def _apply_rate_limit(self):
        """Apply rate limiting between requests."""
        if self.last_request_time > 0:
            time_since_last = time.time() - self.last_request_time
            if time_since_last < self.request_delay:
                sleep_time = self.request_delay - time_since_last
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """Classify error type based on exception."""
        error_str = str(error).lower()
        
        if 'timeout' in error_str or 'timed out' in error_str:
            return ErrorType.TIMEOUT_ERROR
        elif 'network' in error_str or 'connection' in error_str:
            return ErrorType.NETWORK_ERROR
        elif 'rate limit' in error_str or '429' in error_str:
            return ErrorType.RATE_LIMIT_ERROR
        elif 'captcha' in error_str or 'recaptcha' in error_str:
            return ErrorType.CAPTCHA_ERROR
        elif 'authentication' in error_str or '401' in error_str or '403' in error_str:
            return ErrorType.AUTHENTICATION_ERROR
        elif 'parse' in error_str or 'parsing' in error_str:
            return ErrorType.PARSING_ERROR
        elif 'validation' in error_str:
            return ErrorType.VALIDATION_ERROR
        else:
            return ErrorType.UNKNOWN_ERROR
    
    def record_error(self, error_type: ErrorType, message: str, 
                    url: Optional[str] = None, match_id: Optional[str] = None,
                    details: Optional[str] = None):
        """Record an error occurrence."""
        error_record = ErrorRecord(
            timestamp=datetime.now(timezone.utc),
            error_type=error_type,
            message=message,
            details=details,
            url=url,
            match_id=match_id,
            traceback=details
        )
        
        self.errors.append(error_record)
        self.error_counts[error_type] += 1
        
        # Log error
        log_message = f"Error recorded - {error_type.value}: {message}"
        if url:
            log_message += f" (URL: {url})"
        if match_id:
            log_message += f" (Match ID: {match_id})"
        
        self.logger.error(log_message)
        
        # Send to Apify if available
        try:
            Actor.log.error(log_message)
        except:
            pass
    
    def retry_operation(self, operation: Callable, *args, **kwargs) -> Any:
        """Retry an operation with exponential backoff."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return operation(*args, **kwargs)
            
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}"
                    )
                    time.sleep(delay)
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
        
        # If we get here, all retries failed
        if last_exception:
            raise last_exception
    
    def track_match_extraction(self, match_id: str, success: bool = True, data_size: int = 0):
        """Track match extraction metrics."""
        if success:
            self.metrics.matches_extracted += 1
            self.metrics.data_size_bytes += data_size
            self.logger.debug(f"Successfully extracted match: {match_id}")
        else:
            self.logger.warning(f"Failed to extract match: {match_id}")
    
    def track_memory_usage(self):
        """Track current memory usage."""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.memory_samples.append(memory_mb)
            
            if memory_mb > self.metrics.peak_memory_usage:
                self.metrics.peak_memory_usage = memory_mb
            
            # Log if memory usage is high
            if memory_mb > 500:  # 500MB threshold
                self.logger.warning(f"High memory usage: {memory_mb:.1f}MB")
            
        except ImportError:
            # psutil not available
            pass
        except Exception as e:
            self.logger.debug(f"Error tracking memory: {str(e)}")
    
    def finalize_metrics(self):
        """Finalize performance metrics."""
        self.metrics.end_time = time.time()
        self.metrics.calculate_duration()
        self.metrics.calculate_averages()
        
        # Calculate final statistics
        if self.request_times:
            self.metrics.average_request_time = sum(self.request_times) / len(self.request_times)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        self.finalize_metrics()
        
        summary = {
            'execution_summary': {
                'total_duration': self.metrics.duration,
                'start_time': datetime.fromtimestamp(self.metrics.start_time, timezone.utc).isoformat(),
                'end_time': datetime.fromtimestamp(self.metrics.end_time, timezone.utc).isoformat() if self.metrics.end_time else None
            },
            'request_metrics': {
                'total_requests': self.metrics.requests_made,
                'successful_requests': self.metrics.successful_requests,
                'failed_requests': self.metrics.failed_requests,
                'success_rate': (self.metrics.successful_requests / self.metrics.requests_made * 100) if self.metrics.requests_made > 0 else 0,
                'average_request_time': self.metrics.average_request_time
            },
            'extraction_metrics': {
                'matches_extracted': self.metrics.matches_extracted,
                'total_data_size_mb': self.metrics.data_size_bytes / 1024 / 1024,
                'extraction_rate': (self.metrics.matches_extracted / self.metrics.duration) if self.metrics.duration and self.metrics.duration > 0 else 0
            },
            'error_summary': {
                'total_errors': len(self.errors),
                'error_counts': dict(self.error_counts),
                'error_rate': (len(self.errors) / self.metrics.requests_made * 100) if self.metrics.requests_made > 0 else 0
            },
            'memory_metrics': {
                'peak_memory_mb': self.metrics.peak_memory_usage,
                'average_memory_mb': sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
            }
        }
        
        return summary
    
    def get_error_report(self) -> Dict[str, Any]:
        """Get detailed error report."""
        recent_errors = []
        for error in self.errors[-10:]:  # Last 10 errors
            recent_errors.append({
                'timestamp': error.timestamp.isoformat(),
                'type': error.error_type.value,
                'message': error.message,
                'url': error.url,
                'match_id': error.match_id
            })
        
        return {
            'total_errors': len(self.errors),
            'error_counts_by_type': dict(self.error_counts),
            'recent_errors': recent_errors,
            'most_common_error': max(self.error_counts.items(), key=lambda x: x[1])[0].value if self.errors else None
        }
    
    def export_logs(self, output_path: str) -> bool:
        """Export monitoring data to file."""
        try:
            monitoring_data = {
                'performance_summary': self.get_performance_summary(),
                'error_report': self.get_error_report(),
                'detailed_errors': [asdict(error) for error in self.errors],
                'export_timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(monitoring_data, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Monitoring data exported to {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting monitoring data: {str(e)}")
            return False
    
    def send_apify_metrics(self):
        """Send metrics to Apify platform."""
        try:
            summary = self.get_performance_summary()
            
            # Send key metrics to Apify
            Actor.log.info(f"Scraping completed: {summary['extraction_metrics']['matches_extracted']} matches extracted")
            Actor.log.info(f"Success rate: {summary['request_metrics']['success_rate']:.1f}%")
            Actor.log.info(f"Total duration: {summary['execution_summary']['total_duration']:.1f}s")
            
            if summary['error_summary']['total_errors'] > 0:
                Actor.log.warning(f"Total errors encountered: {summary['error_summary']['total_errors']}")
            
            # Set output metadata
            Actor.set_value('PERFORMANCE_METRICS', summary)
            
        except Exception as e:
            self.logger.error(f"Error sending metrics to Apify: {str(e)}")
    
    def log_progress(self, current: int, total: int, operation: str = "Processing"):
        """Log progress updates."""
        if total > 0:
            percentage = (current / total) * 100
            self.logger.info(f"{operation}: {current}/{total} ({percentage:.1f}%)")
            
            # Send to Apify
            try:
                Actor.log.info(f"{operation}: {current}/{total} ({percentage:.1f}%)")
            except:
                pass
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health and return status."""
        health_status = {
            'status': 'healthy',
            'issues': [],
            'recommendations': []
        }
        
        # Check error rate
        if self.metrics.requests_made > 0:
            error_rate = (len(self.errors) / self.metrics.requests_made) * 100
            if error_rate > 20:  # 20% error rate threshold
                health_status['status'] = 'unhealthy'
                health_status['issues'].append(f"High error rate: {error_rate:.1f}%")
                health_status['recommendations'].append("Review error logs and adjust scraping strategy")
        
        # Check memory usage
        if self.metrics.peak_memory_usage > 1000:  # 1GB threshold
            health_status['issues'].append(f"High memory usage: {self.metrics.peak_memory_usage:.1f}MB")
            health_status['recommendations'].append("Consider processing data in smaller batches")
        
        # Check request performance
        if self.metrics.average_request_time > 10:  # 10 second threshold
            health_status['issues'].append(f"Slow request performance: {self.metrics.average_request_time:.1f}s average")
            health_status['recommendations'].append("Consider increasing request delays or using proxies")
        
        # Check for specific error patterns
        if self.error_counts[ErrorType.RATE_LIMIT_ERROR] > 5:
            health_status['issues'].append("Multiple rate limiting errors detected")
            health_status['recommendations'].append("Increase request delays and implement better rate limiting")
        
        if self.error_counts[ErrorType.CAPTCHA_ERROR] > 0:
            health_status['issues'].append("CAPTCHA challenges detected")
            health_status['recommendations'].append("Consider using proxy rotation or reducing request frequency")
        
        if health_status['issues']:
            health_status['status'] = 'degraded' if len(health_status['issues']) < 3 else 'unhealthy'
        
        return health_status
    
    def cleanup(self):
        """Cleanup monitoring resources."""
        self.finalize_metrics()
        
        # Log final summary
        summary = self.get_performance_summary()
        self.logger.info("=== SCRAPING SUMMARY ===")
        self.logger.info(f"Duration: {summary['execution_summary']['total_duration']:.1f}s")
        self.logger.info(f"Matches extracted: {summary['extraction_metrics']['matches_extracted']}")
        self.logger.info(f"Success rate: {summary['request_metrics']['success_rate']:.1f}%")
        self.logger.info(f"Total errors: {summary['error_summary']['total_errors']}")
        self.logger.info("=== END SUMMARY ===")
        
        # Send final metrics to Apify
        self.send_apify_metrics()


# Advanced monitoring utilities
class AlertManager:
    """Manages real-time alerts and notifications."""
    
    def __init__(self, monitor: 'ScrapingMonitor'):
        self.monitor = monitor
        self.alert_thresholds = {
            'error_rate': 15.0,  # 15% error rate
            'memory_usage': 800,  # 800MB
            'request_time': 8.0,  # 8 seconds
            'consecutive_failures': 5
        }
        self.consecutive_failures = 0
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes
    
    def check_alerts(self):
        """Check for alert conditions and trigger notifications."""
        current_time = time.time()
        
        # Check error rate
        if self.monitor.metrics.requests_made > 10:
            error_rate = (len(self.monitor.errors) / self.monitor.metrics.requests_made) * 100
            if error_rate > self.alert_thresholds['error_rate']:
                self._trigger_alert('high_error_rate', f"Error rate: {error_rate:.1f}%", current_time)
        
        # Check memory usage
        if self.monitor.metrics.peak_memory_usage > self.alert_thresholds['memory_usage']:
            self._trigger_alert('high_memory', f"Memory usage: {self.monitor.metrics.peak_memory_usage:.1f}MB", current_time)
        
        # Check request performance
        if self.monitor.metrics.average_request_time > self.alert_thresholds['request_time']:
            self._trigger_alert('slow_requests', f"Avg request time: {self.monitor.metrics.average_request_time:.1f}s", current_time)
    
    def _trigger_alert(self, alert_type: str, message: str, current_time: float):
        """Trigger an alert if cooldown period has passed."""
        last_alert = self.last_alert_time.get(alert_type, 0)
        
        if current_time - last_alert > self.alert_cooldown:
            self.monitor.logger.warning(f"ALERT [{alert_type.upper()}]: {message}")
            self.last_alert_time[alert_type] = current_time
            
            # Send to Apify
            try:
                Actor.log.warning(f"ALERT [{alert_type.upper()}]: {message}")
            except:
                pass
    
    def record_failure(self):
        """Record a consecutive failure."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.alert_thresholds['consecutive_failures']:
            self._trigger_alert('consecutive_failures', 
                              f"{self.consecutive_failures} consecutive failures", 
                              time.time())
    
    def record_success(self):
        """Reset consecutive failures counter."""
        self.consecutive_failures = 0


class RateLimiter:
    """Intelligent rate limiting with adaptive delays."""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 30.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self.last_request_time = 0
        self.success_count = 0
        self.failure_count = 0
        self.adaptive_factor = 1.0
    
    def wait(self):
        """Wait for the appropriate delay before next request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.current_delay:
            sleep_time = self.current_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def record_success(self):
        """Record a successful request and potentially reduce delay."""
        self.success_count += 1
        self.failure_count = 0
        
        # Gradually reduce delay after consecutive successes
        if self.success_count >= 5:
            self.current_delay = max(self.base_delay, self.current_delay * 0.9)
            self.success_count = 0
    
    def record_failure(self, error_type: ErrorType):
        """Record a failed request and increase delay."""
        self.failure_count += 1
        self.success_count = 0
        
        # Increase delay based on error type
        if error_type == ErrorType.RATE_LIMIT_ERROR:
            self.current_delay = min(self.max_delay, self.current_delay * 2.0)
        elif error_type == ErrorType.NETWORK_ERROR:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
        else:
            self.current_delay = min(self.max_delay, self.current_delay * 1.2)
    
    def get_current_delay(self) -> float:
        """Get the current delay setting."""
        return self.current_delay


class HealthChecker:
    """Advanced system health monitoring."""
    
    def __init__(self, monitor: 'ScrapingMonitor'):
        self.monitor = monitor
        self.health_history = []
        self.max_history = 10
    
    def perform_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        health_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'metrics': {},
            'recommendations': []
        }
        
        # Check network connectivity
        health_data['components']['network'] = self._check_network_health()
        
        # Check memory usage
        health_data['components']['memory'] = self._check_memory_health()
        
        # Check error patterns
        health_data['components']['errors'] = self._check_error_patterns()
        
        # Check performance
        health_data['components']['performance'] = self._check_performance_health()
        
        # Determine overall status
        component_statuses = [comp['status'] for comp in health_data['components'].values()]
        if 'critical' in component_statuses:
            health_data['overall_status'] = 'critical'
        elif 'warning' in component_statuses:
            health_data['overall_status'] = 'warning'
        
        # Store in history
        self.health_history.append(health_data)
        if len(self.health_history) > self.max_history:
            self.health_history.pop(0)
        
        return health_data
    
    def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity health."""
        if self.monitor.metrics.requests_made == 0:
            return {'status': 'unknown', 'message': 'No requests made yet'}
        
        success_rate = (self.monitor.metrics.successful_requests / self.monitor.metrics.requests_made) * 100
        
        if success_rate >= 90:
            return {'status': 'healthy', 'success_rate': success_rate}
        elif success_rate >= 70:
            return {'status': 'warning', 'success_rate': success_rate, 'message': 'Moderate network issues'}
        else:
            return {'status': 'critical', 'success_rate': success_rate, 'message': 'Severe network issues'}
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory usage health."""
        peak_memory = self.monitor.metrics.peak_memory_usage
        
        if peak_memory < 500:
            return {'status': 'healthy', 'peak_memory_mb': peak_memory}
        elif peak_memory < 1000:
            return {'status': 'warning', 'peak_memory_mb': peak_memory, 'message': 'High memory usage'}
        else:
            return {'status': 'critical', 'peak_memory_mb': peak_memory, 'message': 'Critical memory usage'}
    
    def _check_error_patterns(self) -> Dict[str, Any]:
        """Check for concerning error patterns."""
        total_errors = len(self.monitor.errors)
        
        if total_errors == 0:
            return {'status': 'healthy', 'total_errors': 0}
        
        # Check for specific error types
        critical_errors = (
            self.monitor.error_counts[ErrorType.CAPTCHA_ERROR] +
            self.monitor.error_counts[ErrorType.AUTHENTICATION_ERROR]
        )
        
        if critical_errors > 0:
            return {'status': 'critical', 'total_errors': total_errors, 'critical_errors': critical_errors}
        elif total_errors > 10:
            return {'status': 'warning', 'total_errors': total_errors, 'message': 'High error count'}
        else:
            return {'status': 'healthy', 'total_errors': total_errors}
    
    def _check_performance_health(self) -> Dict[str, Any]:
        """Check performance metrics health."""
        avg_time = self.monitor.metrics.average_request_time
        
        if avg_time < 3.0:
            return {'status': 'healthy', 'avg_request_time': avg_time}
        elif avg_time < 8.0:
            return {'status': 'warning', 'avg_request_time': avg_time, 'message': 'Slow performance'}
        else:
            return {'status': 'critical', 'avg_request_time': avg_time, 'message': 'Very slow performance'}
    
    def get_health_trend(self) -> str:
        """Analyze health trend over time."""
        if len(self.health_history) < 3:
            return 'insufficient_data'
        
        recent_statuses = [h['overall_status'] for h in self.health_history[-3:]]
        
        if all(status == 'healthy' for status in recent_statuses):
            return 'stable_healthy'
        elif all(status in ['critical', 'warning'] for status in recent_statuses):
            return 'declining'
        elif recent_statuses[-1] == 'healthy' and recent_statuses[0] != 'healthy':
            return 'improving'
        else:
            return 'unstable'


# Utility functions for monitoring setup
def setup_monitoring(config: Dict[str, Any] = None) -> ScrapingMonitor:
    """Setup and configure monitoring system."""
    if config is None:
        config = {}
    
    monitor = ScrapingMonitor(
        max_retries=config.get('max_retries', 3),
        retry_delay=config.get('retry_delay', 2.0),
        log_level=config.get('log_level', 'INFO')
    )
    
    # Setup alert manager
    alert_manager = AlertManager(monitor)
    monitor.alert_manager = alert_manager
    
    # Setup rate limiter
    rate_limiter = RateLimiter(
        base_delay=config.get('base_delay', 1.0),
        max_delay=config.get('max_delay', 30.0)
    )
    monitor.rate_limiter = rate_limiter
    
    # Setup health checker
    health_checker = HealthChecker(monitor)
    monitor.health_checker = health_checker
    
    return monitor


def create_monitoring_decorator(monitor: ScrapingMonitor):
    """Create a decorator for monitoring function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                monitor.track_request_success(time.time() - start_time)
                return result
            except Exception as e:
                monitor.track_request_failure(time.time() - start_time)
                error_type = monitor.classify_error(str(e))
                monitor.record_error(error_type, str(e))
                raise
        return wrapper
    return decorator