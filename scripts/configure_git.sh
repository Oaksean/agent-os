#!/bin/bash

# Agent OS Git配置脚本
# 运行此脚本前，请替换YOUR_GITHUB_USERNAME和YOUR_EMAIL

echo "🔧 配置Git用于GitHub上传..."
echo ""

# 检查是否在项目目录中
if [ ! -f "README.md" ] || [ ! -d "src" ]; then
    echo "❌ 错误：请在agent-os项目根目录运行此脚本"
    exit 1
fi

# 设置变量（请修改这些值）
GITHUB_USERNAME="YOUR_GITHUB_USERNAME"  # 请替换为您的GitHub用户名
GITHUB_EMAIL="YOUR_EMAIL"              # 请替换为您的GitHub邮箱
REPO_NAME="agent-os"

echo "当前配置："
echo "GitHub用户名: $GITHUB_USERNAME"
echo "GitHub邮箱: $GITHUB_EMAIL"
echo "仓库名称: $REPO_NAME"
echo ""

read -p "确认配置正确？(y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "请编辑脚本中的GITHUB_USERNAME和GITHUB_EMAIL变量"
    exit 1
fi

# 设置Git配置
echo "设置Git全局配置..."
git config --global user.name "$GITHUB_USERNAME"
git config --global user.email "$GITHUB_EMAIL"

# 验证配置
echo ""
echo "验证配置："
echo "用户名: $(git config --global user.name)"
echo "邮箱: $(git config --global user.email)"

# 添加远程仓库
echo ""
echo "添加远程仓库..."
REMOTE_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
git remote remove origin 2>/dev/null
git remote add origin "$REMOTE_URL"

echo "远程仓库设置："
git remote -v

# 检查Git状态
echo ""
echo "Git状态："
git status

echo ""
echo "✅ Git配置完成！"
echo ""
echo "下一步操作："
echo "1. 在GitHub网站创建仓库: https://github.com/new"
echo "2. 仓库名称: $REPO_NAME"
echo "3. 不要初始化仓库（我们已有代码）"
echo "4. 创建后运行: git push -u origin master"
echo ""
echo "如果遇到认证问题，使用GitHub个人访问令牌作为密码"
echo "生成令牌: https://github.com/settings/tokens"
