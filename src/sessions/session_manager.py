"""
会话管理系统
管理对话会话和生成摘要
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
from src.core.types import ConversationSession, ConversationSummary, Message


class SessionManager:
    """会话管理器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化会话管理器

        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.sessions: Dict[str, ConversationSession] = {}
        self.summaries: Dict[str, List[ConversationSummary]] = defaultdict(list)

        # 存储路径
        self.data_dir = Path(self.config.get("data_dir", "data/sessions"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 配置
        self.max_session_duration = self.config.get(
            "max_session_duration", 7200
        )  # 2小时
        self.max_message_history = self.config.get("max_message_history", 100)
        self.cleanup_interval = self.config.get("cleanup_interval", 300)  # 5分钟

        # 加载已保存的会话
        self._load_sessions()

        logger.info(f"会话管理器初始化完成，已加载 {len(self.sessions)} 个会话")

    def _load_sessions(self):
        """加载会话"""
        try:
            sessions_file = self.data_dir / "sessions.json"
            if sessions_file.exists():
                with open(sessions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for session_data in data.get("sessions", []):
                    try:
                        session = ConversationSession(**session_data)
                        self.sessions[session.session_id] = session
                    except Exception as e:
                        logger.error(f"加载会话失败: {e}")

            # 加载摘要
            summaries_file = self.data_dir / "summaries.json"
            if summaries_file.exists():
                with open(summaries_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for session_id, summaries in data.items():
                    self.summaries[session_id] = [
                        ConversationSummary(**s) for s in summaries
                    ]

        except Exception as e:
            logger.error(f"加载会话数据失败: {e}")

    def _save_sessions(self):
        """保存会话"""
        try:
            # 保存会话
            sessions_data = {
                "sessions": [s.dict() for s in self.sessions.values()],
                "saved_at": datetime.now().isoformat(),
            }
            with open(self.data_dir / "sessions.json", "w", encoding="utf-8") as f:
                json.dump(sessions_data, f, ensure_ascii=False, indent=2)

            # 保存摘要
            summaries_data = {
                session_id: [s.dict() for s in summaries]
                for session_id, summaries in self.summaries.items()
            }
            with open(self.data_dir / "summaries.json", "w", encoding="utf-8") as f:
                json.dump(summaries_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"保存会话数据失败: {e}")

    # ==================== 会话管理 ====================

    def create_session(
        self, user_id: str, agent_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationSession:
        """
        创建新会话

        Args:
            user_id: 用户ID
            agent_id: Agent ID
            metadata: 元数据

        Returns:
            会话对象
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"

        session = ConversationSession(
            session_id=session_id,
            user_id=user_id,
            agent_id=agent_id,
            metadata=metadata or {},
        )

        self.sessions[session_id] = session
        self._save_sessions()

        logger.info(f"创建会话: {session_id} (用户: {user_id}, Agent: {agent_id})")
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def get_active_sessions(
        self, user_id: Optional[str] = None, agent_id: Optional[str] = None
    ) -> List[ConversationSession]:
        """获取活跃会话"""
        sessions = list(self.sessions.values())

        # 过滤活跃状态
        sessions = [s for s in sessions if s.status == "active"]

        # 过滤用户
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]

        # 过滤Agent
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]

        return sessions

    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.status = "completed"
        session.updated_at = datetime.now()
        self._save_sessions()

        logger.info(f"关闭会话: {session_id}")
        return True

    def archive_session(self, session_id: str) -> bool:
        """归档会话"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.status = "archived"
        session.updated_at = datetime.now()
        self._save_sessions()

        logger.info(f"归档会话: {session_id}")
        return True

    # ==================== 消息管理 ====================

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Message]:
        """
        添加消息到会话

        Args:
            session_id: 会话ID
            role: 角色 (user/assistant/system/function)
            content: 内容
            tokens: Token数量
            metadata: 元数据

        Returns:
            消息对象
        """
        session = self.sessions.get(session_id)
        if not session:
            logger.error(f"会话不存在: {session_id}")
            return None

        # 检查会话状态
        if session.status != "active":
            logger.error(f"会话已关闭或归档: {session_id}")
            return None

        # 创建消息
        message_id = f"msg_{uuid.uuid4().hex[:8]}"

        message = Message(
            message_id=message_id,
            role=role,
            content=content,
            tokens=tokens,
            metadata=metadata or {},
        )

        # 添加到会话
        session.messages.append(message)
        session.total_tokens += tokens
        session.updated_at = datetime.now()

        # 检查消息历史限制
        if len(session.messages) > self.max_message_history:
            # 移除旧消息
            removed_count = len(session.messages) - self.max_message_history
            session.messages = session.messages[-self.max_message_history :]
            logger.info(f"会话 {session_id} 移除 {removed_count} 条旧消息")

        self._save_sessions()

        logger.debug(f"添加消息到会话 {session_id}: {role}")
        return message

    def get_messages(
        self, session_id: str, limit: Optional[int] = None
    ) -> List[Message]:
        """获取会话消息"""
        session = self.sessions.get(session_id)
        if not session:
            return []

        messages = session.messages

        if limit:
            messages = messages[-limit:]

        return messages

    def clear_messages(self, session_id: str) -> bool:
        """清空会话消息"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.messages.clear()
        session.total_tokens = 0
        session.updated_at = datetime.now()
        self._save_sessions()

        logger.info(f"清空会话消息: {session_id}")
        return True

    # ==================== 摘要生成 ====================

    def generate_summary(
        self, session_id: str, max_length: int = 500
    ) -> Optional[ConversationSummary]:
        """
        生成会话摘要

        Args:
            session_id: 会话ID
            max_length: 最大长度

        Returns:
            会话摘要
        """
        session = self.sessions.get(session_id)
        if not session or not session.messages:
            return None

        # 提取关键信息
        summary_id = f"summary_{uuid.uuid4().hex[:8]}"

        # 生成摘要内容（简化实现）
        summary_parts = []
        key_points = []
        entities = set()

        for message in session.messages:
            # 提取用户消息的关键内容
            if message.role == "user":
                content = message.content
                if len(content) > 100:
                    content = content[:97] + "..."
                summary_parts.append(f"用户: {content}")

            # 提取助手回复的关键信息
            elif message.role == "assistant":
                content = message.content
                if len(content) > 150:
                    content = content[:147] + "..."
                summary_parts.append(f"助手: {content}")

                # 提取实体（简化）
                words = content.split()
                for word in words:
                    if len(word) > 5 and word[0].isupper():
                        entities.add(word)

        # 构建摘要
        summary_content = "\n".join(summary_parts[-10:])  # 最多10条

        if len(summary_content) > max_length:
            summary_content = summary_content[: max_length - 3] + "..."

        # 提取关键点
        if session.messages:
            # 简单提取：用户的前几个问题
            user_messages = [m.content for m in session.messages if m.role == "user"]
            key_points = user_messages[:3]  # 最多3个关键点

        # 判断情感
        sentiment = "neutral"
        # 简单情感判断（可以集成NLP模型）
        positive_words = ["好的", "谢谢", "帮助", "成功", "解决"]
        negative_words = ["错误", "失败", "问题", "不行", "不好"]

        content_lower = summary_content.lower()
        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            sentiment = "positive"
        elif negative_count > positive_count:
            sentiment = "negative"

        summary = ConversationSummary(
            summary_id=summary_id,
            session_id=session_id,
            content=summary_content,
            key_points=key_points,
            entities=list(entities)[:10],  # 最多10个实体
            sentiment=sentiment,
        )

        # 保存摘要
        self.summaries[session_id].append(summary)
        self._save_sessions()

        logger.info(f"生成会话摘要: {session_id}")
        return summary

    def get_summaries(self, session_id: str) -> List[ConversationSummary]:
        """获取会话摘要列表"""
        return self.summaries.get(session_id, [])

    def get_latest_summary(self, session_id: str) -> Optional[ConversationSummary]:
        """获取最新摘要"""
        summaries = self.summaries.get(session_id, [])
        if summaries:
            return summaries[-1]
        return None

    # ==================== 会话清理 ====================

    def cleanup_expired_sessions(self) -> int:
        """
        清理过期会话

        Returns:
            清理的会话数量
        """
        now = datetime.now()
        expired_count = 0

        for session_id, session in list(self.sessions.items()):
            # 检查会话时长
            duration = (now - session.created_at).total_seconds()

            if duration > self.max_session_duration and session.status == "active":
                # 自动关闭过期会话
                session.status = "completed"
                session.updated_at = now
                expired_count += 1
                logger.info(f"关闭过期会话: {session_id}")

        if expired_count > 0:
            self._save_sessions()

        return expired_count

    def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id not in self.sessions:
            return False

        del self.sessions[session_id]
        self.summaries.pop(session_id, None)
        self._save_sessions()

        logger.info(f"删除会话: {session_id}")
        return True

    # ==================== 统计和分析 ====================

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """获取会话统计"""
        session = self.sessions.get(session_id)
        if not session:
            return {}

        messages = session.messages

        stats = {
            "session_id": session_id,
            "user_id": session.user_id,
            "agent_id": session.agent_id,
            "status": session.status,
            "message_count": len(messages),
            "total_tokens": session.total_tokens,
            "user_messages": len([m for m in messages if m.role == "user"]),
            "assistant_messages": len([m for m in messages if m.role == "assistant"]),
            "duration_seconds": (
                session.updated_at - session.created_at
            ).total_seconds(),
            "summaries_count": len(self.summaries.get(session_id, [])),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        }

        return stats

    def get_user_sessions_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户会话统计"""
        user_sessions = [s for s in self.sessions.values() if s.user_id == user_id]

        if not user_sessions:
            return {}

        stats = {
            "user_id": user_id,
            "total_sessions": len(user_sessions),
            "active_sessions": len([s for s in user_sessions if s.status == "active"]),
            "completed_sessions": len(
                [s for s in user_sessions if s.status == "completed"]
            ),
            "total_messages": sum(len(s.messages) for s in user_sessions),
            "total_tokens": sum(s.total_tokens for s in user_sessions),
            "avg_session_duration": 0.0,
            "avg_messages_per_session": 0.0,
        }

        # 计算平均值
        if user_sessions:
            durations = [
                (s.updated_at - s.created_at).total_seconds() for s in user_sessions
            ]
            stats["avg_session_duration"] = sum(durations) / len(durations)
            stats["avg_messages_per_session"] = stats["total_messages"] / len(
                user_sessions
            )

        return stats
