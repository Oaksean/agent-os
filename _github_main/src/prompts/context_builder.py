"""
缓存友好型上下文构建器

参考 Claude Code / Codex Harness 的「上下文工程」设计。工业级 Agent 与
普通 Demo 的关键区别，在于对 Token 效率与缓存命中率的极致重视：

1. 静态前缀 (Static Prefix)
   将系统指令、工具定义等不变部分固定放在 Prompt 头部，确保这部分
   始终命中 LLM 提供商的缓存，降低延迟与成本。

2. 追加式历史 (Append-only History)
   对话历史以追加方式处理，避免中间插入导致的整体重算（破坏缓存）。

3. 易失状态分离 (Volatile State Separation)
   将频繁变化的运行时状态（审批策略、临时变量、进度）从 Prompt 中剥离，
   由 Harness 在本地内存管理，仅在必要时通过少量 Token 注入。

4. 多级记忆注入
   构建时按需注入工作记忆与长期记忆检索结果，避免无关信息污染上下文。
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    """消息角色"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    """上下文消息"""

    role: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"role": self.role, "content": self.content}

    def __hash__(self) -> int:  # 用于缓存键
        return hash((self.role, self.content))


@dataclass
class ContextBudget:
    """上下文预算配置"""

    max_tokens: int = 8192  # 上下文窗口上限（近似）
    history_reserve_ratio: float = 0.7  # 历史可占用比例
    compact_threshold: float = 0.9  # 触发压缩的占用比例


class ContextBuilder:
    """
    缓存友好型上下文构建器。

    内部维护三段结构：
        static_prefix  —— 固定不变，优先命中缓存
        history        —— 追加式，只在尾部增长
        volatile       —— 易失状态，本地管理，按需注入
    """

    def __init__(self, budget: Optional[ContextBudget] = None):
        self.budget = budget or ContextBudget()

        self._system_prompt: str = ""
        self._tool_definitions: str = ""
        self._static_prefix: str = ""  # 缓存后的静态前缀
        self._static_hash: str = ""  # 静态前缀哈希（用于判断缓存失效）

        self._history: List[Message] = []  # 追加式历史
        self._volatile: Dict[str, str] = {}  # 易失状态（不进前缀）

        self._working_memory: List[str] = []  # 工作记忆注入
        self._long_term_context: List[str] = []  # 长期记忆注入

    # ==================== 静态前缀 ====================

    def set_system_prompt(self, content: str) -> None:
        """设置系统提示词（属于静态前缀）"""
        self._system_prompt = content
        self._invalidate_static()

    def set_tool_definitions(self, tools: List[Dict[str, Any]]) -> None:
        """设置工具定义（属于静态前缀，需保持序列化顺序稳定）"""
        # 按名称排序，保证跨请求的序列化顺序稳定 → 哈希稳定 → 缓存命中
        tools_sorted = sorted(tools, key=lambda t: t.get("name", ""))
        lines = []
        for tool in tools_sorted:
            lines.append(
                f"- {tool.get('name')}: {tool.get('description', '')}"
            )
            params = tool.get("parameters", {})
            if isinstance(params, dict):
                props = params.get("properties", {})
                if props:
                    for pname, pmeta in props.items():
                        lines.append(
                            f"    {pname} ({pmeta.get('type', 'string')}): {pmeta.get('description', '')}"
                        )
        self._tool_definitions = "\n".join(lines)
        self._invalidate_static()

    def _invalidate_static(self) -> None:
        """静态内容变化时重建静态前缀"""
        self._static_prefix = self._system_prompt
        if self._tool_definitions:
            self._static_prefix += "\n\n可用工具：\n" + self._tool_definitions
        self._static_hash = hashlib.md5(self._static_prefix.encode("utf-8")).hexdigest()[:16]

    # ==================== 追加式历史 ====================

    def append(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """追加一条历史消息（仅尾部增长，保证缓存友好）"""
        self._history.append(Message(role=role, content=content, metadata=metadata or {}))

    def clear_history(self) -> None:
        self._history.clear()

    # ==================== 易失状态 ====================

    def set_volatile(self, key: str, value: Any) -> None:
        """设置易失状态（运行时频繁变化的变量，不进静态前缀）"""
        self._volatile[key] = str(value)

    def get_volatile(self, key: str, default: str = "") -> str:
        return self._volatile.get(key, default)

    # ==================== 记忆注入 ====================

    def inject_working_memory(self, items: List[str]) -> None:
        """注入工作记忆摘要（本次任务的待办、关键文件等）"""
        self._working_memory = list(items)

    def inject_long_term_context(self, items: List[str]) -> None:
        """注入长期记忆语义检索结果（用户偏好、项目约束等）"""
        self._long_term_context = list(items)

    # ==================== 构建 ====================

    def build(self, include_volatile: bool = True) -> List[Dict[str, Any]]:
        """
        构建最终消息列表（模型输入）。

        Args:
            include_volatile: 是否在末尾注入易失状态（默认注入，但用少量 Token 表达）

        Returns:
            有序消息列表（system → 记忆 → 历史 → volatile）
        """
        messages: List[Dict[str, Any]] = []

        # 1. 静态前缀（system + 工具定义）—— 缓存命中区
        if self._static_prefix:
            messages.append({"role": MessageRole.SYSTEM.value, "content": self._static_prefix})

        # 2. 记忆注入（长期 + 工作）—— 相对稳定
        memory_lines: List[str] = []
        if self._long_term_context:
            memory_lines.append("【长期记忆】\n" + "\n".join(self._long_term_context))
        if self._working_memory:
            memory_lines.append("【工作记忆】\n" + "\n".join(self._working_memory))
        if memory_lines:
            messages.append(
                {"role": MessageRole.SYSTEM.value, "content": "\n\n".join(memory_lines)}
            )

        # 3. 追加式历史
        for msg in self._history:
            messages.append(msg.to_dict())

        # 4. 易失状态 —— 仅按需注入（少量 Token）
        if include_volatile and self._volatile:
            volatile_text = "; ".join(f"{k}={v}" for k, v in self._volatile.items())
            messages.append(
                {"role": MessageRole.SYSTEM.value, "content": f"【运行时状态】{volatile_text}"}
            )

        return messages

    # ==================== Token 估算与压缩 ====================

    def estimate_tokens(self, text: Optional[str] = None) -> int:
        """近似估算 token 数（英文 ~4 字符/token，中文 ~1.5 字符/token）"""
        target = text if text is not None else self._serialize_all()
        if not target:
            return 0
        # 粗略估算
        return max(1, len(target) // 4)

    def should_compact(self) -> bool:
        """判断是否达到压缩阈值"""
        ratio = self.estimate_tokens() / self.budget.max_tokens
        return ratio >= self.budget.compact_threshold

    def compact(self, keep_last: int = 10) -> str:
        """
        压缩历史：保留最近 keep_last 条，更早的历史生成摘要。

        Returns:
            被压缩部分的摘要文本（供调用方存入长期/摘要记忆）
        """
        if len(self._history) <= keep_last:
            return ""

        overflow = self._history[:-keep_last]
        kept = self._history[-keep_last:]

        # 生成摘要（简化：拼接前若干字符）
        summary_parts = []
        for msg in overflow:
            snippet = msg.content[:120]
            summary_parts.append(f"[{msg.role}] {snippet}")

        self._history = kept
        summary = "历史摘要:\n" + "\n".join(summary_parts)
        logger.info(f"上下文压缩：{len(overflow)} 条历史 → 摘要")
        return summary

    def _serialize_all(self) -> str:
        """序列化全部上下文（用于估算）"""
        parts = [self._static_prefix]
        parts.extend(f"{m.role}:{m.content}" for m in self._history)
        parts.extend(f"{k}={v}" for k, v in self._volatile.items())
        parts.extend(self._working_memory)
        parts.extend(self._long_term_context)
        return "\n".join(parts)

    # ==================== 诊断 ====================

    def cache_info(self) -> Dict[str, Any]:
        """返回缓存相关诊断信息"""
        return {
            "static_hash": self._static_hash,
            "static_prefix_tokens": self.estimate_tokens(self._static_prefix),
            "history_messages": len(self._history),
            "volatile_keys": list(self._volatile.keys()),
            "estimated_total_tokens": self.estimate_tokens(),
            "should_compact": self.should_compact(),
        }


# ==================== 演示 ====================

def demo():
    """演示缓存友好上下文的构建与压缩"""
    builder = ContextBuilder(budget=ContextBudget(max_tokens=2000))

    builder.set_system_prompt("你是 Agent OS 的智能体内核，负责执行用户任务。")
    builder.set_tool_definitions(
        [
            {"name": "read_file", "description": "读取文件", "parameters": {"properties": {"path": {"type": "string"}}}},
            {"name": "write_file", "description": "写入文件", "parameters": {"properties": {"path": {"type": "string"}}}},
        ]
    )

    builder.inject_long_term_context(["用户偏好 Python", "项目位于 /workspace"])
    builder.inject_working_memory(["TODO: 修复登录 bug", "已读取 main.py"])

    builder.append("user", "帮我修复登录模块的 bug")
    builder.append("assistant", "好的，我先读取相关文件。")
    builder.append("tool", "read_file 返回：login.py 内容...")

    builder.set_volatile("current_step", "3")
    builder.set_volatile("approval_mode", "auto")

    print("=== 构建的消息 ===")
    for msg in builder.build():
        role = msg["role"]
        content = msg["content"][:60].replace("\n", " ")
        print(f"[{role}] {content}...")

    print("\n=== 缓存诊断 ===")
    for k, v in builder.cache_info().items():
        print(f"  {k}: {v}")

    print("\n=== 压缩 ===")
    summary = builder.compact(keep_last=1)
    print(f"压缩摘要: {summary[:100]}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo()
