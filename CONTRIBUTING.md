# 贡献指南

感谢您考虑为Agent OS项目做出贡献！本指南将帮助您了解如何参与贡献。

## 行为准则

请遵守我们的[行为准则](CODE_OF_CONDUCT.md)，确保为每个人提供友好、尊重的环境。

## 如何贡献

### 报告问题

如果您发现了bug或有功能建议，请：
1. 在GitHub Issues中搜索是否已有类似问题
2. 如果没有，创建一个新的issue
3. 提供清晰的问题描述和复现步骤

### 提交代码

1. **Fork仓库**
   - 点击GitHub页面右上角的"Fork"按钮

2. **克隆您的fork**
   ```bash
   git clone https://github.com/your-username/agent-os.git
   cd agent-os
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/issue-description
   ```

4. **进行更改**
   - 编写代码
   - 添加测试
   - 更新文档

5. **运行测试**
   ```bash
   # 安装开发依赖
   pip install -r requirements.txt
   pip install pytest pytest-asyncio flake8 mypy
   
   # 运行测试
   pytest tests/ -v
   
   # 代码检查
   flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
   flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
   
   # 类型检查
   mypy src --ignore-missing-imports
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能"
   # 或
   git commit -m "fix: 修复问题"
   # 或
   git commit -m "docs: 更新文档"
   ```

7. **推送到您的fork**
   ```bash
   git push origin feature/your-feature-name
   ```

8. **创建Pull Request**
   - 在GitHub上创建Pull Request
   - 提供清晰的描述和相关的issue链接

## 开发环境设置

### 前提条件
- Python 3.9+
- Git
- Docker (可选，用于容器化部署)

### 设置步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/agent-os.git
   cd agent-os
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   
   # Linux/macOS
   source venv/bin/activate
   
   # Windows
   venv\Scripts\activate
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # 开发依赖
   ```

4. **运行开发服务器**
   ```bash
   python -m src.api.main
   ```

## 代码规范

### Python代码风格
- 遵循[PEP 8](https://pep8.org/)规范
- 使用[Black](https://black.readthedocs.io/)进行代码格式化
- 使用[MyPy](https://mypy.readthedocs.io/)进行类型检查

### 提交信息规范
使用[Conventional Commits](https://www.conventionalcommits.org/)格式：

```
<type>[optional scope]: <description>

[optional body]

[optional footer]
```

类型包括：
- `feat`: 新功能
- `fix`: bug修复
- `docs`: 文档更新
- `style`: 代码格式调整
- `refactor`: 代码重构
- `test`: 测试相关
- `chore`: 构建过程或辅助工具变动

### 文档规范
- 所有公共API必须有文档字符串
- 使用[Google风格](https://google.github.io/styleguide/pyguide.html#381-docstrings)的文档字符串
- 更新README和API文档

## 项目结构

```
agent-os/
├── src/                    # 源代码
│   ├── kernel/            # 内核与执行引擎
│   ├── memory/            # 记忆系统
│   ├── planner/           # 规划引擎
│   ├── tools/             # 工具总线
│   ├── models/            # 模型路由器
│   ├── communication/     # 通信层
│   ├── extensions/        # 扩展能力
│   ├── security/          # 安全层
│   └── api/               # API服务
├── tests/                 # 测试代码
├── docs/                  # 文档
├── examples/              # 示例代码
├── scripts/               # 脚本工具
├── config/                # 配置文件
└── docker/               # Docker配置
```

## 测试指南

### 单元测试
- 测试文件放在`tests/unit/`目录
- 文件名以`test_`开头
- 使用`pytest`框架

### 集成测试
- 测试文件放在`tests/integration/`目录
- 测试模块间的集成

### 端到端测试
- 测试文件放在`tests/e2e/`目录
- 测试完整的工作流程

### 运行测试
```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_agent_manager.py

# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 发布流程

### 版本号
遵循[语义化版本](https://semver.org/)：
- MAJOR: 不兼容的API修改
- MINOR: 向下兼容的功能性新增
- PATCH: 向下兼容的问题修正

### 发布步骤
1. 更新`pyproject.toml`中的版本号
2. 更新`CHANGELOG.md`
3. 创建发布分支
4. 运行完整测试套件
5. 创建GitHub Release
6. 发布到PyPI (如果适用)

## 获取帮助

- 查看[文档](docs/)
- 在[GitHub Discussions](https://github.com/your-username/agent-os/discussions)提问
- 加入[Discord社区](https://discord.gg/your-discord)

## 致谢

感谢所有贡献者的支持！您的贡献使这个项目变得更好。
