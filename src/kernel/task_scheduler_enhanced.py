# Enhanced Task Scheduler with Cron Support
# Agent OS - Kernel Layer
# Created: 2026-06-10

"""
增强版任务调度器
新增功能：
1. Cron定时调度 - 支持类似Linux Cron的定时任务
2. 任务持久化 - 任务状态保存到JSON文件
3. 任务分配策略 - 智能分配任务到工作线程
"""

import asyncio
import logging
import heapq
import json
import os
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable, Set
from datetime import datetime, timedelta
from pathlib import Path
import threading
from croniter import croniter

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
    SCHEDULED = "scheduled"  # 新增：已调度（定时任务）
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"  # 新增：等待重试


class TaskType(Enum):
    """任务类型"""

    IMMEDIATE = "immediate"  # 立即执行
    SCHEDULED = "scheduled"  # 定时执行
    RECURRING = "recurring"  # 周期执行


class TaskAllocationStrategy(Enum):
    """任务分配策略"""

    ROUND_ROBIN = "round_robin"  # 轮询
    PRIORITY_FIRST = "priority_first"  # 优先级优先
    LOAD_BALANCE = "load_balance"  # 负载均衡
    AFFINITY = "affinity"  # 亲和性调度


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
    task_type: TaskType = field(default=TaskType.IMMEDIATE, compare=False)
    result: Any = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    started_at: Optional[datetime] = field(default=None, compare=False)
    completed_at: Optional[datetime] = field(default=None, compare=False)

    # 新增字段
    cron_expression: Optional[str] = field(default=None, compare=False)
    next_run_time: Optional[datetime] = field(default=None, compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)
    worker_id: Optional[int] = field(default=None, compare=False)
    tags: List[str] = field(default_factory=list, compare=False)

    def __post_init__(self):
        if isinstance(self.priority, TaskPriority):
            self.priority = self.priority.value

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于持久化）"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "status": self.status.value,
            "task_type": self.task_type.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "cron_expression": self.cron_expression,
            "next_run_time": self.next_run_time.isoformat()
            if self.next_run_time
            else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "worker_id": self.worker_id,
            "tags": self.tags,
        }


class CronScheduler:
    """Cron定时调度器"""

    def __init__(self):
        self.cron_jobs: Dict[str, Task] = {}
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None

    async def add_cron_job(self, task: Task) -> bool:
        """添加Cron任务"""
        if not task.cron_expression:
            logger.error(f"任务 {task.task_id} 缺少cron表达式")
            return False

        try:
            # 验证cron表达式
            cron = croniter(task.cron_expression, datetime.now())
            task.next_run_time = cron.get_next(datetime)
            task.task_type = TaskType.RECURRING
            task.status = TaskStatus.SCHEDULED

            self.cron_jobs[task.task_id] = task
            logger.info(
                f"添加Cron任务: {task.task_id} - {task.name}, 下次运行: {task.next_run_time}"
            )
            return True

        except Exception as e:
            logger.error(f"添加Cron任务失败: {e}")
            return False

    async def remove_cron_job(self, task_id: str) -> bool:
        """移除Cron任务"""
        if task_id in self.cron_jobs:
            del self.cron_jobs[task_id]
            logger.info(f"移除Cron任务: {task_id}")
            return True
        return False

    def get_next_run_time(self, cron_expression: str) -> Optional[datetime]:
        """获取下次运行时间"""
        try:
            cron = croniter(cron_expression, datetime.now())
            return cron.get_next(datetime)
        except Exception as e:
            logger.error(f"解析cron表达式失败: {e}")
            return None

    async def start(self):
        """启动Cron调度器"""
        if self.running:
            return

        self.running = True
        self.scheduler_task = asyncio.create_task(self._run_scheduler())
        logger.info("Cron调度器已启动")

    async def stop(self):
        """停止Cron调度器"""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Cron调度器已停止")

    async def _run_scheduler(self):
        """运行调度循环"""
        while self.running:
            try:
                now = datetime.now()

                for task_id, task in list(self.cron_jobs.items()):
                    if task.next_run_time and task.next_run_time <= now:
                        # 触发任务执行
                        logger.info(f"Cron任务到期: {task_id} - {task.name}")

                        # 这里不直接执行，而是返回给TaskScheduler处理
                        yield task

                        # 计算下次运行时间
                        if task.cron_expression:
                            cron = croniter(task.cron_expression, now)
                            task.next_run_time = cron.get_next(datetime)

                # 每10秒检查一次
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Cron调度器错误: {e}")
                await asyncio.sleep(5)


class TaskPersistence:
    """任务持久化管理器"""

    def __init__(self, storage_dir: str = "data/tasks"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.storage_dir / "tasks.json"
        self.lock = asyncio.Lock()

    async def save_tasks(self, tasks: Dict[str, Task]) -> bool:
        """保存任务到文件"""
        async with self.lock:
            try:
                data = {task_id: task.to_dict() for task_id, task in tasks.items()}

                with open(self.tasks_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                logger.info(f"保存 {len(tasks)} 个任务到 {self.tasks_file}")
                return True

            except Exception as e:
                logger.error(f"保存任务失败: {e}")
                return False

    async def load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """从文件加载任务"""
        async with self.lock:
            try:
                if not self.tasks_file.exists():
                    logger.info("任务文件不存在，创建新文件")
                    return {}

                with open(self.tasks_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                logger.info(f"加载 {len(data)} 个任务从 {self.tasks_file}")
                return data

            except Exception as e:
                logger.error(f"加载任务失败: {e}")
                return {}

    async def save_cron_jobs(self, cron_jobs: Dict[str, Task]) -> bool:
        """保存Cron任务"""
        try:
            cron_file = self.storage_dir / "cron_jobs.json"
            data = {task_id: task.to_dict() for task_id, task in cron_jobs.items()}

            with open(cron_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"保存 {len(cron_jobs)} 个Cron任务")
            return True

        except Exception as e:
            logger.error(f"保存Cron任务失败: {e}")
            return False


class TaskAllocator:
    """任务分配器 - 智能分配任务到工作线程"""

    def __init__(
        self, strategy: TaskAllocationStrategy = TaskAllocationStrategy.LOAD_BALANCE
    ):
        self.strategy = strategy
        self.worker_loads: Dict[int, int] = {}  # worker_id -> 当前任务数
        self.task_history: Dict[str, int] = {}  # task_name -> worker_id (亲和性调度)
        self.current_worker = 0  # 轮询调度

    def allocate(self, task: Task, available_workers: Set[int]) -> Optional[int]:
        """分配任务到工作线程"""
        if not available_workers:
            return None

        if self.strategy == TaskAllocationStrategy.ROUND_ROBIN:
            return self._round_robin(available_workers)
        elif self.strategy == TaskAllocationStrategy.PRIORITY_FIRST:
            return self._priority_first(available_workers)
        elif self.strategy == TaskAllocationStrategy.LOAD_BALANCE:
            return self._load_balance(available_workers)
        elif self.strategy == TaskAllocationStrategy.AFFINITY:
            return self._affinity(task, available_workers)
        else:
            return min(available_workers)

    def _round_robin(self, available_workers: Set[int]) -> int:
        """轮询调度"""
        workers = sorted(available_workers)
        worker_id = workers[self.current_worker % len(workers)]
        self.current_worker += 1
        return worker_id

    def _priority_first(self, available_workers: Set[int]) -> int:
        """优先级优先调度 - 选择负载最低的"""
        return min(available_workers, key=lambda w: self.worker_loads.get(w, 0))

    def _load_balance(self, available_workers: Set[int]) -> int:
        """负载均衡调度"""
        # 选择当前负载最小的worker
        min_load = float("inf")
        selected_worker = None

        for worker_id in available_workers:
            load = self.worker_loads.get(worker_id, 0)
            if load < min_load:
                min_load = load
                selected_worker = worker_id

        return selected_worker if selected_worker else min(available_workers)

    def _affinity(self, task: Task, available_workers: Set[int]) -> int:
        """亲和性调度 - 相同任务分配到相同worker"""
        # 如果任务之前执行过，尝试分配到相同的worker
        if task.name in self.task_history:
            preferred_worker = self.task_history[task.name]
            if preferred_worker in available_workers:
                return preferred_worker

        # 否则使用负载均衡
        worker_id = self._load_balance(available_workers)
        self.task_history[task.name] = worker_id
        return worker_id

    def update_load(self, worker_id: int, delta: int):
        """更新worker负载"""
        current = self.worker_loads.get(worker_id, 0)
        self.worker_loads[worker_id] = max(0, current + delta)


class EnhancedTaskScheduler:
    """增强版任务调度器"""

    def __init__(
        self,
        max_workers: int = 4,
        allocation_strategy: TaskAllocationStrategy = TaskAllocationStrategy.LOAD_BALANCE,
        persistence_enabled: bool = True,
        storage_dir: str = "data/tasks",
    ):
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.priority_queue = []
        self.running_tasks: Set[str] = set()
        self.worker_status: Dict[int, str] = {i: "idle" for i in range(max_workers)}

        # 新增组件
        self.cron_scheduler = CronScheduler()
        self.persistence = TaskPersistence(storage_dir) if persistence_enabled else None
        self.allocator = TaskAllocator(allocation_strategy)

        self.task_counter = 0
        self.lock = asyncio.Lock()
        self.running = False

        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "retry_tasks": 0,
            "avg_completion_time": 0.0,
            "avg_wait_time": 0.0,
        }

        logger.info(
            f"初始化增强版任务调度器，最大工作线程: {max_workers}, 策略: {allocation_strategy.value}"
        )

    def generate_task_id(self) -> str:
        """生成任务ID"""
        self.task_counter += 1
        return (
            f"task_{self.task_counter:06d}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    async def submit(
        self,
        name: str,
        function: Callable,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        tags: List[str] = None,
        max_retries: int = 3,
        *args,
        **kwargs,
    ) -> str:
        """提交立即执行的任务"""
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
                kwargs=kwargs,
                tags=tags or [],
                max_retries=max_retries,
            )

            self.tasks[task_id] = task
            heapq.heappush(
                self.priority_queue, (task.priority, task.created_at, task_id)
            )
            self.stats["total_tasks"] += 1

            logger.info(f"提交任务: {task_id} - {name} (优先级: {priority.name})")

            # 持久化
            if self.persistence:
                await self.persistence.save_tasks(self.tasks)

            # 触发调度
            asyncio.create_task(self._schedule_tasks())

            return task_id

    async def schedule_cron(
        self,
        name: str,
        function: Callable,
        cron_expression: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        tags: List[str] = None,
        *args,
        **kwargs,
    ) -> str:
        """提交Cron定时任务"""
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
                kwargs=kwargs,
                cron_expression=cron_expression,
                tags=tags or [],
            )

            # 添加到Cron调度器
            success = await self.cron_scheduler.add_cron_job(task)
            if success:
                self.tasks[task_id] = task
                self.stats["total_tasks"] += 1

                # 持久化
                if self.persistence:
                    await self.persistence.save_cron_jobs(self.cron_scheduler.cron_jobs)

                logger.info(
                    f"提交Cron任务: {task_id} - {name}, 表达式: {cron_expression}"
                )
                return task_id
            else:
                raise ValueError(f"无效的Cron表达式: {cron_expression}")

    async def start(self):
        """启动调度器"""
        if self.running:
            return

        self.running = True

        # 加载持久化的任务
        if self.persistence:
            saved_tasks = await self.persistence.load_tasks()
            logger.info(f"加载 {len(saved_tasks)} 个已保存的任务")

        # 启动Cron调度器
        await self.cron_scheduler.start()

        # 启动Cron任务监听
        asyncio.create_task(self._process_cron_tasks())

        logger.info("增强版任务调度器已启动")

    async def stop(self):
        """停止调度器"""
        self.running = False
        await self.cron_scheduler.stop()

        # 保存任务状态
        if self.persistence:
            await self.persistence.save_tasks(self.tasks)

        logger.info("增强版任务调度器已停止")

    async def _process_cron_tasks(self):
        """处理Cron任务"""
        async for task in self.cron_scheduler._run_scheduler():
            # Cron任务到期，添加到优先级队列
            async with self.lock:
                heapq.heappush(
                    self.priority_queue, (task.priority, task.created_at, task.task_id)
                )

            # 触发调度
            asyncio.create_task(self._schedule_tasks())

    async def _schedule_tasks(self):
        """调度任务执行"""
        async with self.lock:
            while self.priority_queue:
                # 找到空闲的worker
                available_workers = {
                    worker_id
                    for worker_id, status in self.worker_status.items()
                    if status == "idle"
                }

                if not available_workers:
                    break

                _, _, task_id = heapq.heappop(self.priority_queue)
                task = self.tasks.get(task_id)

                if task and task.status == TaskStatus.PENDING:
                    # 分配worker
                    worker_id = self.allocator.allocate(task, available_workers)

                    if worker_id is not None:
                        task.worker_id = worker_id
                        task.status = TaskStatus.RUNNING
                        self.running_tasks.add(task_id)
                        self.worker_status[worker_id] = "busy"
                        self.allocator.update_load(worker_id, 1)

                        # 执行任务
                        asyncio.create_task(self._execute_task(task, worker_id))

    async def _execute_task(self, task: Task, worker_id: int):
        """执行任务"""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        logger.info(f"[Worker-{worker_id}] 开始执行任务: {task.task_id} - {task.name}")

        try:
            # 执行任务函数
            if asyncio.iscoroutinefunction(task.function):
                result = await task.function(*task.args, **task.kwargs)
            else:
                result = task.function(*task.args, **task.kwargs)

            task.result = result
            task.status = TaskStatus.COMPLETED
            self.stats["completed_tasks"] += 1
            logger.info(f"[Worker-{worker_id}] 任务完成: {task.task_id} - {task.name}")

        except Exception as e:
            task.error = str(e)

            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRY
                self.stats["retry_tasks"] += 1
                logger.warning(
                    f"[Worker-{worker_id}] 任务失败，准备重试 ({task.retry_count}/{task.max_retries}): {task.task_id} - {task.name}"
                )

                # 重新加入队列
                await asyncio.sleep(2**task.retry_count)  # 指数退避
                heapq.heappush(
                    self.priority_queue, (task.priority, task.created_at, task.task_id)
                )
            else:
                task.status = TaskStatus.FAILED
                self.stats["failed_tasks"] += 1
                logger.error(
                    f"[Worker-{worker_id}] 任务最终失败: {task.task_id} - {task.name}: {e}"
                )

        finally:
            task.completed_at = datetime.now()
            self.running_tasks.discard(task.task_id)
            self.worker_status[worker_id] = "idle"
            self.allocator.update_load(worker_id, -1)

            # 更新统计
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                self._update_stats(duration)

            # 持久化
            if self.persistence:
                await self.persistence.save_tasks(self.tasks)

            # 继续调度
            asyncio.create_task(self._schedule_tasks())

    def _update_stats(self, duration: float):
        """更新统计信息"""
        completed = self.stats["completed_tasks"]
        current_avg = self.stats["avg_completion_time"]

        if completed == 1:
            self.stats["avg_completion_time"] = duration
        else:
            self.stats["avg_completion_time"] = (
                current_avg * (completed - 1) + duration
            ) / completed

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return None

        return {
            **task.to_dict(),
            "priority_name": TaskPriority(task.priority).name,
        }

    async def get_stats(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            **self.stats,
            "pending_tasks": len(self.priority_queue),
            "running_tasks": len(self.running_tasks),
            "total_queued_tasks": len(self.tasks),
            "cron_jobs": len(self.cron_scheduler.cron_jobs),
            "max_workers": self.max_workers,
            "worker_status": self.worker_status,
            "allocation_strategy": self.allocator.strategy.value,
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
                for item in self.priority_queue:
                    if item[2] != task_id:
                        new_queue.append(item)

                self.priority_queue = new_queue
                heapq.heapify(self.priority_queue)
                task.status = TaskStatus.CANCELLED
                logger.info(f"取消任务: {task_id}")
                return True

            elif task.status == TaskStatus.SCHEDULED:
                # 取消Cron任务
                await self.cron_scheduler.remove_cron_job(task_id)
                task.status = TaskStatus.CANCELLED
                logger.info(f"取消Cron任务: {task_id}")
                return True

            elif task.status == TaskStatus.RUNNING:
                logger.warning(f"无法取消运行中的任务: {task_id}")
                return False

            return False

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """列出任务"""
        tasks = []

        for task in self.tasks.values():
            # 过滤状态
            if status and task.status != status:
                continue

            # 过滤标签
            if tags and not any(tag in task.tags for tag in tags):
                continue

            tasks.append(task.to_dict())

        # 按创建时间排序
        tasks.sort(key=lambda t: t["created_at"], reverse=True)

        return tasks[:limit]


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
        scheduler = EnhancedTaskScheduler(
            max_workers=2,
            allocation_strategy=TaskAllocationStrategy.LOAD_BALANCE,
            persistence_enabled=True,
        )

        # 启动调度器
        await scheduler.start()

        # 提交立即执行的任务
        task1_id = await scheduler.submit(
            name="数据处理",
            function=example_task,
            description="处理用户数据",
            priority=TaskPriority.HIGH,
            tags=["data", "processing"],
            args=("数据处理", 2.0),
        )

        # 提交Cron定时任务（每分钟执行）
        task2_id = await scheduler.schedule_cron(
            name="定时备份",
            function=example_task,
            cron_expression="*/1 * * * *",  # 每分钟
            description="定时备份数据",
            priority=TaskPriority.NORMAL,
            args=("定时备份", 0.5),
        )

        # 等待任务完成
        await asyncio.sleep(5)

        # 获取统计信息
        stats = await scheduler.get_stats()
        print(f"调度器统计: {stats}")

        # 列出所有任务
        tasks = await scheduler.list_tasks()
        print(f"任务列表: {len(tasks)} 个任务")

        # 停止调度器
        await scheduler.stop()

    asyncio.run(main())
