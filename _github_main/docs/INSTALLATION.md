# Agent OS 安装指南

本文档提供 Agent OS 在不同平台上的详细安装说明。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细安装步骤](#详细安装步骤)
  - [Linux/macOS](#linuxmacos)
  - [Windows](#windows)
  - [Docker](#docker)
- [安装验证](#安装验证)
- [常见问题](#常见问题)
- [下一步](#下一步)

## 系统要求

### 必需要求

- **Python**: 3.9 或更高版本
- **pip**: Python 包管理器
- **Git**: 版本控制工具
- **操作系统**: 
  - Linux (Ubuntu 18.04+, CentOS 7+, Debian 10+)
  - macOS 10.15+
  - Windows 10/11

### 可选依赖

- **Docker**: 用于容器化部署
- **PostgreSQL**: 生产环境数据库
- **Redis**: 缓存和消息队列
- **Qdrant**: 向量数据库（用于长期记忆）

## 快速开始

### Linux/macOS

```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 运行安装脚本
chmod +x scripts/install.sh
./scripts/install.sh

# 激活虚拟环境
source venv/bin/activate

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件设置API密钥

# 启动服务
python -m src.api.main
```

### Windows (PowerShell)

```powershell
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 运行安装脚本
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\install.ps1

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 配置环境变量
Copy-Item .env.example .env
# 编辑 .env 文件设置API密钥

# 启动服务
python -m src.api.main
```

### Docker

```bash
# 克隆仓库
git clone https://github.com/yourusername/agent-os.git
cd agent-os

# 使用Docker启动
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 详细安装步骤

### Linux/macOS

#### 1. 安装系统依赖

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv git
```

**CentOS/RHEL:**
```bash
sudo dnf install -y python3 python3-pip git
```

**macOS (使用Homebrew):**
```bash
brew install python3 git
```

#### 2. 运行安装脚本

```bash
# 标准安装
./scripts/install.sh

# 安装开发环境
./scripts/install.sh --dev

# 使用Docker
./scripts/install.sh --docker

# 跳过系统依赖检查
./scripts/install.sh --skip-deps
```

#### 3. 手动安装（可选）

如果不使用安装脚本，可以手动安装：

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip setuptools wheel
pip install -e .

# 配置环境
cp .env.example .env

# 创建必要目录
mkdir -p logs data models
```

### Windows

#### 1. 安装系统依赖

**使用Chocolatey (推荐):**
```powershell
choco install python git
```

**或手动安装:**
- Python: https://www.python.org/downloads/
- Git: https://git-scm.com/download/win

#### 2. 运行安装脚本

```powershell
# 标准安装
.\scripts\install.ps1

# 安装开发环境
.\scripts\install.ps1 -Dev

# 使用Docker
.\scripts\install.ps1 -Docker

# 跳过系统依赖检查
.\scripts\install.ps1 -SkipDeps
```

#### 3. 手动安装（可选）

```powershell
# 创建虚拟环境
python -m venv venv
.\venv\Scripts\Activate.ps1

# 安装依赖
pip install --upgrade pip setuptools wheel
pip install -e .

# 配置环境
Copy-Item .env.example .env

# 创建必要目录
New-Item -ItemType Directory -Force -Path logs, data, models
```

### Docker

#### 1. 安装Docker

- **Linux**: https://docs.docker.com/engine/install/
- **macOS**: https://docs.docker.com/docker-for-mac/install/
- **Windows**: https://docs.docker.com/docker-for-windows/install/

#### 2. 使用Docker Compose

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

#### 3. 手动Docker运行

```bash
# 构建镜像
docker build -t agent-os:latest .

# 运行容器
docker run -d \
  --name agent-os \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  agent-os:latest
```

## 安装验证

安装完成后，运行验证脚本检查安装：

```bash
# Linux/macOS
python scripts/verify_installation.py

# Windows
python scripts\verify_installation.py
```

验证脚本会检查：
- Python版本
- 核心依赖包
- 项目文件和目录
- 源代码模块
- 系统工具

### 手动验证

```bash
# 检查Python版本
python --version  # 应该 >= 3.9

# 检查依赖
python -c "import fastapi, uvicorn, pydantic; print('核心依赖OK')"

# 检查项目模块
python -c "import sys; sys.path.insert(0, 'src'); print('项目路径OK')"

# 启动服务测试
python -m src.api.main
# 访问 http://localhost:8000/docs
```

## 常见问题

### 1. Python版本过低

**问题**: `Python版本过低，需要Python 3.9+`

**解决**:
- 安装Python 3.9+: https://www.python.org/downloads/
- 或使用pyenv管理多个Python版本:
  ```bash
  # Linux/macOS
  curl https://pyenv.run | bash
  pyenv install 3.11.0
  pyenv global 3.11.0
  ```

### 2. 权限错误 (Linux/macOS)

**问题**: `Permission denied`

**解决**:
```bash
# 给脚本执行权限
chmod +x scripts/*.sh

# 或使用sudo（不推荐）
sudo ./scripts/install.sh
```

### 3. PowerShell执行策略 (Windows)

**问题**: `无法加载文件，因为在此系统上禁止运行脚本`

**解决**:
```powershell
# 临时允许脚本执行
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 4. pip安装失败

**问题**: `pip install` 失败

**解决**:
```bash
# 升级pip
python -m pip install --upgrade pip

# 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .

# 或
pip install -i https://mirrors.aliyun.com/pypi/simple/ -e .
```

### 5. 依赖冲突

**问题**: 依赖版本冲突

**解决**:
```bash
# 清理并重新安装
rm -rf venv
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install --upgrade pip setuptools wheel
pip install -e .
```

### 6. 数据库连接失败

**问题**: 无法连接PostgreSQL/Redis

**解决**:
```bash
# 检查服务状态
sudo systemctl status postgresql  # Linux
brew services list  # macOS

# 检查连接配置
# 编辑 .env 文件中的数据库连接字符串
```

### 7. Docker相关问题

**问题**: Docker命令失败

**解决**:
```bash
# 检查Docker状态
docker info

# 重启Docker服务
# Linux
sudo systemctl restart docker

# macOS/Windows - 重启Docker Desktop
```

## 下一步

安装完成后，您可以：

1. **配置API密钥**: 编辑 `.env` 文件设置必要的API密钥
   ```bash
   # OpenAI API密钥
   OPENAI_API_KEY=your-api-key-here
   
   # 其他配置...
   ```

2. **查看文档**:
   - [快速开始](QUICK_START.md)
   - [API文档](api/README.md)
   - [架构设计](architecture/README.md)

3. **运行示例**:
   ```bash
   # 查看示例代码
   ls examples/
   
   # 运行简单示例
   python examples/simple_agent.py
   ```

4. **开始开发**:
   ```bash
   # 运行开发服务器（自动重载）
   make dev
   
   # 运行测试
   make test
   
   # 代码格式化
   make format
   ```

5. **加入社区**:
   - GitHub Issues: https://github.com/yourusername/agent-os/issues
   - Discord: https://discord.gg/your-discord
   - 邮件列表: agent-os-dev@googlegroups.com

## 获取帮助

如果您在安装过程中遇到问题：

1. 查看 [常见问题](#常见问题) 部分
2. 搜索 [GitHub Issues](https://github.com/yourusername/agent-os/issues)
3. 提交新的Issue并附上：
   - 操作系统和版本
   - Python版本
   - 完整的错误信息
   - 已尝试的解决方法

---

**祝您使用愉快！Agent OS 团队**
