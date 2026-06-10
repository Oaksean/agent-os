#!/usr/bin/env python3
"""
Agent OS 快速启动脚本
一键启动API服务和Dashboard
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# 颜色输出
class Colors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header():
    """打印标题"""
    print(f"{Colors.OKBLUE}{Colors.BOLD}")
    print("=" * 60)
    print("        🤖 Agent OS v0.3.0 - 快速启动")
    print("=" * 60)
    print(f"{Colors.ENDC}\n")


def check_dependencies():
    """检查依赖"""
    print(f"{Colors.OKCYAN}[1/4] 检查依赖...{Colors.ENDC}")

    try:
        import fastapi
        import uvicorn

        print(f"{Colors.OKGREEN}  ✓ FastAPI installed{Colors.ENDC}")
    except ImportError:
        print(f"{Colors.FAIL}  ✗ FastAPI not found{Colors.ENDC}")
        print(f"{Colors.WARNING}  Installing dependencies...{Colors.ENDC}")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )

    print()


def start_api_server():
    """启动API服务器"""
    print(f"{Colors.OKCYAN}[2/4] 启动API服务器...{Colors.ENDC}")

    api_script = PROJECT_ROOT / "src" / "api" / "main_complete.py"

    if not api_script.exists():
        print(f"{Colors.FAIL}  ✗ API script not found: {api_script}{Colors.ENDC}")
        sys.exit(1)

    # 启动API服务
    api_process = subprocess.Popen(
        [sys.executable, str(api_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
    )

    # 等待服务启动
    print(
        f"{Colors.OKGREEN}  ✓ API server starting on http://localhost:8000{Colors.ENDC}"
    )
    print()

    return api_process


def start_dashboard():
    """启动Dashboard"""
    print(f"{Colors.OKCYAN}[3/4] 启动Dashboard...{Colors.ENDC}")

    dashboard_dir = PROJECT_ROOT / "dashboard"

    if not dashboard_dir.exists():
        print(
            f"{Colors.FAIL}  ✗ Dashboard directory not found: {dashboard_dir}{Colors.ENDC}"
        )
        sys.exit(1)

    # 使用Python内置HTTP服务器
    dashboard_process = subprocess.Popen(
        [sys.executable, "-m", "http.server", "8080"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dashboard_dir),
    )

    # 等待服务启动
    time.sleep(1)

    print(
        f"{Colors.OKGREEN}  ✓ Dashboard starting on http://localhost:8080{Colors.ENDC}"
    )
    print()

    return dashboard_process


def open_browser():
    """打开浏览器"""
    print(f"{Colors.OKCYAN}[4/4] 打开浏览器...{Colors.ENDC}")

    time.sleep(2)  # 等待服务完全启动

    dashboard_url = "http://localhost:8080"
    webbrowser.open(dashboard_url)

    print(f"{Colors.OKGREEN}  ✓ Browser opened: {dashboard_url}{Colors.ENDC}")
    print()


def print_info():
    """打印信息"""
    print(f"{Colors.OKBLUE}{Colors.BOLD}")
    print("=" * 60)
    print("  🎉 Agent OS 已成功启动!")
    print("=" * 60)
    print(f"{Colors.ENDC}")
    print(f"{Colors.BOLD}服务地址:{Colors.ENDC}")
    print(f"  • API服务: {Colors.OKCYAN}http://localhost:8000{Colors.ENDC}")
    print(f"  • API文档: {Colors.OKCYAN}http://localhost:8000/docs{Colors.ENDC}")
    print(f"  • Dashboard: {Colors.OKCYAN}http://localhost:8080{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}快速操作:{Colors.ENDC}")
    print(f"  • 按 Ctrl+C 停止所有服务")
    print()
    print(f"{Colors.BOLD}测试用户:{Colors.ENDC}")
    print(f"  • User ID: test_user_001")
    print(f"  • Role: admin")
    print(f"  • 在请求头添加: X-User-ID: test_user_001")
    print()


def main():
    """主函数"""
    try:
        # 打印标题
        print_header()

        # 检查依赖
        check_dependencies()

        # 启动API服务器
        api_process = start_api_server()

        # 启动Dashboard
        dashboard_process = start_dashboard()

        # 打开浏览器
        open_browser()

        # 打印信息
        print_info()

        # 等待用户中断
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n{Colors.WARNING}正在停止服务...{Colors.ENDC}")

            # 停止进程
            api_process.terminate()
            dashboard_process.terminate()

            print(f"{Colors.OKGREEN}✓ 服务已停止{Colors.ENDC}")
            sys.exit(0)

    except Exception as e:
        print(f"{Colors.FAIL}Error: {e}{Colors.ENDC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
