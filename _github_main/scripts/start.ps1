# Agent OS 启动脚本 (Windows PowerShell)

Write-Host "🚀 启动 Agent OS 系统..." -ForegroundColor Green

# 检查Python版本
$pythonVersion = python --version 2>&1
if ($pythonVersion -notmatch "Python 3\.[9-9]|3\.1[0-1]") {
    Write-Host "❌ 需要 Python 3.9+，当前版本: $pythonVersion" -ForegroundColor Red
    exit 1
}

# 检查依赖
Write-Host "📦 检查依赖..." -ForegroundColor Cyan
if (!(Get-Command pip -ErrorAction SilentlyContinue)) {
    Write-Host "❌ pip 未安装" -ForegroundColor Red
    exit 1
}

# 创建虚拟环境（如果不存在）
if (!(Test-Path "venv")) {
    Write-Host "🔧 创建虚拟环境..." -ForegroundColor Cyan
    python -m venv venv
}

# 激活虚拟环境
if (Test-Path "venv\Scriptsctivate.ps1") {
    & "venv\Scriptsctivate.ps1"
} else {
    Write-Host "❌ 无法激活虚拟环境" -ForegroundColor Red
    exit 1
}

# 安装依赖
Write-Host "📦 安装Python依赖..." -ForegroundColor Cyan
pip install --upgrade pip
pip install -r requirements.txt

# 创建必要的目录
Write-Host "📁 创建必要的目录..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path logs, data, snapshots, config | Out-Null

# 复制配置文件（如果不存在）
if (!(Test-Path "config\config.yaml")) {
    Write-Host "⚙️ 复制配置文件..." -ForegroundColor Cyan
    Copy-Item config.example.yaml config\config.yaml
    Write-Host "⚠️  请编辑 config\config.yaml 文件以配置系统" -ForegroundColor Yellow
}

if (!(Test-Path ".env")) {
    Write-Host "⚙️ 复制环境变量文件..." -ForegroundColor Cyan
    Copy-Item .env.example .env
    Write-Host "⚠️  请编辑 .env 文件以配置环境变量" -ForegroundColor Yellow
}

# 启动服务
Write-Host "🚀 启动 Agent OS API 服务..." -ForegroundColor Green
Write-Host "🌐 API地址: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 API文档: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "📊 监控面板: http://localhost:3000 (如果启用)" -ForegroundColor Cyan
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host ""

# 运行API服务
python -m src.api.main
