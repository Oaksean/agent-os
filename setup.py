#!/usr/bin/env python
"""
Agent OS - 智能体操作系统
面向"自主智能体"计算范式设计的系统内核与用户态基础设施
"""

from setuptools import setup, find_packages
from pathlib import Path

# 读取README文件
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# 读取requirements
requirements = []
requirements_file = this_directory / "requirements.txt"
if requirements_file.exists():
    with open(requirements_file, "r", encoding="utf-8") as f:
        requirements = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]

setup(
    name="agent-os",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="智能体操作系统 - 面向自主智能体的系统内核与基础设施",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/agent-os",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Operating System",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "mypy>=1.7.1",
            "flake8>=6.1.0",
            "pre-commit>=3.5.0",
        ],
        "docs": [
            "sphinx>=7.2.6",
            "sphinx-rtd-theme>=2.0.0",
            "myst-parser>=2.0.0",
        ],
        "all": [
            "docker>=6.1.3",
            "kubernetes>=28.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "agent-os=src.api.main:main",
            "agent-cli=src.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json", "*.txt"],
    },
    zip_safe=False,
    keywords="agent operating-system ai llm autonomous-agents",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/agent-os/issues",
        "Source": "https://github.com/yourusername/agent-os",
        "Documentation": "https://github.com/yourusername/agent-os/tree/main/docs",
    },
)
