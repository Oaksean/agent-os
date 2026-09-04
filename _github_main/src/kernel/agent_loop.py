"""
Agent Loop —— Agent Harness 的核心循环

参考 OpenAI Codex Harness / Claude Code 的 Agent Runtime 设计，实现一个
高度鲁棒的「观察-思考-行动」(Observe-Think-Act, OTA) 闭环控制。

它并非简单的 `while True` 调用模型，而是一个基于有限状态机 (FSM) 的
复杂流转：

状态机（五态模型 + 终态）：
    IDLE            空闲，等待任务输入
    PLANNING        规划，分解子目标，构建初始上下文
    EXECUTING       执行，调用工具（Shell/File/Web 等）
    WAITING_APPROVAL 待审批，遇到高危操作，暂停并等待用户/策略裁决
    COMPLETED       任务完成（终态）
    ERROR           错误（终态，可带恢复信息）

鲁棒性机制：
    - 最大步数限制 (Max Steps)：防止陷入无限递归或无效尝试
    - 停滞检测 (Stall Detection)：连续 N 步无实质进展则强制中断
    - 指数退避重试 (Exponential Backoff)：API/网络错误按退避策略重试
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class LoopState(Enum):
    """Agent Loop 有限状态机的状态集合"""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    ERROR = "error"


class ActionType(Enum):
    """动作类型（对应不同的工具调用）"""

    TEXT = "text"  # 纯文本回复（任务完成）
    TOOL_CALL = "tool_call"  # 调用工具
    REQUEST_APPROVAL = "request_approval"  # 请求审批


@dataclass
class Action:
    """一次「行动」—— 模型意图的解析结果"""

    type: ActionType
    tool_name: str = ""
    tool_params: Dict[str, Any] = field(default_factory=dict)
    text: str = ""
    approval_request: Optional[Dict[str, Any]] = None


@dataclass
class Step:
    """一次循环迭代的完整记录（用于审计、停滞检测与恢复）"""

    step_id: str
    index: int
    observation: str = ""
    thought: str = ""
    action: Optional[Action] = None
    result: Any = None
    error: Optional[str] = None
    progress_made: bool = False
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None

    @property
    def duration(self) -> float:
        """本步耗时（秒）"""
        if self.finished_at is None:
            return time.time() - self.started_at
        return self.finished_at - self.started_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "index": self.index,
            "observation": self.observation,
            "thought": self.thought,
            "action": self.action.__dict__ if self.action else None,
            "result": self.result,
            "error": self.error,
            "progress_made": self.progress_made,
            "duration": self.duration,
        }


class StallDetector:
    """停滞检测器 —— 连续 N 步无实质进展则判定为停滞"""

    def __init__(self, threshold: int = 5):
        self.threshold = threshold
        self._no_progress_steps = 0

    def observe(self, progress_made: bool) -> bool:
        """
        记录一步是否有进展，返回是否已停滞。

        Args:
            progress_made: 本步是否产生了实质进展（文件变更、新信息等）

        Returns:
            若连续 threshold 步无进展返回 True
        """
        if progress_made:
            self._no_progress_steps = 0
        else:
            self._no_progress_steps += 1
        return self._no_progress_steps >= self.threshold

    def reset(self) -> None:
        self._no_progress_steps = 0

    @property
    def no_progress_steps(self) -> int:
        return self._no_progress_steps


class ExponentialBackoff:
    """指数退避重试 —— 用于 API/网络等临时错误"""

    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, factor: float = 2.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.factor = factor
        self._attempt = 0

    def reset(self) -> None:
        self._attempt = 0

    def next_delay(self) -> float:
        """计算下一次重试前的等待秒数（指数增长，封顶）"""
        delay = min(self.base_delay * (self.factor ** self._attempt), self.max_delay)
        self._attempt += 1
        return delay

    @property
    def attempts(self) -> int:
        return self._attempt


@dataclass
class AgentLoopConfig:
    """Agent Loop 运行配置"""

    max_steps: int = 50  # 最大步数限制，防止无限循环
    stall_threshold: int = 5  # 连续无进展步数阈值
    max_retries: int = 3  # 单步最大重试次数
    backoff_base: float = 1.0  # 退避基础延迟（秒）
    backoff_max: float = 30.0  # 退避最大延迟（秒）
    step_timeout: float = 60.0  # 单步执行超时（秒）
    auto_approve: bool = False  # 是否自动批准（生产环境应关闭）


class ToolExecutor(ABC):
    """
    工具执行器接口 —— Agent Loop 通过它执行工具。

    具体实现可对接 ToolRegistry、沙箱、MCP 客户端等。
    """

    @abstractmethod
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """执行工具并返回结果"""
        ...

    @abstractmethod
    def list_tools(self) -> List[Dict[str, Any]]:
        """返回可用工具列表（供模型参考）"""
        ...


class ModelClient(ABC):
    """
    模型客户端接口 —— Agent Loop 通过它调用大模型推理。

    默认提供一个 MockModelClient 用于离线演示。
    """

    @abstractmethod
    async def reason(
        self, goal: str, observation: str, history: List[Step], tools: List[Dict[str, Any]]
    ) -> Action:
        """
        根据目标、观察和历史，推理出下一步行动。

        Returns:
            解析后的 Action 对象
        """
        ...


class ApprovalHandler(ABC):
    """
    审批处理器接口 —— 高危操作在 WAITING_APPROVAL 态暂停，
    交由该处理器裁决（人机协作 Human-in-the-Loop）。
    """

    @abstractmethod
    async def approve(self, action: Action, context: Dict[str, Any]) -> bool:
        """返回是否批准该动作"""
        ...


class AutoApprovalHandler(ApprovalHandler):
    """自动审批（仅用于演示/测试，生产环境应替换为交互式审批）"""

    async def approve(self, action: Action, context: Dict[str, Any]) -> bool:
        return True


class MockModelClient(ModelClient):
    """
    离线演示用的模型客户端 —— 依据规则模拟推理，不依赖真实 LLM。

    真实环境中应替换为调用 OpenAI/Anthropic/本地模型的实现。
    """

    def __init__(self, steps: Optional[List[Action]] = None):
        # 预置的「剧本」动作序列，用于确定性演示
        self._script = steps or []
        self._cursor = 0

    async def reason(
        self, goal: str, observation: str, history: List[Step], tools: List[Dict[str, Any]]
    ) -> Action:
        if self._cursor < len(self._script):
            action = self._script[self._cursor]
            self._cursor += 1
            return action
        # 剧本耗尽 → 返回完成动作
        return Action(type=ActionType.TEXT, text=f"已完成目标：{goal}")


class AgentLoop:
    """
    Agent Loop —— 智能体运行时的心脏。

    以状态机方式驱动 OTA 循环：观察 → 思考 → 行动 → 验证 → 更新上下文，
    直到任务完成、被中断或触发最大步数/停滞保护。
    """

    def __init__(
        self,
        model: Optional[ModelClient] = None,
        tools: Optional[ToolExecutor] = None,
        approval: Optional[ApprovalHandler] = None,
        config: Optional[AgentLoopConfig] = None,
    ):
        self.model = model or MockModelClient()
        self.tools = tools or _NoopToolExecutor()
        self.approval = approval or AutoApprovalHandler()
        self.config = config or AgentLoopConfig()

        self.state: LoopState = LoopState.IDLE
        self.steps: List[Step] = []
        self.stall_detector = StallDetector(self.config.stall_threshold)
        self.backoff = ExponentialBackoff(self.config.backoff_base, self.config.backoff_max)

        # 工作记忆：循环内的易失状态
        self.working_context: Dict[str, Any] = {}
        # 观测累积：追加式历史（缓存友好）
        self.observations: List[str] = []

    # ==================== 主循环 ====================

    async def run(self, goal: str, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        运行 Agent Loop，执行一个目标。

        Args:
            goal: 任务目标（自然语言描述）
            initial_context: 初始上下文（文件树、约束等）

        Returns:
            执行结果摘要（状态、步数、结果、耗时等）
        """
        start = time.time()
        self.state = LoopState.PLANNING
        self.working_context = dict(initial_context or {})
        self.stall_detector.reset()
        self.backoff.reset()

        logger.info(f"Agent Loop 启动：goal={goal!r}")

        try:
            for index in range(1, self.config.max_steps + 1):
                step = await self._run_step(index, goal)

                # 更新停滞检测
                if self.stall_detector.observe(step.progress_made):
                    logger.warning(
                        f"停滞检测触发：连续 {self.stall_detector.no_progress_steps} 步无进展"
                    )
                    self.state = LoopState.ERROR
                    break

                # 终止条件：任务完成
                if step.action and step.action.type == ActionType.TEXT:
                    self.state = LoopState.COMPLETED
                    break

                # 达到最大步数
                if index >= self.config.max_steps:
                    logger.warning(f"达到最大步数限制 {self.config.max_steps}")
                    self.state = LoopState.ERROR
                    break

        except asyncio.CancelledError:
            self.state = LoopState.ERROR
            logger.info("Agent Loop 被用户中断")
            raise
        except Exception as exc:  # noqa: BLE001
            self.state = LoopState.ERROR
            logger.error(f"Agent Loop 异常终止：{exc}")

        return self._build_summary(goal, time.time() - start)

    async def _run_step(self, index: int, goal: str) -> Step:
        """执行单步 OTA 循环（含指数退避重试）"""
        step = Step(step_id=f"step_{uuid.uuid4().hex[:8]}", index=index)

        self.state = LoopState.EXECUTING

        # 1. 观察 (Observe)
        step.observation = self._observe()
        self.observations.append(step.observation)

        # 2. 思考 (Think) —— 带退避重试
        step.thought = await self._retry(
            lambda: self.model.reason(
                goal, step.observation, self.steps, self.tools.list_tools()
            )
        )
        step.action = self._parse_action(step.thought)
        if step.action is None:
            step.error = "模型未返回有效动作"
            self._finalize_step(step, progress=False)
            return step

        # 3. 行动 (Act) —— 高危操作先进入待审批态
        if step.action.type == ActionType.REQUEST_APPROVAL or (
            step.action.type == ActionType.TOOL_CALL and not self.config.auto_approve
        ):
            self.state = LoopState.WAITING_APPROVAL
            approved = await self.approval.approve(step.action, self.working_context)
            if not approved:
                step.result = "用户拒绝执行该动作"
                self._finalize_step(step, progress=False)
                return step

        # 4. 执行 + 验证 (Act + Verify)
        try:
            step.result = await asyncio.wait_for(
                self._act(step.action), timeout=self.config.step_timeout
            )
            step.progress_made = self._verify_progress(step)
        except asyncio.TimeoutError:
            step.error = f"执行超时（>{self.config.step_timeout}s）"
            step.progress_made = False
        except Exception as exc:  # noqa: BLE001
            step.error = str(exc)
            step.progress_made = False

        # 5. 更新上下文 (Update Context)
        self._update_context(step)

        self._finalize_step(step, progress=step.progress_made)
        return step

    # ==================== OTA 各环节 ====================

    def _observe(self) -> str:
        """观察：汇总当前环境状态（工作上下文 + 已有历史摘要）"""
        parts = []
        for key, value in self.working_context.items():
            parts.append(f"{key}: {value}")
        # 附带最近几步的简要回顾，避免上下文漂移
        if self.steps:
            recent = self.steps[-3:]
            parts.append(
                "最近进展: " + "; ".join(str(s.result or s.error or "") for s in recent)
            )
        return "\n".join(parts) if parts else "(空)"

    async def _act(self, action: Action) -> Any:
        """行动：执行工具调用或返回文本"""
        if action.type == ActionType.TEXT:
            return action.text
        if action.type == ActionType.TOOL_CALL:
            return await self.tools.execute(action.tool_name, action.tool_params)
        return None

    def _verify_progress(self, step: Step) -> bool:
        """验证：判断本步是否产生实质进展（用于停滞检测）"""
        # 文本回复视为「任务完成」而非中间进展
        if step.action and step.action.type == ActionType.TEXT:
            return True
        # 工具执行无错误即视为有进展（可进一步细化：如对比文件 diff）
        return step.error is None and step.result is not None

    def _update_context(self, step: Step) -> None:
        """更新上下文：把本步结果写入易失工作上下文"""
        self.working_context[f"step_{step.index}_result"] = step.result or step.error

    def _parse_action(self, thought: Any) -> Optional[Action]:
        """解析模型输出为 Action（模型可直接返回 Action 或 dict）"""
        if isinstance(thought, Action):
            return thought
        if isinstance(thought, dict):
            try:
                return Action(
                    type=ActionType(thought.get("type", "text")),
                    tool_name=thought.get("tool_name", ""),
                    tool_params=thought.get("tool_params", {}),
                    text=thought.get("text", ""),
                    approval_request=thought.get("approval_request"),
                )
            except ValueError:
                return None
        if isinstance(thought, str):
            return Action(type=ActionType.TEXT, text=thought)
        return None

    async def _retry(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        """带指数退避地重试执行某个可等待函数"""
        last_exc: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                return await fn()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt >= self.config.max_retries:
                    break
                delay = self.backoff.next_delay()
                logger.warning(f"第 {attempt + 1} 次失败：{exc}，{delay:.1f}s 后重试")
                await asyncio.sleep(delay)
        raise last_exc if last_exc else RuntimeError("重试耗尽")

    def _finalize_step(self, step: Step, progress: bool) -> None:
        step.progress_made = progress
        step.finished_at = time.time()
        self.steps.append(step)
        self.state = LoopState.IDLE

    # ==================== 辅助 ====================

    def interrupt(self) -> None:
        """外部中断标记（供调用方在并发场景下取消）"""
        self.state = LoopState.ERROR

    def _build_summary(self, goal: str, elapsed: float) -> Dict[str, Any]:
        return {
            "goal": goal,
            "state": self.state.value,
            "steps": len(self.steps),
            "elapsed_seconds": round(elapsed, 3),
            "success": self.state == LoopState.COMPLETED,
            "final_result": self.steps[-1].result if self.steps else None,
            "error": self.steps[-1].error if self.steps else None,
            "history": [s.to_dict() for s in self.steps],
        }


class _NoopToolExecutor(ToolExecutor):
    """空工具执行器（无工具时使用）"""

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        raise RuntimeError(f"工具不存在：{tool_name}")

    def list_tools(self) -> List[Dict[str, Any]]:
        return []


# ==================== 演示 ====================

async def demo():
    """离线演示 Agent Loop 的完整运行"""

    # 预置「剧本」：先调用工具，再返回文本完成
    script = [
        Action(
            type=ActionType.TOOL_CALL,
            tool_name="read_file",
            tool_params={"path": "README.md"},
        ),
        Action(
            type=ActionType.TOOL_CALL,
            tool_name="write_file",
            tool_params={"path": "out.txt", "content": "done"},
        ),
        Action(type=ActionType.TEXT, text="任务完成"),
    ]

    class DictTools(ToolExecutor):
        async def execute(self, tool_name, params):
            return {"tool": tool_name, "params": params, "ok": True}

        def list_tools(self):
            return [
                {"name": "read_file", "description": "读取文件"},
                {"name": "write_file", "description": "写入文件"},
            ]

    loop = AgentLoop(
        model=MockModelClient(script),
        tools=DictTools(),
        config=AgentLoopConfig(max_steps=10, stall_threshold=5),
    )
    summary = await loop.run("读取并处理 README")
    print("=== Agent Loop 演示结果 ===")
    print(f"状态: {summary['state']}")
    print(f"步数: {summary['steps']}")
    print(f"成功: {summary['success']}")
    print(f"最终结果: {summary['final_result']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(demo())
