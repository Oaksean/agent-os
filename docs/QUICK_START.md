# Agent OS 快速开始指南

## 系统要求

- **Python**: 3.9 或更高版本
- **操作系统**: Windows, macOS, Linux
- **内存**: 至少 4GB RAM (推荐 8GB+)
- **存储**: 至少 1GB 可用空间

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/agent-os.git
cd agent-os
```

### 2. 设置环境 (自动方式)

**Linux/macOS:**
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

**Windows:**
```powershell
.\scripts\start.ps1
```

### 3. 设置环境 (手动方式)

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 创建必要目录
mkdir -p logs data snapshots config

# 复制配置文件
cp config.example.yaml config/config.yaml
cp .env.example .env

# 编辑配置文件
# 1. 编辑 config/config.yaml 配置系统
# 2. 编辑 .env 设置环境变量
```

### 4. 启动服务

```bash
python -m src.api.main
```

服务将在 http://localhost:8000 启动。

## 验证安装

访问以下URL验证安装：

- **API服务**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 使用Docker (推荐)

### 使用Docker Compose启动所有服务

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f api

# 停止服务
docker-compose down
```

### 仅启动API服务

```bash
# 构建镜像
docker build -t agent-os .

# 运行容器
docker run -p 8000:8000 agent-os
```

## 配置说明

### 主要配置文件

1. **config/config.yaml** - 主配置文件
   - 数据库连接
   - 记忆系统配置
   - 规划器配置
   - 安全设置

2. **.env** - 环境变量
   - API密钥
   - 数据库密码
   - 服务端口

### 配置示例

```yaml
# config/config.yaml 示例
server:
  host: "0.0.0.0"
  port: 8000

database:
  postgres:
    host: "localhost"
    port: 5432
    database: "agent_os"
```

```bash
# .env 示例
OPENAI_API_KEY=sk-...
POSTGRES_PASSWORD=your_password
```

## 基本使用

### 创建第一个Agent

```python
import asyncio
from src.kernel.agent_manager import get_agent_manager, AgentConfig

async def create_agent():
    manager = get_agent_manager()
    
    config = AgentConfig(
        agent_id="my_first_agent",
        name="我的第一个Agent",
        description="这是一个测试Agent"
    )
    
    agent_id = await manager.create_agent(config)
    print(f"Agent创建成功: {agent_id}")

asyncio.run(create_agent())
```

### 使用API

```bash
# 创建Agent
curl -X POST http://localhost:8000/api/v1/agents   -H "Content-Type: application/json"   -d '{
    "name": "测试Agent",
    "description": "API创建的Agent"
  }'

# 列出所有Agent
curl http://localhost:8000/api/v1/agents

# 创建任务
curl -X POST http://localhost:8000/api/v1/tasks   -H "Content-Type: application/json"   -d '{
    "goal": "分析市场趋势",
    "priority": 3
  }'
```

## 示例应用

运行示例代码：

```bash
# 运行基础示例
python examples/basic/basic_agent.py

# 运行API测试
pytest tests/unit/test_agent_manager.py -v
```

## 故障排除

### 常见问题

1. **端口冲突**
   ```
   错误: Address already in use
   解决方案: 修改 config/config.yaml 中的端口号
   ```

2. **Python版本问题**
   ```
   错误: Python 3.9+ required
   解决方案: 安装 Python 3.9 或更高版本
   ```

3. **依赖安装失败**
   ```
   错误: Failed to install dependencies
   解决方案: 手动安装: pip install -r requirements.txt --verbose
   ```

4. **数据库连接失败**
   ```
   错误: Could not connect to database
   解决方案: 检查 config/config.yaml 中的数据库配置
   ```

### 获取帮助

- 查看详细文档: `docs/`
- 运行测试: `pytest tests/`
- 查看日志: `logs/app.log`

## 下一步

1. 阅读详细文档了解架构
2. 查看 examples/ 目录中的示例
3. 修改配置文件以启用更多功能
4. 开发自定义工具和扩展

---

**Agent OS - 构建自主智能体的操作系统**
