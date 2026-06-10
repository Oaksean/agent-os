# Cache System with Redis Integration
# Agent OS - Infrastructure Layer
# Created: 2026-06-10

"""
缓存系统
功能：
1. Redis集成 - 分布式缓存
2. 本地内存缓存 - 本地缓存降级
3. 缓存装饰器 - 简化缓存使用
4. 缓存管理 - 过期策略、LRU淘汰
"""

import asyncio
import logging
import json
import time
import hashlib
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
import threading
from collections import OrderedDict

logger = logging.getLogger(__name__)

# 尝试导入Redis
try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，将使用本地内存缓存")


@dataclass
class CacheConfig:
    """缓存配置"""

    enabled: bool = True
    backend: str = "redis"  # "redis" or "memory"
    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 3600  # 默认过期时间（秒）
    max_memory_cache_size: int = 1000  # 本地缓存最大条目数
    key_prefix: str = "agent_os:"
    serialize: bool = True  # 是否序列化


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    ttl: int = 3600
    hit_count: int = 0
    size: int = 0  # 字节大小


class MemoryCache:
    """本地内存缓存（LRU淘汰策略）"""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.lock = threading.Lock()
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "size": 0,
        }

        logger.info(f"初始化本地内存缓存，最大容量: {max_size}")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self.lock:
            if key not in self.cache:
                self.stats["misses"] += 1
                return None

            entry = self.cache[key]

            # 检查是否过期
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self.cache[key]
                self.stats["misses"] += 1
                self.stats["size"] -= 1
                return None

            # LRU: 移到末尾
            self.cache.move_to_end(key)
            entry.hit_count += 1
            self.stats["hits"] += 1

            return entry.value

    async def set(
        self, key: str, value: Any, ttl: int = 3600, serialize: bool = True
    ) -> bool:
        """设置缓存"""
        with self.lock:
            # 计算大小
            try:
                if serialize:
                    size = len(json.dumps(value))
                else:
                    size = len(str(value))
            except Exception:
                size = 0

            # 创建缓存条目
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None,
                ttl=ttl,
                size=size,
            )

            # 如果key已存在，删除旧的
            if key in self.cache:
                del self.cache[key]
                self.stats["size"] -= 1

            # 检查容量，淘汰最久未使用的
            while len(self.cache) >= self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats["evictions"] += 1
                self.stats["size"] -= 1

            # 添加新条目
            self.cache[key] = entry
            self.stats["size"] += 1

            return True

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats["size"] -= 1
                return True
            return False

    async def exists(self, key: str) -> bool:
        """检查key是否存在"""
        with self.lock:
            if key not in self.cache:
                return False

            entry = self.cache[key]
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self.cache[key]
                self.stats["size"] -= 1
                return False

            return True

    async def clear(self) -> bool:
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.stats["size"] = 0
            return True

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.lock:
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (
                (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
            )

            return {
                **self.stats,
                "hit_rate": f"{hit_rate:.2f}%",
                "total_requests": total_requests,
                "max_size": self.max_size,
            }

    async def get_keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的keys"""
        import fnmatch

        with self.lock:
            if pattern == "*":
                return list(self.cache.keys())

            return [key for key in self.cache.keys() if fnmatch.fnmatch(key, pattern)]


class RedisCache:
    """Redis缓存"""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        if not REDIS_AVAILABLE:
            raise RuntimeError("Redis未安装，请运行: pip install redis")

        self.redis_url = redis_url
        self.client: Optional[redis.Redis] = None
        self.connected = False
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0,
            "errors": 0,
        }

        logger.info(f"初始化Redis缓存，URL: {redis_url}")

    async def connect(self) -> bool:
        """连接Redis"""
        try:
            self.client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

            # 测试连接
            await self.client.ping()
            self.connected = True
            logger.info("Redis连接成功")
            return True

        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            self.connected = False
            self.stats["errors"] += 1
            return False

    async def disconnect(self):
        """断开连接"""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Redis连接已关闭")

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.connected:
            self.stats["misses"] += 1
            return None

        try:
            value = await self.client.get(key)

            if value is None:
                self.stats["misses"] += 1
                return None

            self.stats["hits"] += 1

            # 尝试反序列化
            try:
                return json.loads(value)
            except Exception:
                return value

        except Exception as e:
            logger.error(f"Redis获取失败: {e}")
            self.stats["errors"] += 1
            return None

    async def set(
        self, key: str, value: Any, ttl: int = 3600, serialize: bool = True
    ) -> bool:
        """设置缓存"""
        if not self.connected:
            return False

        try:
            # 序列化
            if serialize:
                value = json.dumps(value)

            await self.client.setex(key, ttl, value)
            self.stats["sets"] += 1
            return True

        except Exception as e:
            logger.error(f"Redis设置失败: {e}")
            self.stats["errors"] += 1
            return False

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.connected:
            return False

        try:
            result = await self.client.delete(key)
            self.stats["deletes"] += 1
            return result > 0

        except Exception as e:
            logger.error(f"Redis删除失败: {e}")
            self.stats["errors"] += 1
            return False

    async def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not self.connected:
            return False

        try:
            result = await self.client.exists(key)
            return result > 0

        except Exception as e:
            logger.error(f"Redis检查失败: {e}")
            return False

    async def clear(self) -> bool:
        """清空缓存"""
        if not self.connected:
            return False

        try:
            await self.client.flushdb()
            return True

        except Exception as e:
            logger.error(f"Redis清空失败: {e}")
            return False

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (
            (self.stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        stats = {
            **self.stats,
            "hit_rate": f"{hit_rate:.2f}%",
            "total_requests": total_requests,
            "connected": self.connected,
        }

        # 获取Redis信息
        if self.connected:
            try:
                info = await self.client.info("memory")
                stats["used_memory"] = info.get("used_memory_human", "N/A")
                stats["connected_clients"] = info.get("connected_clients", 0)

                dbsize = await self.client.dbsize()
                stats["total_keys"] = dbsize

            except Exception as e:
                logger.error(f"获取Redis信息失败: {e}")

        return stats

    async def get_keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的keys"""
        if not self.connected:
            return []

        try:
            keys = []
            async for key in self.client.scan_iter(match=pattern):
                keys.append(key)
            return keys

        except Exception as e:
            logger.error(f"Redis获取keys失败: {e}")
            return []

    async def ttl(self, key: str) -> int:
        """获取key的剩余过期时间"""
        if not self.connected:
            return -1

        try:
            return await self.client.ttl(key)
        except Exception:
            return -1


class CacheManager:
    """缓存管理器"""

    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.backend: Union[MemoryCache, RedisCache] = None

        if not self.config.enabled:
            logger.info("缓存已禁用")
            return

        # 初始化缓存后端
        if self.config.backend == "redis" and REDIS_AVAILABLE:
            self.backend = RedisCache(self.config.redis_url)
        else:
            if self.config.backend == "redis":
                logger.warning("Redis不可用，降级到本地内存缓存")
            self.backend = MemoryCache(self.config.max_memory_cache_size)

        logger.info(f"初始化缓存管理器，后端: {type(self.backend).__name__}")

    async def initialize(self) -> bool:
        """初始化缓存"""
        if not self.config.enabled:
            return True

        if isinstance(self.backend, RedisCache):
            return await self.backend.connect()

        return True

    async def shutdown(self):
        """关闭缓存"""
        if isinstance(self.backend, RedisCache):
            await self.backend.disconnect()

    def _make_key(self, key: str) -> str:
        """生成完整key"""
        return f"{self.config.key_prefix}{key}"

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.config.enabled or not self.backend:
            return None

        full_key = self._make_key(key)
        return await self.backend.get(full_key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: Optional[bool] = None,
    ) -> bool:
        """设置缓存"""
        if not self.config.enabled or not self.backend:
            return False

        full_key = self._make_key(key)
        ttl = ttl or self.config.default_ttl
        serialize = serialize if serialize is not None else self.config.serialize

        return await self.backend.set(full_key, value, ttl, serialize)

    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.config.enabled or not self.backend:
            return False

        full_key = self._make_key(key)
        return await self.backend.delete(full_key)

    async def exists(self, key: str) -> bool:
        """检查key是否存在"""
        if not self.config.enabled or not self.backend:
            return False

        full_key = self._make_key(key)
        return await self.backend.exists(full_key)

    async def clear(self) -> bool:
        """清空缓存"""
        if not self.config.enabled or not self.backend:
            return False

        return await self.backend.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self.config.enabled or not self.backend:
            return {"enabled": False}

        stats = await self.backend.get_stats()
        stats["backend"] = type(self.backend).__name__
        stats["config"] = {
            "default_ttl": self.config.default_ttl,
            "key_prefix": self.config.key_prefix,
        }

        return stats

    async def get_keys(self, pattern: str = "*") -> List[str]:
        """获取匹配的keys"""
        if not self.config.enabled or not self.backend:
            return []

        return await self.backend.get_keys(pattern)

    async def get_or_set(
        self, key: str, func: Callable, ttl: Optional[int] = None, *args, **kwargs
    ) -> Any:
        """获取缓存，如果不存在则调用函数并缓存结果"""
        # 尝试从缓存获取
        value = await self.get(key)
        if value is not None:
            return value

        # 调用函数获取值
        if asyncio.iscoroutinefunction(func):
            value = await func(*args, **kwargs)
        else:
            value = func(*args, **kwargs)

        # 缓存结果
        await self.set(key, value, ttl)

        return value


def cached(
    key: Optional[str] = None,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
    condition: Optional[Callable] = None,
):
    """
    缓存装饰器

    Args:
        key: 缓存key（可选，自动生成）
        ttl: 过期时间（秒）
        key_builder: key生成函数 func(*args, **kwargs) -> str
        condition: 条件函数 func(result) -> bool，返回True时才缓存

    Usage:
        @cached(ttl=300)
        async def get_user(user_id: str):
            return await db.get_user(user_id)

        @cached(key_builder=lambda user_id: f"user:{user_id}")
        async def get_user_profile(user_id: str):
            return await db.get_profile(user_id)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 获取缓存管理器（从全局或参数）
            cache_manager = kwargs.get("cache_manager")
            if not cache_manager:
                # 尝试从全局获取
                from src.api.main_complete import app_state

                cache_manager = app_state.get("cache_manager")

            if not cache_manager:
                # 缓存不可用，直接执行函数
                return await func(*args, **kwargs)

            # 生成缓存key
            if key:
                cache_key = key
            elif key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # 自动生成key
                func_name = f"{func.__module__}.{func.__name__}"
                args_hash = hashlib.md5(
                    json.dumps(
                        {"args": args, "kwargs": kwargs}, sort_keys=True
                    ).encode()
                ).hexdigest()
                cache_key = f"{func_name}:{args_hash}"

            # 尝试从缓存获取
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"缓存命中: {cache_key}")
                return cached_value

            # 执行函数
            result = await func(*args, **kwargs)

            # 检查条件
            if condition and not condition(result):
                return result

            # 缓存结果
            await cache_manager.set(cache_key, result, ttl)
            logger.debug(f"缓存设置: {cache_key}")

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 同步函数包装
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(async_wrapper(*args, **kwargs))

        # 根据函数类型返回不同的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 示例用法
if __name__ == "__main__":

    async def example_usage():
        # 创建缓存管理器
        config = CacheConfig(
            backend="memory",  # 或 "redis"
            default_ttl=600,
            max_memory_cache_size=100,
        )

        cache_manager = CacheManager(config)
        await cache_manager.initialize()

        # 基本操作
        await cache_manager.set("user:123", {"name": "Alice", "age": 30}, ttl=300)
        user = await cache_manager.get("user:123")
        print(f"缓存数据: {user}")

        # 使用get_or_set
        async def fetch_data():
            print("从数据库获取数据...")
            await asyncio.sleep(1)
            return {"data": "value"}

        data1 = await cache_manager.get_or_set("data_key", fetch_data, ttl=600)
        data2 = await cache_manager.get_or_set(
            "data_key", fetch_data, ttl=600
        )  # 从缓存获取

        # 使用装饰器
        @cached(ttl=300)
        async def get_config(key: str):
            print(f"加载配置: {key}")
            await asyncio.sleep(0.5)
            return {"config_key": key, "value": "config_value"}

        config1 = await get_config("app_settings")
        config2 = await get_config("app_settings")  # 从缓存获取

        # 获取统计信息
        stats = await cache_manager.get_stats()
        print(f"缓存统计: {stats}")

        # 关闭缓存
        await cache_manager.shutdown()

    asyncio.run(example_usage())
