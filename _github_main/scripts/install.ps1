<#
.SYNOPSIS
    Agent OS - Windows 安装脚本
    
.DESCRIPTION
    此脚本用于在Windows系统上安装Agent OS
    
.PARAMETER Dev
    安装开发依赖

.PARAMETER Docker
    使用Docker安装

.PARAMETER SkipDeps
    跳过系统依赖检查

.EXAMPLE
    .\install.ps1
    标准安装

.EXAMPLE
    .\install.ps1 -Dev
    安装开发环境

.EXAMPLE
    .\install.ps1 -Docker
    使用Docker安装

.NOTES
    作者: Your Name
    版本: 0.1.0
#>

param(
    [switch]$Dev,
    [switch]$Docker,
    [switch]$SkipDeps,
    [switch]$Help
)

# 错误处理
$ErrorActionPreference = "Stop"

# 颜色函数
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $color = switch ($Type) {
        "Info" { "Cyan" }
        "Success" { "Green" }
        "Warning" { "Yellow" }
        "Error" { "Red" }
        default { "White" }
    }
    
    $prefix = switch ($Type) {
        "Info" { "[INFO]" }
        "Success" { "[SUCCESS]" }
        "Warning" { "[WARNING]" }
        "Error" { "[ERROR]" }
        default { "" }
    }
    
    Write-Host "$prefix " -ForegroundColor $color -NoNewline
    Write-Host $Message
}

# 显示帮助信息
function Show-Help {
    $helpText = @"

Agent OS - Windows 安装脚本

用法: .\install.ps1 [选项]

选项:
  -Dev          安装开发依赖
  -Docker       使用Docker安装
  -SkipDeps     跳过系统依赖检查
  -Help         显示此帮助信息

示例:
  .\install.ps1              # 标准安装
  .\install.ps1 -Dev         # 安装开发环境
  .\install.ps1 -Docker      # 使用Docker安装

更多信息请访问: https://github.com/yourusername/agent-os

"@
    Write-Host $helpText
    exit 0
}

# 检查管理员权限
function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 检查Python
function Test-Python {
    Write-ColorOutput "检查Python版本..." "Info"
    
    $pythonCmd = $null
    $pythonVersion = $null
    
    # 尝试找到Python
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        Write-ColorOutput "未找到Python，请先安装Python 3.9+" "Error"
        Write-ColorOutput "下载地址: https://www.python.org/downloads/" "Info"
        exit 1
    }
    
    # 获取版本
    $versionOutput = & $pythonCmd --version 2>&1
    if ($versionOutput -match "Python (\d+)\.(\d+)") {
        $major = [int]$matches[1]
        $minor = [int]$matches[2]
        $pythonVersion = "$major.$minor"
        
        if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 9)) {
            Write-ColorOutput "Python版本过低: $pythonVersion，需要Python 3.9+" "Error"
            exit 1
        }
        
        Write-ColorOutput "Python版本: $pythonVersion ✓" "Success"
        return $pythonCmd
    } else {
        Write-ColorOutput "无法获取Python版本" "Error"
        exit 1
    }
}

# 检查系统依赖
function Test-SystemDependencies {
    Write-ColorOutput "检查系统依赖..." "Info"
    
    $missingDeps = @()
    
    # 检查git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        $missingDeps += "git"
    }
    
    # 检查pip
    if (-not (Get-Command pip -ErrorAction SilentlyContinue) -and 
        -not (Get-Command pip3 -ErrorAction SilentlyContinue)) {
        $missingDeps += "pip"
    }
    
    if ($missingDeps.Count -gt 0) {
        Write-ColorOutput "缺失系统依赖: $($missingDeps -join ', ')" "Warning"
        
        if (Test-Administrator) {
            Write-ColorOutput "检测到管理员权限，尝试安装..." "Info"
            
            foreach ($dep in $missingDeps) {
                switch ($dep) {
                    "git" {
                        Write-ColorOutput "安装Git..." "Info"
                        winget install --id Git.Git -e --source winget
                    }
                    "pip" {
                        Write-ColorOutput "安装pip..." "Info"
                        # Python安装时通常已包含pip
                    }
                }
            }
        } else {
            Write-ColorOutput "请手动安装缺失的依赖或以管理员身份运行此脚本" "Warning"
            Write-ColorOutput "Git下载: https://git-scm.com/download/win" "Info"
            
            $response = Read-Host "是否继续安装? (y/n)"
            if ($response -ne "y") {
                Write-ColorOutput "安装已取消" "Error"
                exit 1
            }
        }
    } else {
        Write-ColorOutput "系统依赖检查完成 ✓" "Success"
    }
}

# 创建虚拟环境
function New-VirtualEnvironment {
    param($PythonCmd, $ProjectRoot)
    
    Write-ColorOutput "创建Python虚拟环境..." "Info"
    
    $venvPath = Join-Path $ProjectRoot "venv"
    
    if (Test-Path $venvPath) {
        Write-ColorOutput "虚拟环境已存在，跳过创建" "Warning"
    } else {
        & $PythonCmd -m venv $venvPath
        Write-ColorOutput "虚拟环境创建成功 ✓" "Success"
    }
    
    # 激活虚拟环境
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        & $activateScript
        Write-ColorOutput "虚拟环境已激活 ✓" "Success"
    } else {
        Write-ColorOutput "未找到激活脚本: $activateScript" "Error"
        exit 1
    }
}

# 安装Python依赖
function Install-PythonDependencies {
    param($ProjectRoot, $InstallDev)
    
    Write-ColorOutput "安装Python依赖..." "Info"
    
    # 升级pip
    python -m pip install --upgrade pip setuptools wheel
    
    # 安装项目
    if ($InstallDev) {
        Write-ColorOutput "安装开发依赖..." "Info"
        pip install -e ".[dev,docs]"
    } else {
        pip install -e .
    }
    
    # 如果存在requirements.txt，也安装
    $requirementsPath = Join-Path $ProjectRoot "requirements.txt"
    if (Test-Path $requirementsPath) {
        pip install -r $requirementsPath
    }
    
    Write-ColorOutput "Python依赖安装完成 ✓" "Success"
}

# 配置环境变量
function Set-Environment {
    param($ProjectRoot)
    
    Write-ColorOutput "配置环境变量..." "Info"
    
    $envFile = Join-Path $ProjectRoot ".env"
    $envExample = Join-Path $ProjectRoot ".env.example"
    
    if (-not (Test-Path $envFile)) {
        if (Test-Path $envExample) {
            Copy-Item $envExample $envFile
            Write-ColorOutput "已从.env.example创建.env文件 ✓" "Success"
            Write-ColorOutput "请编辑.env文件配置您的API密钥" "Warning"
        } else {
            Write-ColorOutput "未找到.env.example文件" "Warning"
        }
    } else {
        Write-ColorOutput ".env文件已存在，跳过创建" "Info"
    }
}

# 创建必要目录
function New-ProjectDirectories {
    param($ProjectRoot)
    
    Write-ColorOutput "创建必要目录..." "Info"
    
    $directories = @("logs", "data", "models")
    
    foreach ($dir in $directories) {
        $path = Join-Path $ProjectRoot $dir
        if (-not (Test-Path $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
    
    Write-ColorOutput "目录创建完成 ✓" "Success"
}

# Docker安装
function Install-Docker {
    param($ProjectRoot)
    
    Write-ColorOutput "使用Docker安装..." "Info"
    
    # 检查Docker
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-ColorOutput "未找到Docker，请先安装Docker Desktop" "Error"
        Write-ColorOutput "下载地址: https://www.docker.com/products/docker-desktop" "Info"
        exit 1
    }
    
    # 检查Docker是否运行
    try {
        docker info | Out-Null
    } catch {
        Write-ColorOutput "Docker未运行，请先启动Docker Desktop" "Error"
        exit 1
    }
    
    Set-Location $ProjectRoot
    
    # 构建镜像
    Write-ColorOutput "构建Docker镜像..." "Info"
    docker-compose build
    
    # 启动服务
    Write-ColorOutput "启动服务..." "Info"
    docker-compose up -d
    
    Write-ColorOutput "Docker安装完成 ✓" "Success"
    Write-ColorOutput "访问: http://localhost:8000" "Info"
}

# 验证安装
function Test-Installation {
    Write-ColorOutput "验证安装..." "Info"
    
    # 检查关键模块
    try {
        python -c "import fastapi; import uvicorn" 2>$null
        Write-ColorOutput "核心依赖验证通过 ✓" "Success"
    } catch {
        Write-ColorOutput "核心依赖验证失败" "Error"
        exit 1
    }
    
    Write-ColorOutput "安装验证通过 ✓" "Success"
}

# 显示安装后信息
function Show-PostInstallInfo {
    param($ProjectRoot)
    
    $infoText = @"

========================================
   Agent OS 安装完成！
========================================

快速开始:
  1. 激活虚拟环境:
     .\venv\Scripts\Activate.ps1

  2. 配置API密钥:
     编辑 .env 文件

  3. 启动服务:
     python -m src.api.main
     或
     agent-os

  4. 访问Web界面:
     http://localhost:8000

文档:
  - README: $ProjectRoot\README.md
  - 快速开始: $ProjectRoot\docs\QUICK_START.md
  - API文档: http://localhost:8000/docs

社区:
  - GitHub: https://github.com/yourusername/agent-os
  - Issues: https://github.com/yourusername/agent-os/issues

提示: 运行 'python scripts/verify_installation.py' 进行完整验证

"@
    
    Write-Host $infoText -ForegroundColor Green
}

# 主函数
function Main {
    # 显示帮助
    if ($Help) {
        Show-Help
    }
    
    # 获取项目根目录
    $scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectRoot = Split-Path -Parent $scriptPath
    Set-Location $projectRoot
    
    Write-ColorOutput "开始安装 Agent OS..." "Info"
    Write-ColorOutput "项目目录: $projectRoot" "Info"
    
    # Docker安装流程
    if ($Docker) {
        Install-Docker -ProjectRoot $projectRoot
        exit 0
    }
    
    # 检查Python
    $pythonCmd = Test-Python
    
    # 检查系统依赖
    if (-not $SkipDeps) {
        Test-SystemDependencies
    }
    
    # 创建虚拟环境
    New-VirtualEnvironment -PythonCmd $pythonCmd -ProjectRoot $projectRoot
    
    # 安装Python依赖
    Install-PythonDependencies -ProjectRoot $projectRoot -InstallDev $Dev
    
    # 配置环境
    Set-Environment -ProjectRoot $projectRoot
    
    # 创建目录
    New-ProjectDirectories -ProjectRoot $projectRoot
    
    # 验证安装
    Test-Installation
    
    # 显示安装后信息
    Show-PostInstallInfo -ProjectRoot $projectRoot
}

# 执行主函数
Main
