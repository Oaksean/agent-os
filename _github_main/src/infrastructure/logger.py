# 日志记录系统
# Agent OS - Infrastructure Layer
# Created: 2026-06-09

"""
日志记录系统
参考Hermes Agent设计，实现结构化日志、审计日志和性能追踪
"""

import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum
import sys


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(Enum):
    """日志类别"""

    SYSTEM = "system"  # 系统日志
    USER = "user"  # 用户操作
    AGENT = "agent"  # Agent活动
    SESSION = "session"  # 会话管理
    TASK = "task"  # 任务执行
    TOOL = "tool"  # 工具调用
    SECURITY = "security"  # 安全相关
    PERFORMANCE = "performance"  # 性能指标
    AUDIT = "audit"  # 审计日志


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: datetime
    level: LogLevel
    category: LogCategory
    message: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "extra": self.extra,
        }

    def to_json(self) -> str:
        """转换为JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class AuditLog:
    """审计日志"""

    audit_id: str
    timestamp: datetime
    user_id: str
    action: str
    resource_type: str
    resource_id: str
    details: Dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "audit_id": self.audit_id,
            "timestamp": self.timestamp.isoformat(),
            "user_id": self.user_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "error_message": self.error_message,
        }


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(
        self,
        name: str,
        log_dir: str = "logs",
        log_level: LogLevel = LogLevel.INFO,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
    ):
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.log_level = log_level
        self.max_file_size = max_file_size
        self.backup_count = backup_count

        # 日志缓冲区
        self.log_buffer: List[LogEntry] = []
        self.buffer_size = 100

        # 审计日志缓冲区
        self.audit_buffer: List[AuditLog] = []
        self.audit_buffer_size = 50

        # 计数器
        self.audit_counter = 0

        # 配置Python logger
        self._setup_logger()

        logger.info(f"初始化日志系统: {name}")

    def _setup_logger(self):
        """配置Python logger"""
        global logger
        logger = logging.getLogger(self.name)
        logger.setLevel(getattr(logging, self.log_level.value))

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # 文件处理器
        log_file = self.log_dir / "agent_os.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)

    def log(
        self,
        level: LogLevel,
        category: LogCategory,
        message: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **extra,
    ):
        """记录日志"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            user_id=user_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            extra=extra,
        )

        # 添加到缓冲区
        self.log_buffer.append(entry)

        # 缓冲区满时写入文件
        if len(self.log_buffer) >= self.buffer_size:
            self._flush_logs()

        # 同时输出到Python logger
        log_method = getattr(logger, level.value.lower())
        log_method(f"[{category.value}] {message} | extra: {extra}")

    def _flush_logs(self):
        """刷新日志缓冲区"""
        if not self.log_buffer:
            return

        # 写入文件
        log_file = self.log_dir / "structured_logs.json"

        with open(log_file, "a", encoding="utf-8") as f:
            for entry in self.log_buffer:
                f.write(entry.to_json() + "\n")

        # 清空缓冲区
        self.log_buffer.clear()

    def audit(
        self,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """记录审计日志"""
        self.audit_counter += 1
        audit_id = (
            f"audit_{self.audit_counter:08d}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )

        audit_log = AuditLog(
            audit_id=audit_id,
            timestamp=datetime.now(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message,
        )

        # 添加到缓冲区
        self.audit_buffer.append(audit_log)

        # 缓冲区满时写入文件
        if len(self.audit_buffer) >= self.audit_buffer_size:
            self._flush_audit_logs()

        # 同时记录到主日志
        status = "成功" if success else f"失败: {error_message}"
        logger.info(
            f"[AUDIT] {user_id} {action} {resource_type}:{resource_id} - {status}"
        )

    def _flush_audit_logs(self):
        """刷新审计日志缓冲区"""
        if not self.audit_buffer:
            return

        # 写入文件
        audit_file = self.log_dir / "audit_logs.json"

        with open(audit_file, "a", encoding="utf-8") as f:
            for audit in self.audit_buffer:
                f.write(json.dumps(audit.to_dict(), ensure_ascii=False) + "\n")

        # 清空缓冲区
        self.audit_buffer.clear()

    def debug(self, message: str, **kwargs):
        """记录DEBUG日志"""
        self.log(LogLevel.DEBUG, LogCategory.SYSTEM, message, **kwargs)

    def info(self, message: str, **kwargs):
        """记录INFO日志"""
        self.log(LogLevel.INFO, LogCategory.SYSTEM, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """记录WARNING日志"""
        self.log(LogLevel.WARNING, LogCategory.SYSTEM, message, **kwargs)

    def error(self, message: str, **kwargs):
        """记录ERROR日志"""
        self.log(LogLevel.ERROR, LogCategory.SYSTEM, message, **kwargs)

    def critical(self, message: str, **kwargs):
        """记录CRITICAL日志"""
        self.log(LogLevel.CRITICAL, LogCategory.SYSTEM, message, **kwargs)

    # 分类日志方法
    def user_action(self, message: str, user_id: str, **kwargs):
        """用户操作日志"""
        self.log(LogLevel.INFO, LogCategory.USER, message, user_id=user_id, **kwargs)

    def agent_activity(self, message: str, agent_id: str, **kwargs):
        """Agent活动日志"""
        self.log(LogLevel.INFO, LogCategory.AGENT, message, agent_id=agent_id, **kwargs)

    def session_event(self, message: str, session_id: str, **kwargs):
        """会话事件日志"""
        self.log(
            LogLevel.INFO, LogCategory.SESSION, message, session_id=session_id, **kwargs
        )

    def task_execution(self, message: str, task_id: str, **kwargs):
        """任务执行日志"""
        self.log(LogLevel.INFO, LogCategory.TASK, message, task_id=task_id, **kwargs)

    def tool_call(self, message: str, **kwargs):
        """工具调用日志"""
        self.log(LogLevel.INFO, LogCategory.TOOL, message, **kwargs)

    def security_event(self, message: str, **kwargs):
        """安全事件日志"""
        self.log(LogLevel.WARNING, LogCategory.SECURITY, message, **kwargs)

    def performance_metric(self, message: str, **kwargs):
        """性能指标日志"""
        self.log(LogLevel.INFO, LogCategory.PERFORMANCE, message, **kwargs)

    def query_logs(
        self,
        level: Optional[LogLevel] = None,
        category: Optional[LogCategory] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """查询日志"""
        # 读取日志文件
        log_file = self.log_dir / "structured_logs.json"

        if not log_file.exists():
            return []

        results = []

        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                if len(results) >= limit:
                    break

                data = json.loads(line)
                entry = LogEntry(
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    level=LogLevel(data["level"]),
                    category=LogCategory(data["category"]),
                    message=data["message"],
                    user_id=data.get("user_id"),
                    agent_id=data.get("agent_id"),
                    session_id=data.get("session_id"),
                    task_id=data.get("task_id"),
                    extra=data.get("extra", {}),
                )

                # 过滤条件
                if level and entry.level != level:
                    continue

                if category and entry.category != category:
                    continue

                if user_id and entry.user_id != user_id:
                    continue

                if agent_id and entry.agent_id != agent_id:
                    continue

                if session_id and entry.session_id != session_id:
                    continue

                if start_time and entry.timestamp < start_time:
                    continue

                if end_time and entry.timestamp > end_time:
                    continue

                results.append(entry)

        return results

    def query_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditLog]:
        """查询审计日志"""
        audit_file = self.log_dir / "audit_logs.json"

        if not audit_file.exists():
            return []

        results = []

        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                if len(results) >= limit:
                    break

                data = json.loads(line)
                audit = AuditLog(
                    audit_id=data["audit_id"],
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                    user_id=data["user_id"],
                    action=data["action"],
                    resource_type=data["resource_type"],
                    resource_id=data["resource_id"],
                    details=data.get("details", {}),
                    ip_address=data.get("ip_address"),
                    user_agent=data.get("user_agent"),
                    success=data.get("success", True),
                    error_message=data.get("error_message"),
                )

                # 过滤条件
                if user_id and audit.user_id != user_id:
                    continue

                if action and audit.action != action:
                    continue

                if resource_type and audit.resource_type != resource_type:
                    continue

                if start_time and audit.timestamp < start_time:
                    continue

                if end_time and audit.timestamp > end_time:
                    continue

                results.append(audit)

        return results

    def flush(self):
        """强制刷新所有缓冲区"""
        self._flush_logs()
        self._flush_audit_logs()
        logger.info("日志缓冲区已刷新")


# 全局实例
structured_logger = StructuredLogger("agent_os")


# 便捷函数
def get_logger(name: str = "agent_os") -> StructuredLogger:
    """获取日志记录器"""
    return structured_logger


# 示例用法
if __name__ == "__main__":
    # 获取日志记录器
    log = get_logger()

    # 记录各种类型的日志
    log.info("系统启动", version="0.2.0")
    log.debug("调试信息", module="test")

    # 分类日志
    log.user_action("用户登录", user_id="user_123", ip="192.168.1.1")
    log.agent_activity("Agent创建", agent_id="agent_456", type="assistant")
    log.session_event("会话创建", session_id="session_789")
    log.task_execution("任务开始", task_id="task_001")
    log.tool_call("工具调用", tool="calculator", args={"a": 1, "b": 2})

    # 审计日志
    log.audit(
        user_id="user_123",
        action="create",
        resource_type="agent",
        resource_id="agent_456",
        details={"name": "助手A", "type": "assistant"},
        ip_address="192.168.1.1",
    )

    log.audit(
        user_id="user_123",
        action="delete",
        resource_type="session",
        resource_id="session_789",
        success=False,
        error_message="权限不足",
    )

    # 刷新缓冲区
    log.flush()

    # 查询日志
    print("\n查询用户日志:")
    user_logs = log.query_logs(user_id="user_123")
    for entry in user_logs:
        print(f"  {entry.timestamp} - {entry.message}")

    print("\n查询审计日志:")
    audit_logs = log.query_audit_logs(user_id="user_123")
    for audit in audit_logs:
        print(
            f"  {audit.timestamp} - {audit.action} {audit.resource_type}:{audit.resource_id}"
        )
