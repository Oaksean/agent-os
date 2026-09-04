"""
Agent OS 增强版 API服务
整合所有核心功能的RESTful API
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import logging

# 导入核心模块
from src.core.types import (
    AgentStatus,
    TaskStatus,
    TaskPriority,
    MemoryType,
    Permission,
    Role,
    PromptType,
    LogLevel,
)
from src.kernel.agent_manager import AgentManager
from src.users.user_manager import UserManager
from src.prompts.prompt_manager import PromptManager
from src.sessions.session_manager import SessionManager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Agent OS API",
    description="智能体操作系统完整API服务",
    version="0.2.0",
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


# ==================== Pydantic模型 ====================


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str
    version: str
    timestamp: float
    uptime: float


class UserCreateRequest(BaseModel):
    """创建用户请求"""

    username: str = Field(..., description="用户名")
    email: Optional[str] = Field(None, description="邮箱")
    role: str = Field("user", description="角色")


class UserResponse(BaseModel):
    """用户响应"""

    user_id: str
    username: str
    email: Optional[str]
    role: str
    created_at: str


class HabitCreateRequest(BaseModel):
    """创建习惯请求"""

    name: str
    description: str
    pattern: str


class TagCreateRequest(BaseModel):
    """创建标签请求"""

    name: str
    category: str
    weight: float = 1.0


class MemoryCreateRequest(BaseModel):
    """创建记忆请求"""

    memory_type: str
    content: str
    importance: float = 1.0
    tags: List[str] = []


class PromptCreateRequest(BaseModel):
    """创建提示词请求"""

    name: str
    content: str
    variables: List[str] = []
    description: str = ""
    tags: List[str] = []


class PromptRenderRequest(BaseModel):
    """渲染提示词请求"""

    template_id: str
    variables: Dict[str, Any] = {}


class SessionCreateRequest(BaseModel):
    """创建会话请求"""

    user_id: str
    agent_id: str


class MessageCreateRequest(BaseModel):
    """创建消息请求"""

    role: str
    content: str
    tokens: int = 0


class SummaryGenerateRequest(BaseModel):
    """生成摘要请求"""

    session_id: str
    max_length: int = 500


class AgentCreateRequest(BaseModel):
    """创建Agent请求"""

    name: str
    description: str = ""
    capabilities: List[str] = []


class TaskCreateRequest(BaseModel):
    """创建任务请求"""

    goal: str
    priority: int = 2
    context: Optional[Dict[str, Any]] = None


# ==================== 根路由 ====================


@app.get("/", response_model=Dict[str, Any])
async def root():
    """根端点"""
    return {
        "service": "Agent OS API",
        "version": "0.2.0",
        "status": "running",
        "timestamp": datetime.now().timestamp(),
        "endpoints": {
            "health": "/health",
            "users": "/api/v1/users",
            "prompts": "/api/v1/prompts",
            "sessions": "/api/v1/sessions",
            "agents": "/api/v1/agents",
            "dashboard": "/api/v1/dashboard",
        },
        "features": [
            "用户管理系统",
            "提示词管理",
            "会话管理",
            "记忆系统",
            "习惯追踪",
            "标签系统",
            "流量监控",
            "权限控制",
        ],
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version="0.2.0",
        timestamp=datetime.now().timestamp(),
        uptime=0.0,  # 可以实现实际运行时间计算
    )


# ==================== 用户管理API ====================


@app.post(
    "/api/v1/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(request: UserCreateRequest):
    """创建用户"""
    role = Role(request.role)
    user = user_manager.create_user(
        username=request.username, email=request.email, role=role
    )

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


@app.get("/api/v1/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """获取用户"""
    user = user_manager.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


@app.get("/api/v1/users", response_model=List[UserResponse])
async def list_users(role: Optional[str] = None):
    """列出用户"""
    role_filter = Role(role) if role else None
    users = user_manager.list_users(role_filter)

    return [
        UserResponse(
            user_id=user.user_id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=user.created_at.isoformat(),
        )
        for user in users
    ]


# ==================== 习惯管理API ====================


@app.post("/api/v1/users/{user_id}/habits")
async def add_habit(user_id: str, request: HabitCreateRequest):
    """添加用户习惯"""
    habit = user_manager.add_habit(
        user_id=user_id,
        name=request.name,
        description=request.description,
        pattern=request.pattern,
    )

    if not habit:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return {
        "habit_id": habit.habit_id,
        "name": habit.name,
        "confidence": habit.confidence,
    }


@app.get("/api/v1/users/{user_id}/habits")
async def get_user_habits(user_id: str):
    """获取用户习惯"""
    habits = user_manager.get_user_habits(user_id)

    return {
        "user_id": user_id,
        "habits": [
            {
                "habit_id": h.habit_id,
                "name": h.name,
                "description": h.description,
                "confidence": h.confidence,
                "trigger_count": h.trigger_count,
            }
            for h in habits
        ],
        "total": len(habits),
    }


# ==================== 标签管理API ====================


@app.post("/api/v1/users/{user_id}/tags")
async def add_tag(user_id: str, request: TagCreateRequest):
    """添加用户标签"""
    tag = user_manager.add_tag(
        user_id=user_id,
        name=request.name,
        category=request.category,
        weight=request.weight,
    )

    if not tag:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return {
        "tag_id": tag.tag_id,
        "name": tag.name,
        "category": tag.category,
        "weight": tag.weight,
    }


@app.get("/api/v1/users/{user_id}/tags")
async def get_user_tags(user_id: str, category: Optional[str] = None):
    """获取用户标签"""
    tags = user_manager.get_user_tags(user_id, category)

    return {
        "user_id": user_id,
        "tags": [
            {
                "tag_id": t.tag_id,
                "name": t.name,
                "category": t.category,
                "weight": t.weight,
                "source": t.source,
            }
            for t in tags
        ],
        "total": len(tags),
    }


# ==================== 记忆管理API ====================


@app.post("/api/v1/users/{user_id}/memories")
async def add_memory(user_id: str, request: MemoryCreateRequest):
    """添加用户记忆"""
    memory_type = MemoryType(request.memory_type)

    memory = user_manager.add_memory(
        user_id=user_id,
        memory_type=memory_type,
        content=request.content,
        importance=request.importance,
        tags=request.tags,
    )

    if not memory:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return {
        "memory_id": memory.memory_id,
        "memory_type": memory.memory_type,
        "importance": memory.importance,
        "created_at": memory.created_at.isoformat(),
    }


@app.get("/api/v1/users/{user_id}/memories")
async def get_user_memories(
    user_id: str,
    memory_type: Optional[str] = None,
    min_importance: float = 0.0,
    limit: int = 100,
):
    """获取用户记忆"""
    mem_type = MemoryType(memory_type) if memory_type else None

    memories = user_manager.get_user_memories(
        user_id=user_id,
        memory_type=mem_type,
        min_importance=min_importance,
        limit=limit,
    )

    return {
        "user_id": user_id,
        "memories": [
            {
                "memory_id": m.memory_id,
                "memory_type": m.memory_type,
                "content": m.content[:100] + "..."
                if len(m.content) > 100
                else m.content,
                "importance": m.importance,
                "access_count": m.access_count,
                "tags": m.tags,
            }
            for m in memories
        ],
        "total": len(memories),
    }


# ==================== 提示词管理API ====================


@app.post("/api/v1/prompts/system")
async def create_system_prompt(request: PromptCreateRequest):
    """创建系统提示词"""
    prompt = prompt_manager.create_system_prompt(
        name=request.name,
        content=request.content,
        variables=request.variables,
        description=request.description,
        tags=request.tags,
    )

    return {
        "template_id": prompt.template_id,
        "name": prompt.name,
        "type": "system",
        "variables": prompt.variables,
    }


@app.post("/api/v1/prompts/user")
async def create_user_prompt(request: PromptCreateRequest):
    """创建用户提示词"""
    prompt = prompt_manager.create_user_prompt(
        name=request.name,
        content=request.content,
        variables=request.variables,
        description=request.description,
        tags=request.tags,
    )

    return {
        "template_id": prompt.template_id,
        "name": prompt.name,
        "type": "user",
        "variables": prompt.variables,
    }


@app.post("/api/v1/prompts/render")
async def render_prompt(request: PromptRenderRequest):
    """渲染提示词"""
    content = prompt_manager.render_prompt(
        template_id=request.template_id, **request.variables
    )

    return {
        "template_id": request.template_id,
        "rendered_content": content,
        "length": len(content),
    }


@app.get("/api/v1/prompts")
async def list_prompts(prompt_type: Optional[str] = None, tags: Optional[str] = None):
    """列出提示词"""
    p_type = PromptType(prompt_type) if prompt_type else None
    tag_list = tags.split(",") if tags else None

    prompts = prompt_manager.list_prompts(p_type, tag_list)

    return {
        "prompts": [
            {
                "template_id": p.template_id,
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "variables": p.variables,
                "tags": p.tags,
            }
            for p in prompts
        ],
        "total": len(prompts),
    }


# ==================== 会话管理API ====================


@app.post("/api/v1/sessions")
async def create_session(request: SessionCreateRequest):
    """创建会话"""
    session = session_manager.create_session(
        user_id=request.user_id, agent_id=request.agent_id
    )

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "agent_id": session.agent_id,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
    }


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """获取会话"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在: {session_id}")

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "agent_id": session.agent_id,
        "status": session.status,
        "message_count": len(session.messages),
        "total_tokens": session.total_tokens,
        "created_at": session.created_at.isoformat(),
    }


@app.post("/api/v1/sessions/{session_id}/messages")
async def add_message(session_id: str, request: MessageCreateRequest):
    """添加消息"""
    message = session_manager.add_message(
        session_id=session_id,
        role=request.role,
        content=request.content,
        tokens=request.tokens,
    )

    if not message:
        raise HTTPException(status_code=404, detail=f"会话不存在或已关闭: {session_id}")

    return {
        "message_id": message.message_id,
        "role": message.role,
        "content": message.content,
        "tokens": message.tokens,
        "timestamp": message.timestamp.isoformat(),
    }


@app.get("/api/v1/sessions/{session_id}/messages")
async def get_messages(session_id: str, limit: Optional[int] = None):
    """获取会话消息"""
    messages = session_manager.get_messages(session_id, limit)

    return {
        "session_id": session_id,
        "messages": [
            {
                "message_id": m.message_id,
                "role": m.role,
                "content": m.content,
                "tokens": m.tokens,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in messages
        ],
        "total": len(messages),
    }


@app.post("/api/v1/sessions/{session_id}/summary")
async def generate_summary(session_id: str, request: SummaryGenerateRequest):
    """生成会话摘要"""
    summary = session_manager.generate_summary(
        session_id=session_id, max_length=request.max_length
    )

    if not summary:
        raise HTTPException(status_code=404, detail=f"会话不存在或无消息: {session_id}")

    return {
        "summary_id": summary.summary_id,
        "content": summary.content,
        "key_points": summary.key_points,
        "entities": summary.entities,
        "sentiment": summary.sentiment,
    }


# ==================== Agent管理API ====================


@app.post("/api/v1/agents")
async def create_agent(request: AgentCreateRequest):
    """创建Agent"""
    from src.kernel.agent_manager import AgentConfig, AgentCapability

    config = AgentConfig(
        name=request.name,
        description=request.description,
        capabilities=[AgentCapability(cap) for cap in request.capabilities],
    )

    agent_id = agent_manager.create_agent(config)

    return {"agent_id": agent_id, "name": config.name, "status": "created"}


@app.get("/api/v1/agents")
async def list_agents():
    """列出所有Agent"""
    agents = agent_manager.list_agents()

    return {
        "agents": [
            {
                "agent_id": a.agent_id,
                "name": a.config.name,
                "status": a.status.value,
                "created_at": a.created_at.isoformat(),
            }
            for a in agents
        ],
        "total": len(agents),
    }


# ==================== Dashboard API ====================


@app.get("/api/v1/dashboard/stats")
async def get_dashboard_stats():
    """获取Dashboard统计"""
    return {
        "users": {
            "total": len(user_manager.users),
            "active": len(
                [u for u in user_manager.users.values() if u.role == Role.USER]
            ),
        },
        "sessions": {
            "total": len(session_manager.sessions),
            "active": len(
                [s for s in session_manager.sessions.values() if s.status == "active"]
            ),
        },
        "agents": {
            "total": len(agent_manager.agents),
            "running": len(
                [
                    a
                    for a in agent_manager.agents.values()
                    if a.status == AgentStatus.RUNNING
                ]
            ),
        },
        "prompts": {
            "system": len(prompt_manager.system_prompts),
            "user": len(prompt_manager.user_prompts),
        },
        "memory": {
            "users_with_memory": len(user_manager.user_memories),
            "total_memories": sum(len(m) for m in user_manager.user_memories.values()),
        },
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/dashboard/activity")
async def get_recent_activity(limit: int = 20):
    """获取最近活动"""
    activities = []

    # 最近会话
    recent_sessions = sorted(
        session_manager.sessions.values(), key=lambda s: s.updated_at, reverse=True
    )[:limit]

    for session in recent_sessions:
        activities.append(
            {
                "type": "session",
                "id": session.session_id,
                "user_id": session.user_id,
                "agent_id": session.agent_id,
                "action": "created" if len(session.messages) == 0 else "updated",
                "timestamp": session.updated_at.isoformat(),
            }
        )

    # 按时间排序
    activities.sort(key=lambda x: x["timestamp"], reverse=True)

    return {"activities": activities[:limit], "total": len(activities)}


# ==================== 系统管理API ====================


@app.post("/api/v1/system/cleanup")
async def cleanup_system():
    """系统清理"""
    # 清理过期会话
    expired = session_manager.cleanup_expired_sessions()

    # 巩固用户记忆
    consolidated = 0
    for user_id in user_manager.users:
        consolidated += user_manager.consolidate_memories(user_id)

    return {
        "expired_sessions": expired,
        "consolidated_memories": consolidated,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/v1/system/health")
async def system_health():
    """系统健康检查"""
    return {
        "status": "healthy",
        "components": {
            "user_manager": "ok" if user_manager else "error",
            "session_manager": "ok" if session_manager else "error",
            "agent_manager": "ok" if agent_manager else "error",
            "prompt_manager": "ok" if prompt_manager else "error",
        },
        "timestamp": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main_enhanced:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
