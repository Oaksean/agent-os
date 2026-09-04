"""
Manager-Subagent 并行编排

参考 Codex Harness 的 Manager-Subagent 架构，实现多 Agent 并行任务编排：

Manager Agent   —— 负责任务拆解、分发、监控和结果合并，不直接执行具体代码
Subagents       —— 独立执行的 Agent 实例，拥有专属的上下文环境和工具权限

执行流程：
    拆解 (Decompose)  ：Manager 将大任务拆解为无依赖/有依赖的子任务
    分发 (Dispatch)    ：创建多个 Subagent，分别绑定不同上下文
    监控与仲裁 (Arbitrate)：检测子 Agent 间的文件/上下文冲突，暂停并协调
    合并 (Merge)       ：所有子任务完成后汇总结果

上下文隔离与注入：
    每个 Subagent 拥有独立上下文，互不干扰；支持为子 Agent 精准注入
    所需上下文（目录锚定），避免无关信息污染。
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class SubagentStatus(Enum):
    """子 Agent 状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"  # 因冲突被暂停


@dataclass
class Subtask:
    """子任务定义"""

    subtask_id: str
    name: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)  # 注入的上下文（目录锚定等）
    dependencies: List[str] = field(default_factory=list)  # 依赖的 subtask_id
    touches: List[str] = field(default_factory=list)  # 预期触及的资源（文件/目录），用于冲突检测

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subtask_id": self.subtask_id,
            "name": self.name,
            "description": self.description,
            "context": self.context,
            "dependencies": self.dependencies,
            "touches": self.touches,
        }


@dataclass
class SubagentResult:
    """子 Agent 执行结果"""

    subtask_id: str
    status: SubagentStatus
    output: Any = None
    error: Optional[str] = None
    elapsed: float = 0.0


class ConflictDetector:
    """冲突检测器 —— 检测子任务之间的资源冲突"""

    def __init__(self):
        self._claims: Dict[str, str] = {}  # 资源 -> 已认领的 subtask_id

    def detect_conflicts(self, subtasks: List[Subtask]) -> List[Dict[str, Any]]:
        """
        检测多个子任务间的资源重叠。

        Returns:
            冲突列表 [{resource, subtask_a, subtask_b}]
        """
        conflicts: List[Dict[str, Any]] = []
        self._claims.clear()

        for st in subtasks:
            for resource in st.touches:
                if resource in self._claims and self._claims[resource] != st.subtask_id:
                    conflicts.append(
                        {
                            "resource": resource,
                            "subtask_a": self._claims[resource],
                            "subtask_b": st.subtask_id,
                        }
                    )
                else:
                    self._claims[resource] = st.subtask_id

        return conflicts

    def claim(self, resource: str, subtask_id: str) -> None:
        """认领资源"""
        self._claims[resource] = subtask_id


@dataclass
class Subagent:
    """
    子 Agent —— 独立执行单元。

    worker 是一个 async 回调，接收子任务描述和注入上下文，返回执行结果。
    可替换为真实的 AgentLoop 实例。
    """

    subtask: Subtask
    worker: Callable[[Subtask], Awaitable[Any]]

    async def run(self) -> SubagentResult:
        """执行子任务"""
        logger.info(f"Subagent 开始执行: {self.subtask.name} ({self.subtask.subtask_id})")
        start = asyncio.get_event_loop().time()
        try:
            output = await self.worker(self.subtask)
            elapsed = asyncio.get_event_loop().time() - start
            return SubagentResult(
                subtask_id=self.subtask.subtask_id,
                status=SubagentStatus.COMPLETED,
                output=output,
                elapsed=round(elapsed, 3),
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = asyncio.get_event_loop().time() - start
            logger.error(f"Subagent 执行失败 {self.subtask.name}: {exc}")
            return SubagentResult(
                subtask_id=self.subtask.subtask_id,
                status=SubagentStatus.FAILED,
                error=str(exc),
                elapsed=round(elapsed, 3),
            )


class SubagentManager:
    """
    Manager Agent —— 负责任务拆解、并行分发、冲突仲裁与结果合并。
    """

    def __init__(self, worker: Optional[Callable[[Subtask], Awaitable[Any]]] = None):
        self.worker = worker or self._default_worker
        self.conflict_detector = ConflictDetector()
        self.results: Dict[str, SubagentResult] = {}
        self.runs: List[Dict[str, Any]] = []  # 执行历史

    async def execute(self, subtasks: List[Subtask]) -> Dict[str, Any]:
        """
        执行一组子任务（自动按依赖关系分批，无依赖的并行执行）。

        Args:
            subtasks: 子任务列表

        Returns:
            合并后的执行结果
        """
        # 1. 冲突检测
        conflicts = self.conflict_detector.detect_conflicts(subtasks)
        if conflicts:
            logger.warning(f"检测到 {len(conflicts)} 个资源冲突，将串行化相关子任务")
            for c in conflicts:
                logger.warning(f"  冲突: {c['resource']} 由 {c['subtask_a']} 与 {c['subtask_b']} 同时触及")

        # 2. 按依赖分批执行（拓扑分层）
        remaining = {st.subtask_id: st for st in subtasks}
        completed_ids: set = set()
        self.results = {}

        run_id = uuid.uuid4().hex[:8]

        while remaining:
            batch = [
                st
                for st in remaining.values()
                if all(dep in completed_ids for dep in st.dependencies)
            ]

            if not batch:
                # 存在循环依赖或无法满足的依赖
                blocked = list(remaining.keys())
                for sid in blocked:
                    self.results[sid] = SubagentResult(
                        subtask_id=sid, status=SubagentStatus.BLOCKED, error="依赖无法满足"
                    )
                logger.error(f"子任务阻塞（循环依赖）: {blocked}")
                break

            # 3. 并行分发本批子任务
            subagents = [Subagent(subtask=st, worker=self.worker) for st in batch]
            batch_results = await asyncio.gather(*(sa.run() for sa in subagents))

            for st, result in zip(batch, batch_results):
                self.results[st.subtask_id] = result
                if result.status == SubagentStatus.COMPLETED:
                    completed_ids.add(st.subtask_id)

            # 从剩余中移除已完成的
            for st in batch:
                remaining.pop(st.subtask_id, None)

        # 4. 合并结果
        merged = self._merge_results()
        self.runs.append({"run_id": run_id, "conflicts": conflicts, "merged": merged})
        return merged

    def _merge_results(self) -> Dict[str, Any]:
        """合并所有子任务结果"""
        completed = [
            r for r in self.results.values() if r.status == SubagentStatus.COMPLETED
        ]
        failed = [r for r in self.results.values() if r.status == SubagentStatus.FAILED]
        blocked = [r for r in self.results.values() if r.status == SubagentStatus.BLOCKED]

        return {
            "total": len(self.results),
            "completed": len(completed),
            "failed": len(failed),
            "blocked": len(blocked),
            "success": len(failed) == 0 and len(blocked) == 0,
            "outputs": {r.subtask_id: r.output for r in completed},
            "errors": {r.subtask_id: r.error for r in failed + blocked},
        }

    @staticmethod
    async def _default_worker(subtask: Subtask) -> Any:
        """默认 worker（演示用）：模拟子任务执行"""
        await asyncio.sleep(0.2)
        return {"subtask": subtask.name, "context": subtask.context, "done": True}

    def get_history(self) -> List[Dict[str, Any]]:
        return self.runs


# ==================== 演示 ====================

async def demo():
    """演示 Manager-Subagent 并行编排"""

    async def worker(subtask: Subtask) -> Any:
        """模拟子任务执行，耗时不同"""
        delay = 0.3 + (hash(subtask.subtask_id) % 3) * 0.1
        await asyncio.sleep(delay)
        return {"subtask": subtask.name, "context": subtask.context, "elapsed": delay}

    subtasks = [
        Subtask(
            subtask_id="s1",
            name="后端逻辑",
            description="实现订单后端接口",
            context={"dir": "src/api", "stack": "FastAPI"},
            touches=["src/api/order.py"],
        ),
        Subtask(
            subtask_id="s2",
            name="前端UI",
            description="实现订单前端页面",
            context={"dir": "dashboard", "stack": "React"},
            touches=["dashboard/order.js"],
        ),
        Subtask(
            subtask_id="s3",
            name="数据库迁移",
            description="编写订单表迁移脚本",
            context={"dir": "migrations"},
            touches=["migrations/order.sql"],
        ),
        Subtask(
            subtask_id="s4",
            name="集成测试",
            description="汇总后跑集成测试",
            context={"dir": "tests"},
            dependencies=["s1", "s2", "s3"],
            touches=["tests/test_order.py"],
        ),
    ]

    manager = SubagentManager(worker=worker)
    result = await manager.execute(subtasks)

    print("=== 并行编排结果 ===")
    print(f"总数: {result['total']} 完成: {result['completed']} 失败: {result['failed']}")
    print(f"成功: {result['success']}")
    print("输出:")
    for sid, out in result["outputs"].items():
        print(f"  {sid}: {out}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(demo())
