"""
Performance monitoring and health indicators for MCP DuckDuckGo server.
Implements 2025 best practices for observability and metrics collection.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class PerformanceMetrics:
    """Performance metrics collection."""

    # Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0

    # System metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    memory_usage_mb: float = 0.0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_ratio: float = 0.0

    # Security metrics
    security_violations: int = 0
    rate_limit_hits: int = 0

    # Timestamp
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": self.successful_requests / max(self.total_requests, 1),
            "average_response_time": self.average_response_time,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "memory_usage_mb": self.memory_usage_mb,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_ratio": self.cache_hit_ratio,
            "security_violations": self.security_violations,
            "rate_limit_hits": self.rate_limit_hits,
            "timestamp": self.timestamp,
        }


@dataclass
class HealthCheck:
    """Individual health check result."""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    check_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)


class PerformanceMonitor:
    """Monitors performance metrics and health indicators."""

    def __init__(self) -> None:
        self.metrics_history: list[PerformanceMetrics] = []
        self.health_checks: dict[str, HealthCheck] = {}
        self.start_time = time.time()
        self.request_times: list[float] = []
        self.max_history_size = 100

    def record_request(self, duration: float, success: bool) -> None:
        """Record a request with its duration and success status."""
        self.request_times.append(duration)

        # Keep only last 100 request times for efficiency
        if len(self.request_times) > self.max_history_size:
            self.request_times = self.request_times[-self.max_history_size:]

    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory_info = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        # Calculate average response time
        avg_response_time = 0.0
        if self.request_times:
            avg_response_time = sum(self.request_times) / len(self.request_times)

        # Get cache metrics from server metrics if available
        try:
            from .server import server_metrics
            cache_hits = server_metrics.get("cache_hits", 0)
            cache_misses = server_metrics.get("cache_misses", 0)
            total_requests = server_metrics.get("requests_processed", 0)
            total_errors = server_metrics.get("errors_count", 0)
        except ImportError:
            # Fallback if server module not available during initialization
            cache_hits = cache_misses = total_requests = total_errors = 0

        total_cache_requests = cache_hits + cache_misses
        cache_hit_ratio = cache_hits / max(total_cache_requests, 1)

        return PerformanceMetrics(
            total_requests=int(total_requests),
            successful_requests=int(total_requests - total_errors),
            failed_requests=int(total_errors),
            average_response_time=avg_response_time,
            cpu_usage=cpu_percent,
            memory_usage=memory_info.percent,
            memory_usage_mb=process_memory.rss / 1024 / 1024,
            cache_hits=int(cache_hits),
            cache_misses=int(cache_misses),
            cache_hit_ratio=cache_hit_ratio,
            security_violations=0,  # Would be populated by security manager
            rate_limit_hits=0,      # Would be populated by security manager
        )

    async def perform_health_check(self, name: str, check_func: Callable) -> HealthCheck:
        """Perform an individual health check."""
        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            duration = time.time() - start_time

            if result is True:
                status = HealthStatus.HEALTHY
                message = "Check passed"
                details = {}
            elif isinstance(result, dict):
                status = result.get("status", HealthStatus.HEALTHY)
                message = result.get("message", "Check completed")
                details = result.get("details", {})
            else:
                status = HealthStatus.DEGRADED
                message = str(result)
                details = {}

            return HealthCheck(
                name=name,
                status=status,
                message=message,
                details=details,
                check_duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Health check '{name}' failed: {e}")

            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {e!s}",
                details={"exception": str(e)},
                check_duration=duration,
            )

    async def check_http_client_health(self) -> dict[str, Any]:
        """Check HTTP client health."""
        try:
            from .server import http_client

            if http_client is None:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "HTTP client not initialized",
                }

            if http_client.is_closed:
                return {
                    "status": HealthStatus.UNHEALTHY,
                    "message": "HTTP client is closed",
                }

            return {
                "status": HealthStatus.HEALTHY,
                "message": "HTTP client is operational",
                "details": {
                    "is_closed": http_client.is_closed,
                }
            }

        except (ImportError, Exception) as e:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": f"HTTP client check failed: {e}",
            }

    def check_memory_health(self) -> dict[str, Any]:
        """Check memory usage health."""
        memory_info = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        # Memory usage thresholds
        system_memory_threshold = 90.0  # 90% system memory usage
        process_memory_threshold = 500.0  # 500MB process memory usage

        process_memory_mb = process_memory.rss / 1024 / 1024

        if memory_info.percent > system_memory_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"High system memory usage: {memory_info.percent:.1f}%"
        elif process_memory_mb > process_memory_threshold:
            status = HealthStatus.DEGRADED
            message = f"High process memory usage: {process_memory_mb:.1f}MB"
        else:
            status = HealthStatus.HEALTHY
            message = "Memory usage is normal"

        return {
            "status": status,
            "message": message,
            "details": {
                "system_memory_percent": memory_info.percent,
                "process_memory_mb": process_memory_mb,
                "available_memory_mb": memory_info.available / 1024 / 1024,
            }
        }

    def check_response_time_health(self) -> dict[str, Any]:
        """Check response time health."""
        if not self.request_times:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "No requests to analyze",
            }

        avg_response_time = sum(self.request_times) / len(self.request_times)
        max_response_time = max(self.request_times)

        # Response time thresholds (in seconds)
        degraded_threshold = 5.0    # 5 seconds
        unhealthy_threshold = 15.0  # 15 seconds

        if max_response_time > unhealthy_threshold:
            status = HealthStatus.UNHEALTHY
            message = f"Very slow response times detected (max: {max_response_time:.2f}s)"
        elif avg_response_time > degraded_threshold:
            status = HealthStatus.DEGRADED
            message = f"Slow average response time: {avg_response_time:.2f}s"
        else:
            status = HealthStatus.HEALTHY
            message = "Response times are normal"

        return {
            "status": status,
            "message": message,
            "details": {
                "average_response_time": avg_response_time,
                "max_response_time": max_response_time,
                "total_requests": len(self.request_times),
            }
        }

    async def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status."""
        health_checks = [
            await self.perform_health_check("http_client", self.check_http_client_health),
            await self.perform_health_check("memory", self.check_memory_health),
            await self.perform_health_check("response_time", self.check_response_time_health),
        ]

        # Determine overall health status
        overall_status = HealthStatus.HEALTHY
        unhealthy_checks = []
        degraded_checks = []

        for check in health_checks:
            if check.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                unhealthy_checks.append(check.name)
            elif check.status == HealthStatus.DEGRADED:
                if overall_status == HealthStatus.HEALTHY:
                    overall_status = HealthStatus.DEGRADED
                degraded_checks.append(check.name)

        # Calculate uptime
        uptime_seconds = time.time() - self.start_time

        return {
            "status": overall_status.value,
            "timestamp": time.time(),
            "uptime_seconds": uptime_seconds,
            "checks": {check.name: {
                "status": check.status.value,
                "message": check.message,
                "details": check.details,
                "check_duration": check.check_duration,
            } for check in health_checks},
            "summary": {
                "total_checks": len(health_checks),
                "healthy_checks": len([c for c in health_checks if c.status == HealthStatus.HEALTHY]),
                "degraded_checks": len(degraded_checks),
                "unhealthy_checks": len(unhealthy_checks),
            }
        }

    def update_metrics_history(self) -> None:
        """Update metrics history with current metrics."""
        current_metrics = self.get_current_metrics()
        self.metrics_history.append(current_metrics)

        # Keep only last N metrics for memory efficiency
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary with current and historical data."""
        current_metrics = self.get_current_metrics()

        # Calculate trends if we have historical data
        trends = {}
        if len(self.metrics_history) >= 2:
            previous_metrics = self.metrics_history[-2]

            trends = {
                "cpu_usage_trend": current_metrics.cpu_usage - previous_metrics.cpu_usage,
                "memory_usage_trend": current_metrics.memory_usage - previous_metrics.memory_usage,
                "response_time_trend": current_metrics.average_response_time - previous_metrics.average_response_time,
                "cache_hit_ratio_trend": current_metrics.cache_hit_ratio - previous_metrics.cache_hit_ratio,
            }

        return {
            "current": current_metrics.to_dict(),
            "trends": trends,
            "uptime_seconds": time.time() - self.start_time,
            "metrics_count": len(self.metrics_history),
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_request(func: Callable) -> Callable:
    """Decorator to monitor request performance."""
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        success = False

        try:
            result = await func(*args, **kwargs)
            success = True
            return result
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            performance_monitor.record_request(duration, success)

            # Update server metrics
            try:
                from .server import server_metrics
                server_metrics["requests_processed"] += 1
                if not success:
                    server_metrics["errors_count"] += 1
            except ImportError:
                # Fallback if server module not available
                pass

    return wrapper

