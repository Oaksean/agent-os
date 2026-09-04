# Agent OS：智能体操作系统

## 项目简介

Agent OS 是一个面向"自主智能体"计算范式设计的系统内核与用户态基础设施。它为AI智能体提供运行、感知、规划、记忆、行动、协作与自我进化的统一环境。

## 核心设计理念

1. **自主性** - 智能体能够自主决策和执行任务
2. **安全性** - 沙箱隔离和权限控制，防止恶意操作
3. **可扩展性** - 模块化架构，支持插件式扩展
4. **互操作性** - 与传统操作系统无缝集成
5. **可迁移性** - 智能体状态可在不同设备间迁移
6. **高效性** - 优化资源使用，降低运行成本

## 六大层次架构

### �� 第一层：内核与执行引擎
- **Agent生命周期管理** - 创建、暂停、恢复、迁移、销毁
- **沙箱执行环境** - 独立的执行环境，最小权限原则
- **混合任务调度** - 确定性+非确定性任务调度
- **事件驱动引擎** - 监听和响应外部事件

### �� 第二层：记忆系统
- **工作记忆** - 短期上下文，自动摘要压缩
- **长期记忆** - 向量存储+知识图谱，语义检索
- **情景记忆** - 历史行动记录，用于反思学习
- **记忆巩固** - 定期整理，选择性遗忘

### �� 第三层：规划引擎
- **分层任务规划** - HTN/LLM-based任务分解
- **动态重规划** - 失败恢复和异常处理
- **约束推理** - 资源、隐私、偏好约束
- **并行规划** - DAG依赖图，提升执行效率

### �� 第四层：工具总线
- **工具注册与发现** - 标准化的工具描述格式
- **多协议适配器** - REST、GraphQL、gRPC、命令行等
- **工具链编排** - 宏工具和技能组合
- **调用审计** - 监控、限流、配额控制

### �� 第五层：模型路由器
- **模型抽象层** - 统一接口对接各类模型
- **智能路由策略** - 基于任务需求选择最佳模型
- **成本监控** - 实时追踪Token消耗和费用
- **模型级联** - 小模型尝试，大模型兜底

### ⚙️ 第六层：扩展能力
- **多Agent通信** - Agent间消息总线和协调机制
- **环境感知** - 数字孪生和世界模型
- **技能学习** - 任务流程提炼为可复用技能
- **用户交互** - 人在回路，解释和授权机制
- **安全护栏** - 策略引擎，合规性检查
- **状态迁移** - 快照和跨设备转移

## Harness 核心机制（执行编排内核）

对标 Claude Code 与 OpenAI Codex 的 Agent Runtime 设计，Agent OS 实现了一套完整的
**Harness 内核**，确保自主 Agent 可靠、安全、可观测地执行长任务：

| 机制 | 模块 | 说明 |
|------|------|------|
| Agent Loop 状态机 | `src/kernel/agent_loop.py` | Observe-Think-Act 有限状态机，停滞检测、最大步数、指数退避 |
| 缓存友好上下文 | `src/prompts/context_builder.py` | 静态前缀缓存、追加式历史、易失状态分离 |
| 文件差异跟踪 | `src/tools/diff_tracker.py` | TurnDiffTracker：基线快照、UUID 映射、统一 Diff、提交/回滚 |
| 分级审批护栏 | `src/security/guardrails.py` | AUTO/INTERACTIVE/FORBIDDEN 三级审批 + OverlayFS 写时复制 |
| 并行编排 | `src/communication/subagent.py` | Manager-Subagent 依赖分层并行、冲突检测 |
| 长期记忆 | `src/memory/long_term_memory.py` | TF-IDF 语义检索、时间衰减、选择性遗忘 |
| 记忆巩固 | `src/memory/memory_consolidator.py` | 触发判断、摘要、遗忘 |
| MCP 客户端 | `src/tools/mcp_client.py` | JSON-RPC 2.0，Stdio/InMemory 传输 |

详细设计见 [Harness 架构文档](docs/HARNESS_ARCHITECTURE.md)。

### 快速体验 Harness

```bash
# 端到端演示（串联 AgentLoop + 护栏 + Overlay + 差异跟踪 + 长期记忆 + 上下文构建）
python examples/basic/harness_demo.py

# 运行测试套件
python -m pytest tests/unit -q
```

## 快速开始

### 安装依赖
```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Linux/Mac）
source venv/bin/activate

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置文件
复制配置文件模板：
```bash
cp config/config.example.yaml config/config.yaml
```

编辑 `config/config.yaml`，配置你的API密钥和其他设置。

### 运行示例
```bash
# 启动API服务
python -m src.api.main

# 或者使用uvicorn
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 访问Web界面
打开浏览器访问：http://localhost:8000

## 使用示例

### 创建智能体
```python
from src.kernel.agent_manager import AgentManager

# 创建Agent管理器
manager = AgentManager()

# 创建新的智能体
agent = manager.create_agent(
    name="个人助手",
    description="帮助处理日常任务",
    capabilities=["web_search", "file_operation", "calendar_management"]
)

# 给智能体分配任务
task = {
    "goal": "帮我查找最新的AI研究论文",
    "constraints": ["只用arXiv来源", "只要最近7天的", "关注大模型方向"]
}

result = agent.execute_task(task)
print(f"任务结果: {result}")
```

### 使用工具总线
```python
from src.tools.tool_registry import ToolRegistry

# 初始化工具注册表
registry = ToolRegistry()

# 注册工具
registry.register_tool({
    "name": "web_search",
    "description": "搜索网页内容",
    "endpoint": "https://api.search.com/v1/search",
    "parameters": {
        "query": {"type": "string", "required": True},
        "limit": {"type": "integer", "default": 10}
    }
})

# 查找合适的工具
tools = registry.find_tools("搜索")
for tool in tools:
    print(f"工具: {tool['name']} - {tool['description']}")
```

### 配置模型路由
```yaml
# config/models.yaml
models:
  gpt-4:
    provider: openai
    api_key: ${OPENAI_API_KEY}
    capabilities: ["reasoning", "coding", "analysis"]
    cost_per_token: 0.00003
  
  claude-3:
    provider: anthropic
    api_key: ${ANTHROPIC_API_KEY}
    capabilities: ["writing", "analysis", "summarization"]
    cost_per_token: 0.000025
  
  llama3:
    provider: local
    endpoint: "http://localhost:8080"
    capabilities: ["general", "coding"]
    cost_per_token: 0.000001

routing_rules:
  - when: "task.type == 'coding'"
    use: ["gpt-4", "llama3"]
    priority: "gpt-4"
  
  - when: "task.type == 'writing'"
    use: ["claude-3", "gpt-4"]
    priority: "claude-3"
```

## 应用场景

### 个人助理
- 自动化日常任务（邮件处理、日程安排）
- 智能信息整理（文档分类、笔记总结）
- 个性化推荐（新闻、学习资源）

### 企业自动化
- 业务流程自动化（审批流程、数据录入）
- 客户服务支持（自动问答、工单处理）
- 数据分析和报告（销售分析、运营报告）

### 开发工具
- 代码生成和审查（自动补全、代码检查）
- 系统监控和运维（日志分析、异常检测）
- 测试自动化（测试用例生成、回归测试）

### 研究平台
- AI算法实验（多Agent系统研究）
- 人机协作研究（交互模式探索）
- 智能体行为分析（决策过程可视化）

## 贡献指南

我们欢迎各种形式的贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细指南。

### 报告问题
- 使用 [GitHub Issues](https://github.com/yourusername/agent-os/issues) 报告bug
- 描述清晰的重现步骤
- 包含环境信息和错误日志

### 提交代码
1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

### 代码规范
- 使用Black进行代码格式化
- 使用MyPy进行类型检查
- 遵循PEP 8编码规范
- 编写单元测试和文档

## 文档

- [Harness 架构设计](docs/HARNESS_ARCHITECTURE.md) - Harness 核心机制详解
- [架构设计](docs/architecture.md) - 详细架构说明
- [API文档](docs/api.md) - REST API接口文档
- [开发指南](docs/development.md) - 开发环境设置
- [部署指南](docs/deployment.md) - 生产环境部署
- [用户手册](docs/user_manual.md) - 使用教程和示例

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 社区

- **GitHub Discussions**: [技术讨论](https://github.com/yourusername/agent-os/discussions)
- **Discord社区**: [实时交流](https://discord.gg/your-discord)
- **邮件列表**: agent-os-dev@googlegroups.com
- **微信公众号**: AgentOS社区 (待创建)

## 支持

如果你喜欢这个项目，请考虑：

1. ⭐ Star 这个仓库
2. 🐛 提交问题和建议
3. 🔧 提交代码贡献
4. 📢 分享给更多人

---

**Agent OS - 让每个人都能拥有自主的数字员工**

*"未来不是被AI取代，而是与AI协作"*