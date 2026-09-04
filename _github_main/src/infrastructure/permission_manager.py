# 权限控制系统
# Agent OS - Infrastructure Layer
# Created: 2026-06-09

"""
权限控制系统
参考Hermes Agent设计，实现RBAC（基于角色的访问控制）
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""

    # 用户权限
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"

    # Agent权限
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"

    # 会话权限
    SESSION_CREATE = "session:create"
    SESSION_READ = "session:read"
    SESSION_DELETE = "session:delete"

    # 记忆权限
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"

    # 工具权限
    TOOL_EXECUTE = "tool:execute"
    TOOL_REGISTER = "tool:register"

    # 系统权限
    SYSTEM_ADMIN = "system:admin"
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"

    # 数据权限
    DATA_EXPORT = "data:export"
    DATA_IMPORT = "data:import"


class Role(Enum):
    """角色枚举"""

    ADMIN = "admin"  # 管理员
    POWER_USER = "power_user"  # 高级用户
    USER = "user"  # 普通用户
    GUEST = "guest"  # 访客
    AGENT = "agent"  # Agent角色


@dataclass
class PermissionRule:
    """权限规则"""

    rule_id: str
    resource: str  # 资源类型（user、agent、session等）
    action: str  # 动作（read、write、delete等）
    conditions: Dict[str, Any] = field(default_factory=dict)  # 条件
    effect: str = "allow"  # allow 或 deny
    priority: int = 0  # 优先级（数字越大优先级越高）
    enabled: bool = True

    def matches(self, resource: str, action: str, context: Dict[str, Any]) -> bool:
        """检查规则是否匹配"""
        if not self.enabled:
            return False

        # 检查资源和动作
        if self.resource != "*" and self.resource != resource:
            return False

        if self.action != "*" and self.action != action:
            return False

        # 检查条件
        for key, value in self.conditions.items():
            if key not in context or context[key] != value:
                return False

        return True


@dataclass
class AccessControlList:
    """访问控制列表"""

    acl_id: str
    resource_type: str  # 资源类型
    resource_id: str  # 资源ID
    permissions: Dict[str, List[str]] = field(
        default_factory=dict
    )  # user_id -> [permissions]
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def grant(self, user_id: str, permissions: List[str]):
        """授予权限"""
        if user_id not in self.permissions:
            self.permissions[user_id] = []

        for perm in permissions:
            if perm not in self.permissions[user_id]:
                self.permissions[user_id].append(perm)

        self.updated_at = datetime.now()

    def revoke(self, user_id: str, permissions: List[str]):
        """撤销权限"""
        if user_id in self.permissions:
            for perm in permissions:
                if perm in self.permissions[user_id]:
                    self.permissions[user_id].remove(perm)

            if not self.permissions[user_id]:
                del self.permissions[user_id]

        self.updated_at = datetime.now()

    def check_permission(self, user_id: str, permission: str) -> bool:
        """检查权限"""
        if user_id not in self.permissions:
            return False

        # 支持通配符
        for perm in self.permissions[user_id]:
            if perm == "*" or perm == permission:
                return True

            # 支持 resource:* 格式
            if perm.endswith(":*"):
                resource = perm.split(":")[0]
                if permission.startswith(f"{resource}:"):
                    return True

        return False


@dataclass
class RolePermissions:
    """角色权限配置"""

    role: Role
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""

    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有权限"""
        return permission in self.permissions


class PermissionManager:
    """权限管理器"""

    def __init__(self, data_dir: str = "data/permissions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 角色权限映射
        self.role_permissions: Dict[Role, RolePermissions] = {}

        # 权限规则
        self.permission_rules: Dict[str, PermissionRule] = {}

        # ACL列表
        self.acls: Dict[str, AccessControlList] = {}

        # 用户角色映射
        self.user_roles: Dict[str, Set[Role]] = {}

        # 初始化默认角色权限
        self._setup_default_roles()

        logger.info("初始化权限控制系统")

    def _setup_default_roles(self):
        """设置默认角色权限"""
        # 管理员 - 拥有所有权限
        self.role_permissions[Role.ADMIN] = RolePermissions(
            role=Role.ADMIN,
            permissions=set(Permission),
            description="系统管理员，拥有所有权限",
        )

        # 高级用户
        self.role_permissions[Role.POWER_USER] = RolePermissions(
            role=Role.POWER_USER,
            permissions={
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.AGENT_CREATE,
                Permission.AGENT_READ,
                Permission.AGENT_UPDATE,
                Permission.AGENT_EXECUTE,
                Permission.SESSION_CREATE,
                Permission.SESSION_READ,
                Permission.MEMORY_READ,
                Permission.MEMORY_WRITE,
                Permission.TOOL_EXECUTE,
                Permission.DATA_EXPORT,
                Permission.DATA_IMPORT,
            },
            description="高级用户，拥有大部分操作权限",
        )

        # 普通用户
        self.role_permissions[Role.USER] = RolePermissions(
            role=Role.USER,
            permissions={
                Permission.USER_READ,
                Permission.USER_WRITE,
                Permission.AGENT_READ,
                Permission.AGENT_EXECUTE,
                Permission.SESSION_CREATE,
                Permission.SESSION_READ,
                Permission.MEMORY_READ,
                Permission.MEMORY_WRITE,
                Permission.TOOL_EXECUTE,
            },
            description="普通用户，拥有基本操作权限",
        )

        # 访客
        self.role_permissions[Role.GUEST] = RolePermissions(
            role=Role.GUEST,
            permissions={
                Permission.USER_READ,
                Permission.AGENT_READ,
                Permission.SESSION_READ,
                Permission.MEMORY_READ,
            },
            description="访客，只有只读权限",
        )

        # Agent角色
        self.role_permissions[Role.AGENT] = RolePermissions(
            role=Role.AGENT,
            permissions={
                Permission.AGENT_READ,
                Permission.AGENT_EXECUTE,
                Permission.SESSION_CREATE,
                Permission.SESSION_READ,
                Permission.MEMORY_READ,
                Permission.MEMORY_WRITE,
                Permission.TOOL_EXECUTE,
            },
            description="Agent角色，用于Agent之间的权限控制",
        )

        logger.info("默认角色权限配置完成")

    def assign_role(self, user_id: str, role: Role):
        """分配角色"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = set()

        self.user_roles[user_id].add(role)
        logger.info(f"为用户 {user_id} 分配角色: {role.value}")

    def remove_role(self, user_id: str, role: Role):
        """移除角色"""
        if user_id in self.user_roles and role in self.user_roles[user_id]:
            self.user_roles[user_id].remove(role)
            logger.info(f"移除用户 {user_id} 的角色: {role.value}")

    def get_user_roles(self, user_id: str) -> List[Role]:
        """获取用户角色"""
        return list(self.user_roles.get(user_id, {Role.GUEST}))

    def check_permission(
        self,
        user_id: str,
        permission: Permission,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """检查权限"""
        context = context or {}

        # 1. 检查用户角色权限
        user_roles = self.get_user_roles(user_id)
        has_permission = False

        for role in user_roles:
            if role in self.role_permissions:
                if self.role_permissions[role].has_permission(permission):
                    has_permission = True
                    break

        if not has_permission:
            return False

        # 2. 检查ACL（如果指定了资源ID）
        if resource_id:
            # 构造ACL键
            resource_type = permission.value.split(":")[0]
            acl_key = f"{resource_type}:{resource_id}"

            if acl_key in self.acls:
                acl = self.acls[acl_key]
                if not acl.check_permission(user_id, permission.value):
                    return False

        # 3. 检查权限规则
        resource, action = permission.value.split(":")

        for rule in sorted(
            self.permission_rules.values(), key=lambda r: r.priority, reverse=True
        ):
            if rule.matches(resource, action, context):
                return rule.effect == "allow"

        # 默认允许
        return True

    def add_permission_rule(
        self,
        rule_id: str,
        resource: str,
        action: str,
        conditions: Dict[str, Any],
        effect: str = "allow",
        priority: int = 0,
    ):
        """添加权限规则"""
        self.permission_rules[rule_id] = PermissionRule(
            rule_id=rule_id,
            resource=resource,
            action=action,
            conditions=conditions,
            effect=effect,
            priority=priority,
        )
        logger.info(f"添加权限规则: {rule_id}")

    def remove_permission_rule(self, rule_id: str):
        """移除权限规则"""
        if rule_id in self.permission_rules:
            del self.permission_rules[rule_id]
            logger.info(f"移除权限规则: {rule_id}")

    def create_acl(
        self,
        resource_type: str,
        resource_id: str,
        initial_permissions: Optional[Dict[str, List[str]]] = None,
    ) -> str:
        """创建ACL"""
        acl_id = f"{resource_type}:{resource_id}"

        self.acls[acl_id] = AccessControlList(
            acl_id=acl_id,
            resource_type=resource_type,
            resource_id=resource_id,
            permissions=initial_permissions or {},
        )

        logger.info(f"创建ACL: {acl_id}")
        return acl_id

    def grant_permission(
        self, resource_type: str, resource_id: str, user_id: str, permissions: List[str]
    ):
        """授予权限"""
        acl_id = f"{resource_type}:{resource_id}"

        if acl_id not in self.acls:
            self.create_acl(resource_type, resource_id)

        self.acls[acl_id].grant(user_id, permissions)
        logger.info(f"授予权限: {user_id} -> {permissions} on {acl_id}")

    def revoke_permission(
        self, resource_type: str, resource_id: str, user_id: str, permissions: List[str]
    ):
        """撤销权限"""
        acl_id = f"{resource_type}:{resource_id}"

        if acl_id in self.acls:
            self.acls[acl_id].revoke(user_id, permissions)
            logger.info(f"撤销权限: {user_id} -> {permissions} on {acl_id}")

    def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """获取用户权限摘要"""
        roles = self.get_user_roles(user_id)
        permissions = set()

        for role in roles:
            if role in self.role_permissions:
                permissions.update(
                    perm.value for perm in self.role_permissions[role].permissions
                )

        return {
            "user_id": user_id,
            "roles": [role.value for role in roles],
            "permissions": list(permissions),
            "permission_count": len(permissions),
        }

    def save_state(self, filepath: Optional[str] = None):
        """保存状态"""
        filepath = filepath or self.data_dir / "permission_state.json"

        state = {
            "user_roles": {
                user_id: [role.value for role in roles]
                for user_id, roles in self.user_roles.items()
            },
            "permission_rules": {
                rule_id: {
                    "resource": rule.resource,
                    "action": rule.action,
                    "conditions": rule.conditions,
                    "effect": rule.effect,
                    "priority": rule.priority,
                    "enabled": rule.enabled,
                }
                for rule_id, rule in self.permission_rules.items()
            },
            "acls": {
                acl_id: {
                    "resource_type": acl.resource_type,
                    "resource_id": acl.resource_id,
                    "permissions": acl.permissions,
                    "created_at": acl.created_at.isoformat(),
                    "updated_at": acl.updated_at.isoformat(),
                }
                for acl_id, acl in self.acls.items()
            },
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        logger.info(f"权限状态已保存: {filepath}")

    def load_state(self, filepath: Optional[str] = None):
        """加载状态"""
        filepath = filepath or self.data_dir / "permission_state.json"

        if not Path(filepath).exists():
            logger.warning(f"权限状态文件不存在: {filepath}")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            state = json.load(f)

        # 恢复用户角色
        self.user_roles = {
            user_id: {Role(role) for role in roles}
            for user_id, roles in state.get("user_roles", {}).items()
        }

        # 恢复权限规则
        self.permission_rules = {}
        for rule_id, rule_data in state.get("permission_rules", {}).items():
            self.permission_rules[rule_id] = PermissionRule(
                rule_id=rule_id,
                resource=rule_data["resource"],
                action=rule_data["action"],
                conditions=rule_data["conditions"],
                effect=rule_data["effect"],
                priority=rule_data["priority"],
                enabled=rule_data["enabled"],
            )

        # 恢复ACL
        self.acls = {}
        for acl_id, acl_data in state.get("acls", {}).items():
            self.acls[acl_id] = AccessControlList(
                acl_id=acl_id,
                resource_type=acl_data["resource_type"],
                resource_id=acl_data["resource_id"],
                permissions=acl_data["permissions"],
                created_at=datetime.fromisoformat(acl_data["created_at"]),
                updated_at=datetime.fromisoformat(acl_data["updated_at"]),
            )

        logger.info(f"权限状态已加载: {filepath}")


# 全局实例
permission_manager = PermissionManager()


# 装饰器：权限检查
def require_permission(permission: Permission):
    """权限检查装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 提取user_id
            user_id = kwargs.get("user_id")
            if not user_id:
                raise PermissionError("未提供用户ID")

            # 检查权限
            if not permission_manager.check_permission(user_id, permission):
                raise PermissionError(f"权限不足: 需要 {permission.value}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# 示例用法
if __name__ == "__main__":
    # 测试权限管理
    pm = PermissionManager()

    # 分配角色
    pm.assign_role("user_123", Role.USER)
    pm.assign_role("user_456", Role.ADMIN)

    # 检查权限
    print("用户 user_123 检查权限:")
    print(f"  USER_READ: {pm.check_permission('user_123', Permission.USER_READ)}")
    print(f"  USER_DELETE: {pm.check_permission('user_123', Permission.USER_DELETE)}")

    print("\n用户 user_456 检查权限:")
    print(f"  USER_DELETE: {pm.check_permission('user_456', Permission.USER_DELETE)}")
    print(f"  SYSTEM_ADMIN: {pm.check_permission('user_456', Permission.SYSTEM_ADMIN)}")

    # 获取用户权限
    print("\n用户 user_123 权限摘要:")
    print(pm.get_user_permissions("user_123"))

    # ACL测试
    print("\n创建ACL并授予特定权限...")
    pm.grant_permission(
        resource_type="agent",
        resource_id="agent_001",
        user_id="user_123",
        permissions=["agent:update", "agent:execute"],
    )

    # 保存状态
    pm.save_state()
    print("\n权限状态已保存")
