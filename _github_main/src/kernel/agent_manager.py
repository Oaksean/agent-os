#!/usr/bin/env python3
"""
Agent管理器
负责Agent的生命周期管理：创建、暂停、恢复、迁移、销毁
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from pathlib import Path

from pydantic import BaseModel, Field, ConfigDict
from loguru import logger


class AgentStatus(Enum):
    """Agent状态枚举"""
    CREATED = "created"        # 已创建
    INITIALIZING = "initializing"  # 初始化中
    READY = "ready"           # 就绪
    RUNNING = "running"       # 运行中
    PAUSED = "paused"         # 已暂停
    STOPPED = "stopped"       # 已停止
    ERROR = "error"           # 错误状态
    MIGRATING = "migrating"   # 迁移中


class AgentCapability(Enum):
    """Agent能力枚举"""
    TEXT_GENERATION = "text_generation"
    CODE_EXECUTION = "code_execution"
    WEB_SEARCH = "web_search"
    FILE_OPERATION = "file_operation"
    DATABASE_QUERY = "database_query"
    API_CALL = "api_call"
    IMAGE_PROCESSING = "image_processing"
    AUDIO_PROCESSING = "audio_processing"
    PLANNING = "planning"
    REASONING = "reasoning"
    MEMORY_MANAGEMENT = "memory_management"
    TOOL_USAGE = "tool_usage"


class AgentConfig(BaseModel):
    """Agent配置"""
    name: str = Field(..., description="Agent名称")
    description: str = Field("", description="Agent描述")
    capabilities: List[AgentCapability] = Field(default_factory=list, description="Agent能力列表")
    model_settings: Dict[str, Any] = Field(default_factory=dict, description="模型配置")
    memory_config: Dict[str, Any] = Field(default_factory=dict, description="记忆配置")
    tool_config: Dict[str, Any] = Field(default_factory=dict, description="工具配置")
    security_config: Dict[str, Any] = Field(default_factory=dict, description="安全配置")

    model_config = ConfigDict(use_enum_values=True)


@dataclass
class AgentState:
    """Agent状态"""
    agent_id: str
    config: AgentConfig
    status: AgentStatus
    created_at: datetime
    updated_at: datetime
    current_task: Optional[str] = None
    resources: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_info: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['config'] = self.config.model_dump()
        data['status'] = self.status.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """从字典创建"""
        config = AgentConfig(**data['config'])
        status = AgentStatus(data['status'])
        created_at = datetime.fromisoformat(data['created_at'])
        updated_at = datetime.fromisoformat(data['updated_at'])
        
        return cls(
            agent_id=data['agent_id'],
            config=config,
            status=status,
            created_at=created_at,
            updated_at=updated_at,
            current_task=data.get('current_task'),
            resources=data.get('resources', {}),
            metrics=data.get('metrics', {}),
            error_info=data.get('error_info')
        )


class AgentManager:
    """Agent管理器"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化Agent管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config or {}
        self.agents: Dict[str, AgentState] = {}
        self.agent_tasks: Dict[str, asyncio.Task] = {}
        self.state_file = Path(self.config.get('state_file', 'data/agents/agents_state.json'))
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载已保存的状态
        self._load_state()
        
        logger.info(f"Agent管理器初始化完成，已加载 {len(self.agents)} 个Agent")
    
    def _load_state(self):
        """加载保存的状态"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for agent_data in data.get('agents', []):
                    try:
                        agent_state = AgentState.from_dict(agent_data)
                        self.agents[agent_state.agent_id] = agent_state
                    except Exception as e:
                        logger.error(f"加载Agent状态失败: {e}")
        except Exception as e:
            logger.error(f"加载Agent状态文件失败: {e}")
    
    def _save_state(self):
        """保存状态到文件"""
        try:
            data = {
                'agents': [agent.to_dict() for agent in self.agents.values()],
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存Agent状态失败: {e}")
    
    def create_agent(self, config: AgentConfig) -> str:
        """
        创建新的Agent
        
        Args:
            config: Agent配置
            
        Returns:
            Agent ID
        """
        agent_id = f"agent_{uuid.uuid4().hex[:8]}"
        
        agent_state = AgentState(
            agent_id=agent_id,
            config=config,
            status=AgentStatus.CREATED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.agents[agent_id] = agent_state
        self._save_state()
        
        logger.info(f"创建Agent: {agent_id} - {config.name}")
        return agent_id
    
    async def initialize_agent(self, agent_id: str) -> bool:
        """
        初始化Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否初始化成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        agent.status = AgentStatus.INITIALIZING
        agent.updated_at = datetime.now()
        
        try:
            # 这里可以添加具体的初始化逻辑
            # 例如：加载模型、初始化记忆系统、注册工具等
            
            # 模拟初始化过程
            await asyncio.sleep(0.1)
            
            agent.status = AgentStatus.READY
            agent.updated_at = datetime.now()
            self._save_state()
            
            logger.info(f"Agent初始化完成: {agent_id}")
            return True
            
        except Exception as e:
            agent.status = AgentStatus.ERROR
            agent.error_info = str(e)
            agent.updated_at = datetime.now()
            self._save_state()
            
            logger.error(f"Agent初始化失败 {agent_id}: {e}")
            return False
    
    async def start_agent(self, agent_id: str, task: Optional[Dict[str, Any]] = None) -> bool:
        """
        启动Agent执行任务
        
        Args:
            agent_id: Agent ID
            task: 任务描述
            
        Returns:
            是否启动成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        if agent.status != AgentStatus.READY:
            logger.error(f"Agent状态不可用: {agent.status}")
            return False
        
        # 创建任务
        agent.status = AgentStatus.RUNNING
        agent.current_task = str(task) if task else None
        agent.updated_at = datetime.now()
        
        # 创建异步任务
        task_obj = asyncio.create_task(self._run_agent_task(agent_id, task))
        self.agent_tasks[agent_id] = task_obj
        
        self._save_state()
        logger.info(f"启动Agent任务: {agent_id}")
        return True
    
    async def _run_agent_task(self, agent_id: str, task: Optional[Dict[str, Any]] = None):
        """运行Agent任务（内部方法）"""
        try:
            # 这里实现具体的任务执行逻辑
            # 例如：调用规划器、执行工具、更新记忆等
            
            agent = self.agents[agent_id]
            
            # 模拟任务执行
            await asyncio.sleep(1.0)
            
            # 更新状态
            agent.status = AgentStatus.READY
            agent.current_task = None
            agent.updated_at = datetime.now()
            
            # 更新指标
            agent.metrics['tasks_completed'] = agent.metrics.get('tasks_completed', 0) + 1
            agent.metrics['last_completed'] = datetime.now().isoformat()
            
            self._save_state()
            logger.info(f"Agent任务完成: {agent_id}")
            
        except Exception as e:
            agent = self.agents[agent_id]
            agent.status = AgentStatus.ERROR
            agent.error_info = str(e)
            agent.updated_at = datetime.now()
            self._save_state()
            
            logger.error(f"Agent任务失败 {agent_id}: {e}")
    
    async def pause_agent(self, agent_id: str) -> bool:
        """
        暂停Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否暂停成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        if agent.status != AgentStatus.RUNNING:
            logger.warning(f"Agent不在运行状态: {agent.status}")
            return False
        
        # 暂停任务
        if agent_id in self.agent_tasks:
            task = self.agent_tasks[agent_id]
            task.cancel()
            del self.agent_tasks[agent_id]
        
        agent.status = AgentStatus.PAUSED
        agent.updated_at = datetime.now()
        self._save_state()
        
        logger.info(f"暂停Agent: {agent_id}")
        return True
    
    async def resume_agent(self, agent_id: str) -> bool:
        """
        恢复Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否恢复成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        if agent.status != AgentStatus.PAUSED:
            logger.warning(f"Agent不在暂停状态: {agent.status}")
            return False
        
        agent.status = AgentStatus.READY
        agent.updated_at = datetime.now()
        self._save_state()
        
        logger.info(f"恢复Agent: {agent_id}")
        return True
    
    async def stop_agent(self, agent_id: str) -> bool:
        """
        停止Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否停止成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        
        # 取消任务
        if agent_id in self.agent_tasks:
            task = self.agent_tasks[agent_id]
            task.cancel()
            del self.agent_tasks[agent_id]
        
        agent.status = AgentStatus.STOPPED
        agent.current_task = None
        agent.updated_at = datetime.now()
        self._save_state()
        
        logger.info(f"停止Agent: {agent_id}")
        return True
    
    async def migrate_agent(self, agent_id: str, target_node: str) -> bool:
        """
        迁移Agent到其他节点
        
        Args:
            agent_id: Agent ID
            target_node: 目标节点
            
        Returns:
            是否迁移成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        agent = self.agents[agent_id]
        agent.status = AgentStatus.MIGRATING
        agent.updated_at = datetime.now()
        
        try:
            # 序列化Agent状态
            agent_state = agent.to_dict()
            
            # 这里应该实现实际的迁移逻辑
            # 例如：通过网络发送到其他节点
            
            # 模拟迁移过程
            await asyncio.sleep(0.5)
            
            # 从当前节点移除
            del self.agents[agent_id]
            if agent_id in self.agent_tasks:
                task = self.agent_tasks[agent_id]
                task.cancel()
                del self.agent_tasks[agent_id]
            
            self._save_state()
            logger.info(f"迁移Agent {agent_id} 到节点 {target_node}")
            return True
            
        except Exception as e:
            agent.status = AgentStatus.ERROR
            agent.error_info = f"迁移失败: {e}"
            agent.updated_at = datetime.now()
            self._save_state()
            
            logger.error(f"Agent迁移失败 {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[AgentState]:
        """
        获取Agent状态
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent状态，如果不存在返回None
        """
        return self.agents.get(agent_id)
    
    def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[AgentState]:
        """
        列出Agent
        
        Args:
            status_filter: 状态过滤器
            
        Returns:
            Agent状态列表
        """
        agents = list(self.agents.values())
        
        if status_filter:
            agents = [agent for agent in agents if agent.status == status_filter]
        
        return agents
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        删除Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否删除成功
        """
        if agent_id not in self.agents:
            logger.error(f"Agent不存在: {agent_id}")
            return False
        
        # 停止Agent（如果正在运行）
        if agent_id in self.agent_tasks:
            task = self.agent_tasks[agent_id]
            task.cancel()
            del self.agent_tasks[agent_id]
        
        # 删除Agent
        del self.agents[agent_id]
        self._save_state()
        
        logger.info(f"删除Agent: {agent_id}")
        return True
    
    def cleanup(self):
        """清理资源"""
        # 取消所有任务
        for task in self.agent_tasks.values():
            task.cancel()
        
        self.agent_tasks.clear()
        self._save_state()
        
        logger.info("Agent管理器清理完成")


async def test_agent_manager():
    """测试Agent管理器"""
    import asyncio
    
    # 创建管理器
    manager = AgentManager()
    
    # 创建Agent配置
    config = AgentConfig(
        name="个人助手",
        description="帮助处理日常任务的智能助手",
        capabilities=[
            AgentCapability.TEXT_GENERATION,
            AgentCapability.WEB_SEARCH,
            AgentCapability.FILE_OPERATION
        ],
        model_settings={
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 1000
        }
    )
    
    # 创建Agent
    agent_id = manager.create_agent(config)
    print(f"创建Agent: {agent_id}")
    
    # 初始化Agent
    success = await manager.initialize_agent(agent_id)
    print(f"初始化Agent: {'成功' if success else '失败'}")
    
    # 启动Agent执行任务
    task = {
        "goal": "查找最新的AI研究进展",
        "constraints": ["只使用arXiv", "最近7天", "关注大模型"]
    }
    
    success = await manager.start_agent(agent_id, task)
    print(f"启动Agent任务: {'成功' if success else '失败'}")
    
    # 等待任务完成
    await asyncio.sleep(2.0)
    
    # 获取Agent状态
    agent = manager.get_agent(agent_id)
    print(f"Agent状态: {agent.status.value if agent else '不存在'}")
    
    # 列出所有Agent
    agents = manager.list_agents()
    print(f"总Agent数: {len(agents)}")
    
    # 清理
    manager.cleanup()


if __name__ == "__main__":
    # 配置日志
    import sys
    from loguru import logger
    
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 运行测试
    asyncio.run(test_agent_manager())
