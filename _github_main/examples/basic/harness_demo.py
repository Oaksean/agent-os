"""
Agent Harness 端到端演示

将本仓库实现的 Harness 核心机制串成一个完整可运行的工作流：

    Agent Loop（OTA 状态机）
      ├── Guardrails（分级审批 + Overlay 文件系统）
      ├── TurnDiffTracker（文件变更跟踪）
      ├── ContextBuilder（缓存友好上下文）
      ├── LongTermMemory（长期记忆 + 语义检索）
      └── ToolExecutor（工具执行）

演示一个「读取 → 修改 → 执行命令 → 沉淀记忆」的自主任务流程。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# 将项目根加入 sys.path，便于直接运行
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.kernel.agent_loop import (  # noqa: E402
    Action,
    ActionType,
    AgentLoop,
    AgentLoopConfig,
    LoopState,
    MockModelClient,
    ToolExecutor,
)
from src.prompts.context_builder import ContextBuilder  # noqa: E402
from src.security.guardrails import ApprovalLevel, Guardrails, OverlayFS  # noqa: E402
from src.tools.diff_tracker import TurnDiffTracker  # noqa: E402
from src.memory.long_term_memory import LongTermMemory  # noqa: E402


class HarnessToolExecutor(ToolExecutor):
    """真实执行文件与命令的工具，串联护栏与差异跟踪"""

    def __init__(self, workspace: str, guardrails: Guardrails, overlay: OverlayFS, tracker: TurnDiffTracker):
        self.workspace = workspace
        self.guardrails = guardrails
        self.overlay = overlay
        self.tracker = tracker
        self.audit: list = []

    async def execute(self, tool_name, params):
        if tool_name == "read_file":
            return self._read(params["path"])
        if tool_name == "write_file":
            return self._write(params["path"], params["content"])
        if tool_name == "run_command":
            return self._run(params["command"])
        raise KeyError(f"未知工具: {tool_name}")

    def list_tools(self):
        return [
            {"name": "read_file", "description": "读取工作区文件"},
            {"name": "write_file", "description": "写入工作区文件（需审批）"},
            {"name": "run_command", "description": "执行 Shell 命令（需风险评估）"},
        ]

    def _read(self, path):
        abs_path = os.path.join(self.workspace, path)
        if not os.path.exists(abs_path):
            return {"ok": False, "error": "文件不存在"}
        with open(abs_path, encoding="utf-8") as f:
            return {"ok": True, "content": f.read()}

    def _write(self, path, content):
        # 护栏：文件写入风险评估
        assessment = self.guardrails.assess_file_write(path)
        if assessment.approval == ApprovalLevel.FORBIDDEN:
            return {"ok": False, "error": f"禁止写入: {assessment.reason}"}
        # 先写 Overlay，再跟踪基线
        self.tracker.snapshot_baseline(path)
        self.overlay.write(path, content)
        self.audit.append(("write_file", assessment))
        return {"ok": True, "staged": True, "risk": assessment.risk.value}

    def _run(self, command):
        assessment = self.guardrails.assess_command(command)
        self.audit.append(("run_command", assessment))
        if assessment.approval == ApprovalLevel.FORBIDDEN:
            return {"ok": False, "error": f"禁止执行: {assessment.reason}"}
        if assessment.approval == ApprovalLevel.INTERACTIVE:
            # 演示中自动批准，真实环境应由用户在 WAITING_APPROVAL 态裁决
            return {"ok": True, "simulated": True, "risk": assessment.risk.value}
        return {"ok": True, "simulated": True, "risk": assessment.risk.value}


async def main():
    workspace = tempfile.mkdtemp(prefix="harness_demo_")
    # 初始文件
    with open(os.path.join(workspace, "README.md"), "w", encoding="utf-8") as f:
        f.write("# 初始项目\n")

    guardrails = Guardrails()
    overlay = OverlayFS(workspace)
    tracker = TurnDiffTracker(root=workspace)
    ltm = LongTermMemory()
    context = ContextBuilder()

    tools = HarnessToolExecutor(workspace, guardrails, overlay, tracker)

    # 预置模型「剧本」：读 → 写 → 跑命令 → 完成
    script = [
        Action(type=ActionType.TOOL_CALL, tool_name="read_file", tool_params={"path": "README.md"}),
        Action(type=ActionType.TOOL_CALL, tool_name="write_file", tool_params={"path": "app.py", "content": "print('hello agent-os')\n"}),
        Action(type=ActionType.TOOL_CALL, tool_name="run_command", tool_params={"command": "python app.py"}),
        Action(type=ActionType.TEXT, text="任务完成"),
    ]

    loop = AgentLoop(
        model=MockModelClient(script),
        tools=tools,
        config=AgentLoopConfig(max_steps=10, stall_threshold=5),
    )

    print("=" * 60)
    print("Agent Harness 端到端演示")
    print("=" * 60)

    # 注入长期记忆与上下文
    ltm.add("项目使用 Python 开发", importance=0.8, tags=["stack"])
    context.set_system_prompt("你是 Agent OS 智能体内核")
    context.set_tool_definitions(tools.list_tools())
    context.inject_long_term_context([e.content for e in ltm.search("Python 开发")])

    # 运行 Agent Loop
    summary = await loop.run("读取项目并生成 app.py")

    print(f"\n[Agent Loop] 状态: {summary['state']}  步数: {summary['steps']}  成功: {summary['success']}")

    print("\n[护栏审计]")
    for action, assessment in tools.audit:
        print(f"  {action}: risk={assessment.risk.value}, approval={assessment.approval.value}")

    # 提交 Overlay（把暂存写入真实文件）
    committed = overlay.commit()
    print(f"\n[OverlayFS] 已提交 {committed} 个文件到工作区")

    # 提交后再计算 diff：此时磁盘状态已反映真实变更
    print("\n[文件变更 (TurnDiffTracker)]")
    for change in tracker.compute_diff():
        print(f"  [{change.change_type.value}] {change.path}")

    # 上下文构建结果
    print("\n[上下文构建] 消息数量:", len(context.build()))

    print("\n" + "=" * 60)
    print("演示完成。核心机制：Agent Loop + Guardrails + DiffTracker + Context + Memory 已串联")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
