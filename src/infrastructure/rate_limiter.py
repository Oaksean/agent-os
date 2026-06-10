# 流量控制系统
# Agent OS - Infrastructure Layer
# Created: 2026-06-09

"""
流量控制系统
参考Hermes Agent和OpenClaw设计，实现速率限制、流量监控和配额管理
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """速率限制类型"""

    RPM = "requests_per_minute"  # 每分钟请求数
    RPS = "requests_per_second"  # 每秒请求数
    TPS = "tokens_per_second"  # 每秒Token数
    TPM = "tokens_per_minute"  # 每分钟Token数


class LimitScope(Enum):
    """限制范围"""

    GLOBAL = "global"  # 全局限制
    USER = "user"  # 用户级别
    AGENT = "agent"  # Agent级别
    ENDPOINT = "endpoint"  # API端点级别


@dataclass
class RateLimit:
    """速率限制配置"""

    limit_type: RateLimitType
    limit: int
    scope: LimitScope
    window_seconds: int = 60  # 时间窗口（秒）
    enabled: bool = True

    # 统计数据
    current_count: int = 0
    last_reset: datetime = field(default_factory=datetime.now)

    def is_exceeded(self) -> bool:
        """检查是否超出限制"""
        if not self.enabled:
            return False

        # 检查是否需要重置计数
        now = datetime.now()
        if (now - self.last_reset).total_seconds() >= self.window_seconds:
            self.current_count = 0
            self.last_reset = now

        return self.current_count >= self.limit

    def increment(self, count: int = 1):
        """增加计数"""
        self.current_count += count


@dataclass
class TrafficMetrics:
    """流量指标"""

    timestamp: datetime
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    tokens_total: int = 0
    avg_response_time: float = 0.0
    peak_requests_per_second: float = 0.0

    # 按用户/Agent分组统计
    requests_by_user: Dict[str, int] = field(default_factory=dict)
    requests_by_agent: Dict[str, int] = field(default_factory=dict)
    tokens_by_user: Dict[str, int] = field(default_factory=dict)


@dataclass
class QuotaConfig:
    """配额配置"""

    daily_limit: int = 10000  # 每日限制
    monthly_limit: int = 300000  # 每月限制
    token_limit: int = 1000000  # Token限制

    # 当前使用量
    daily_used: int = 0
    monthly_used: int = 0
    token_used: int = 0

    # 重置时间
    last_daily_reset: datetime = field(default_factory=datetime.now)
    last_monthly_reset: datetime = field(default_factory=datetime.now)


class RateLimiter:
    """速率限制器"""

    def __init__(self):
        # 多级速率限制
        self.rate_limits: Dict[str, RateLimit] = {}

        # 请求历史记录（用于计算实时速率）
        self.request_history: Dict[str, deque] = {}

        # 流量指标
        self.metrics: List[TrafficMetrics] = []
        self.current_metrics = TrafficMetrics(timestamp=datetime.now())

        # 配额管理
        self.quotas: Dict[str, QuotaConfig] = {}

        # 锁
        self.lock = asyncio.Lock()

        # 配置默认限制
        self._setup_default_limits()

        logger.info("初始化流量控制系统")

    def _setup_default_limits(self):
        """设置默认速率限制"""
        # 全局限制
        self.rate_limits["global_rpm"] = RateLimit(
            limit_type=RateLimitType.RPM,
            limit=1000,
            scope=LimitScope.GLOBAL,
            window_seconds=60,
        )

        # 用户级别限制
        self.rate_limits["user_rpm"] = RateLimit(
            limit_type=RateLimitType.RPM,
            limit=60,
            scope=LimitScope.USER,
            window_seconds=60,
        )

        # Agent级别限制
        self.rate_limits["agent_rpm"] = RateLimit(
            limit_type=RateLimitType.RPM,
            limit=100,
            scope=LimitScope.AGENT,
            window_seconds=60,
        )

        logger.info("默认速率限制配置完成")

    async def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """检查速率限制"""
        async with self.lock:
            result = {"allowed": True, "limits": {}, "retry_after": None}

            # 检查全局限制
            if "global_rpm" in self.rate_limits:
                limit = self.rate_limits["global_rpm"]
                if limit.is_exceeded():
                    result["allowed"] = False
                    result["limits"]["global"] = {
                        "limit": limit.limit,
                        "current": limit.current_count,
                        "retry_after": limit.window_seconds,
                    }
                    result["retry_after"] = limit.window_seconds

            # 检查用户级别限制
            if user_id and "user_rpm" in self.rate_limits:
                key = f"user_{user_id}"
                if key not in self.request_history:
                    self.request_history[key] = deque(maxlen=1000)

                history = self.request_history[key]
                now = time.time()

                # 清理过期记录
                while history and now - history[0] > 60:
                    history.popleft()

                if len(history) >= self.rate_limits["user_rpm"].limit:
                    result["allowed"] = False
                    result["limits"]["user"] = {
                        "limit": self.rate_limits["user_rpm"].limit,
                        "current": len(history),
                        "retry_after": 60 - (now - history[0]),
                    }
                    if (
                        not result["retry_after"]
                        or result["limits"]["user"]["retry_after"]
                        < result["retry_after"]
                    ):
                        result["retry_after"] = result["limits"]["user"]["retry_after"]

            # 检查Agent级别限制
            if agent_id and "agent_rpm" in self.rate_limits:
                key = f"agent_{agent_id}"
                if key not in self.request_history:
                    self.request_history[key] = deque(maxlen=1000)

                history = self.request_history[key]
                now = time.time()

                # 清理过期记录
                while history and now - history[0] > 60:
                    history.popleft()

                if len(history) >= self.rate_limits["agent_rpm"].limit:
                    result["allowed"] = False
                    result["limits"]["agent"] = {
                        "limit": self.rate_limits["agent_rpm"].limit,
                        "current": len(history),
                        "retry_after": 60 - (now - history[0]),
                    }
                    if (
                        not result["retry_after"]
                        or result["limits"]["agent"]["retry_after"]
                        < result["retry_after"]
                    ):
                        result["retry_after"] = result["limits"]["agent"]["retry_after"]

            return result

    async def record_request(
        self,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tokens: int = 0,
        success: bool = True,
        response_time: float = 0.0,
    ):
        """记录请求"""
        async with self.lock:
            now = time.time()

            # 更新请求历史
            if user_id:
                key = f"user_{user_id}"
                if key not in self.request_history:
                    self.request_history[key] = deque(maxlen=1000)
                self.request_history[key].append(now)

            if agent_id:
                key = f"agent_{agent_id}"
                if key not in self.request_history:
                    self.request_history[key] = deque(maxlen=1000)
                self.request_history[key].append(now)

            # 更新全局限制
            if "global_rpm" in self.rate_limits:
                self.rate_limits["global_rpm"].increment()

            # 更新指标
            self.current_metrics.requests_total += 1
            if success:
                self.current_metrics.requests_success += 1
            else:
                self.current_metrics.requests_failed += 1

            self.current_metrics.tokens_total += tokens

            # 按用户/Agent分组统计
            if user_id:
                self.current_metrics.requests_by_user[user_id] = (
                    self.current_metrics.requests_by_user.get(user_id, 0) + 1
                )
                self.current_metrics.tokens_by_user[user_id] = (
                    self.current_metrics.tokens_by_user.get(user_id, 0) + tokens
                )

            if agent_id:
                self.current_metrics.requests_by_agent[agent_id] = (
                    self.current_metrics.requests_by_agent.get(agent_id, 0) + 1
                )

            # 更新平均响应时间
            if response_time > 0:
                total = self.current_metrics.requests_total
                current_avg = self.current_metrics.avg_response_time
                self.current_metrics.avg_response_time = (
                    current_avg * (total - 1) + response_time
                ) / total

    async def get_metrics(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """获取流量指标"""
        async with self.lock:
            # 计算实时RPS
            now = time.time()
            total_requests = sum(
                len([t for t in history if now - t <= 60])
                for history in self.request_history.values()
            )

            # 获取当前指标
            metrics = {
                "timestamp": self.current_metrics.timestamp.isoformat(),
                "requests_total": self.current_metrics.requests_total,
                "requests_success": self.current_metrics.requests_success,
                "requests_failed": self.current_metrics.requests_failed,
                "tokens_total": self.current_metrics.tokens_total,
                "avg_response_time": self.current_metrics.avg_response_time,
                "current_rps": total_requests / 60.0,
                "requests_by_user": dict(self.current_metrics.requests_by_user),
                "requests_by_agent": dict(self.current_metrics.requests_by_agent),
                "tokens_by_user": dict(self.current_metrics.tokens_by_user),
                "active_users": len(self.current_metrics.requests_by_user),
                "active_agents": len(self.current_metrics.requests_by_agent),
            }

            return metrics

    async def set_rate_limit(
        self,
        name: str,
        limit_type: RateLimitType,
        limit: int,
        scope: LimitScope,
        window_seconds: int = 60,
    ):
        """设置速率限制"""
        async with self.lock:
            self.rate_limits[name] = RateLimit(
                limit_type=limit_type,
                limit=limit,
                scope=scope,
                window_seconds=window_seconds,
            )
            logger.info(f"设置速率限制: {name} - {limit} {limit_type.value}")

    async def get_rate_limits(self) -> Dict[str, Any]:
        """获取所有速率限制"""
        async with self.lock:
            return {
                name: {
                    "limit_type": limit.limit_type.value,
                    "limit": limit.limit,
                    "scope": limit.scope.value,
                    "window_seconds": limit.window_seconds,
                    "current_count": limit.current_count,
                    "enabled": limit.enabled,
                }
                for name, limit in self.rate_limits.items()
            }

    async def set_quota(
        self,
        entity_id: str,
        daily_limit: int = 10000,
        monthly_limit: int = 300000,
        token_limit: int = 1000000,
    ):
        """设置配额"""
        async with self.lock:
            self.quotas[entity_id] = QuotaConfig(
                daily_limit=daily_limit,
                monthly_limit=monthly_limit,
                token_limit=token_limit,
            )
            logger.info(
                f"设置配额: {entity_id} - 每日{daily_limit}, 每月{monthly_limit}, Token{token_limit}"
            )

    async def check_quota(self, entity_id: str) -> Dict[str, Any]:
        """检查配额"""
        async with self.lock:
            if entity_id not in self.quotas:
                return {"has_quota": False, "message": "未设置配额"}

            quota = self.quotas[entity_id]
            now = datetime.now()

            # 检查是否需要重置
            if (now - quota.last_daily_reset).days >= 1:
                quota.daily_used = 0
                quota.last_daily_reset = now

            if (now - quota.last_monthly_reset).days >= 30:
                quota.monthly_used = 0
                quota.last_monthly_reset = now

            return {
                "has_quota": True,
                "daily": {
                    "limit": quota.daily_limit,
                    "used": quota.daily_used,
                    "remaining": quota.daily_limit - quota.daily_used,
                },
                "monthly": {
                    "limit": quota.monthly_limit,
                    "used": quota.monthly_used,
                    "remaining": quota.monthly_limit - quota.monthly_used,
                },
                "tokens": {
                    "limit": quota.token_limit,
                    "used": quota.token_used,
                    "remaining": quota.token_limit - quota.token_used,
                },
            }

    async def reset_metrics(self):
        """重置指标"""
        async with self.lock:
            self.current_metrics = TrafficMetrics(timestamp=datetime.now())
            logger.info("流量指标已重置")


# 全局实例
rate_limiter = RateLimiter()


# 装饰器：自动速率限制
def rate_limit(scope: LimitScope = LimitScope.USER):
    """速率限制装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取user_id和agent_id
            user_id = kwargs.get("user_id")
            agent_id = kwargs.get("agent_id")

            # 检查速率限制
            result = await rate_limiter.check_rate_limit(
                user_id=user_id, agent_id=agent_id
            )

            if not result["allowed"]:
                raise Exception(f"速率限制: 请等待 {result['retry_after']:.1f} 秒")

            # 执行函数
            start_time = time.time()
            try:
                result_data = await func(*args, **kwargs)
                response_time = time.time() - start_time

                # 记录成功请求
                await rate_limiter.record_request(
                    user_id=user_id,
                    agent_id=agent_id,
                    success=True,
                    response_time=response_time,
                )

                return result_data

            except Exception as e:
                response_time = time.time() - start_time

                # 记录失败请求
                await rate_limiter.record_request(
                    user_id=user_id,
                    agent_id=agent_id,
                    success=False,
                    response_time=response_time,
                )

                raise e

        return wrapper

    return decorator


# 示例用法
if __name__ == "__main__":
    import asyncio

    async def test_rate_limiter():
        """测试速率限制器"""
        limiter = RateLimiter()

        # 测试速率限制
        print("测试速率限制...")
        for i in range(5):
            result = await limiter.check_rate_limit(user_id="user_123")
            print(f"请求 {i + 1}: {'允许' if result['allowed'] else '拒绝'}")

            await limiter.record_request(
                user_id="user_123", tokens=100, success=True, response_time=0.5
            )

        # 获取指标
        metrics = await limiter.get_metrics()
        print(f"\n流量指标: {metrics}")

        # 测试配额
        print("\n测试配额...")
        await limiter.set_quota("user_123", daily_limit=100, monthly_limit=3000)
        quota = await limiter.check_quota("user_123")
        print(f"配额信息: {quota}")

    asyncio.run(test_rate_limiter())
