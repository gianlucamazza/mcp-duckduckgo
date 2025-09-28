"""
MCP Security enhancements following 2025 best practices.
Implements Resource Indicators (RFC 8707) and enhanced authorization flows.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources that can be accessed via MCP."""

    WEB_SEARCH = "web_search"
    WEB_CONTENT = "web_content"
    CACHE_READ = "cache_read"
    CACHE_WRITE = "cache_write"
    SNAPSHOT_READ = "snapshot_read"
    SNAPSHOT_WRITE = "snapshot_write"
    KNOWLEDGE_GRAPH = "knowledge_graph"


class SecurityLevel(Enum):
    """Security levels for different operations."""

    PUBLIC = "public"           # No consent required
    LOW = "low"                 # Basic consent
    MEDIUM = "medium"           # Explicit consent with details
    HIGH = "high"               # Strong consent with full disclosure
    RESTRICTED = "restricted"   # Admin-only operations


@dataclass
class ResourceIndicator:
    """Resource Indicator per RFC 8707 to prevent token mis-redemption."""

    resource_type: ResourceType
    resource_identifier: str
    intended_recipient: str
    security_level: SecurityLevel
    timestamp: float = field(default_factory=time.time)
    nonce: str = field(default_factory=lambda: hashlib.sha256(str(time.time()).encode()).hexdigest()[:16])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for token inclusion."""
        return {
            "resource_type": self.resource_type.value,
            "resource_identifier": self.resource_identifier,
            "intended_recipient": self.intended_recipient,
            "security_level": self.security_level.value,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
        }


@dataclass
class ConsentRecord:
    """Record of user consent for specific operations."""

    resource_indicator: ResourceIndicator
    user_id: str
    consent_granted: bool
    consent_timestamp: float
    expiry_timestamp: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SecurityManager:
    """Manages security policies and consent flows for MCP operations."""

    def __init__(self) -> None:
        self.consent_cache: dict[str, ConsentRecord] = {}
        self.blocked_domains: set[str] = {
            # Security-sensitive domains that require explicit approval
            "localhost",
            "127.0.0.1",
            "0.0.0.0",  # noqa: S104 - intentionally blocked for security
            "internal",
            "admin",
        }
        self.rate_limits: dict[str, list[float]] = {}

    def create_resource_indicator(
        self,
        resource_type: ResourceType,
        resource_identifier: str,
        intended_recipient: str = "mcp-client",
        security_level: SecurityLevel = SecurityLevel.MEDIUM,
    ) -> ResourceIndicator:
        """Create a new Resource Indicator per RFC 8707."""
        return ResourceIndicator(
            resource_type=resource_type,
            resource_identifier=resource_identifier,
            intended_recipient=intended_recipient,
            security_level=security_level,
        )

    def validate_resource_indicator(
        self,
        indicator: ResourceIndicator,
        actual_recipient: str,
    ) -> bool:
        """Validate that the resource indicator matches the actual recipient."""
        if indicator.intended_recipient != actual_recipient:
            logger.warning(
                f"Resource indicator mismatch: expected {indicator.intended_recipient}, "
                f"got {actual_recipient}"
            )
            return False

        # Check if indicator is not too old (max 1 hour)
        if time.time() - indicator.timestamp > 3600:
            logger.warning("Resource indicator has expired")
            return False

        return True

    def check_domain_safety(self, url: str) -> bool:
        """Check if a domain is safe for access."""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            # Check blocked domains
            for blocked in self.blocked_domains:
                if blocked in domain:
                    logger.warning(f"Blocked domain access attempt: {domain}")
                    return False

            return True
        except Exception:
            logger.warning(f"Invalid URL format: {url}")
            return False

    def check_rate_limit(
        self,
        user_id: str,
        operation: str,
        max_requests: int = 100,
        window_seconds: int = 3600,
    ) -> bool:
        """Check if operation is within rate limits."""
        now = time.time()
        key = f"{user_id}:{operation}"

        if key not in self.rate_limits:
            self.rate_limits[key] = []

        # Clean old entries
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if now - timestamp < window_seconds
        ]

        # Check limit
        if len(self.rate_limits[key]) >= max_requests:
            logger.warning(f"Rate limit exceeded for {user_id}:{operation}")
            return False

        # Record this request
        self.rate_limits[key].append(now)
        return True

    def require_consent(
        self,
        resource_indicator: ResourceIndicator,
        user_id: str = "default",
        description: str = "",
    ) -> bool:
        """Check if operation requires consent and if it's been granted."""
        # For demonstration, we'll implement a simple consent mechanism
        # In production, this would integrate with the MCP host's consent system

        consent_key = f"{user_id}:{resource_indicator.nonce}"

        # Check if consent already exists and is valid
        if consent_key in self.consent_cache:
            consent = self.consent_cache[consent_key]
            if consent.consent_granted:
                # Check if consent hasn't expired
                if (consent.expiry_timestamp is None or
                    time.time() < consent.expiry_timestamp):
                    return True

        # For security levels that require consent
        if resource_indicator.security_level in [SecurityLevel.MEDIUM, SecurityLevel.HIGH]:
            logger.info(
                f"Consent required for {resource_indicator.resource_type.value}: {description}"
            )
            # In a real implementation, this would trigger a consent prompt
            # For now, we'll auto-grant for non-restricted operations
            if resource_indicator.security_level != SecurityLevel.RESTRICTED:
                consent = ConsentRecord(
                    resource_indicator=resource_indicator,
                    user_id=user_id,
                    consent_granted=True,
                    consent_timestamp=time.time(),
                    expiry_timestamp=time.time() + 3600,  # 1 hour expiry
                )
                self.consent_cache[consent_key] = consent
                return True

        return resource_indicator.security_level in [SecurityLevel.PUBLIC, SecurityLevel.LOW]

    def sanitize_search_query(self, query: str) -> str:
        """Sanitize search queries to prevent injection attacks."""
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '|', ';', '`', '$']
        sanitized = query

        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')

        # Limit length
        if len(sanitized) > 400:
            sanitized = sanitized[:400]

        return sanitized.strip()

    def validate_url_safety(self, url: str) -> bool:
        """Comprehensive URL safety validation."""
        if not self.check_domain_safety(url):
            return False

        # Additional URL safety checks
        suspicious_patterns = [
            'javascript:',
            'data:',
            'file:',
            'ftp:',
            'telnet:',
        ]

        url_lower = url.lower()
        for pattern in suspicious_patterns:
            if url_lower.startswith(pattern):
                logger.warning(f"Suspicious URL pattern detected: {pattern}")
                return False

        return True


# Global security manager instance
security_manager = SecurityManager()


def secure_operation(
    resource_type: ResourceType,
    resource_identifier: str,
    security_level: SecurityLevel = SecurityLevel.MEDIUM,
    description: str = "",
) -> Callable:
    """Decorator for securing MCP operations with Resource Indicators."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Create resource indicator
            indicator = security_manager.create_resource_indicator(
                resource_type=resource_type,
                resource_identifier=resource_identifier,
                security_level=security_level,
            )

            # Check consent
            if not security_manager.require_consent(indicator, description=description):
                raise PermissionError(
                    f"Consent required for {resource_type.value}: {description}"
                )

            # Validate resource indicator (in real implementation, this would be done by the client)
            if not security_manager.validate_resource_indicator(indicator, "mcp-client"):
                raise SecurityError("Invalid resource indicator")

            # Execute the original function
            return await func(*args, **kwargs)
        return wrapper
    return decorator


class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass

