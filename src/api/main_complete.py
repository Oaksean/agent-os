"""
Agent OS 完整版 API服务
整合流量控制、权限管理、日志记录等基础设施功能
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    Request,
    BackgroundTasks,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
import logging

# 导入核心模块
from src.core.types import (
    AgentStatus,
    TaskStatus,
    TaskPriority,
    MemoryType,
    Role,
    PromptType,
)
from src.kernel.agent_manager import AgentManager
from src.kernel.task_scheduler_enhanced import (
    EnhancedTaskScheduler,
    TaskPriority as SchedulerPriority,
    TaskAllocationStrategy,
)
from src.users.user_manager import UserManager
from src.prompts.prompt_manager import PromptManager
from src.sessions.session_manager import SessionManager

# 导入基础设施模块
from src.infrastructure import (
    rate_limiter,
    permission_manager,
    structured_logger,
    Permission,
    LogLevel,
    LogCategory,
)
from src.infrastructure.cache_manager import CacheManager, CacheConfig

# 全局状态（供装饰器使用）
app_state = {}

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Agent OS Complete API",
    description="智能体操作系统完整API服务 - 包含流量控制、权限管理、日志记录",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局管理器实例
user_manager = UserManager()
prompt_manager = PromptManager()
session_manager = SessionManager()
agent_manager = AgentManager()

# 增强版任务调度器（支持Cron、持久化、智能分配）
task_scheduler = EnhancedTaskScheduler(
    max_workers=4,
    allocation_strategy=TaskAllocationStrategy.LOAD_BALANCE,
    persistence_enabled=True,
    storage_dir="data/tasks",
)

# 缓存管理器
cache_config = CacheConfig(
    backend="memory",  # 可改为 "redis" 如果Redis可用
    default_ttl=3600,
    max_memory_cache_size=1000,
)
cache_manager = CacheManager(cache_config)

# 更新全局状态
app_state.update({"cache_manager": cache_manager, "task_scheduler": task_scheduler})


# ==================== Pydantic模型 ====================


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    timestamp: float
    uptime: float


class ErrorResponse(BaseModel):
    """错误响应"""

    error: str
    detail: str
    timestamp: float


# ==================== 中间件 ====================


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """流量控制中间件"""
    start_time = time.time()

    # 提取用户ID（从header或query参数）
    user_id = request.headers.get("X-User-ID") or request.query_params.get("user_id")
    agent_id = request.headers.get("X-Agent-ID") or request.query_params.get("agent_id")

    # 检查速率限制
    rate_check = await rate_limiter.check_rate_limit(user_id=user_id, agent_id=agent_id)

    if not rate_check["allowed"]:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded",
                "retry_after": rate_check.get("retry_after", 60),
                "limits": rate_check.get("limits", {}),
            },
        )

    # 执行请求
    response = await call_next(request)

    # 记录请求
    response_time = time.time() - start_time
    await rate_limiter.record_request(
        user_id=user_id,
        agent_id=agent_id,
        tokens=0,  # 可以后续从响应中提取
        success=response.status_code < 400,
        response_time=response_time,
    )

    return response


@app.middleware("http")
async def log_middleware(request: Request, call_next):
    """日志记录中间件"""
    start_time = time.time()

    # 记录请求
    structured_logger.info(
        f"请求开始: {request.method} {request.url.path}",
        user_id=request.headers.get("X-User-ID"),
        agent_id=request.headers.get("X-Agent-ID"),
        method=request.method,
        path=request.url.path,
    )

    # 执行请求
    try:
        response = await call_next(request)
        response_time = time.time() - start_time

        # 记录成功响应
        structured_logger.info(
            f"请求完成: {request.method} {request.url.path} - {response.status_code}",
            user_id=request.headers.get("X-User-ID"),
            agent_id=request.headers.get("X-Agent-ID"),
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            response_time=response_time,
        )

        return response

    except Exception as e:
        response_time = time.time() - start_time

        # 记录错误
        structured_logger.error(
            f"请求失败: {request.method} {request.url.path} - {str(e)}",
            user_id=request.headers.get("X-User-ID"),
            agent_id=request.headers.get("X-Agent-ID"),
            method=request.method,
            path=request.url.path,
            error=str(e),
            response_time=response_time,
        )

        raise


# ==================== 依赖项 ====================


async def get_current_user(request: Request) -> str:
    """获取当前用户ID"""
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供用户ID"
        )
    return user_id


async def check_permission(permission: Permission):
    """权限检查依赖"""

    async def _check(request: Request):
        user_id = await get_current_user(request)

        if not permission_manager.check_permission(user_id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 {permission.value}",
            )

        return user_id

    return _check


# ==================== API端点 ====================


@app.get("/", response_model=HealthResponse)
async def root():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="0.3.0",
        timestamp=time.time(),
        uptime=time.time(),  # 可以后续实现真实的uptime
    )


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """健康检查API"""
    return await root()


# ==================== 用户管理API ====================


class UserCreateRequest(BaseModel):
    """创建用户请求"""

    username: str
    email: Optional[str] = None
    role: str = "user"


@app.post("/api/v1/users")
async def create_user(
    request: UserCreateRequest,
    _: str = Depends(check_permission(Permission.USER_WRITE)),
):
    """创建用户"""
    try:
        user = user_manager.create_user(
            username=request.username, email=request.email, role=Role(request.role)
        )

        # 审计日志
        structured_logger.audit(
            user_id=user.user_id,
            action="create",
            resource_type="user",
            resource_id=user.user_id,
            details={"username": user.username, "email": user.email},
        )

        return {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "created_at": user.created_at.isoformat(),
        }
    except Exception as e:
        structured_logger.error(f"创建用户失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/users/{user_id}")
async def get_user(
    user_id: str, _: str = Depends(check_permission(Permission.USER_READ))
):
    """获取用户"""
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return {
        "user_id": user.user_id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "created_at": user.created_at.isoformat(),
    }


# ==================== 权限管理API ====================


@app.post("/api/v1/permissions/assign-role")
async def assign_role(
    user_id: str = Query(...),
    role: str = Query(...),
    _: str = Depends(check_permission(Permission.SYSTEM_ADMIN)),
):
    """分配角色"""
    try:
        permission_manager.assign_role(user_id, Role(role))

        structured_logger.audit(
            user_id=_,
            action="assign_role",
            resource_type="user",
            resource_id=user_id,
            details={"role": role},
        )

        return {"message": "角色分配成功", "user_id": user_id, "role": role}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/permissions/user/{user_id}")
async def get_user_permissions(
    user_id: str, _: str = Depends(check_permission(Permission.USER_READ))
):
    """获取用户权限"""
    return permission_manager.get_user_permissions(user_id)


# ==================== 流量控制API ====================


@app.get("/api/v1/traffic/metrics")
async def get_traffic_metrics(
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """获取流量指标"""
    return await rate_limiter.get_metrics()


@app.get("/api/v1/traffic/rate-limits")
async def get_rate_limits(_: str = Depends(check_permission(Permission.SYSTEM_ADMIN))):
    """获取速率限制配置"""
    return await rate_limiter.get_rate_limits()


@app.post("/api/v1/traffic/rate-limits")
async def set_rate_limit(
    name: str = Query(...),
    limit_type: str = Query(...),
    limit: int = Query(...),
    scope: str = Query(...),
    window_seconds: int = Query(60),
    _: str = Depends(check_permission(Permission.SYSTEM_ADMIN)),
):
    """设置速率限制"""
    from src.infrastructure import RateLimitType, LimitScope

    await rate_limiter.set_rate_limit(
        name=name,
        limit_type=RateLimitType(limit_type),
        limit=limit,
        scope=LimitScope(scope),
        window_seconds=window_seconds,
    )

    return {"message": "速率限制设置成功"}


# ==================== 日志管理API ====================


@app.get("/api/v1/logs")
async def query_logs(
    level: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    session_id: Optional[str] = Query(None),
    limit: int = Query(100),
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """查询日志"""
    from src.infrastructure import LogLevel, LogCategory

    logs = structured_logger.query_logs(
        level=LogLevel(level) if level else None,
        category=LogCategory(category) if category else None,
        user_id=user_id,
        agent_id=agent_id,
        session_id=session_id,
        limit=limit,
    )

    return {"count": len(logs), "logs": [log.to_dict() for log in logs]}


@app.get("/api/v1/logs/audit")
async def query_audit_logs(
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    limit: int = Query(100),
    _: str = Depends(check_permission(Permission.SYSTEM_ADMIN)),
):
    """查询审计日志"""
    audits = structured_logger.query_audit_logs(
        user_id=user_id, action=action, resource_type=resource_type, limit=limit
    )

    return {"count": len(audits), "audits": [audit.to_dict() for audit in audits]}


# ==================== 任务调度API ====================


class TaskSubmitRequest(BaseModel):
    """提交任务请求"""

    name: str
    description: str = ""
    priority: str = "normal"
    tags: List[str] = []
    max_retries: int = 3
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


class CronTaskSubmitRequest(BaseModel):
    """提交Cron任务请求"""

    name: str
    description: str = ""
    priority: str = "normal"
    cron_expression: str
    tags: List[str] = []
    args: List[Any] = []
    kwargs: Dict[str, Any] = {}


@app.post("/api/v1/tasks")
async def submit_task(
    request: TaskSubmitRequest,
    user_id: str = Depends(get_current_user),
):
    """提交立即执行的任务"""
    from src.kernel.task_scheduler_enhanced import TaskPriority as TP

    # 简单的任务函数示例
    async def simple_task():
        import asyncio

        await asyncio.sleep(1)
        return {"result": "task_completed", "user_id": user_id}

    task_id = await task_scheduler.submit(
        name=request.name,
        function=simple_task,
        description=request.description,
        priority=TP[request.priority.upper()],
        tags=request.tags,
        max_retries=request.max_retries,
        *request.args,
        **request.kwargs,
    )

    structured_logger.task_execution(
        f"任务提交: {request.name}", task_id=task_id, user_id=user_id
    )

    return {"task_id": task_id, "status": "submitted", "name": request.name}


@app.post("/api/v1/tasks/cron")
async def submit_cron_task(
    request: CronTaskSubmitRequest,
    user_id: str = Depends(get_current_user),
):
    """提交Cron定时任务"""
    from src.kernel.task_scheduler_enhanced import TaskPriority as TP

    # 简单的任务函数示例
    async def cron_task():
        import asyncio

        await asyncio.sleep(0.5)
        return {
            "result": "cron_task_completed",
            "user_id": user_id,
            "time": datetime.now().isoformat(),
        }

    try:
        task_id = await task_scheduler.schedule_cron(
            name=request.name,
            function=cron_task,
            cron_expression=request.cron_expression,
            description=request.description,
            priority=TP[request.priority.upper()],
            tags=request.tags,
            *request.args,
            **request.kwargs,
        )

        structured_logger.task_execution(
            f"Cron任务提交: {request.name}", task_id=task_id, user_id=user_id
        )

        return {
            "task_id": task_id,
            "status": "scheduled",
            "name": request.name,
            "cron_expression": request.cron_expression,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    status = await task_scheduler.get_task_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="任务不存在")

    return status


@app.get("/api/v1/tasks")
async def list_tasks(
    status: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    limit: int = Query(100),
    user_id: str = Depends(get_current_user),
):
    """列出任务"""
    from src.kernel.task_scheduler_enhanced import TaskStatus as TS

    task_status = TS(status) if status else None
    tag_list = tags.split(",") if tags else None

    tasks = await task_scheduler.list_tasks(
        status=task_status, tags=tag_list, limit=limit
    )

    return {"count": len(tasks), "tasks": tasks}


@app.get("/api/v1/tasks/stats")
async def get_task_stats():
    """获取任务统计"""
    return await task_scheduler.get_stats()


@app.delete("/api/v1/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    user_id: str = Depends(get_current_user),
):
    """取消任务"""
    success = await task_scheduler.cancel_task(task_id)

    if success:
        structured_logger.task_execution(
            f"任务取消: {task_id}", task_id=task_id, user_id=user_id
        )
        return {"message": "任务已取消", "task_id": task_id}
    else:
        raise HTTPException(status_code=400, detail="无法取消任务")


# ==================== 缓存管理API ====================


@app.get("/api/v1/cache/stats")
async def get_cache_stats(
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """获取缓存统计"""
    return await cache_manager.get_stats()


@app.get("/api/v1/cache/keys")
async def get_cache_keys(
    pattern: str = Query("*"),
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """获取缓存keys"""
    keys = await cache_manager.get_keys(pattern)
    return {"count": len(keys), "keys": keys}


@app.get("/api/v1/cache/{key}")
async def get_cache_value(
    key: str,
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """获取缓存值"""
    value = await cache_manager.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail="缓存键不存在")

    return {"key": key, "value": value}


@app.delete("/api/v1/cache/{key}")
async def delete_cache_value(
    key: str,
    _: str = Depends(check_permission(Permission.SYSTEM_ADMIN)),
):
    """删除缓存"""
    success = await cache_manager.delete(key)

    if success:
        structured_logger.audit(
            user_id=_,
            action="delete_cache",
            resource_type="cache",
            resource_id=key,
        )
        return {"message": "缓存已删除", "key": key}
    else:
        raise HTTPException(status_code=404, detail="缓存键不存在")


@app.delete("/api/v1/cache")
async def clear_cache(
    _: str = Depends(check_permission(Permission.SYSTEM_ADMIN)),
):
    """清空缓存"""
    success = await cache_manager.clear()

    if success:
        structured_logger.audit(
            user_id=_,
            action="clear_cache",
            resource_type="cache",
            resource_id="all",
        )
        return {"message": "缓存已清空"}
    else:
        raise HTTPException(status_code=500, detail="清空缓存失败")


# ==================== Dashboard API ====================


@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats(
    _: str = Depends(check_permission(Permission.SYSTEM_MONITOR)),
):
    """获取Dashboard统计数据"""
    # 获取流量指标
    traffic_metrics = await rate_limiter.get_metrics()

    # 获取任务统计
    task_stats = await task_scheduler.get_stats()

    # 获取缓存统计
    cache_stats = await cache_manager.get_stats()

    # 用户统计
    user_stats = {
        "total_users": len(user_manager.users),
        "active_users": traffic_metrics.get("active_users", 0),
    }

    # Agent统计
    agent_stats = {
        "total_agents": len(agent_manager.agents),
        "active_agents": sum(
            1
            for agent in agent_manager.agents.values()
            if agent.status == AgentStatus.ACTIVE
        ),
    }

    return {
        "timestamp": datetime.now().isoformat(),
        "traffic": traffic_metrics,
        "tasks": task_stats,
        "cache": cache_stats,
        "users": user_stats,
        "agents": agent_stats,
    }


# ==================== 启动和关闭事件 ====================


@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Agent OS API 启动中...")

    # 加载权限状态
    permission_manager.load_state()

    # 初始化缓存系统
    await cache_manager.initialize()
    logger.info("缓存系统已初始化")

    # 启动任务调度器
    await task_scheduler.start()
    logger.info("任务调度器已启动")

    logger.info("Agent OS API 启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Agent OS API 关闭中...")

    # 停止任务调度器
    await task_scheduler.stop()
    logger.info("任务调度器已停止")

    # 关闭缓存系统
    await cache_manager.shutdown()
    logger.info("缓存系统已关闭")

    # 刷新日志缓冲区
    structured_logger.flush()

    # 保存权限状态
    permission_manager.save_state()

    logger.info("Agent OS API 已关闭")


# ==================== 主函数 ====================


def main():
    """主函数"""
    uvicorn.run(
        "main_complete:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )


if __name__ == "__main__":
    main()
