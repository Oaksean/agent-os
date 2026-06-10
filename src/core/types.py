"""
Agent OS 核心类型系统
定义所有核心数据结构和类型
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass, field as dataclass_field


# ==================== 枚举类型 ====================


class AgentStatus(str, Enum):
    """Agent状态"""

    CREATED = "created"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    MIGRATING = "migrating"


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """任务优先级"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


class MemoryType(str, Enum):
    """记忆类型"""

    WORKING = "working"  # 工作记忆（短期）
    EPISODIC = "episodic"  # 情景记忆
    SEMANTIC = "semantic"  # 语义记忆
    PROCEDURAL = "procedural"  # 程序记忆


class Permission(str, Enum):
    """权限类型"""

    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    DELETE = "delete"


class Role(str, Enum):
    """用户角色"""

    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"


class PromptType(str, Enum):
    """提示词类型"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class LogLevel(str, Enum):
    """日志级别"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """指标类型"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


# ==================== 基础模型 ====================


class TimestampMixin(BaseModel):
    """时间戳混入"""

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now()


class IDMixin(BaseModel):
    """ID混入"""

    id: str = Field(..., description="唯一标识符")


class MetadataMixin(BaseModel):
    """元数据混入"""

    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


# ==================== 用户系统 ====================


class UserHabit(BaseModel):
    """用户习惯"""

    habit_id: str
    name: str
    description: str
    pattern: str  # 习惯模式描述
    frequency: float  # 频率 0.0-1.0
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    confidence: float = 0.0  # 置信度 0.0-1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserTag(BaseModel):
    """用户标签"""

    tag_id: str
    name: str
    category: str  # 标签类别：行为、偏好、技能等
    weight: float = 1.0  # 权重 0.0-1.0
    source: str = "system"  # 来源：system、inferred、manual
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserMemory(BaseModel):
    """用户记忆项"""

    memory_id: str
    memory_type: MemoryType
    content: str
    importance: float = 1.0  # 重要性 0.0-1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None  # 过期时间（用于短期记忆）
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UserProfile(BaseModel):
    """用户画像"""

    user_id: str
    username: str
    email: Optional[str] = None
    role: Role = Role.USER
    habits: List[UserHabit] = Field(default_factory=list)
    tags: List[UserTag] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    statistics: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


# ==================== 提示词系统 ====================


class PromptTemplate(BaseModel):
    """提示词模板"""

    template_id: str
    name: str
    type: PromptType
    content: str
    variables: List[str] = Field(default_factory=list)  # 模板变量
    description: str = ""
    version: str = "1.0"
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def render(self, **kwargs) -> str:
        """渲染模板"""
        content = self.content
        for var in self.variables:
            if var in kwargs:
                content = content.replace(f"{{{var}}}", str(kwargs[var]))
        return content


class SystemPrompt(PromptTemplate):
    """系统提示词"""

    type: PromptType = PromptType.SYSTEM
    model_compatibility: List[str] = Field(default_factory=list)  # 兼容的模型
    optimization_hints: Dict[str, Any] = Field(default_factory=dict)


class UserPrompt(PromptTemplate):
    """用户提示词"""

    type: PromptType = PromptType.USER
    context_requirements: List[str] = Field(default_factory=list)


# ==================== 会话系统 ====================


class Message(BaseModel):
    """消息"""

    message_id: str
    role: str  # user, assistant, system, function
    content: str
    tokens: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSession(BaseModel):
    """会话"""

    session_id: str
    user_id: str
    agent_id: str
    messages: List[Message] = Field(default_factory=list)
    summary: Optional[str] = None
    total_tokens: int = 0
    status: str = "active"  # active, completed, archived
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    """会话摘要"""

    summary_id: str
    session_id: str
    content: str
    key_points: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)  # 提到的实体
    sentiment: str = "neutral"  # positive, negative, neutral
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== 日志系统 ====================


class LogEntry(BaseModel):
    """日志条目"""

    log_id: str
    level: LogLevel
    message: str
    source: str  # 来源模块
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    task_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    duration: Optional[float] = None  # 执行时长（毫秒）
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AuditLog(LogEntry):
    """审计日志"""

    action: str
    resource: str
    result: str  # success, failure
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


# ==================== 任务系统 ====================


class Task(BaseModel):
    """任务"""

    task_id: str
    name: str
    description: str
    goal: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    assigned_agent: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    subtasks: List[str] = Field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True


class TaskSchedule(BaseModel):
    """任务调度"""

    schedule_id: str
    task_id: str
    cron_expression: Optional[str] = None  # Cron表达式
    interval_seconds: Optional[int] = None  # 间隔秒数
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.now)


# ==================== 流量控制 ====================


class RateLimit(BaseModel):
    """速率限制"""

    limit_id: str
    name: str
    requests_per_minute: Optional[int] = None
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    tokens_per_minute: Optional[int] = None
    tokens_per_hour: Optional[int] = None
    tokens_per_day: Optional[int] = None
    current_requests: Dict[str, int] = Field(default_factory=dict)
    current_tokens: Dict[str, int] = Field(default_factory=dict)
    enabled: bool = True


class TrafficMetrics(BaseModel):
    """流量指标"""

    metric_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    total_tokens: int = 0
    active_sessions: int = 0
    active_agents: int = 0
    queue_length: int = 0


# ==================== 权限系统 ====================


class PermissionRule(BaseModel):
    """权限规则"""

    rule_id: str
    resource: str  # 资源标识符（支持通配符）
    permissions: List[Permission]
    roles: List[Role]
    conditions: Dict[str, Any] = Field(default_factory=dict)  # 条件
    created_at: datetime = Field(default_factory=datetime.now)
    enabled: bool = True

    class Config:
        use_enum_values = True


class AccessControl(BaseModel):
    """访问控制"""

    user_id: str
    resource: str
    permission: Permission
    granted: bool
    reason: str
    timestamp: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ==================== 监控系统 ====================


class Metric(BaseModel):
    """指标"""

    metric_id: str
    name: str
    type: MetricType
    value: Union[int, float]
    unit: str = ""
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class Alert(BaseModel):
    """告警"""

    alert_id: str
    name: str
    severity: str  # info, warning, error, critical
    message: str
    source: str
    metric_name: Optional[str] = None
    threshold: Optional[float] = None
    current_value: Optional[float] = None
    status: str = "firing"  # firing, resolved
    created_at: datetime = Field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DashboardWidget(BaseModel):
    """Dashboard组件"""

    widget_id: str
    name: str
    type: str  # chart, metric, table, graph
    config: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval: int = 60  # 刷新间隔（秒）
    created_at: datetime = Field(default_factory=datetime.now)


class Dashboard(BaseModel):
    """Dashboard"""

    dashboard_id: str
    name: str
    widgets: List[DashboardWidget] = Field(default_factory=list)
    layout: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ==================== 配置系统 ====================


class SystemConfig(BaseModel):
    """系统配置"""

    # Agent配置
    max_agents: int = 100
    default_agent_timeout: int = 300  # 秒
    agent_heartbeat_interval: int = 30  # 秒

    # 任务配置
    max_task_retries: int = 3
    task_timeout: int = 600  # 秒
    max_concurrent_tasks: int = 10

    # 记忆配置
    working_memory_max_size: int = 100
    working_memory_max_tokens: int = 4000
    long_term_memory_enabled: bool = True
    memory_consolidation_interval: int = 3600  # 秒

    # 会话配置
    max_session_duration: int = 7200  # 秒
    session_cleanup_interval: int = 300  # 秒
    max_message_history: int = 100

    # 流量控制
    rate_limit_enabled: bool = True
    default_rate_limit_rpm: int = 60  # 每分钟请求数
    default_rate_limit_tpm: int = 10000  # 每分钟Token数

    # 日志配置
    log_level: LogLevel = LogLevel.INFO
    log_retention_days: int = 30
    audit_log_enabled: bool = True

    # 监控配置
    metrics_enabled: bool = True
    metrics_retention_days: int = 7
    alert_enabled: bool = True

    # 安全配置
    auth_enabled: bool = True
    token_expiry: int = 3600  # 秒
    max_login_attempts: int = 5

    class Config:
        use_enum_values = True
