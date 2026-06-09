"""
Agent管理器测试
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.kernel.agent_manager import AgentManager, AgentConfig, AgentStatus

@pytest.fixture
def agent_manager():
    """Agent管理器fixture"""
    return AgentManager()

@pytest.fixture
def sample_config():
    """示例配置fixture"""
    return AgentConfig(
        agent_id="test_agent_001",
        name="测试Agent",
        description="用于测试的Agent",
        capabilities=["planning", "memory"],
        memory_config={"max_size": 100},
        planner_config={"llm_enabled": True}
    )

@pytest.mark.asyncio
async def test_create_agent(agent_manager, sample_config):
    """测试创建Agent"""
    agent_id = await agent_manager.create_agent(sample_config)
    
    assert agent_id == sample_config.agent_id
    assert agent_id in agent_manager.agents
    assert agent_id in agent_manager.states
    
    state = await agent_manager.get_agent_status(agent_id)
    assert state is not None
    assert state.agent_id == agent_id
    assert state.status == AgentStatus.CREATED

@pytest.mark.asyncio
async def test_pause_and_resume_agent(agent_manager, sample_config):
    """测试暂停和恢复Agent"""
    agent_id = await agent_manager.create_agent(sample_config)
    
    # 启动Agent
    state = await agent_manager.get_agent_status(agent_id)
    state.status = AgentStatus.RUNNING
    
    # 暂停
    result = await agent_manager.pause_agent(agent_id)
    assert result is True
    
    state = await agent_manager.get_agent_status(agent_id)
    assert state.status == AgentStatus.PAUSED
    
    # 恢复
    result = await agent_manager.resume_agent(agent_id)
    assert result is True
    
    state = await agent_manager.get_agent_status(agent_id)
    assert state.status == AgentStatus.RUNNING

@pytest.mark.asyncio
async def test_destroy_agent(agent_manager, sample_config):
    """测试销毁Agent"""
    agent_id = await agent_manager.create_agent(sample_config)
    
    assert agent_id in agent_manager.agents
    assert agent_id in agent_manager.states
    
    # 销毁
    result = await agent_manager.destroy_agent(agent_id)
    assert result is True
    
    assert agent_id not in agent_manager.agents
    assert agent_id not in agent_manager.states
    assert agent_id not in agent_manager.tasks

@pytest.mark.asyncio
async def test_list_agents(agent_manager, sample_config):
    """测试列出Agent"""
    # 创建多个Agent
    configs = []
    for i in range(3):
        config = AgentConfig(
            agent_id=f"test_agent_{i:03d}",
            name=f"测试Agent{i}",
            description=f"测试Agent{i}的描述"
        )
        configs.append(config)
        await agent_manager.create_agent(config)
    
    # 列出Agent
    agents = await agent_manager.list_agents()
    assert len(agents) == 3
    
    agent_ids = {agent.agent_id for agent in agents}
    expected_ids = {config.agent_id for config in configs}
    assert agent_ids == expected_ids

@pytest.mark.asyncio
async def test_agent_not_found(agent_manager):
    """测试不存在的Agent"""
    state = await agent_manager.get_agent_status("non_existent_agent")
    assert state is None
    
    result = await agent_manager.pause_agent("non_existent_agent")
    assert result is False
    
    result = await agent_manager.resume_agent("non_existent_agent")
    assert result is False
    
    result = await agent_manager.destroy_agent("non_existent_agent")
    assert result is False

def test_agent_config_serialization():
    """测试Agent配置序列化"""
    config = AgentConfig(
        agent_id="test_001",
        name="测试Agent",
        description="描述",
        capabilities=["a", "b", "c"],
        memory_config={"key": "value"},
        planner_config={"enabled": True}
    )
    
    # 检查属性
    assert config.agent_id == "test_001"
    assert config.name == "测试Agent"
    assert config.description == "描述"
    assert config.capabilities == ["a", "b", "c"]
    assert config.memory_config == {"key": "value"}
    assert config.planner_config == {"enabled": True}

def test_agent_state_tracking():
    """测试Agent状态跟踪"""
    from src.kernel.agent_manager import AgentState
    import time
    
    state = AgentState(
        agent_id="test_001",
        status=AgentStatus.RUNNING,
        created_at=time.time(),
        last_active=time.time(),
        memory_usage=1024,
        cpu_usage=25.5,
        error_count=0,
        current_task="test_task"
    )
    
    assert state.agent_id == "test_001"
    assert state.status == AgentStatus.RUNNING
    assert state.memory_usage == 1024
    assert state.cpu_usage == 25.5
    assert state.error_count == 0
    assert state.current_task == "test_task"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
