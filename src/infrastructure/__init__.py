# Agent OS Infrastructure Layer
# Created: 2026-06-09

"""
基础设施层
提供流量控制、权限管理、日志记录、缓存管理等核心基础设施服务
"""

from .rate_limiter import (
    RateLimiter,
    RateLimit,
    RateLimitType,
    LimitScope,
    TrafficMetrics,
    QuotaConfig,
    rate_limiter,
    rate_limit,
)

from .permission_manager import (
    PermissionManager,
    Permission,
    Role,
    PermissionRule,
    AccessControlList,
    RolePermissions,
    permission_manager,
    require_permission,
)

from .logger import (
    StructuredLogger,
    LogLevel,
    LogCategory,
    LogEntry,
    AuditLog,
    structured_logger,
    get_logger,
)

from .cache_manager import (
    CacheManager,
    CacheConfig,
    CacheEntry,
    MemoryCache,
    RedisCache,
    cached,
)

__all__ = [
    # 流量控制
    "RateLimiter",
    "RateLimit",
    "RateLimitType",
    "LimitScope",
    "TrafficMetrics",
    "QuotaConfig",
    "rate_limiter",
    "rate_limit",
    # 权限管理
    "PermissionManager",
    "Permission",
    "Role",
    "PermissionRule",
    "AccessControlList",
    "RolePermissions",
    "permission_manager",
    "require_permission",
    # 日志记录
    "StructuredLogger",
    "LogLevel",
    "LogCategory",
    "LogEntry",
    "AuditLog",
    "structured_logger",
    "get_logger",
    # 缓存管理
    "CacheManager",
    "CacheConfig",
    "CacheEntry",
    "MemoryCache",
    "RedisCache",
    "cached",
]
