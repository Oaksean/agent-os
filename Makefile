# Agent OS Makefile
# 简化常用操作的命令集合

.PHONY: help install install-dev install-docker clean test lint format run dev docker-up docker-down docs

# 默认目标
.DEFAULT_GOAL := help

# 变量定义
PYTHON := python3
VENV_DIR := venv
VENV_ACTIVATE := $(VENV_DIR)/bin/activate
PROJECT_NAME := agent-os

# 帮助信息
help: ## 显示帮助信息
	@echo "Agent OS - 可用命令:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# 安装
install: ## 标准安装
	@echo "安装 Agent OS..."
	$(PYTHON) -m venv $(VENV_DIR)
	. $(VENV_ACTIVATE) && pip install --upgrade pip setuptools wheel
	. $(VENV_ACTIVATE) && pip install -e .
	@echo "安装完成!"

install-dev: ## 安装开发环境
	@echo "安装开发环境..."
	$(PYTHON) -m venv $(VENV_DIR)
	. $(VENV_ACTIVATE) && pip install --upgrade pip setuptools wheel
	. $(VENV_ACTIVATE) && pip install -e ".[dev,docs]"
	. $(VENV_ACTIVATE) && pre-commit install
	@echo "开发环境安装完成!"

install-docker: ## 使用Docker安装
	@echo "使用Docker安装..."
	docker-compose build
	docker-compose up -d
	@echo "Docker安装完成! 访问: http://localhost:8000"

# 开发
run: ## 运行生产服务器
	. $(VENV_ACTIVATE) && $(PYTHON) -m src.api.main

dev: ## 运行开发服务器（自动重载）
	. $(VENV_ACTIVATE) && uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 测试
test: ## 运行所有测试
	. $(VENV_ACTIVATE) && pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-unit: ## 运行单元测试
	. $(VENV_ACTIVATE) && pytest tests/unit -v

test-integration: ## 运行集成测试
	. $(VENV_ACTIVATE) && pytest tests/integration -v

# 代码质量
lint: ## 代码检查
	. $(VENV_ACTIVATE) && flake8 src/ tests/
	. $(VENV_ACTIVATE) && mypy src/

format: ## 格式化代码
	. $(VENV_ACTIVATE) && black src/ tests/
	. $(VENV_ACTIVATE) && isort src/ tests/

format-check: ## 检查代码格式
	. $(VENV_ACTIVATE) && black --check src/ tests/
	. $(VENV_ACTIVATE) && isort --check-only src/ tests/

# Docker
docker-up: ## 启动Docker服务
	docker-compose up -d

docker-down: ## 停止Docker服务
	docker-compose down

docker-logs: ## 查看Docker日志
	docker-compose logs -f

docker-restart: ## 重启Docker服务
	docker-compose restart

# 数据库
db-init: ## 初始化数据库
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/init_db.py

db-migrate: ## 运行数据库迁移
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/migrate_db.py

db-reset: ## 重置数据库
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/reset_db.py

# 文档
docs: ## 生成文档
	. $(VENV_ACTIVATE) && cd docs && make html

docs-serve: ## 启动文档服务器
	. $(VENV_ACTIVATE) && cd docs/_build/html && $(PYTHON) -m http.server 8001

# 清理
clean: ## 清理构建产物
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean-all: clean ## 清理所有生成文件（包括虚拟环境）
	rm -rf $(VENV_DIR)
	rm -rf .tox
	rm -rf .eggs

# 其他
check: lint test ## 运行完整检查（代码检查+测试）

version: ## 显示版本信息
	@echo "$(PROJECT_NAME) version: $$(python -c 'import setup; print(setup.setup().get("version", "unknown"))')"

# 监控
monitor: ## 启动监控服务
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/monitoring/start_monitoring.py

# 备份
backup: ## 备份数据
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/backup.py

restore: ## 恢复数据
	. $(VENV_ACTIVATE) && $(PYTHON) scripts/restore.py
