"""
工作记忆（短期记忆）
负责管理当前会话或任务的上下文
"""

import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import deque
import hashlib
import logging

logger = logging.getLogger(__name__)

@dataclass
class MemoryItem:
    """记忆项"""
    content: str
    timestamp: float
    importance: float = 1.0  # 重要性评分 0.0-1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = ""
    
    def __post_init__(self):
        if not self.id:
            # 基于内容和时间戳生成唯一ID
            content_hash = hashlib.md5(f"{self.content}{self.timestamp}".encode()).hexdigest()[:8]
            self.id = f"mem_{content_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp,
            "importance": self.importance,
            "metadata": self.metadata
        }

class WorkingMemory:
    """工作记忆管理器"""
    
    def __init__(self, max_size: int = 100, max_tokens: int = 4000):
        self.max_size = max_size  # 最大记忆项数量
        self.max_tokens = max_tokens  # 最大token数（近似）
        self.memory_items = deque(maxlen=max_size)
        self.current_tokens = 0
        
    def add(self, content: str, importance: float = 1.0, metadata: Optional[Dict[str, Any]] = None) -> str:
        """添加新的记忆项"""
        item = MemoryItem(
            content=content,
            timestamp=time.time(),
            importance=importance,
            metadata=metadata or {}
        )
        
        # 检查容量
        estimated_tokens = len(content) // 4  # 近似估算
        
        if len(self.memory_items) >= self.max_size:
            # 移除最不重要的记忆项
            self._evict_least_important()
        
        if self.current_tokens + estimated_tokens > self.max_tokens:
            # 压缩记忆
            self._compress_memory()
        
        self.memory_items.append(item)
        self.current_tokens += estimated_tokens
        
        logger.debug(f"工作记忆添加: {item.id}, 重要性: {importance}")
        return item.id
    
    def get(self, memory_id: str) -> Optional[MemoryItem]:
        """根据ID获取记忆项"""
        for item in self.memory_items:
            if item.id == memory_id:
                return item
        return None
    
    def get_recent(self, count: int = 10, min_importance: float = 0.0) -> List[MemoryItem]:
        """获取最近的记忆项"""
        items = list(self.memory_items)[-count:]
        return [item for item in items if item.importance >= min_importance]
    
    def get_by_importance(self, min_importance: float = 0.5) -> List[MemoryItem]:
        """获取重要性高于阈值的记忆项"""
        return [item for item in self.memory_items if item.importance >= min_importance]
    
    def search(self, query: str, limit: int = 5) -> List[MemoryItem]:
        """搜索记忆项（简单文本匹配）"""
        query_lower = query.lower()
        results = []
        
        for item in reversed(self.memory_items):  # 从最新开始搜索
            if query_lower in item.content.lower():
                # 计算简单相关性评分
                relevance = item.importance * (1.0 - (len(self.memory_items) - list(self.memory_items).index(item)) / len(self.memory_items))
                results.append((relevance, item))
        
        # 按相关性排序
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:limit]]
    
    def clear(self) -> None:
        """清空工作记忆"""
        self.memory_items.clear()
        self.current_tokens = 0
        logger.info("工作记忆已清空")
    
    def summarize(self, max_length: int = 500) -> str:
        """生成工作记忆的摘要"""
        if not self.memory_items:
            return "工作记忆为空"
        
        # 获取最重要的记忆项
        important_items = self.get_by_importance(min_importance=0.7)
        
        if not important_items:
            important_items = list(self.memory_items)[-5:]  # 获取最近5项
        
        # 生成摘要
        summary_parts = []
        for item in important_items:
            # 简化内容
            content = item.content
            if len(content) > 100:
                content = content[:97] + "..."
            
            summary_parts.append(f"- {content}")
        
        summary = "工作记忆摘要:\n" + "\n".join(summary_parts)
        
        # 截断到最大长度
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "max_size": self.max_size,
            "max_tokens": self.max_tokens,
            "current_size": len(self.memory_items),
            "current_tokens": self.current_tokens,
            "items": [item.to_dict() for item in self.memory_items]
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """从字典导入"""
        self.clear()
        
        if "max_size" in data:
            self.max_size = data["max_size"]
            self.memory_items = deque(maxlen=self.max_size)
        
        if "max_tokens" in data:
            self.max_tokens = data["max_tokens"]
        
        if "items" in data:
            for item_data in data["items"]:
                item = MemoryItem(
                    content=item_data["content"],
                    timestamp=item_data["timestamp"],
                    importance=item_data.get("importance", 1.0),
                    metadata=item_data.get("metadata", {}),
                    id=item_data.get("id", "")
                )
                self.memory_items.append(item)
            
            # 重新计算token数
            self.current_tokens = sum(len(item.content) // 4 for item in self.memory_items)
    
    def _evict_least_important(self) -> None:
        """驱逐最不重要的记忆项"""
        if not self.memory_items:
            return
        
        # 找到重要性最低的项
        min_importance = float('inf')
        min_index = -1
        
        for i, item in enumerate(self.memory_items):
            if item.importance < min_importance:
                min_importance = item.importance
                min_index = i
        
        if min_index >= 0:
            removed_item = self.memory_items[min_index]
            removed_tokens = len(removed_item.content) // 4
            
            # 创建新列表并移除该项
            items_list = list(self.memory_items)
            del items_list[min_index]
            
            self.memory_items = deque(items_list, maxlen=self.max_size)
            self.current_tokens -= removed_tokens
            
            logger.debug(f"工作记忆驱逐: {removed_item.id}, 重要性: {min_importance}")
    
    def _compress_memory(self) -> None:
        """压缩记忆以节省空间"""
        if len(self.memory_items) < 2:
            return
        
        # 合并相似或相关的记忆项
        compressed_items = []
        
        # 简单实现：合并时间接近的记忆项
        items_list = list(self.memory_items)
        
        i = 0
        while i < len(items_list):
            current_item = items_list[i]
            
            if i + 1 < len(items_list):
                next_item = items_list[i + 1]
                
                # 检查是否可以合并
                time_diff = next_item.timestamp - current_item.timestamp
                can_merge = time_diff < 60  # 60秒内
                
                if can_merge:
                    # 合并内容
                    merged_content = f"{current_item.content}\n{next_item.content}"
                    merged_importance = max(current_item.importance, next_item.importance)
                    merged_metadata = {**current_item.metadata, **next_item.metadata}
                    
                    merged_item = MemoryItem(
                        content=merged_content[:200],  # 限制长度
                        timestamp=current_item.timestamp,
                        importance=merged_importance,
                        metadata=merged_metadata
                    )
                    
                    compressed_items.append(merged_item)
                    i += 2  # 跳过已合并的项
                    logger.debug(f"工作记忆合并: {current_item.id} + {next_item.id}")
                    continue
            
            compressed_items.append(current_item)
            i += 1
        
        # 更新记忆
        self.memory_items = deque(compressed_items, maxlen=self.max_size)
        self.current_tokens = sum(len(item.content) // 4 for item in self.memory_items)
        
        logger.info(f"工作记忆压缩: {len(items_list)} -> {len(compressed_items)} 项")
