"""
缓存友好上下文构建器 + 长期记忆 + 子 Agent 编排测试
"""

import pytest

from src.prompts.context_builder import ContextBuilder, ContextBudget
from src.memory.long_term_memory import LongTermMemory, EpisodicMemory
from src.communication.subagent import Subtask, SubagentManager


# ==================== ContextBuilder ====================


def test_static_prefix_cache_stable():
    builder = ContextBuilder()
    builder.set_system_prompt("system")
    builder.set_tool_definitions([{"name": "b"}, {"name": "a"}])

    hash1 = builder.cache_info()["static_hash"]
    # 重新设置相同工具（顺序不同）→ 哈希应稳定
    builder.set_tool_definitions([{"name": "a"}, {"name": "b"}])
    hash2 = builder.cache_info()["static_hash"]
    assert hash1 == hash2


def test_append_only_history():
    builder = ContextBuilder()
    builder.append("user", "hello")
    builder.append("assistant", "hi")
    msgs = builder.build()
    # system 前缀 + 2 条历史
    assert len(msgs) >= 2
    assert msgs[-2]["role"] == "user"
    assert msgs[-1]["role"] == "assistant"


def test_volatile_separation():
    builder = ContextBuilder()
    builder.set_system_prompt("system")
    builder.set_volatile("step", "5")
    messages = builder.build()
    # 易失状态应出现在末尾，且不影响静态前缀
    assert "运行时状态" in messages[-1]["content"]


def test_compact_history():
    builder = ContextBuilder()
    for i in range(20):
        builder.append("user", f"message {i}")
    summary = builder.compact(keep_last=5)
    assert "历史摘要" in summary
    # 未设置 system 前缀，build() 仅返回保留的 5 条历史
    assert len(builder.build()) == 5


# ==================== LongTermMemory ====================


def test_semantic_search():
    ltm = LongTermMemory()
    ltm.add("用户偏好 Python 开发", importance=0.9)
    ltm.add("数据库使用 PostgreSQL", importance=0.6)
    results = ltm.search("Python 语言")
    assert results and "Python" in results[0].content


def test_selective_forgetting():
    ltm = LongTermMemory()
    ltm.add("重要记忆", importance=0.9)
    ltm.add("次要记忆", importance=0.1)
    removed = ltm.forget_low_importance(threshold=0.2)
    assert removed == 1
    assert ltm.summary()["total_entries"] == 1


def test_episodic_reflection():
    ep = EpisodicMemory()
    ep.record("任务A", "操作1", "failure", "应加超时")
    ep.record("任务B", "操作2", "success", "")
    lessons = ep.reflect()
    assert len(lessons) == 1
    assert "超时" in lessons[0]


# ==================== SubagentManager ====================


@pytest.mark.asyncio
async def test_parallel_execution_with_dependencies():
    async def worker(subtask: Subtask):
        return {"name": subtask.name}

    subtasks = [
        Subtask(subtask_id="a", name="A", description="", touches=["f1"]),
        Subtask(subtask_id="b", name="B", description="", touches=["f2"]),
        Subtask(subtask_id="c", name="C", description="", dependencies=["a", "b"]),
    ]
    manager = SubagentManager(worker=worker)
    result = await manager.execute(subtasks)
    assert result["success"] is True
    assert result["completed"] == 3


@pytest.mark.asyncio
async def test_conflict_detection():
    async def worker(subtask: Subtask):
        return {"name": subtask.name}

    subtasks = [
        Subtask(subtask_id="a", name="A", description="", touches=["shared.txt"]),
        Subtask(subtask_id="b", name="B", description="", touches=["shared.txt"]),
    ]
    manager = SubagentManager(worker=worker)
    result = await manager.execute(subtasks)
    # 冲突应被检测并记录，但仍完成执行
    assert manager.get_history()
    assert result["completed"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
