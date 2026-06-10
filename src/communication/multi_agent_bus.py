# Multi-Agent Communication Bus
# Agent OS - Communication Layer
# Created: 2026-06-09

"""
多Agent通信总线
参考Hermes设计，实现异步消息传递和订阅发布模式
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Set
from collections import defaultdict

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """消息类型"""
    COMMAND = "command"  # 命令消息
    EVENT = "event"      # 事件通知
    RESPONSE = "response"  # 响应消息
    BROADCAST = "broadcast"  # 广播消息
    HEARTBEAT = "heartbeat"  # 心跳消息

class MessagePriority(Enum):
    """消息优先级"""
    HIGH = 0
    NORMAL = 1
    LOW = 2

@dataclass
class AgentMessage:
    """Agent消息对象"""
    message_id: str
    sender_id: str
    receiver_id: Optional[str] = None  # None表示广播
    message_type: MessageType = MessageType.EVENT
    priority: MessagePriority = MessagePriority.NORMAL
    topic: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None  # 生存时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "topic": self.topic,
            "payload": self.payload,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "ttl": self.ttl,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """从字典创建"""
        return cls(
            message_id=data["message_id"],
            sender_id=data["sender_id"],
            receiver_id=data.get("receiver_id"),
            message_type=MessageType(data["message_type"]),
            priority=MessagePriority(data["priority"]),
            topic=data.get("topic"),
            payload=data.get("payload", {}),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            ttl=data.get("ttl"),
        )

class MessageHandler:
    """消息处理器"""
    
    def __init__(self):
        self.callback = None
        self.filter_topic = None
        self.filter_sender = None
    
    async def handle(self, message: AgentMessage) -> bool:
        """处理消息"""
        if self.callback:
            try:
                await self.callback(message)
                return True
            except Exception as e:
                logger.error(f"消息处理失败: {e}")
                return False
        return False

class MultiAgentBus:
    """多Agent通信总线"""
    
    def __init__(self, bus_name: str = "default"):
        self.bus_name = bus_name
        self.agents = {}  # agent_id -> AgentInfo
        self.message_handlers = defaultdict(list)  # topic -> [MessageHandler]
        self.message_queue = asyncio.Queue()
        self.message_history = []
        self.max_history = 1000
        self.running = False
        self.task = None
        
        # 统计信息
        self.stats = {
            "total_messages": 0,
            "delivered_messages": 0,
            "failed_messages": 0,
            "active_agents": 0,
            "active_topics": 0,
        }
        
        logger.info(f"初始化多Agent通信总线: {bus_name}")
    
    async def start(self):
        """启动消息总线"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._message_dispatcher())
        logger.info(f"消息总线已启动: {self.bus_name}")
    
    async def stop(self):
        """停止消息总线"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"消息总线已停止: {self.bus_name}")
    
    def register_agent(self, agent_id: str, agent_info: Dict[str, Any] = None):
        """注册Agent"""
        if agent_id in self.agents:
            logger.warning(f"Agent已注册: {agent_id}")
            return False
        
        self.agents[agent_id] = {
            "id": agent_id,
            "info": agent_info or {},
            "registered_at": datetime.now(),
            "last_seen": datetime.now(),
            "topics": set(),
        }
        
        self.stats["active_agents"] = len(self.agents)
        logger.info(f"Agent注册成功: {agent_id}")
        return True
    
    def unregister_agent(self, agent_id: str):
        """注销Agent"""
        if agent_id not in self.agents:
            return False
        
        # 移除该Agent的所有处理器
        for topic, handlers in self.message_handlers.items():
            self.message_handlers[topic] = [
                h for h in handlers if h.filter_sender != agent_id
            ]
        
        del self.agents[agent_id]
        self.stats["active_agents"] = len(self.agents)
        logger.info(f"Agent注销成功: {agent_id}")
        return True
    
    def subscribe(
        self,
        agent_id: str,
        topic: str,
        callback: Callable[[AgentMessage], Awaitable[None]],
        filter_sender: Optional[str] = None
    ):
        """订阅主题"""
        if agent_id not in self.agents:
            logger.error(f"Agent未注册: {agent_id}")
            return False
        
        handler = MessageHandler()
        handler.callback = callback
        handler.filter_topic = topic
        handler.filter_sender = filter_sender
        
        self.message_handlers[topic].append(handler)
        self.agents[agent_id]["topics"].add(topic)
        self.stats["active_topics"] = len(self.message_handlers)
        
        logger.info(f"Agent {agent_id} 订阅主题: {topic}")
        return True
    
    def unsubscribe(self, agent_id: str, topic: str):
        """取消订阅"""
        if agent_id not in self.agents:
            return False
        
        if topic in self.message_handlers:
            self.message_handlers[topic] = [
                h for h in self.message_handlers[topic]
                if not (h.filter_topic == topic and h.filter_sender == agent_id)
            ]
            
            if not self.message_handlers[topic]:
                del self.message_handlers[topic]
        
        self.agents[agent_id]["topics"].discard(topic)
        self.stats["active_topics"] = len(self.message_handlers)
        
        logger.info(f"Agent {agent_id} 取消订阅主题: {topic}")
        return True
    
    async def send_message(self, message: AgentMessage) -> bool:
        """发送消息"""
        if not self.running:
            logger.error("消息总线未启动")
            return False
        
        self.stats["total_messages"] += 1
        
        # 检查TTL
        if message.ttl and (datetime.now() - message.created_at).seconds > message.ttl:
            logger.warning(f"消息已过期: {message.message_id}")
            self.stats["failed_messages"] += 1
            return False
        
        # 添加到队列
        await self.message_queue.put(message)
        logger.debug(f"消息已加入队列: {message.message_id}")
        return True
    
    async def publish(
        self,
        sender_id: str,
        topic: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.EVENT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """发布消息到主题"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            message_type=message_type,
            priority=priority,
            topic=topic,
            payload=payload,
            metadata=metadata or {},
            created_at=datetime.now(),
        )
        
        success = await self.send_message(message)
        if success:
            logger.info(f"消息发布成功: {message.message_id} 主题: {topic}")
            return message.message_id
        else:
            logger.error(f"消息发布失败: {topic}")
            return ""
    
    async def send_direct(
        self,
        sender_id: str,
        receiver_id: str,
        payload: Dict[str, Any],
        message_type: MessageType = MessageType.COMMAND,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """发送直接消息"""
        message = AgentMessage(
            message_id=str(uuid.uuid4()),
            sender_id=sender_id,
            receiver_id=receiver_id,
            message_type=message_type,
            priority=priority,
            payload=payload,
            metadata=metadata or {},
            created_at=datetime.now(),
        )
        
        success = await self.send_message(message)
        if success:
            logger.info(f"直接消息发送成功: {message.message_id} 从 {sender_id} 到 {receiver_id}")
            return message.message_id
        else:
            logger.error(f"直接消息发送失败: {sender_id} -> {receiver_id}")
            return ""
    
    async def _message_dispatcher(self):
        """消息分发器"""
        logger.info("消息分发器启动")
        
        while self.running:
            try:
                # 从队列获取消息
                message = await asyncio.wait_for(
                    self.message_queue.get(),
                    timeout=1.0
                )
                
                # 分发消息
                await self._dispatch_message(message)
                
                # 标记任务完成
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                # 超时正常，继续循环
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"消息分发错误: {e}")
        
        logger.info("消息分发器停止")
    
    async def _dispatch_message(self, message: AgentMessage):
        """分发消息到处理器"""
        delivered = False
        
        # 添加到历史记录
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        # 如果是直接消息
        if message.receiver_id:
            # 查找特定接收者的处理器
            for handlers in self.message_handlers.values():
                for handler in handlers:
                    if handler.filter_sender == message.receiver_id:
                        if await handler.handle(message):
                            delivered = True
        
        # 如果是主题消息
        elif message.topic:
            handlers = self.message_handlers.get(message.topic, [])
            for handler in handlers:
                # 检查发送者过滤
                if handler.filter_sender and handler.filter_sender != message.sender_id:
                    continue
                
                if await handler.handle(message):
                    delivered = True
        
        # 更新统计
        if delivered:
            self.stats["delivered_messages"] += 1
            logger.debug(f"消息分发成功: {message.message_id}")
        else:
            self.stats["failed_messages"] += 1
            logger.warning(f"消息未分发: {message.message_id}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取总线统计信息"""
        return {
            **self.stats,
            "bus_name": self.bus_name,
            "running": self.running,
            "queue_size": self.message_queue.qsize(),
            "history_size": len(self.message_history),
            "registered_agents": list(self.agents.keys()),
            "active_topics_list": list(self.message_handlers.keys()),
        }
    
    async def get_agent_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取Agent信息"""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        
        return {
            "id": agent["id"],
            "info": agent["info"],
            "registered_at": agent["registered_at"].isoformat(),
            "last_seen": agent["last_seen"].isoformat(),
            "topics": list(agent["topics"]),
        }

# 示例用法
if __name__ == "__main__":
    async def agent1_handler(message: AgentMessage):
        print(f"Agent1 收到消息: {message.topic} - {message.payload}")
    
    async def agent2_handler(message: AgentMessage):
        print(f"Agent2 收到消息: {message.topic} - {message.payload}")
    
    async def main():
        # 创建消息总线
        bus = MultiAgentBus(bus_name="test_bus")
        await bus.start()
        
        # 注册Agent
        bus.register_agent("agent_1", {"type": "worker", "version": "1.0"})
        bus.register_agent("agent_2", {"type": "monitor", "version": "1.0"})
        
        # 订阅主题
        bus.subscribe("agent_1", "system.events", agent1_handler)
        bus.subscribe("agent_2", "system.events", agent2_handler)
        
        # 发布消息
        await bus.publish(
            sender_id="system",
            topic="system.events",
            payload={"event": "startup", "time": "2026-06-09"},
            message_type=MessageType.EVENT
        )
        
        # 发送直接消息
        await bus.send_direct(
            sender_id="agent_1",
            receiver_id="agent_2",
            payload={"command": "status", "request_id": "123"},
            message_type=MessageType.COMMAND
        )
        
        # 等待消息处理
        await asyncio.sleep(1)
        
        # 获取统计信息
        stats = await bus.get_stats()
        print(f"总线统计: {stats}")
        
        # 停止总线
        await bus.stop()
    
    asyncio.run(main())