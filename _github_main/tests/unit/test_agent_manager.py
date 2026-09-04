"""
Agent管理器测试（对齐 src/kernel/agent_manager.py 的真实 API）
"""

import pytest

from src.kernel.agent_manager import (
    AgentManager,
    AgentConfig,
    AgentStatus,
    AgentCapability,
    AgentState,
)


@pytest.fixture
def agent_manager(tmp_path):
    """使用临时状态文件，避免污染仓库目录"""
    return AgentManager(config={"state_file": str(tmp_path / "agents.json")})


@pytest.fixture
def sample_config():
    """示例配置"""
    return AgentConfig(
        name="测试Agent",
        description="用于测试的Agent",
        capabilities=[AgentCapability.PLANNING, AgentCapability.MEMORY_MANAGEMENT],
        memory_config={"max_size": 100},
    )


def test_create_agent(agent_manager, sample_config):
    """测试创建Agent"""
    agent_id = agent_manager.create_agent(sample_config)

    assert agent_id.startswith("agent_")
    assert agent_id in agent_manager.agents

    state = agent_manager.get_agent(agent_id)
    assert state is not None
    assert state.agent_id == agent_id
    assert state.status == AgentStatus.CREATED


def test_get_and_list_agents(agent_manager, sample_config):
    """测试获取与列出Agent"""
    created = []
    for i in range(3):
        config = AgentConfig(name=f"测试Agent{i}", description=f"描述{i}")
        created.append(agent_manager.create_agent(config))

    agents = agent_manager.list_agents()
    assert len(agents) == 3

    ids = {a.agent_id for a in agents}
    assert ids == set(created)

    # 状态过滤
    ready = agent_manager.list_agents(status_filter=AgentStatus.READY)
    assert ready == []


def test_agent_not_found(agent_manager):
    """测试不存在的Agent"""
    assert agent_manager.get_agent("non_existent") is None
    assert agent_manager.delete_agent("non_existent") is False


def test_delete_agent(agent_manager, sample_config):
    """测试删除Agent"""
    agent_id = agent_manager.create_agent(sample_config)
    assert agent_id in agent_manager.agents

    result = agent_manager.delete_agent(agent_id)
    assert result is True
    assert agent_id not in agent_manager.agents


@pytest.mark.asyncio
async def test_pause_and_resume_agent(agent_manager, sample_config):
    """测试暂停与恢复Agent"""
    agent_id = agent_manager.create_agent(sample_config)

    # 初始化到 READY
    ok = await agent_manager.initialize_agent(agent_id)
    assert ok is True
    assert agent_manager.get_agent(agent_id).status == AgentStatus.READY

    # 启动
    ok = await agent_manager.start_agent(agent_id, {"goal": "test"})
    assert ok is True
    assert agent_manager.get_agent(agent_id).status == AgentStatus.RUNNING

    # 暂停
    result = await agent_manager.pause_agent(agent_id)
    assert result is True
    assert agent_manager.get_agent(agent_id).status == AgentStatus.PAUSED

    # 恢复
    result = await agent_manager.resume_agent(agent_id)
    assert result is True
    assert agent_manager.get_agent(agent_id).status == AgentStatus.READY


@pytest.mark.asyncio
async def test_stop_agent(agent_manager, sample_config):
    """测试停止Agent"""
    agent_id = agent_manager.create_agent(sample_config)
    await agent_manager.initialize_agent(agent_id)

    result = await agent_manager.stop_agent(agent_id)
    assert result is True
    assert agent_manager.get_agent(agent_id).status == AgentStatus.STOPPED


def test_agent_config_fields(sample_config):
    """测试AgentConfig字段"""
    assert sample_config.name == "测试Agent"
    assert sample_config.description == "用于测试的Agent"
    assert sample_config.memory_config == {"max_size": 100}


def test_agent_state_serialization(sample_config):
    """测试AgentState序列化往返"""
    import datetime

    state = AgentState(
        agent_id="test_001",
        config=sample_config,
        status=AgentStatus.CREATED,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now(),
        current_task=None,
    )

    data = state.to_dict()
    assert data["agent_id"] == "test_001"
    assert data["status"] == "created"
    assert data["config"]["name"] == "测试Agent"

    restored = AgentState.from_dict(data)
    assert restored.agent_id == "test_001"
    assert restored.status == AgentStatus.CREATED
    assert restored.config.name == "测试Agent"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
