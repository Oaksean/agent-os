#!/bin/bash

# Agent OS 启动脚本

set -e

echo "🚀 启动 Agent OS 系统..."

# 检查Python版本
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
if [[ $PYTHON_VERSION != 3.9* && $PYTHON_VERSION != 3.10* && $PYTHON_VERSION != 3.11* ]]; then
    echo "❌ 需要 Python 3.9+，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 检查依赖
echo "📦 检查依赖..."
if ! command -v pip &> /dev/null; then
    echo "❌ pip 未安装"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "🔧 创建虚拟环境..."
    python -m venv venv
fi

# 激活虚拟环境
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "❌ 无法激活虚拟环境"
    exit 1
fi

# 安装依赖
echo "📦 安装Python依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs data snapshots config

# 复制配置文件（如果不存在）
if [ ! -f "config/config.yaml" ]; then
    echo "⚙️ 复制配置文件..."
    cp config.example.yaml config/config.yaml
    echo "⚠️  请编辑 config/config.yaml 文件以配置系统"
fi

if [ ! -f ".env" ]; then
    echo "⚙️ 复制环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件以配置环境变量"
fi

# 启动服务
echo "🚀 启动 Agent OS API 服务..."
echo "🌐 API地址: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/docs"
echo "📊 监控面板: http://localhost:3000 (如果启用)"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 运行API服务
python -m src.api.main
