"""
Agent Loop 状态机测试
"""

import pytest

from src.kernel.agent_loop import (
    Action,
    ActionType,
    AgentLoop,
    AgentLoopConfig,
    LoopState,
    MockModelClient,
    StallDetector,
    ToolExecutor,
)


class _DictTools(ToolExecutor):
    async def execute(self, tool_name, params):
        return {"tool": tool_name, "params": params, "ok": True}

    def list_tools(self):
        return [{"name": "read_file"}, {"name": "write_file"}]


@pytest.mark.asyncio
async def test_complete_loop():
    """测试完整 OTA 循环：工具调用 → 文本完成"""
    script = [
        Action(type=ActionType.TOOL_CALL, tool_name="read_file", tool_params={"path": "a.txt"}),
        Action(type=ActionType.TEXT, text="done"),
    ]
    loop = AgentLoop(
        model=MockModelClient(script), tools=_DictTools(), config=AgentLoopConfig(max_steps=10)
    )
    summary = await loop.run("读取文件")
    assert summary["success"] is True
    assert summary["state"] == LoopState.COMPLETED.value
    assert summary["steps"] == 2


@pytest.mark.asyncio
async def test_max_steps_limit():
    """测试最大步数限制：永不完成时触发保护"""
    script = [Action(type=ActionType.TOOL_CALL, tool_name="read_file", tool_params={})] * 100
    loop = AgentLoop(
        model=MockModelClient(script), tools=_DictTools(), config=AgentLoopConfig(max_steps=3)
    )
    summary = await loop.run("无限循环任务")
    assert summary["success"] is False
    assert summary["steps"] == 3
    assert loop.state == LoopState.ERROR


def test_stall_detector():
    """测试停滞检测"""
    detector = StallDetector(threshold=3)
    assert detector.observe(True) is False  # 有进展
    assert detector.observe(False) is False
    assert detector.observe(False) is False
    assert detector.observe(False) is True  # 连续 3 步无进展 → 停滞
    assert detector.observe(True) is False  # 进展重置计数


def test_parse_action():
    """测试动作解析"""
    loop = AgentLoop(tools=_DictTools())
    # dict 输入
    action = loop._parse_action({"type": "tool_call", "tool_name": "x", "tool_params": {}})
    assert action is not None and action.type == ActionType.TOOL_CALL
    # 字符串输入 → 文本动作
    action = loop._parse_action("完成")
    assert action is not None and action.type == ActionType.TEXT
    # 非法输入
    assert loop._parse_action({"type": "bogus"}) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
