# Agent OS 安装快速参考

## 🚀 快速开始（3分钟）

### Linux/macOS
```bash
git clone https://github.com/yourusername/agent-os.git && cd agent-os
./scripts/install.sh && source venv/bin/activate
python -m src.api.main
```

### Windows
```powershell
git clone https://github.com/yourusername/agent-os.git; cd agent-os
.\scripts\install.ps1; .\venv\Scripts\Activate.ps1
python -m src.api.main
```

### Docker
```bash
git clone https://github.com/yourusername/agent-os.git && cd agent-os
docker-compose up -d
```

## 📋 系统要求

| 项目 | 要求 |
|------|------|
| Python | >= 3.9 |
| pip | 最新版本 |
| Git | 任意版本 |
| 内存 | >= 4GB |
| 磁盘 | >= 2GB |

## 🔧 安装命令

### 一键安装
```bash
# Linux/macOS
./scripts/install.sh

# Windows
.\scripts\install.ps1

# Docker
docker-compose up -d
```

### 安装选项
```bash
# 开发环境
./scripts/install.sh --dev        # Linux/macOS
.\scripts\install.ps1 -Dev        # Windows

# Docker模式
./scripts/install.sh --docker     # Linux/macOS
.\scripts\install.ps1 -Docker     # Windows

# 跳过依赖检查
./scripts/install.sh --skip-deps  # Linux/macOS
.\scripts\install.ps1 -SkipDeps   # Windows
```

## 🛠️ Makefile命令

```bash
make help           # 显示所有命令
make install        # 标准安装
make install-dev    # 开发环境
make run            # 运行生产服务
make dev            # 运行开发服务
make test           # 运行测试
make lint           # 代码检查
make format         # 格式化代码
make docker-up      # 启动Docker
make docker-down    # 停止Docker
```

## ✅ 验证安装

```bash
# 自动验证
python scripts/verify_installation.py

# 手动验证
python --version                    # Python >= 3.9
python -c "import fastapi"         # 核心依赖
python -m src.api.main             # 启动服务
```

## 🌐 访问服务

- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health
- **Web界面**: http://localhost:8000

## 🔑 环境配置

创建 `.env` 文件：
```bash
cp .env.example .env
```

必需配置：
```env
OPENAI_API_KEY=your-api-key-here
```

## ❓ 常见问题

### Python版本过低
```bash
# 使用pyenv安装Python 3.11
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0
```

### 权限错误 (Linux/macOS)
```bash
chmod +x scripts/*.sh
```

### PowerShell脚本禁止 (Windows)
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### pip安装失败
```bash
pip install --upgrade pip setuptools wheel
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -e .
```

## 📚 文档资源

- [详细安装指南](docs/INSTALLATION.md)
- [快速开始](docs/QUICK_START.md)
- [API文档](docs/api/README.md)
- [架构设计](docs/architecture/README.md)

## 🆘 获取帮助

- **GitHub Issues**: https://github.com/yourusername/agent-os/issues
- **Discord**: https://discord.gg/your-discord
- **邮件列表**: agent-os-dev@googlegroups.com

## 📦 安装后步骤

1. ✅ 配置API密钥（编辑 `.env`）
2. ✅ 启动服务（`python -m src.api.main`）
3. ✅ 访问文档（http://localhost:8000/docs）
4. ✅ 运行示例（`python examples/simple_agent.py`）

---

**需要帮助？** 查看 [完整文档](docs/INSTALLATION.md) 或 [提交Issue](https://github.com/yourusername/agent-os/issues)
