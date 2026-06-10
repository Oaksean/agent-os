# Agent OS：智能体操作系统 - 架构蓝图

## 🎉 最新更新（v1.0.0）

### 新增功能
- ✅ **增强任务调度**：Cron定时调度、任务持久化、智能任务分配
- ✅ **缓存系统**：Redis集成、LRU淘汰、缓存装饰器
- ✅ **基础设施层**：流量控制、权限管理、日志系统
- ✅ **Dashboard前端**：完整的可视化监控界面
- ✅ **完整API**：集成基础设施的API服务
- ✅ **实时推送**：WebSocket实时数据更新

### 快速启动

**Windows:**
```bash
scripts\start_dashboard.bat
```

**Linux/Mac:**
```bash
python scripts/start_dashboard.py
```

访问：
- **Dashboard**: `http://localhost:8080`
- **API文档**: `http://localhost:8000/docs`
- **API根路径**: `http://localhost:8000`

### 测试用户

| User ID | Role | 权限 |
|---------|------|------|
| `test_user_001` | admin | 所有权限 |
| `test_user_002` | user | 基本权限 |

请求头添加：`X-User-ID: test_user_001`

### 快速测试

```bash
# 提交任务
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user_001" \
  -d '{"name": "test_task", "priority": "normal"}'

# 提交Cron任务（每5分钟执行）
curl -X POST http://localhost:8000/api/v1/tasks/cron \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user_001" \
  -d '{"name": "backup", "cron_expression": "*/5 * * * *"}'

# 获取缓存统计
curl http://localhost:8000/api/v1/cache/stats \
  -H "X-User-ID: admin"
```

---

## 📖 详细文档

- [安装指南](docs/INSTALLATION.md)
- [快速开始](docs/QUICK_START.md)
- [API文档](http://localhost:8000/docs)
- [Dashboard指南](dashboard/README.md)
- [功能总结](IMPLEMENTATION_SUMMARY.md)

---

## 项目概述

Agent OS是一个面向"自主智能体"计算范式设计的系统内核与用户态基础设施。它为AI智能体提供运行、感知、规划、记忆、行动、协作与自我进化的统一环境。

## 核心设计原则

1. **自主性**：智能体能够自主决策和执行任务
2. **安全性**：沙箱隔离和权限控制，防止恶意操作
3. **可扩展性**：模块化架构，支持插件式扩展
4. **互操作性**：与传统操作系统无缝集成
5. **可迁移性**：智能体状态可在不同设备间迁移
6. **效率性**：优化资源使用，降低运行成本

## 六大层次架构

### �� 第一层：内核与执行引擎（Agent Kernel & Execution Engine）

**核心模块**：
1. **Agent生命周期管理器** - 创建、暂停、恢复、迁移、销毁
2. **沙箱执行环境** - 独立的执行环境，最小权限原则
3. **混合任务调度器** - 确定性+非确定性任务调度
4. **事件驱动引擎** - 监听和响应外部事件

### �� 第二层：记忆系统（Memory）

**三级记忆架构**：
1. **工作记忆** - 短期上下文，自动摘要压缩
2. **长期记忆** - 向量存储+知识图谱，语义检索
3. **情景记忆** - 历史行动记录，用于反思学习
4. **记忆巩固** - 定期整理，选择性遗忘

### �� 第三层：规划引擎（Planner）

**规划能力**：
1. **分层任务规划** - HTN/LLM-based任务分解
2. **动态重规划** - 失败恢复和异常处理
3. **约束推理** - 资源、隐私、偏好约束
4. **并行规划** - DAG依赖图，提升执行效率

### �� 第四层：工具总线（Tool Bus）

**工具生态系统**：
1. **工具注册与发现** - 标准化的工具描述格式
2. **多协议适配器** - REST、GraphQL、gRPC、命令行等
3. **工具链编排** - 宏工具和技能组合
4. **调用审计** - 监控、限流、配额控制

### �� 第五层：模型路由器（Model Router）

**模型管理**：
1. **模型抽象层** - 统一接口对接各类模型
2. **智能路由策略** - 基于任务需求选择最佳模型
3. **成本监控** - 实时追踪Token消耗和费用
4. **模型级联** - 小模型尝试，大模型兜底

### ⚙️ 第六层：扩展能力

**高级功能**：
1. **多Agent通信** - Agent间消息总线和协调机制
2. **环境感知** - 数字孪生和世界模型
3. **技能学习** - 任务流程提炼为可复用技能
4. **用户交互** - 人在回路，解释和授权机制
5. **安全护栏** - 策略引擎，合规性检查
6. **状态迁移** - 快照和跨设备转移

## 技术栈选择

### 后端技术
- **语言**：Python 3.9+（主要），Rust（性能关键部分）
- **框架**：FastAPI（Web服务），Pydantic（数据验证）
- **数据库**：PostgreSQL（关系数据），Redis（缓存），Qdrant（向量存储）
- **消息队列**：RabbitMQ / Redis Streams
- **任务队列**：Celery / Dramatiq

### AI/ML技术
- **模型框架**：LangChain，LlamaIndex
- **向量存储**：Qdrant，Pinecone，Weaviate
- **模型服务**：Ollama，vLLM，OpenAI API
- **规划算法**：HTN规划器，LLM-based规划

### 前端技术
- **框架**：React + TypeScript
- **UI库**：Material-UI / Ant Design
- **可视化**：D3.js，ECharts
- **状态管理**：Redux / Zustand

### 部署和运维
- **容器化**：Docker，Docker Compose
- **编排**：Kubernetes（可选）
- **监控**：Prometheus，Grafana
- **日志**：ELK Stack / Loki

## 项目结构

```
agent-os/
├── src/                          # 源代码
│   ├── kernel/                   # 内核与执行引擎
│   │   ├── agent_manager.py      # Agent生命周期管理
│   │   ├── sandbox.py           # 沙箱执行环境
│   │   ├── scheduler.py         # 任务调度器
│   │   └── event_engine.py      # 事件驱动引擎
│   ├── memory/                   # 记忆系统
│   │   ├── working_memory.py    # 工作记忆
│   │   ├── long_term_memory.py  # 长期记忆
│   │   ├── episodic_memory.py   # 情景记忆
│   │   └── memory_consolidator.py # 记忆巩固
│   ├── planner/                  # 规划引擎
│   │   ├── hierarchical_planner.py # 分层规划
│   │   ├── dynamic_replanner.py # 动态重规划
│   │   ├── constraint_solver.py # 约束求解器
│   │   └── parallel_planner.py  # 并行规划
│   ├── tools/                    # 工具总线
│   │   ├── tool_registry.py     # 工具注册
│   │   ├── protocol_adapters.py # 协议适配器
│   │   ├── tool_orchestrator.py # 工具编排
│   │   └── tool_auditor.py      # 工具审计
│   ├── models/                   # 模型路由器
│   │   ├── model_router.py      # 模型路由
│   │   ├── cost_monitor.py      # 成本监控
│   │   ├── model_cascade.py     # 模型级联
│   │   └── model_registry.py    # 模型注册
│   ├── communication/            # 通信层
│   │   ├── message_bus.py       # 消息总线
│   │   ├── agent_coordinator.py # Agent协调器
│   │   └── protocol.py          # 通信协议
│   ├── extensions/               # 扩展能力
│   │   ├── skill_learner.py     # 技能学习
│   │   ├── environment_sensor.py # 环境感知
│   │   └── state_migrator.py    # 状态迁移
│   ├── security/                 # 安全层
│   │   ├── permission_manager.py # 权限管理
│   │   ├── policy_engine.py     # 策略引擎
│   │   └── audit_logger.py      # 审计日志
│   ├── api/                      # API服务
│   │   ├── main.py              # FastAPI应用
│   │   ├── routes/              # API路由
│   │   └── middleware/          # 中间件
│   └── web/                      # Web界面
│       ├── frontend/            # React前端
│       └── backend/             # Web服务后端
├── tests/                        # 测试代码
├── docs/                         # 文档
├── examples/                     # 示例代码
├── scripts/                      # 脚本工具
├── config/                       # 配置文件
├── data/                         # 数据文件
└── logs/                         # 日志文件
```

## 开发路线图

### 第一阶段：基础框架（1-2周）
1. 搭建项目结构和开发环境
2. 实现Agent生命周期管理
3. 实现基础记忆系统
4. 创建简单的规划器

### 第二阶段：核心功能（2-3周）
1. 完善工具总线和模型路由器
2. 实现多Agent通信机制
3. 添加安全护栏和权限控制
4. 开发Web界面和API

### 第三阶段：高级功能（2-3周）
1. 实现技能学习和环境感知
2. 添加状态迁移和快照功能
3. 优化性能和资源管理
4. 完善监控和日志系统

### 第四阶段：生态建设（持续）
1. 开发更多工具和适配器
2. 集成更多AI模型和服务
3. 创建应用商店和插件系统
4. 社区建设和文档完善

## 使用场景

### 个人助理
- 自动化日常任务
- 智能信息整理
- 个性化推荐

### 企业自动化
- 业务流程自动化
- 客户服务支持
- 数据分析和报告

### 开发工具
- 代码生成和审查
- 系统监控和运维
- 测试自动化

### 研究平台
- AI算法实验
- 多Agent系统研究
- 人机协作研究

## 贡献指南

## 快速安装

### 一键安装

**Linux/macOS:**
```bash
git clone https://github.com/yourusername/agent-os.git
cd agent-os
./scripts/install.sh
```

**Windows:**
```powershell
git clone https://github.com/yourusername/agent-os.git
cd agent-os
.\scripts\install.ps1
```

**Docker:**
```bash
docker-compose up -d
```

详细安装指南请查看 [INSTALLATION.md](docs/INSTALLATION.md)

## 详细安装指南

完整的安装说明请参考：

- **[安装文档](docs/INSTALLATION.md)** - 包含所有平台的详细安装步骤
- **[快速开始](docs/QUICK_START.md)** - 5分钟快速上手指南
- **[系统要求](docs/INSTALLATION.md#系统要求)** - 必需和可选依赖

### 系统要求

- Python 3.9+
- pip (Python包管理器)
- Git (版本控制)
- 可选: Docker, PostgreSQL, Redis

### 安装选项

```bash
# 标准安装
./scripts/install.sh              # Linux/macOS
.\scripts\install.ps1             # Windows

# 开发环境安装
./scripts/install.sh --dev        # Linux/macOS
.\scripts\install.ps1 -Dev        # Windows

# Docker安装
./scripts/install.sh --docker     # Linux/macOS
.\scripts\install.ps1 -Docker     # Windows
```

### 验证安装

```bash
python scripts/verify_installation.py
```

## 手动安装

### Linux/macOS

```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip setuptools wheel
pip install -e .

# 配置环境
cp .env.example .env
# 编辑 .env 文件设置API密钥

# 创建目录
mkdir -p logs data models

# 启动服务
python -m src.api.main
```

### Windows

```powershell
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install --upgrade pip setuptools wheel
pip install -e .

# 配置环境
Copy-Item .env.example .env
# 编辑 .env 文件设置API密钥

# 创建目录
New-Item -ItemType Directory -Force -Path logs, data, models

# 启动服务
python -m src.api.main
```

### 使用Makefile

```bash
# 查看所有可用命令
make help

# 安装
make install          # 标准安装
make install-dev      # 开发环境安装

# 开发
make run              # 运行生产服务器
make dev              # 运行开发服务器（自动重载）

# 测试
make test             # 运行所有测试
make lint             # 代码检查
make format           # 格式化代码

# Docker
make docker-up        # 启动Docker服务
make docker-down      # 停止Docker服务
```

### 代码规范
- 使用Black进行代码格式化
- 使用MyPy进行类型检查
- 遵循PEP 8编码规范
- 编写单元测试和文档

### 提交规范
- 使用Conventional Commits
- 每个PR解决一个具体问题
- 包含测试和文档更新

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系我们

- **GitHub Issues**: [项目问题跟踪](https://github.com/yourusername/agent-os/issues)
- **Discord**: [社区讨论](https://discord.gg/your-discord)
- **邮件列表**: agent-os-dev@googlegroups.com

---

**Agent OS - 构建自主智能体的操作系统**

"为每个人提供自主的数字员工"