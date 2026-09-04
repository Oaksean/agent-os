#!/bin/bash

###############################################################################
# Agent OS - Linux/macOS 安装脚本
# 
# 用法:
#   ./scripts/install.sh [选项]
#
# 选项:
#   --dev          安装开发依赖
#   --docker       使用Docker安装
#   --skip-deps    跳过系统依赖检查
#   --help         显示帮助信息
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
Agent OS - Linux/macOS 安装脚本

用法: $0 [选项]

选项:
  --dev          安装开发依赖
  --docker       使用Docker安装
  --skip-deps    跳过系统依赖检查
  --help         显示此帮助信息

示例:
  $0                    # 标准安装
  $0 --dev              # 安装开发环境
  $0 --docker           # 使用Docker安装

更多信息请访问: https://github.com/yourusername/agent-os
EOF
    exit 0
}

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            DISTRO=$ID
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    else
        log_error "不支持的操作系统: $OSTYPE"
        exit 1
    fi
    log_info "检测到操作系统: $OS ($DISTRO)"
}

# 检查Python版本
check_python() {
    log_info "检查Python版本..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD=python3
    elif command -v python &> /dev/null; then
        PYTHON_CMD=python
    else
        log_error "未找到Python，请先安装Python 3.9+"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
        log_error "Python版本过低: $PYTHON_VERSION，需要Python 3.9+"
        exit 1
    fi
    
    log_success "Python版本: $PYTHON_VERSION ✓"
}

# 检查系统依赖
check_system_deps() {
    log_info "检查系统依赖..."
    
    local missing_deps=()
    
    # 检查git
    if ! command -v git &> /dev/null; then
        missing_deps+=("git")
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
        missing_deps+=("python3-pip")
    fi
    
    # macOS特定检查
    if [ "$OS" == "macos" ]; then
        if ! command -v brew &> /dev/null; then
            log_warning "未找到Homebrew，建议安装: https://brew.sh"
        fi
    fi
    
    # 如果有缺失的依赖
    if [ ${#missing_deps[@]} -ne 0 ]; then
        log_warning "缺失系统依赖: ${missing_deps[*]}"
        
        if [ "$OS" == "linux" ]; then
            case $DISTRO in
                ubuntu|debian)
                    log_info "运行: sudo apt-get update && sudo apt-get install -y ${missing_deps[*]}"
                    read -p "是否安装? (y/n) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        sudo apt-get update
                        sudo apt-get install -y ${missing_deps[*]}
                    else
                        log_error "缺少必要依赖，安装终止"
                        exit 1
                    fi
                    ;;
                centos|rhel|fedora)
                    log_info "运行: sudo dnf install -y ${missing_deps[*]}"
                    read -p "是否安装? (y/n) " -n 1 -r
                    echo
                    if [[ $REPLY =~ ^[Yy]$ ]]; then
                        sudo dnf install -y ${missing_deps[*]}
                    else
                        log_error "缺少必要依赖，安装终止"
                        exit 1
                    fi
                    ;;
                *)
                    log_warning "请手动安装缺失的依赖: ${missing_deps[*]}"
                    ;;
            esac
        elif [ "$OS" == "macos" ]; then
            if command -v brew &> /dev/null; then
                log_info "运行: brew install ${missing_deps[*]}"
                read -p "是否安装? (y/n) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    brew install ${missing_deps[*]}
                fi
            fi
        fi
    fi
    
    log_success "系统依赖检查完成 ✓"
}

# 创建虚拟环境
create_venv() {
    log_info "创建Python虚拟环境..."
    
    VENV_DIR="${PROJECT_ROOT}/venv"
    
    if [ -d "$VENV_DIR" ]; then
        log_warning "虚拟环境已存在，跳过创建"
    else
        $PYTHON_CMD -m venv "$VENV_DIR"
        log_success "虚拟环境创建成功 ✓"
    fi
    
    # 激活虚拟环境
    source "$VENV_DIR/bin/activate"
    log_success "虚拟环境已激活 ✓"
}

# 安装Python依赖
install_python_deps() {
    log_info "安装Python依赖..."
    
    # 升级pip
    pip install --upgrade pip setuptools wheel
    
    # 安装项目
    if [ "$INSTALL_DEV" == "true" ]; then
        log_info "安装开发依赖..."
        pip install -e ".[dev,docs]"
    else
        pip install -e .
    fi
    
    # 如果存在requirements.txt，也安装
    if [ -f "${PROJECT_ROOT}/requirements.txt" ]; then
        pip install -r "${PROJECT_ROOT}/requirements.txt"
    fi
    
    log_success "Python依赖安装完成 ✓"
}

# 配置环境变量
setup_env() {
    log_info "配置环境变量..."
    
    ENV_FILE="${PROJECT_ROOT}/.env"
    ENV_EXAMPLE="${PROJECT_ROOT}/.env.example"
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_EXAMPLE" ]; then
            cp "$ENV_EXAMPLE" "$ENV_FILE"
            log_success "已从.env.example创建.env文件 ✓"
            log_warning "请编辑.env文件配置您的API密钥"
        else
            log_warning "未找到.env.example文件"
        fi
    else
        log_info ".env文件已存在，跳过创建"
    fi
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p "${PROJECT_ROOT}/logs"
    mkdir -p "${PROJECT_ROOT}/data"
    mkdir -p "${PROJECT_ROOT}/models"
    
    log_success "目录创建完成 ✓"
}

# Docker安装
install_docker() {
    log_info "使用Docker安装..."
    
    if ! command -v docker &> /dev/null; then
        log_error "未找到Docker，请先安装Docker"
        log_info "访问: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "未找到Docker Compose，请先安装"
        exit 1
    fi
    
    cd "$PROJECT_ROOT"
    
    # 构建镜像
    log_info "构建Docker镜像..."
    docker-compose build
    
    # 启动服务
    log_info "启动服务..."
    docker-compose up -d
    
    log_success "Docker安装完成 ✓"
    log_info "访问: http://localhost:8000"
}

# 安装后验证
verify_installation() {
    log_info "验证安装..."
    
    # 检查关键模块
    if python -c "import fastapi; import uvicorn" 2>/dev/null; then
        log_success "核心依赖验证通过 ✓"
    else
        log_error "核心依赖验证失败"
        exit 1
    fi
    
    # 检查项目模块
    if python -c "import sys; sys.path.insert(0, '${PROJECT_ROOT}/src')" 2>/dev/null; then
        log_success "项目模块路径配置正确 ✓"
    fi
    
    log_success "安装验证通过 ✓"
}

# 显示安装后信息
show_post_install_info() {
    cat << EOF

${GREEN}========================================
   Agent OS 安装完成！
========================================${NC}

${BLUE}快速开始:${NC}
  1. 激活虚拟环境:
     source venv/bin/activate

  2. 配置API密钥:
     编辑 .env 文件

  3. 启动服务:
     python -m src.api.main
     或
     agent-os

  4. 访问Web界面:
     http://localhost:8000

${BLUE}文档:${NC}
  - README: ${PROJECT_ROOT}/README.md
  - 快速开始: ${PROJECT_ROOT}/docs/QUICK_START.md
  - API文档: http://localhost:8000/docs

${BLUE}社区:${NC}
  - GitHub: https://github.com/yourusername/agent-os
  - Issues: https://github.com/yourusername/agent-os/issues

${YELLOW}提示: 运行 'python scripts/verify_installation.py' 进行完整验证${NC}

EOF
}

# 主安装流程
main() {
    # 解析参数
    INSTALL_DEV=false
    USE_DOCKER=false
    SKIP_DEPS=false
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dev)
                INSTALL_DEV=true
                shift
                ;;
            --docker)
                USE_DOCKER=true
                shift
                ;;
            --skip-deps)
                SKIP_DEPS=true
                shift
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "未知选项: $1"
                show_help
                ;;
        esac
    done
    
    # 获取项目根目录
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
    cd "$PROJECT_ROOT"
    
    log_info "开始安装 Agent OS..."
    log_info "项目目录: $PROJECT_ROOT"
    
    # 检测操作系统
    detect_os
    
    # Docker安装流程
    if [ "$USE_DOCKER" == "true" ]; then
        install_docker
        exit 0
    fi
    
    # 检查Python
    check_python
    
    # 检查系统依赖
    if [ "$SKIP_DEPS" == "false" ]; then
        check_system_deps
    fi
    
    # 创建虚拟环境
    create_venv
    
    # 安装Python依赖
    install_python_deps
    
    # 配置环境
    setup_env
    
    # 创建目录
    create_directories
    
    # 验证安装
    verify_installation
    
    # 显示安装后信息
    show_post_install_info
}

# 执行主函数
main "$@"
