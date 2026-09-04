"""
用户管理系统
管理用户画像、习惯、标签和记忆
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from collections import defaultdict
import logging

from pydantic import BaseModel
from loguru import logger

# 导入核心类型
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.core.types import UserProfile, UserHabit, UserTag, UserMemory, MemoryType, Role


class UserManager:
    """用户管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化用户管理器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.users: Dict[str, UserProfile] = {}
        self.user_habits: Dict[str, List[UserHabit]] = defaultdict(list)
        self.user_tags: Dict[str, List[UserTag]] = defaultdict(list)
        self.user_memories: Dict[str, Dict[str, UserMemory]] = defaultdict(dict)

        # 存储路径
        self.data_dir = Path(self.config.get("data_dir", "data/users"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 加载已保存的用户数据
        self._load_users()

        logger.info(f"用户管理器初始化完成，已加载 {len(self.users)} 个用户")

    def _load_users(self):
        """加载用户数据"""
        try:
            users_file = self.data_dir / "users.json"
            if users_file.exists():
                with open(users_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for user_data in data.get("users", []):
                    try:
                        user = UserProfile(**user_data)
                        self.users[user.user_id] = user
                    except Exception as e:
                        logger.error(f"加载用户失败: {e}")

            # 加载习惯
            habits_file = self.data_dir / "habits.json"
            if habits_file.exists():
                with open(habits_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, habits in data.items():
                    self.user_habits[user_id] = [UserHabit(**h) for h in habits]

            # 加载标签
            tags_file = self.data_dir / "tags.json"
            if tags_file.exists():
                with open(tags_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, tags in data.items():
                    self.user_tags[user_id] = [UserTag(**t) for t in tags]

            # 加载记忆
            memories_file = self.data_dir / "memories.json"
            if memories_file.exists():
                with open(memories_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for user_id, memories in data.items():
                    for mem_id, mem_data in memories.items():
                        self.user_memories[user_id][mem_id] = UserMemory(**mem_data)

        except Exception as e:
            logger.error(f"加载用户数据失败: {e}")

    def _save_users(self):
        """保存用户数据"""
        try:
            # 保存用户
            users_data = {
                "users": [user.dict() for user in self.users.values()],
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.data_dir / "users.json", "w", encoding="utf-8") as f:
                json.dump(users_data, f, ensure_ascii=False, indent=2)

            # 保存习惯
            habits_data = {
                user_id: [habit.dict() for habit in habits]
                for user_id, habits in self.user_habits.items()
            }
            with open(self.data_dir / "habits.json", "w", encoding="utf-8") as f:
                json.dump(habits_data, f, ensure_ascii=False, indent=2)

            # 保存标签
            tags_data = {
                user_id: [tag.dict() for tag in tags]
                for user_id, tags in self.user_tags.items()
            }
            with open(self.data_dir / "tags.json", "w", encoding="utf-8") as f:
                json.dump(tags_data, f, ensure_ascii=False, indent=2)

            # 保存记忆
            memories_data = {
                user_id: {mem_id: mem.dict() for mem_id, mem in memories.items()}
                for user_id, memories in self.user_memories.items()
            }
            with open(self.data_dir / "memories.json", "w", encoding="utf-8") as f:
                json.dump(memories_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存用户数据失败: {e}")

    # ==================== 用户管理 ====================

    def create_user(
        self, username: str, email: Optional[str] = None, role: Role = Role.USER
    ) -> UserProfile:
        """
        创建新用户

        Args:
            username: 用户名
            email: 邮箱
            role: 角色

        Returns:
            用户画像
        """
        user_id = f"user_{uuid.uuid4().hex[:8]}"

        user = UserProfile(user_id=user_id, username=username, email=email, role=role)

        self.users[user_id] = user
        self._save_users()

        logger.info(f"创建用户: {user_id} - {username}")
        return user

    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """获取用户"""
        return self.users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[UserProfile]:
        """通过用户名获取用户"""
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def update_user(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """更新用户信息"""
        if user_id not in self.users:
            return False

        user = self.users[user_id]

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = datetime.now()
        self._save_users()

        logger.info(f"更新用户: {user_id}")
        return True

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id not in self.users:
            return False

        del self.users[user_id]
        self.user_habits.pop(user_id, None)
        self.user_tags.pop(user_id, None)
        self.user_memories.pop(user_id, None)

        self._save_users()

        logger.info(f"删除用户: {user_id}")
        return True

    def list_users(self, role_filter: Optional[Role] = None) -> List[UserProfile]:
        """列出用户"""
        users = list(self.users.values())

        if role_filter:
            users = [u for u in users if u.role == role_filter]

        return users

    # ==================== 习惯管理 ====================

    def add_habit(
        self,
        user_id: str,
        name: str,
        description: str,
        pattern: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserHabit]:
        """
        添加用户习惯

        Args:
            user_id: 用户ID
            name: 习惯名称
            description: 描述
            pattern: 模式
            metadata: 元数据

        Returns:
            用户习惯
        """
        if user_id not in self.users:
            logger.error(f"用户不存在: {user_id}")
            return None

        habit_id = f"habit_{uuid.uuid4().hex[:8]}"

        habit = UserHabit(
            habit_id=habit_id,
            name=name,
            description=description,
            pattern=pattern,
            metadata=metadata or {},
        )

        self.user_habits[user_id].append(habit)
        self._save_users()

        logger.info(f"添加用户习惯: {user_id} - {name}")
        return habit

    def get_user_habits(self, user_id: str) -> List[UserHabit]:
        """获取用户习惯列表"""
        return self.user_habits.get(user_id, [])

    def trigger_habit(self, user_id: str, habit_id: str) -> bool:
        """触发习惯"""
        habits = self.user_habits.get(user_id, [])

        for habit in habits:
            if habit.habit_id == habit_id:
                habit.last_triggered = datetime.now()
                habit.trigger_count += 1
                habit.confidence = min(1.0, habit.trigger_count / 10.0)
                self._save_users()
                return True

        return False

    def update_habit_confidence(
        self, user_id: str, habit_id: str, confidence: float
    ) -> bool:
        """更新习惯置信度"""
        habits = self.user_habits.get(user_id, [])

        for habit in habits:
            if habit.habit_id == habit_id:
                habit.confidence = max(0.0, min(1.0, confidence))
                self._save_users()
                return True

        return False

    # ==================== 标签管理 ====================

    def add_tag(
        self,
        user_id: str,
        name: str,
        category: str,
        weight: float = 1.0,
        source: str = "system",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserTag]:
        """
        添加用户标签

        Args:
            user_id: 用户ID
            name: 标签名
            category: 类别
            weight: 权重
            source: 来源
            metadata: 元数据

        Returns:
            用户标签
        """
        if user_id not in self.users:
            logger.error(f"用户不存在: {user_id}")
            return None

        # 检查是否已存在同名标签
        existing_tags = self.user_tags.get(user_id, [])
        for tag in existing_tags:
            if tag.name == name:
                # 更新权重和时间
                tag.weight = weight
                tag.updated_at = datetime.now()
                self._save_users()
                return tag

        tag_id = f"tag_{uuid.uuid4().hex[:8]}"

        tag = UserTag(
            tag_id=tag_id,
            name=name,
            category=category,
            weight=weight,
            source=source,
            metadata=metadata or {},
        )

        self.user_tags[user_id].append(tag)
        self._save_users()

        logger.info(f"添加用户标签: {user_id} - {name}")
        return tag

    def get_user_tags(
        self, user_id: str, category: Optional[str] = None
    ) -> List[UserTag]:
        """获取用户标签"""
        tags = self.user_tags.get(user_id, [])

        if category:
            tags = [t for t in tags if t.category == category]

        return tags

    def remove_tag(self, user_id: str, tag_id: str) -> bool:
        """移除标签"""
        tags = self.user_tags.get(user_id, [])

        for i, tag in enumerate(tags):
            if tag.tag_id == tag_id:
                del tags[i]
                self._save_users()
                return True

        return False

    # ==================== 记忆管理 ====================

    def add_memory(
        self,
        user_id: str,
        memory_type: MemoryType,
        content: str,
        importance: float = 1.0,
        tags: Optional[List[str]] = None,
        expires_in: Optional[int] = None,  # 过期时间（秒）
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[UserMemory]:
        """
        添加用户记忆

        Args:
            user_id: 用户ID
            memory_type: 记忆类型
            content: 内容
            importance: 重要性
            tags: 标签列表
            expires_in: 过期时间（秒）
            metadata: 元数据

        Returns:
            用户记忆
        """
        if user_id not in self.users:
            logger.error(f"用户不存在: {user_id}")
            return None

        memory_id = f"mem_{uuid.uuid4().hex[:8]}"

        # 计算过期时间
        expires_at = None
        if expires_in and memory_type == MemoryType.WORKING:
            expires_at = datetime.now() + timedelta(seconds=expires_in)

        memory = UserMemory(
            memory_id=memory_id,
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags or [],
            expires_at=expires_at,
            metadata=metadata or {},
        )

        self.user_memories[user_id][memory_id] = memory
        self._save_users()

        logger.info(f"添加用户记忆: {user_id} - {memory_type.value}")
        return memory

    def get_memory(self, user_id: str, memory_id: str) -> Optional[UserMemory]:
        """获取记忆"""
        memories = self.user_memories.get(user_id, {})
        memory = memories.get(memory_id)

        if memory:
            # 更新访问信息
            memory.access_count += 1
            memory.last_accessed = datetime.now()
            self._save_users()

        return memory

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        min_importance: float = 0.0,
        limit: int = 100,
    ) -> List[UserMemory]:
        """获取用户记忆"""
        memories = list(self.user_memories.get(user_id, {}).values())

        # 过滤过期记忆
        now = datetime.now()
        memories = [m for m in memories if not m.expires_at or m.expires_at > now]

        # 过滤类型
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]

        # 过滤重要性
        memories = [m for m in memories if m.importance >= min_importance]

        # 按重要性排序
        memories.sort(key=lambda m: m.importance, reverse=True)

        return memories[:limit]

    def search_memories(
        self, user_id: str, query: str, limit: int = 10
    ) -> List[UserMemory]:
        """搜索记忆"""
        memories = self.get_user_memories(user_id)

        # 简单文本搜索
        query_lower = query.lower()
        results = []

        for memory in memories:
            if query_lower in memory.content.lower():
                # 计算相关性分数
                relevance = memory.importance * (1.0 + memory.access_count * 0.1)
                results.append((relevance, memory))

        # 排序
        results.sort(key=lambda x: x[0], reverse=True)

        return [m for _, m in results[:limit]]

    def consolidate_memories(self, user_id: str) -> int:
        """
        记忆巩固：清理过期记忆，提升重要记忆

        Args:
            user_id: 用户ID

        Returns:
            清理的记忆数量
        """
        memories = self.user_memories.get(user_id, {})
        now = datetime.now()

        # 清理过期记忆
        expired = [
            mem_id
            for mem_id, mem in memories.items()
            if mem.expires_at and mem.expires_at <= now
        ]

        for mem_id in expired:
            del memories[mem_id]

        # 提升高频访问记忆的重要性
        for memory in memories.values():
            if memory.access_count > 5:
                memory.importance = min(1.0, memory.importance + 0.1)

        self._save_users()

        logger.info(f"用户 {user_id} 记忆巩固完成，清理 {len(expired)} 条记忆")
        return len(expired)

    # ==================== 统计和分析 ====================

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        user = self.get_user(user_id)
        if not user:
            return {}

        habits = self.get_user_habits(user_id)
        tags = self.get_user_tags(user_id)
        memories = self.get_user_memories(user_id)

        # 计算统计信息
        stats = {
            "user_id": user_id,
            "username": user.username,
            "role": user.role,
            "habits_count": len(habits),
            "active_habits": len([h for h in habits if h.confidence > 0.5]),
            "tags_count": len(tags),
            "tags_by_category": defaultdict(int),
            "memories_count": len(memories),
            "memories_by_type": defaultdict(int),
            "avg_memory_importance": 0.0,
            "account_age_days": (datetime.now() - user.created_at).days,
            "last_active": user.updated_at.isoformat(),
        }

        # 标签分类统计
        for tag in tags:
            stats["tags_by_category"][tag.category] += 1

        # 记忆类型统计
        for memory in memories:
            stats["memories_by_type"][memory.memory_type] += 1

        # 平均重要性
        if memories:
            stats["avg_memory_importance"] = sum(m.importance for m in memories) / len(
                memories
            )

        # 更新用户统计
        user.statistics = stats
        self._save_users()

        return stats

    def infer_user_tags(self, user_id: str) -> List[UserTag]:
        """
        从用户行为推断标签

        Args:
            user_id: 用户ID

        Returns:
            推断的标签列表
        """
        inferred_tags = []

        # 基于习惯推断
        habits = self.get_user_habits(user_id)
        for habit in habits:
            if habit.confidence > 0.7:  # 高置信度习惯
                tag = self.add_tag(
                    user_id=user_id,
                    name=f"habit_{habit.name}",
                    category="behavior",
                    weight=habit.confidence,
                    source="inferred",
                    metadata={"habit_id": habit.habit_id},
                )
                if tag:
                    inferred_tags.append(tag)

        # 基于记忆推断
        memories = self.get_user_memories(user_id, min_importance=0.8)
        for memory in memories[:5]:  # 只处理最重要的5条
            # 简单的关键词提取（实际应用中可以使用NLP）
            keywords = memory.tags
            for keyword in keywords:
                tag = self.add_tag(
                    user_id=user_id,
                    name=keyword,
                    category="interest",
                    weight=memory.importance,
                    source="inferred",
                    metadata={"memory_id": memory.memory_id},
                )
                if tag:
                    inferred_tags.append(tag)

        logger.info(f"为用户 {user_id} 推断了 {len(inferred_tags)} 个标签")
        return inferred_tags
