"""
记忆巩固器

参考 Claude Code 的「摘要记忆」与「Checkpoint」机制，以及人脑记忆巩固
(Hippocampus → Cortex) 的类比，负责把工作记忆中的关键信息沉淀为长期记忆，
并对历史进行多级压缩、选择性遗忘，防止上下文溢出。

核心能力：
    1. 巩固 (Consolidation)：将高重要性的工作记忆沉淀为长期记忆
    2. 摘要压缩 (Summary Compression)：对历史做多级压缩，优雅退化
    3. 选择性遗忘 (Selective Forgetting)：按重要性 + 访问频次 + 时间衰减淘汰
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationConfig:
    """巩固配置"""

    importance_threshold: float = 0.6  # 高于此重要性的工作记忆才巩固
    min_access_count: int = 2  # 至少被访问过 N 次才巩固
    decay_half_life: float = 86400.0  # 重要性衰减半衰期（秒，默认 24h）
    max_summary_length: int = 500  # 摘要最大长度


def _decayed_importance(importance: float, created_at: float, half_life: float) -> float:
    """按时间衰减的重要性（模拟记忆遗忘曲线）"""
    elapsed = max(0.0, time.time() - created_at)
    decay = 0.5 ** (elapsed / half_life)
    return importance * decay


class MemoryConsolidator:
    """记忆巩固器"""

    def __init__(self, config: Optional[ConsolidationConfig] = None):
        self.config = config or ConsolidationConfig()

    def should_consolidate(self, item: Dict[str, Any]) -> bool:
        """
        判断一条工作记忆是否应被巩固为长期记忆。

        Args:
            item: {"content", "importance", "access_count", "created_at"(可选)}

        Returns:
            是否巩固
        """
        importance = item.get("importance", 0.5)
        access_count = item.get("access_count", 0)
        created_at = item.get("created_at", time.time())

        # 时间衰减后的重要性
        effective = _decayed_importance(importance, created_at, self.config.decay_half_life)

        if effective < self.config.importance_threshold:
            return False
        if access_count < self.config.min_access_count:
            return False
        return True

    def consolidate(
        self, working_items: List[Dict[str, Any]], long_term_memory: Any
    ) -> List[str]:
        """
        把工作记忆中符合条件的高价值条目沉淀到长期记忆。

        Args:
            working_items: 工作记忆条目列表（dict）
            long_term_memory: 长期记忆实例（需有 add(content, importance, ...) 方法）

        Returns:
            已巩固的长期记忆条目 ID 列表
        """
        consolidated_ids: List[str] = []
        for item in working_items:
            if self.should_consolidate(item):
                entry_id = long_term_memory.add(
                    content=item.get("content", ""),
                    importance=item.get("importance", 0.5),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                )
                consolidated_ids.append(entry_id)
        logger.info(f"记忆巩固：{len(consolidated_ids)} 条工作记忆 → 长期记忆")
        return consolidated_ids

    def summarize(self, items: List[Dict[str, Any]], max_length: Optional[int] = None) -> str:
        """
        对一组记忆条目做摘要压缩。

        Args:
            items: 记忆条目列表
            max_length: 摘要最大长度

        Returns:
            压缩后的摘要文本
        """
        max_length = max_length or self.config.max_summary_length
        if not items:
            return ""

        # 按重要性降序，优先保留重要条目
        sorted_items = sorted(items, key=lambda i: i.get("importance", 0), reverse=True)

        parts = []
        for item in sorted_items:
            content = str(item.get("content", ""))
            if len(content) > 120:
                content = content[:117] + "..."
            parts.append(f"- {content}")

        summary = "\n".join(parts)
        if len(summary) > max_length:
            summary = summary[: max_length - 3] + "..."
        return summary

    def forget(self, long_term_memory: Any, threshold: Optional[float] = None) -> int:
        """
        选择性遗忘：淘汰低重要性且衰减后的长期记忆条目。

        Args:
            long_term_memory: 长期记忆实例（需有 forget_low_importance 或 delete 方法）
            threshold: 重要性阈值

        Returns:
            遗忘的条目数量
        """
        threshold = threshold or self.config.importance_threshold
        if hasattr(long_term_memory, "forget_low_importance"):
            return long_term_memory.forget_low_importance(threshold=threshold)
        return 0

    def consolidate_and_summarize(
        self, working_items: List[Dict[str, Any]], long_term_memory: Any
    ) -> Dict[str, Any]:
        """
        一站式：巩固 + 摘要。

        Returns:
            {"consolidated_ids": [...], "summary": "..."}
        """
        consolidated_ids = self.consolidate(working_items, long_term_memory)
        summary = self.summarize(working_items)
        return {"consolidated_ids": consolidated_ids, "summary": summary}


# ==================== 演示 ====================

def demo():
    """演示记忆巩固与摘要压缩"""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.memory.long_term_memory import LongTermMemory

    ltm = LongTermMemory()
    consolidator = MemoryConsolidator(
        ConsolidationConfig(importance_threshold=0.5, min_access_count=1)
    )

    working_items = [
        {"content": "用户偏好 Python，避免过度设计", "importance": 0.9, "access_count": 5},
        {"content": "本次会话打开了 3 个临时文件", "importance": 0.2, "access_count": 1},
        {"content": "项目使用 FastAPI 框架", "importance": 0.8, "access_count": 3},
        {"content": "刚才的报错是端口占用", "importance": 0.3, "access_count": 2},
    ]

    result = consolidator.consolidate_and_summarize(working_items, ltm)

    print("=== 巩固结果 ===")
    print(f"巩固为长期记忆 {len(result['consolidated_ids'])} 条")
    print("长期记忆当前内容:")
    for entry in ltm.search("偏好 框架"):
        print(f"  - {entry.content}")

    print("\n=== 摘要压缩 ===")
    print(result["summary"])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo()
