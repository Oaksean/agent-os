"""
基础Agent示例
演示如何使用Agent OS创建和运行简单的Agent
"""

import asyncio
import time
from src.kernel.agent_manager import get_agent_manager, AgentConfig
from src.memory.working_memory import WorkingMemory
from src.planner.hierarchical_planner import HierarchicalPlanner
from src.tools.tool_registry import get_tool_registry, ToolCategory

async def create_basic_agent():
    """创建基础Agent"""
    print("=== 创建基础Agent ===")
    
    # 获取Agent管理器
    agent_manager = get_agent_manager()
    
    # 创建Agent配置
    config = AgentConfig(
        agent_id="basic_agent_001",
        name="基础助手",
        description="一个简单的示例Agent，用于演示基本功能",
        capabilities=["planning", "memory", "tool_usage"],
        memory_config={"max_size": 50, "max_tokens": 2000},
        planner_config={"llm_enabled": False}
    )
    
    # 创建Agent
    agent_id = await agent_manager.create_agent(config)
    print(f"Agent创建成功: {agent_id}")
    
    return agent_id

async def demonstrate_working_memory():
    """演示工作记忆功能"""
    print("
=== 演示工作记忆 ===")
    
    # 创建工作记忆实例
    memory = WorkingMemory(max_size=10, max_tokens=1000)
    
    # 添加记忆项
    print("添加记忆项...")
    memory.add("用户想要创建一个待办事项应用", importance=0.9)
    memory.add("用户偏好暗色主题", importance=0.7)
    memory.add("用户需要截止日期提醒功能", importance=0.8)
    memory.add("用户使用Windows 11系统", importance=0.5)
    
    # 获取最近记忆
    recent = memory.get_recent(count=3)
    print(f"最近3项记忆: {[item.content for item in recent]}")
    
    # 搜索记忆
    results = memory.search("主题")
    print(f"搜索'主题': {[item.content for item in results]}")
    
    # 生成摘要
    summary = memory.summarize(max_length=200)
    print(f"记忆摘要: {summary}")
    
    return memory

async def demonstrate_planner():
    """演示规划器功能"""
    print("
=== 演示任务规划 ===")
    
    # 创建规划器
    planner = HierarchicalPlanner()
    
    # 创建任务计划
    goal = "开发一个简单的待办事项应用"
    task = await planner.plan(goal)
    
    print(f"目标: {goal}")
    print(f"生成任务: {task.name}")
    print(f"任务ID: {task.id}")
    print(f"子任务数量: {len(task.subtasks)}")
    
    # 显示任务树
    visualization = planner.visualize_plan(task.id)
    print(f"任务计划可视化:\n{visualization}")
    
    # 模拟任务执行
    print("\n模拟任务执行...")
    for i, subtask in enumerate(task.subtasks):
        print(f"  [{i+1}] 执行: {subtask.description}")
        planner.update_task_status(subtask.id, TaskStatus.COMPLETED)
        await asyncio.sleep(0.1)  # 模拟执行时间
    
    # 检查父任务状态
    parent_task = planner.get_task(task.id)
    print(f"父任务状态: {parent_task.status.value}")
    
    return planner

async def demonstrate_tools():
    """演示工具使用"""
    print("
=== 演示工具使用 ===")
    
    # 获取工具注册表
    registry = get_tool_registry()
    
    # 注册示例工具
    from src.tools.tool_registry import example_calculator, example_file_read
    
    # 执行计算器工具
    print("执行计算器工具...")
    result = await registry.execute("example_calculator", operation="add", a=10, b=20)
    print(f"计算结果: {result}")
    
    # 执行文件读取工具
    print("\n执行文件读取工具...")
    result = await registry.execute("example_file_read", filepath="README.md")
    print(f"文件读取结果: {result.get('success', False)}")
    
    # 列出可用工具
    tools = registry.list_tools()
    print(f"\n可用工具数量: {len(tools)}")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")
    
    return registry

async def main():
    """主函数"""
    print("Agent OS 基础示例")
    print("=" * 50)
    
    try:
        # 1. 创建Agent
        agent_id = await create_basic_agent()
        
        # 2. 演示记忆功能
        memory = await demonstrate_working_memory()
        
        # 3. 演示规划功能
        planner = await demonstrate_planner()
        
        # 4. 演示工具功能
        registry = await demonstrate_tools()
        
        print("
" + "=" * 50)
        print("示例执行完成！")
        print(f"创建的Agent: {agent_id}")
        print(f"工作记忆项数: {len(memory.memory_items)}")
        print(f"规划的任务数: {len(planner.tasks)}")
        print(f"注册的工具数: {len(registry.tools)}")
        
    except Exception as e:
        print(f"示例执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
