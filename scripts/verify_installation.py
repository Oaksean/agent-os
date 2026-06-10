#!/usr/bin/env python3
"""
Agent OS 安装验证脚本
验证所有依赖和配置是否正确安装
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import List, Tuple


# 颜色定义
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def print_info(message: str):
    """打印信息"""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")


def print_success(message: str):
    """打印成功消息"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")


def print_warning(message: str):
    """打印警告消息"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def print_error(message: str):
    """打印错误消息"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


def check_python_version() -> Tuple[bool, str]:
    """检查Python版本"""
    print_info("检查Python版本...")

    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        return False, f"Python版本过低: {version_str}，需要Python 3.9+"

    print_success(f"Python版本: {version_str} ✓")
    return True, version_str


def check_module(module_name: str, package_name: str = None) -> Tuple[bool, str]:
    """检查Python模块是否安装"""
    if package_name is None:
        package_name = module_name

    try:
        __import__(module_name)
        print_success(f"{package_name} 已安装 ✓")
        return True, f"{package_name} 已安装"
    except ImportError:
        print_error(f"{package_name} 未安装 ✗")
        return False, f"{package_name} 未安装"


def check_command(command: str) -> Tuple[bool, str]:
    """检查系统命令是否存在"""
    try:
        result = subprocess.run(
            [command, "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            print_success(f"{command} 已安装 ✓")
            return True, f"{command} 已安装"
        else:
            print_error(f"{command} 安装异常 ✗")
            return False, f"{command} 安装异常"
    except FileNotFoundError:
        print_error(f"{command} 未找到 ✗")
        return False, f"{command} 未找到"
    except subprocess.TimeoutExpired:
        print_error(f"{command} 响应超时 ✗")
        return False, f"{command} 响应超时"
    except Exception as e:
        print_error(f"{command} 检查失败: {str(e)} ✗")
        return False, f"{command} 检查失败"


def check_file(filepath: str, description: str) -> Tuple[bool, str]:
    """检查文件是否存在"""
    path = Path(filepath)
    if path.exists():
        print_success(f"{description} 存在 ✓")
        return True, f"{description} 存在"
    else:
        print_error(f"{description} 不存在 ✗")
        return False, f"{description} 不存在"


def check_directory(dirpath: str, description: str) -> Tuple[bool, str]:
    """检查目录是否存在"""
    path = Path(dirpath)
    if path.exists() and path.is_dir():
        print_success(f"{description} 存在 ✓")
        return True, f"{description} 存在"
    else:
        print_error(f"{description} 不存在 ✗")
        return False, f"{description} 不存在"


def run_all_checks() -> Tuple[int, int]:
    """运行所有检查"""
    print("\n" + "=" * 60)
    print("Agent OS 安装验证")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0

    # 1. Python版本检查
    print("\n[1] Python环境检查")
    print("-" * 60)
    result, _ = check_python_version()
    if result:
        passed += 1
    else:
        failed += 1

    # 2. 核心依赖检查
    print("\n[2] 核心依赖检查")
    print("-" * 60)
    core_modules = [
        ("fastapi", "FastAPI"),
        ("uvicorn", "Uvicorn"),
        ("pydantic", "Pydantic"),
        ("asyncpg", "AsyncPG"),
        ("redis", "Redis"),
        ("openai", "OpenAI"),
        ("langchain", "LangChain"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
    ]

    for module, package in core_modules:
        result, _ = check_module(module, package)
        if result:
            passed += 1
        else:
            failed += 1

    # 3. 可选依赖检查
    print("\n[3] 可选依赖检查")
    print("-" * 60)
    optional_modules = [
        ("chromadb", "ChromaDB"),
        ("qdrant_client", "Qdrant Client"),
        ("llama_index", "LlamaIndex"),
    ]

    for module, package in optional_modules:
        result, _ = check_module(module, package)
        if result:
            passed += 1

    # 4. 项目文件检查
    print("\n[4] 项目文件检查")
    print("-" * 60)

    project_root = Path(__file__).parent.parent

    # 检查关键文件
    key_files = [
        (str(project_root / "README.md"), "README文档"),
        (str(project_root / "requirements.txt"), "依赖清单"),
        (str(project_root / ".env"), "环境配置"),
        (str(project_root / "setup.py"), "安装脚本"),
    ]

    for filepath, desc in key_files:
        result, _ = check_file(filepath, desc)
        if result:
            passed += 1
        else:
            failed += 1

    # 5. 项目目录检查
    print("\n[5] 项目目录检查")
    print("-" * 60)

    key_dirs = [
        (str(project_root / "src"), "源代码目录"),
        (str(project_root / "tests"), "测试目录"),
        (str(project_root / "docs"), "文档目录"),
        (str(project_root / "logs"), "日志目录"),
        (str(project_root / "data"), "数据目录"),
    ]

    for dirpath, desc in key_dirs:
        result, _ = check_directory(dirpath, desc)
        if result:
            passed += 1
        else:
            failed += 1

    # 6. 源代码模块检查
    print("\n[6] 源代码模块检查")
    print("-" * 60)

    # 将src添加到路径
    sys.path.insert(0, str(project_root / "src"))

    src_modules = [
        "kernel",
        "memory",
        "planner",
        "tools",
        "models",
    ]

    for module in src_modules:
        module_path = project_root / "src" / module
        if module_path.exists():
            print_success(f"{module} 模块存在 ✓")
            passed += 1
        else:
            print_warning(f"{module} 模块不存在（可能尚未开发）")

    # 7. 系统工具检查
    print("\n[7] 系统工具检查")
    print("-" * 60)

    system_commands = [
        ("git", "Git"),
        ("docker", "Docker（可选）"),
    ]

    for cmd, desc in system_commands:
        result, _ = check_command(cmd)
        if "可选" in desc:
            if result:
                passed += 1
        else:
            if result:
                passed += 1
            else:
                failed += 1

    return passed, failed


def print_summary(passed: int, failed: int):
    """打印总结"""
    total = passed + failed

    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)

    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n总计检查项: {total}")
    print(f"{Colors.GREEN}通过: {passed}{Colors.NC}")
    print(f"{Colors.RED}失败: {failed}{Colors.NC}")
    print(f"成功率: {success_rate:.1f}%")

    if failed == 0:
        print(f"\n{Colors.GREEN}✓ 所有检查通过！安装成功！{Colors.NC}")
        print("\n下一步:")
        print("  1. 编辑 .env 文件配置API密钥")
        print("  2. 运行 'python -m src.api.main' 启动服务")
        print("  3. 访问 http://localhost:8000 查看API文档")
        return 0
    else:
        print(f"\n{Colors.RED}✗ 部分检查失败{Colors.NC}")
        print("\n建议操作:")
        print("  1. 检查失败的依赖项")
        print("  2. 重新运行安装脚本: ./scripts/install.sh")
        print("  3. 查看文档: docs/QUICK_START.md")
        return 1


def main():
    """主函数"""
    try:
        passed, failed = run_all_checks()
        exit_code = print_summary(passed, failed)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n验证已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"验证过程出错: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
