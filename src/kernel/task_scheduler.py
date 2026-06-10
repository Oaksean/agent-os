# Task Scheduler
# Agent OS - Kernel Layer
# Created: 2026-06-09

"""
任务调度器模块
参考OpenClaw设计，实现动态任务分配和优先级队列
"""

import asyncio
import logging
import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass(order=True)
class Task:
    """任务对象"""
    priority: int = field(compare=False)
    created_at: datetime = field(compare=False)
    task_id: str = field(compare=False)
    name: str = field(compare=False)
    description: str = field(compare=False)
    function: Callable = field(compare=False)
    args: tuple = field(compare=False)
    kwargs: Dict[str, Any] = field(compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)
    
    def __post_init__(self):
        # 确保优先级正确
        if isinstance(self.priority, TaskPriority):
            self.priority = self.priority.value

class TaskScheduler:
    """任务调度器 - 参考OpenClaw设计"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.tasks = {}  # task_id -> Task
        self.priority_queue = []  # 优先级队列
        self.running_tasks = set()
        self.completed_tasks = []
        self.task_counter = 0
        self.lock = asyncio.Lock()
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "avg_completion_time": 0.0,
        }
        
        logger.info(f"初始化任务调度器，最大工作线程: {max_workers}")
    
    def generate_task_id(self) -> str:
        """生成任务ID"""
        self.task_counter += 1
        return f"task_{self.task_counter:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    async def submit(
        self,
        name: str,
        function: Callable,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        *args,
        **kwargs
    ) -> str:
        """提交新任务"""
        async with self.lock:
            task_id = self.generate_task_id()
            task = Task(
                priority=priority.value,
                created_at=datetime.now(),
                task_id=task_id,
                name=name,
                description=description,
                function=function,
                args=args,
                kwargs=kwargs
            )
            
            self.tasks[task_id] = task
            heapq.heappush(self.priority_queue, (task.priority, task_id))
            self.stats["total_tasks"] += 1
            
            logger.info(f"提交任务: {task_id} - {name} (优先级: {priority.name})")
            
            # 触发调度
            asyncio.create_task(self._schedule_tasks())
            
            return task_id
    
    async def _schedule_tasks(self):
        """调度任务执行"""
        async with self.lock:
            while len(self.running_tasks) < self.max_workers and self.priority_queue:
                _, task_id = heapq.heappop(self.priority_queue)
                task = self.tasks.get(task_id)
                
                if task and task.status == TaskStatus.PENDING:
                    self.running_tasks.add(task_id)
                    asyncio.create_task(self._execute_task(task))
    
    async def _execute_task(self, task: Task):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        logger.info(f"开始执行任务: {task.task_id} - {task.name}")
        
        try:
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.function):
                result = await task.function(*task.args, **task.kwargs)
            else:
                result = task.function(*task.args, **task.kwargs)
            
            task.result = result
            task.status = TaskStatus.COMPLETED
            self.stats["completed_tasks"] += 1
            logger.info(f"任务完成: {task.task_id} - {task.name}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            self.stats["failed_tasks"] += 1
            logger.error(f"任务失败: {task.task_id} - {task.name}: {e}")
        
        finally:
            task.completed_at = datetime.now()
            self.running_tasks.remove(task.task_id)
            
            # 更新统计
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                self._update_stats(duration)
            
            # 继续调度
            asyncio.create_task(self._schedule_tasks())
    
    def _update_stats(self, duration: float):
        """更新统计信息"""
        completed = self.stats["completed_tasks"]
        current_avg = self.stats["avg_completion_time"]
        
        # 计算新的平均值
        if completed == 1:
            self.stats["avg_completion_time"] = duration
        else:
            self.stats["avg_completion_time"] = (
                (current_avg * (completed - 1) + duration) / completed
            )
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.task_id,
            "name": task.name,
            "description": task.description,
            "status": task.status.value,
            "priority": TaskPriority(task.priority).name,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "error": task.error,
        }
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            **self.stats,
            "pending_tasks": len(self.priority_queue),
            "running_tasks": len(self.running_tasks),
            "total_queued_tasks": len(self.tasks),
            "max_workers": self.max_workers,
        }
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        async with self.lock:
            task = self.tasks.get(task_id)
            if not task:
                return False
            
            if task.status == TaskStatus.PENDING:
                # 从优先级队列中移除
                new_queue = []
                for priority, tid in self.priority_queue:
                    if tid != task_id:
                        new_queue.append((priority, tid))
                
                self.priority_queue = new_queue
                heapq.heapify(self.priority_queue)
                task.status = TaskStatus.CANCELLED
                logger.info(f"取消任务: {task_id}")
                return True
            
            elif task.status == TaskStatus.RUNNING:
                # 无法取消运行中的任务
                logger.warning(f"无法取消运行中的任务: {task_id}")
                return False
            
            return False

# 示例用法
if __name__ == "__main__":
    import time
    
    async def example_task(name: str, duration: float = 1.0):
        """示例任务"""
        print(f"任务 {name} 开始执行")
        await asyncio.sleep(duration)
        print(f"任务 {name} 执行完成")
        return f"{name}_result"
    
    async def main():
        scheduler = TaskScheduler(max_workers=2)
        
        # 提交任务
        task1_id = await scheduler.submit(
            name="数据处理",
            function=example_task,
            description="处理用户数据",
            priority=TaskPriority.HIGH,
            args=("数据处理", 2.0)
        )
        
        task2_id = await scheduler.submit(
            name="模型推理",
            function=example_task,
            description="运行AI模型",
            priority=TaskPriority.CRITICAL,
            args=("模型推理", 1.0)
        )
        
        task3_id = await scheduler.submit(
            name="日志清理",
            function=example_task,
            description="清理旧日志",
            priority=TaskPriority.LOW,
            args=("日志清理", 0.5)
        )
        
        # 等待任务完成
        await asyncio.sleep(3)
        
        # 获取状态
        stats = await scheduler.get_stats()
        print(f"调度器统计: {stats}")
        
        for task_id in [task1_id, task2_id, task3_id]:
            status = await scheduler.get_task_status(task_id)
            print(f"任务状态 {task_id}: {status}")
    
    asyncio.run(main())