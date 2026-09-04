"""
Agent OS API 服务入口
基于FastAPI的RESTful API服务
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import uvicorn
import logging

from src.kernel.agent_manager import get_agent_manager
from src.memory.working_memory import WorkingMemory
from src.planner.hierarchical_planner import HierarchicalPlanner
from src.tools.tool_registry import get_tool_registry, ToolCategory

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Agent OS API",
    description="智能体操作系统API服务",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic模型定义

class AgentCreateRequest(BaseModel):
    """创建Agent请求"""
    name: str = Field(..., description="Agent名称")
    description: str = Field("", description="Agent描述")
    capabilities: List[str] = Field([], description="能力列表")
    memory_config: Dict[str, Any] = Field({}, description="记忆配置")
    planner_config: Dict[str, Any] = Field({}, description="规划器配置")

class AgentResponse(BaseModel):
    """Agent响应"""
    agent_id: str
    name: str
    description: str
    status: str
    created_at: float
    last_active: float

class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    goal: str = Field(..., description="任务目标")
    context: Optional[Dict[str, Any]] = Field(None, description="任务上下文")
    priority: int = Field(1, ge=1, le=5, description="优先级(1-5)")

class TaskResponse(BaseModel):
    """任务响应"""
    task_id: str
    name: str
    description: str
    status: str
    priority: int
    subtasks: List[Dict[str, Any]]

class ToolExecuteRequest(BaseModel):
    """执行工具请求"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field({}, description="工具参数")

class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None

# API路由

@app.get("/")
async def root():
    """根端点"""
    return {
        "service": "Agent OS API",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "agents": "/api/v1/agents",
            "tasks": "/api/v1/tasks",
            "tools": "/api/v1/tools",
            "memory": "/api/v1/memory",
            "health": "/health"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": __import__("time").time()
    }

# Agent管理API

@app.get("/api/v1/agents", response_model=List[AgentResponse])
async def list_agents():
    """列出所有Agent"""
    agent_manager = get_agent_manager()
    agents = await agent_manager.list_agents()
    
    return [
        AgentResponse(
            agent_id=agent.agent_id,
            name=agent_manager.agents[agent.agent_id].name,
            description=agent_manager.agents[agent.agent_id].description,
            status=agent.status.value,
            created_at=agent.created_at,
            last_active=agent.last_active
        )
        for agent in agents
    ]

@app.post("/api/v1/agents", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(request: AgentCreateRequest):
    """创建新的Agent"""
    from src.kernel.agent_manager import AgentConfig
    
    agent_manager = get_agent_manager()
    
    # 生成Agent ID
    import uuid
    agent_id = f"agent_{uuid.uuid4().hex[:8]}"
    
    # 创建配置
    config = AgentConfig(
        agent_id=agent_id,
        name=request.name,
        description=request.description,
        capabilities=request.capabilities,
        memory_config=request.memory_config,
        planner_config=request.planner_config
    )
    
    # 创建Agent
    created_id = await agent_manager.create_agent(config)
    
    # 获取状态
    state = await agent_manager.get_agent_status(created_id)
    
    return AgentResponse(
        agent_id=created_id,
        name=config.name,
        description=config.description,
        status=state.status.value if state else "unknown",
        created_at=state.created_at if state else __import__("time").time(),
        last_active=state.last_active if state else __import__("time").time()
    )

@app.get("/api/v1/agents/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """获取Agent信息"""
    agent_manager = get_agent_manager()
    
    state = await agent_manager.get_agent_status(agent_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Agent不存在: {agent_id}")
    
    config = agent_manager.agents.get(agent_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Agent配置不存在: {agent_id}")
    
    return AgentResponse(
        agent_id=agent_id,
        name=config.name,
        description=config.description,
        status=state.status.value,
        created_at=state.created_at,
        last_active=state.last_active
    )

# 任务规划API

@app.post("/api/v1/tasks", response_model=TaskResponse)
async def create_task(request: TaskCreateRequest):
    """创建新任务"""
    planner = HierarchicalPlanner()
    
    # 创建任务
    task = await planner.plan(request.goal, request.context)
    
    # 设置优先级
    task.priority = request.priority
    for subtask in task.subtasks:
        subtask.priority = request.priority
    
    return TaskResponse(
        task_id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        priority=task.priority,
        subtasks=[subtask.to_dict() for subtask in task.subtasks]
    )

@app.get("/api/v1/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """获取任务信息"""
    planner = HierarchicalPlanner()
    
    task = planner.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    
    return TaskResponse(
        task_id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        priority=task.priority,
        subtasks=[subtask.to_dict() for subtask in task.subtasks]
    )

# 工具管理API

@app.get("/api/v1/tools")
async def list_tools(category: Optional[str] = None):
    """列出所有工具"""
    registry = get_tool_registry()
    
    if category:
        try:
            tool_category = ToolCategory(category)
            tools = registry.list_tools(tool_category)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的工具类别: {category}")
    else:
        tools = registry.list_tools()
    
    return {
        "tools": [tool.to_dict() for tool in tools],
        "total": len(tools),
        "categories": [cat.value for cat in ToolCategory]
    }

@app.post("/api/v1/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(request: ToolExecuteRequest):
    """执行工具"""
    registry = get_tool_registry()
    
    result = await registry.execute(request.tool_name, **request.parameters)
    
    return ToolExecuteResponse(
        success=result.get("success", False),
        result=result.get("result"),
        error=result.get("error"),
        execution_time=result.get("execution_time")
    )

# 记忆管理API

@app.post("/api/v1/memory/{agent_id}/add")
async def add_memory(agent_id: str, content: str, importance: float = 1.0):
    """添加工作记忆"""
    # 这里应该根据agent_id获取对应的记忆实例
    # 简化实现：创建新的工作记忆
    memory = WorkingMemory()
    memory_id = memory.add(content, importance)
    
    return {
        "agent_id": agent_id,
        "memory_id": memory_id,
        "content": content,
        "importance": importance,
        "timestamp": __import__("time").time()
    }

@app.get("/api/v1/memory/{agent_id}/summary")
async def get_memory_summary(agent_id: str, max_length: int = 500):
    """获取记忆摘要"""
    memory = WorkingMemory()
    summary = memory.summarize(max_length)
    
    return {
        "agent_id": agent_id,
        "summary": summary,
        "length": len(summary)
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
