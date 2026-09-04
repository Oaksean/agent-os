#!/bin/bash

# Agent OS GitHub仓库创建和发布脚本

set -e

echo "🚀 Agent OS GitHub发布脚本"
echo "=" * 50

# 检查是否在Git仓库中
if [ ! -d ".git" ]; then
    echo "❌ 当前目录不是Git仓库"
    exit 1
fi

# 设置Git配置
echo ""
echo "📝 设置Git配置..."
read -p "请输入您的GitHub用户名: " github_username
read -p "请输入您的GitHub邮箱: " github_email
read -p "请输入仓库名称 (默认: agent-os): " repo_name
repo_name=${repo_name:-agent-os}

# 设置Git用户信息
git config --global user.name "$github_username"
git config --global user.email "$github_email"

echo ""
echo "🔧 配置Git远程仓库..."
echo "请选择远程仓库URL类型:"
echo "1) HTTPS (推荐，无需SSH密钥)"
echo "2) SSH (需要配置SSH密钥)"
read -p "选择 (1/2): " url_type

if [ "$url_type" = "1" ]; then
    remote_url="https://github.com/$github_username/$repo_name.git"
elif [ "$url_type" = "2" ]; then
    remote_url="git@github.com:$github_username/$repo_name.git"
else
    echo "❌ 无效选择"
    exit 1
fi

# 添加远程仓库
git remote add origin "$remote_url" 2>/dev/null || git remote set-url origin "$remote_url"

echo ""
echo "📦 准备提交..."
git add .

# 创建提交
read -p "请输入提交信息 (默认: 'Initial commit'): " commit_msg
commit_msg=${commit_msg:-"Initial commit"}
git commit -m "$commit_msg"

echo ""
echo "🌐 推送到GitHub..."
echo "注意: 您需要在GitHub上创建仓库: https://github.com/new"
echo "仓库名称: $repo_name"
echo "描述: Agent OS - 智能体操作系统"
echo "许可证: MIT License"
echo ""
read -p "已在GitHub创建仓库？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "⚠️  请在GitHub创建仓库后重新运行此脚本"
    exit 1
fi

# 推送代码
echo "推送代码到GitHub..."
git push -u origin master

echo ""
echo "✅ 完成！"
echo ""
echo "🔗 您的仓库地址: https://github.com/$github_username/$repo_name"
echo "📚 文档地址: https://github.com/$github_username/$repo_name#readme"
echo ""
echo "下一步:"
echo "1. 设置GitHub Actions工作流"
echo "2. 添加README徽章"
echo "3. 配置代码质量检查"
echo "4. 发布第一个版本"

# 创建GitHub Actions工作流文件
echo ""
echo "📋 创建GitHub Actions工作流..."
mkdir -p .github/workflows

cat > .github/workflows/ci.yml << 'EOF'
name: CI

on:
  push:
    branches: [ master, main ]
  pull_request:
    branches: [ master, main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.9, 3.10, 3.11]

    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-asyncio
    
    - name: Lint with flake8
      run: |
        pip install flake8
        flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
    
    - name: Test with pytest
      run: |
        pytest tests/ -v
    
    - name: Type check with mypy
      run: |
        pip install mypy
        mypy src --ignore-missing-imports

  docker:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Build Docker image
      run: |
        docker build -t agent-os:latest .
    
    - name: Test Docker image
      run: |
        docker run --rm agent-os:latest python -c "import sys; print('Python', sys.version)"

EOF

echo "✅ GitHub Actions工作流已创建: .github/workflows/ci.yml"

# 创建README徽章
echo ""
echo "🛡️  创建README徽章..."

cat >> README.md << 'EOF'

## 🛡️ 状态徽章

![CI](https://github.com/$github_username/$repo_name/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-0.1.0-orange)

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/$github_username/$repo_name.git
cd $repo_name

# 启动服务
./scripts/start.sh
```

## 🚀 快速开始

查看 [快速开始指南](docs/QUICK_START.md) 获取详细安装和使用说明。

## 🤝 贡献

欢迎贡献！请查看 [贡献指南](CONTRIBUTING.md)。

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。
EOF

echo "✅ README已更新"

# 提交GitHub Actions配置
git add .github/
git add README.md
git commit -m "ci: 添加GitHub Actions工作流和徽章"

echo ""
echo "📤 推送更新..."
git push origin master

echo ""
echo "🎉 完成！您的Agent OS项目已成功推送到GitHub。"
echo "访问 https://github.com/$github_username/$repo_name 查看您的仓库。"
