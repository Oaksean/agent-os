"""
分层任务规划器
基于HTN（分层任务网络）和LLM的任务分解
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
import asyncio

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1  # 1-5, 5为最高
    estimated_duration: float = 0.0  # 预估耗时（秒）
    dependencies: List[str] = field(default_factory=list)  # 依赖的任务ID
    subtasks: List["Task"] = field(default_factory=list)  # 子任务
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority,
            "estimated_duration": self.estimated_duration,
            "dependencies": self.dependencies,
            "subtasks": [subtask.to_dict() for subtask in self.subtasks],
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata
        }

class HierarchicalPlanner:
    """分层任务规划器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0
        
    async def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Task:
        """为给定目标创建计划"""
        logger.info(f"开始规划: {goal}")
        
        # 生成任务ID
        task_id = f"task_{self.task_counter:04d}"
        self.task_counter += 1
        
        # 创建主任务
        main_task = Task(
            id=task_id,
            name="主任务",
            description=goal,
            status=TaskStatus.PENDING
        )
        
        self.tasks[task_id] = main_task
        
        # 使用LLM分解任务（如果可用）
        if self.llm_client:
            subtasks = await self._decompose_with_llm(goal, context)
        else:
            subtasks = self._decompose_manually(goal)
        
        # 创建子任务
        for i, subtask_desc in enumerate(subtasks):
            subtask_id = f"{task_id}_sub{i:03d}"
            subtask = Task(
                id=subtask_id,
                name=f"子任务{i+1}",
                description=subtask_desc,
                status=TaskStatus.PENDING,
                priority=main_task.priority
            )
            main_task.subtasks.append(subtask)
            self.tasks[subtask_id] = subtask
        
        logger.info(f"规划完成: {goal}, 生成{len(subtasks)}个子任务")
        return main_task
    
    async def _decompose_with_llm(self, goal: str, context: Optional[Dict[str, Any]] = None) -> List[str]:
        """使用LLM分解任务"""
        try:
            prompt = f"""请将以下目标分解为具体的执行步骤：

目标：{goal}

{context.get('constraints', '') if context else ''}

请将目标分解为3-8个具体的、可执行的步骤。每个步骤应该：
1. 是具体的动作
2. 有明确的完成标准
3. 可以独立执行或检查

请以JSON数组格式返回步骤，例如：["步骤1描述", "步骤2描述", ...]"""
            
            # 这里应该调用实际的LLM客户端
            # response = await self.llm_client.complete(prompt)
            # 模拟响应
            response = '[' + '
' + '    "分析任务需求和约束条件",' + '
' + '    "收集必要的信息和资源",' + '
' + '    "设计解决方案的架构",' + '
' + '    "实现核心功能模块",' + '
' + '    "测试和验证功能",' + '
' + '    "优化性能和用户体验",' + '
' + '    "编写文档和说明"' + '
' + ']'
            
            # 解析JSON响应
            import json
            try:
                steps = json.loads(response)
                if isinstance(steps, list) and all(isinstance(s, str) for s in steps):
                    return steps
            except json.JSONDecodeError:
                # 如果JSON解析失败，尝试从文本中提取
                pass
            
            # 尝试从文本中提取步骤
            steps = []
            lines = response.split('
')
            for line in lines:
                line = line.strip()
                # 匹配数字开头的步骤
                match = re.match(r'^(\d+)[\.、]?\s*(.+)$', line)
                if match:
                    steps.append(match.group(2))
                elif line and len(line) > 10 and not line.startswith('[') and not line.startswith('{'):
                    steps.append(line)
            
            return steps[:8]  # 最多返回8个步骤
            
        except Exception as e:
            logger.error(f"LLM分解失败: {e}")
            return self._decompose_manually(goal)
    
    def _decompose_manually(self, goal: str) -> List[str]:
        """手动分解任务（备用方案）"""
        # 简单的基于关键词的分解
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ["开发", "实现", "构建", "创建"]):
            return [
                "分析需求",
                "设计架构",
                "实现核心功能",
                "编写测试",
                "集成测试",
                "部署上线"
            ]
        elif any(word in goal_lower for word in ["分析", "研究", "调查"]):
            return [
                "定义研究问题",
                "收集数据",
                "分析数据",
                "得出结论",
                "撰写报告"
            ]
        elif any(word in goal_lower for word in ["修复", "调试", "解决"]):
            return [
                "重现问题",
                "定位原因",
                "设计修复方案",
                "实施修复",
                "验证修复"
            ]
        else:
            return [
                "分析任务",
                "制定计划",
                "执行任务",
                "检查结果",
                "完成交付"
            ]
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          result: Any = None, error: str = None) -> bool:
        """更新任务状态"""
        if task_id not in self.tasks:
            logger.error(f"任务不存在: {task_id}")
            return False
        
        task = self.tasks[task_id]
        task.status = status
        
        if result is not None:
            task.result = result
        
        if error is not None:
            task.error = error
        
        logger.debug(f"任务状态更新: {task_id} -> {status.value}")
        
        # 如果父任务的所有子任务都完成，更新父任务状态
        if "_sub" in task_id:
            parent_id = task_id.rsplit("_sub", 1)[0]
            if parent_id in self.tasks:
                parent_task = self.tasks[parent_id]
                all_completed = all(
                    subtask.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
                    for subtask in parent_task.subtasks
                )
                
                if all_completed:
                    # 检查是否有失败的任务
                    has_failed = any(subtask.status == TaskStatus.FAILED for subtask in parent_task.subtasks)
                    parent_task.status = TaskStatus.FAILED if has_failed else TaskStatus.COMPLETED
        
        return True
    
    def get_ready_tasks(self) -> List[Task]:
        """获取就绪的任务（无依赖或依赖已完成）"""
        ready_tasks = []
        
        for task_id, task in self.tasks.items():
            if task.status != TaskStatus.PENDING:
                continue
            
            # 检查依赖
            dependencies_met = True
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                ready_tasks.append(task)
        
        # 按优先级排序
        ready_tasks.sort(key=lambda t: t.priority, reverse=True)
        return ready_tasks
    
    def visualize_plan(self, task_id: str) -> str:
        """可视化任务计划"""
        if task_id not in self.tasks:
            return f"任务不存在: {task_id}"
        
        task = self.tasks[task_id]
        
        def build_tree(t: Task, level: int = 0) -> str:
            indent = "  " * level
            status_symbol = {
                TaskStatus.PENDING: "○",
                TaskStatus.READY: "→",
                TaskStatus.RUNNING: "▶",
                TaskStatus.COMPLETED: "✓",
                TaskStatus.FAILED: "✗",
                TaskStatus.CANCELLED: "⨯"
            }.get(t.status, "?")
            
            tree = f"{indent}{status_symbol} [{t.id}] {t.name}
"
            tree += f"{indent}    {t.description[:50]}{'...' if len(t.description) > 50 else ''}
"
            
            for subtask in t.subtasks:
                tree += build_tree(subtask, level + 1)
            
            return tree
        
        return f"任务计划: {task.name}
{build_tree(task)}"
    
    def to_dict(self) -> Dict[str, Any]:
        """导出为字典"""
        return {
            "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
            "task_counter": self.task_counter
        }
    
    def from_dict(self, data: Dict[str, Any]) -> None:
        """从字典导入"""
        self.tasks.clear()
        
        if "tasks" in data:
            for task_id, task_data in data["tasks"].items():
                # 递归创建任务对象
                task = self._create_task_from_dict(task_data)
                self.tasks[task_id] = task
        
        if "task_counter" in data:
            self.task_counter = data["task_counter"]
    
    def _create_task_from_dict(self, data: Dict[str, Any]) -> Task:
        """从字典创建任务对象"""
        # 先创建子任务
        subtasks = []
        for subtask_data in data.get("subtasks", []):
            subtask = self._create_task_from_dict(subtask_data)
            subtasks.append(subtask)
        
        # 创建任务
        task = Task(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            status=TaskStatus(data["status"]),
            priority=data.get("priority", 1),
            estimated_duration=data.get("estimated_duration", 0.0),
            dependencies=data.get("dependencies", []),
            subtasks=subtasks,
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )
        
        return task
