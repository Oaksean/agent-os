"""
工具注册与发现
统一管理Agent可用的所有工具
"""

import json
import inspect
from typing import Dict, List, Any, Optional, Callable, Type, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class ToolCategory(Enum):
    """工具类别"""
    WEB = "web"
    FILE = "file"
    DATABASE = "database"
    NETWORK = "network"
    AI = "ai"
    SYSTEM = "system"
    CUSTOM = "custom"

@dataclass
class ParameterSchema:
    """参数模式定义"""
    name: str
    type: str  # "string", "integer", "number", "boolean", "array", "object"
    description: str = ""
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为OpenAPI兼容的字典"""
        schema = {
            "type": self.type,
            "description": self.description
        }
        
        if self.default is not None:
            schema["default"] = self.default
        
        if self.enum:
            schema["enum"] = self.enum
            
        return schema

@dataclass
class ToolDefinition:
    """工具定义"""
    name: str
    description: str
    category: ToolCategory
    function: Callable
    parameters: List[ParameterSchema] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    rate_limit: Optional[int] = None  # 每分钟调用次数限制
    timeout: float = 30.0  # 超时时间（秒）
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为OpenAPI兼容的字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": {
                "type": "object",
                "properties": {p.name: p.to_dict() for p in self.parameters},
                "required": [p.name for p in self.parameters if p.required]
            },
            "returns": self.returns,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout
        }

class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self.categories: Dict[ToolCategory, List[str]] = {cat: [] for cat in ToolCategory}
        self.call_history: List[Dict[str, Any]] = []
        
    def register(self, tool_def: ToolDefinition) -> bool:
        """注册工具"""
        if tool_def.name in self.tools:
            logger.warning(f"工具已存在: {tool_def.name}")
            return False
        
        # 验证工具函数
        if not callable(tool_def.function):
            logger.error(f"工具函数不可调用: {tool_def.name}")
            return False
        
        # 添加到注册表
        self.tools[tool_def.name] = tool_def
        self.categories[tool_def.category].append(tool_def.name)
        
        logger.info(f"工具注册成功: {tool_def.name} ({tool_def.category.value})")
        return True
    
    def register_decorator(self, name: str, description: str, category: ToolCategory, **kwargs):
        """工具注册装饰器"""
        def decorator(func: Callable):
            # 从函数签名提取参数信息
            sig = inspect.signature(func)
            parameters = []
            
            for param_name, param in sig.parameters.items():
                if param_name == "self":
                    continue
                    
                # 推断参数类型
                param_type = "string"
                if param.annotation != inspect.Parameter.empty:
                    type_name = str(param.annotation)
                    if "int" in type_name:
                        param_type = "integer"
                    elif "float" in type_name or "number" in type_name:
                        param_type = "number"
                    elif "bool" in type_name:
                        param_type = "boolean"
                    elif "list" in type_name or "List" in type_name:
                        param_type = "array"
                    elif "dict" in type_name or "Dict" in type_name:
                        param_type = "object"
                
                # 推断是否必需
                required = param.default == inspect.Parameter.empty
                
                param_schema = ParameterSchema(
                    name=param_name,
                    type=param_type,
                    description=f"参数: {param_name}",
                    required=required,
                    default=param.default if not required else None
                )
                parameters.append(param_schema)
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=name,
                description=description,
                category=category,
                function=func,
                parameters=parameters,
                **kwargs
            )
            
            # 注册工具
            self.register(tool_def)
            
            # 返回包装后的函数
            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            
            return wrapper
        
        return decorator
    
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """获取工具定义"""
        return self.tools.get(name)
    
    def list_tools(self, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """列出工具"""
        if category:
            tool_names = self.categories.get(category, [])
            return [self.tools[name] for name in tool_names if name in self.tools]
        else:
            return list(self.tools.values())
    
    def search_tools(self, query: str, category: Optional[ToolCategory] = None) -> List[ToolDefinition]:
        """搜索工具"""
        results = []
        query_lower = query.lower()
        
        tools_to_search = self.list_tools(category)
        
        for tool in tools_to_search:
            # 搜索名称、描述和标签
            if (query_lower in tool.name.lower() or
                query_lower in tool.description.lower() or
                any(query_lower in tag.lower() for tag in tool.tags)):
                results.append(tool)
        
        return results
    
    async def execute(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self.tools:
            return {
                "success": False,
                "error": f"工具不存在: {tool_name}",
                "available_tools": list(self.tools.keys())
            }
        
        tool_def = self.tools[tool_name]
        
        # 记录调用历史
        call_record = {
            "tool": tool_name,
            "timestamp": self._get_timestamp(),
            "parameters": kwargs,
            "status": "started"
        }
        self.call_history.append(call_record)
        
        try:
            # 检查速率限制
            if not self._check_rate_limit(tool_def):
                return {
                    "success": False,
                    "error": f"速率限制超出: {tool_name}",
                    "rate_limit": tool_def.rate_limit
                }
            
            # 验证参数
            validation_result = self._validate_parameters(tool_def, kwargs)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": "参数验证失败",
                    "details": validation_result["errors"]
                }
            
            # 执行工具
            import asyncio
            if inspect.iscoroutinefunction(tool_def.function):
                # 异步函数
                result = await asyncio.wait_for(
                    tool_def.function(**kwargs),
                    timeout=tool_def.timeout
                )
            else:
                # 同步函数
                result = tool_def.function(**kwargs)
            
            # 更新调用记录
            call_record["status"] = "completed"
            call_record["result"] = result
            call_record["execution_time"] = self._get_timestamp()  # 实际应该计算耗时
            
            logger.info(f"工具执行成功: {tool_name}")
            return {
                "success": True,
                "result": result,
                "tool": tool_name,
                "execution_time": call_record.get("execution_time", 0)
            }
            
        except asyncio.TimeoutError:
            call_record["status"] = "timeout"
            logger.error(f"工具执行超时: {tool_name}")
            return {
                "success": False,
                "error": f"工具执行超时: {tool_name}",
                "timeout": tool_def.timeout
            }
        except Exception as e:
            call_record["status"] = "error"
            call_record["error"] = str(e)
            logger.error(f"工具执行错误: {tool_name}, 错误: {e}")
            return {
                "success": False,
                "error": f"工具执行错误: {str(e)}",
                "tool": tool_name
            }
    
    def _validate_parameters(self, tool_def: ToolDefinition, params: Dict[str, Any]) -> Dict[str, Any]:
        """验证参数"""
        errors = []
        
        # 检查必需参数
        for param in tool_def.parameters:
            if param.required and param.name not in params:
                errors.append(f"缺少必需参数: {param.name}")
        
        # 检查未知参数
        param_names = {p.name for p in tool_def.parameters}
        for param_name in params.keys():
            if param_name not in param_names:
                errors.append(f"未知参数: {param_name}")
        
        # 类型检查（简化版本）
        for param in tool_def.parameters:
            if param.name in params:
                value = params[param.name]
                
                # 基本类型检查
                if param.type == "string" and not isinstance(value, str):
                    errors.append(f"参数 {param.name} 应为字符串类型")
                elif param.type == "integer" and not isinstance(value, int):
                    errors.append(f"参数 {param.name} 应为整数类型")
                elif param.type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"参数 {param.name} 应为数字类型")
                elif param.type == "boolean" and not isinstance(value, bool):
                    errors.append(f"参数 {param.name} 应为布尔类型")
                elif param.type == "array" and not isinstance(value, list):
                    errors.append(f"参数 {param.name} 应为数组类型")
                elif param.type == "object" and not isinstance(value, dict):
                    errors.append(f"参数 {param.name} 应为对象类型")
                
                # 枚举值检查
                if param.enum and value not in param.enum:
                    errors.append(f"参数 {param.name} 的值必须在 {param.enum} 中")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _check_rate_limit(self, tool_def: ToolDefinition) -> bool:
        """检查速率限制"""
        if not tool_def.rate_limit:
            return True
        
        # 计算过去一分钟内的调用次数
        import time
        one_minute_ago = time.time() - 60
        recent_calls = [
            call for call in self.call_history
            if call.get("tool") == tool_def.name and 
            call.get("timestamp", 0) > one_minute_ago
        ]
        
        return len(recent_calls) < tool_def.rate_limit
    
    def _get_timestamp(self) -> float:
        """获取时间戳"""
        import time
        return time.time()
    
    def get_call_history(self, tool_name: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """获取调用历史"""
        history = self.call_history.copy()
        
        if tool_name:
            history = [call for call in history if call.get("tool") == tool_name]
        
        return history[-limit:] if limit > 0 else history
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "tools": {name: tool.to_dict() for name, tool in self.tools.items()},
            "categories": {cat.value: tools for cat, tools in self.categories.items()},
            "total_tools": len(self.tools)
        }

# 全局工具注册表实例
_tool_registry_instance = None

def get_tool_registry() -> ToolRegistry:
    """获取工具注册表单例"""
    global _tool_registry_instance
    if _tool_registry_instance is None:
        _tool_registry_instance = ToolRegistry()
    return _tool_registry_instance

# 示例工具函数
def example_web_search(query: str, limit: int = 10) -> Dict[str, Any]:
    """示例：网页搜索工具"""
    return {
        "query": query,
        "limit": limit,
        "results": [
            {"title": "示例结果1", "url": "https://example.com/1", "snippet": "这是示例结果1"},
            {"title": "示例结果2", "url": "https://example.com/2", "snippet": "这是示例结果2"}
        ]
    }

def example_file_read(filepath: str) -> Dict[str, Any]:
    """示例：文件读取工具"""
    import os
    if not os.path.exists(filepath):
        return {"success": False, "error": f"文件不存在: {filepath}"}
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "filepath": filepath,
            "content": content,
            "size": len(content)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def example_calculator(operation: str, a: float, b: float) -> Dict[str, Any]:
    """示例：计算器工具"""
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else None
    }
    
    if operation not in operations:
        return {"success": False, "error": f"不支持的操作: {operation}", "supported": list(operations.keys())}
    
    try:
        result = operations[operation](a, b)
        if result is None:
            return {"success": False, "error": "除以零错误"}
        
        return {
            "success": True,
            "operation": operation,
            "a": a,
            "b": b,
            "result": result
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
