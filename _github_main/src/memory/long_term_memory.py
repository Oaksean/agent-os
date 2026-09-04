"""
长期记忆与情景记忆

参考 Claude Code 的五层记忆体系与 Codex 的上下文管理设计。解决上下文窗口
限制并保持状态一致性：

- 长期记忆 (Long-term)：持久化的用户偏好、项目约束、参考文档等，
  通过语义检索仅加载最相关部分到上下文。
- 情景记忆 (Episodic)：历史行动记录，用于反思学习与经验复用。

本实现不依赖外部向量数据库，采用轻量级的词频-逆文档频率 (TF-IDF) 加权
与余弦相似度进行语义检索，便于离线运行与测试。
"""

from __future__ import annotations

import logging
import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class LongTermMemoryEntry:
    """长期记忆条目"""

    entry_id: str
    content: str
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0
    last_accessed: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "importance": self.importance,
            "tags": self.tags,
            "created_at": self.created_at,
            "access_count": self.access_count,
            "metadata": self.metadata,
        }


@dataclass
class EpisodicMemoryEntry:
    """情景记忆条目（一次行动记录）"""

    episode_id: str
    task: str
    action: str
    outcome: str  # success / failure
    reflection: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "task": self.task,
            "action": self.action,
            "outcome": self.outcome,
            "reflection": self.reflection,
            "created_at": self.created_at,
        }


def _tokenize(text: str) -> List[str]:
    """中文按字符切分 + 英文按词切分的简易分词"""
    tokens: List[str] = []
    # 英文单词
    tokens.extend(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
    # 中文字符（作为 unigram）
    tokens.extend(re.findall(r"[\u4e00-\u9fff]", text))
    return tokens


class _TfIdfIndex:
    """轻量级 TF-IDF 索引 + 余弦相似度检索（无外部依赖）"""

    def __init__(self):
        self.documents: List[Tuple[str, List[str]]] = []  # (entry_id, tokens)
        self.df: Counter = Counter()  # 文档频率

    def add(self, entry_id: str, tokens: List[str]) -> None:
        unique = set(tokens)
        self.documents.append((entry_id, tokens))
        for token in unique:
            self.df[token] += 1

    def remove(self, entry_id: str) -> None:
        for i, (eid, tokens) in enumerate(self.documents):
            if eid == entry_id:
                unique = set(tokens)
                for token in unique:
                    self.df[token] -= 1
                    if self.df[token] <= 0:
                        del self.df[token]
                del self.documents[i]
                return

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """返回 [(entry_id, 相似度)] 按相似度降序"""
        query_tokens = _tokenize(query)
        if not query_tokens or not self.documents:
            return []

        n_docs = len(self.documents)
        query_vec = self._tf_idf_vector(query_tokens, n_docs)
        scores: List[Tuple[str, float]] = []

        for entry_id, tokens in self.documents:
            doc_vec = self._tf_idf_vector(tokens, n_docs)
            sim = self._cosine(query_vec, doc_vec)
            if sim > 0:
                scores.append((entry_id, sim))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _tf_idf_vector(self, tokens: List[str], n_docs: int) -> Dict[str, float]:
        tf = Counter(tokens)
        vec: Dict[str, float] = {}
        for token, count in tf.items():
            idf = math.log((1 + n_docs) / (1 + self.df.get(token, 0))) + 1.0
            vec[token] = count * idf
        return vec

    @staticmethod
    def _cosine(a: Dict[str, float], b: Dict[str, float]) -> float:
        if not a or not b:
            return 0.0
        common = set(a.keys()) & set(b.keys())
        dot = sum(a[t] * b[t] for t in common)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


class LongTermMemory:
    """长期记忆管理器（语义检索）"""

    def __init__(self, max_entries: int = 1000):
        self.max_entries = max_entries
        self.entries: Dict[str, LongTermMemoryEntry] = {}
        self.index = _TfIdfIndex()

    def add(
        self,
        content: str,
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """添加长期记忆条目"""
        import uuid

        entry_id = f"ltm_{uuid.uuid4().hex[:8]}"
        entry = LongTermMemoryEntry(
            entry_id=entry_id,
            content=content,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.entries[entry_id] = entry
        self.index.add(entry_id, _tokenize(content))

        self._enforce_limit()
        return entry_id

    def search(self, query: str, top_k: int = 5) -> List[LongTermMemoryEntry]:
        """语义检索最相关的记忆条目"""
        results = []
        for entry_id, _score in self.index.search(query, top_k):
            entry = self.entries.get(entry_id)
            if entry:
                entry.access_count += 1
                entry.last_accessed = time.time()
                results.append(entry)
        return results

    def search_by_tag(self, tag: str, limit: int = 10) -> List[LongTermMemoryEntry]:
        """按标签检索"""
        return [e for e in self.entries.values() if tag in e.tags][:limit]

    def get(self, entry_id: str) -> Optional[LongTermMemoryEntry]:
        entry = self.entries.get(entry_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed = time.time()
        return entry

    def delete(self, entry_id: str) -> bool:
        if entry_id in self.entries:
            del self.entries[entry_id]
            self.index.remove(entry_id)
            return True
        return False

    def forget_low_importance(self, threshold: float = 0.2) -> int:
        """选择性遗忘：删除重要性低于阈值且长期未访问的条目"""
        removed = 0
        for entry_id in list(self.entries.keys()):
            entry = self.entries[entry_id]
            if entry.importance < threshold:
                self.delete(entry_id)
                removed += 1
        logger.info(f"选择性遗忘：删除 {removed} 条低重要性记忆")
        return removed

    def _enforce_limit(self) -> None:
        if len(self.entries) <= self.max_entries:
            return
        # 按重要性 + 访问次数排序，删除最不重要的
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.importance, e.access_count),
        )
        excess = len(self.entries) - self.max_entries
        for entry in sorted_entries[:excess]:
            self.delete(entry.entry_id)

    def summary(self) -> Dict[str, Any]:
        return {"total_entries": len(self.entries)}


class EpisodicMemory:
    """情景记忆管理器（历史行动记录，用于反思学习）"""

    def __init__(self, max_episodes: int = 500):
        self.max_episodes = max_episodes
        self.episodes: List[EpisodicMemoryEntry] = []

    def record(self, task: str, action: str, outcome: str, reflection: str = "") -> str:
        """记录一次行动"""
        import uuid

        episode_id = f"ep_{uuid.uuid4().hex[:8]}"
        self.episodes.append(
            EpisodicMemoryEntry(
                episode_id=episode_id,
                task=task,
                action=action,
                outcome=outcome,
                reflection=reflection,
            )
        )
        if len(self.episodes) > self.max_episodes:
            self.episodes = self.episodes[-self.max_episodes :]
        return episode_id

    def retrieve_similar(self, task: str, top_k: int = 3) -> List[EpisodicMemoryEntry]:
        """检索与当前任务相似的历史情景（用于经验复用）"""
        query_tokens = set(_tokenize(task))
        if not query_tokens:
            return []
        scored: List[Tuple[float, EpisodicMemoryEntry]] = []
        for ep in self.episodes:
            ep_tokens = set(_tokenize(ep.task + " " + ep.action))
            overlap = len(query_tokens & ep_tokens) / max(1, len(query_tokens))
            if overlap > 0:
                scored.append((overlap, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def reflect(self) -> List[str]:
        """反思：从失败情景中提取经验教训"""
        lessons = []
        for ep in self.episodes:
            if ep.outcome == "failure":
                lessons.append(f"[{ep.task}] {ep.reflection or ep.action}")
        return lessons[-10:]

    def summary(self) -> Dict[str, Any]:
        success = sum(1 for e in self.episodes if e.outcome == "success")
        failure = sum(1 for e in self.episodes if e.outcome == "failure")
        return {"total": len(self.episodes), "success": success, "failure": failure}


# ==================== 演示 ====================

def demo():
    """演示长期记忆的语义检索与情景记忆的反思"""
    ltm = LongTermMemory()

    ltm.add("用户偏好使用 Python 进行 AI 开发", importance=0.8, tags=["preference"])
    ltm.add("项目使用 FastAPI 作为 Web 框架", importance=0.7, tags=["stack"])
    ltm.add("数据库采用 PostgreSQL 存储关系数据", importance=0.6, tags=["stack"])
    ltm.add("用户喜欢简洁的代码风格，避免过度设计", importance=0.7, tags=["preference"])

    print("=== 语义检索：查询 '用什么语言开发' ===")
    for entry in ltm.search("用什么语言开发"):
        print(f"  [{entry.importance}] {entry.content}")

    print("\n=== 语义检索：查询 '数据库技术栈' ===")
    for entry in ltm.search("数据库技术栈"):
        print(f"  [{entry.importance}] {entry.content}")

    print("\n=== 情景记忆 ===")
    ep = EpisodicMemory()
    ep.record("部署服务", "使用 docker-compose up", "success", "一次成功")
    ep.record("连接数据库", "直接用明文密码", "failure", "应使用环境变量管理密钥")
    ep.record("调用第三方API", "未做超时处理", "failure", "应设置超时与重试")

    print(f"统计: {ep.summary()}")
    print("反思经验教训:")
    for lesson in ep.reflect():
        print(f"  - {lesson}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo()
