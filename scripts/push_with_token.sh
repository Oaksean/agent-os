#!/bin/bash

# GitHub令牌推送脚本
# 使用GitHub个人访问令牌推送代码

echo "🚀 Agent OS GitHub推送脚本"
echo "=" * 50

# 检查是否在项目目录中
if [ ! -f "README.md" ] || [ ! -d "src" ]; then
    echo "❌ 错误：请在agent-os项目根目录运行此脚本"
    exit 1
fi

# 设置远程仓库
echo "设置远程仓库..."
git remote remove origin 2>/dev/null
git remote add origin https://github.com/Oaksean/agent-os.git

# 获取GitHub令牌
echo ""
echo "🔑 请输入GitHub个人访问令牌"
echo "获取地址：https://github.com/settings/tokens"
echo "需要权限：repo (全部仓库权限)"
echo ""
read -sp "请输入令牌: " GITHUB_TOKEN
echo ""

if [ -z "$GITHUB_TOKEN" ]; then
    echo "❌ 错误：令牌不能为空"
    exit 1
fi

# 验证令牌格式（基本检查）
if [[ ! $GITHUB_TOKEN =~ ^(ghp_|gho_|ghu_|ghs_|ghr_) ]]; then
    echo "⚠️  警告：令牌格式可能不正确"
    echo "GitHub令牌通常以 ghp_ 开头"
    read -p "是否继续？(y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 使用令牌设置远程仓库URL
echo "配置远程仓库使用令牌..."
REMOTE_URL="https://${GITHUB_TOKEN}@github.com/Oaksean/agent-os.git"
git remote set-url origin "$REMOTE_URL"

# 推送代码
echo ""
echo "📤 推送代码到GitHub..."
echo "仓库：https://github.com/Oaksean/agent-os"
echo "分支：master"
echo ""

if git push -u origin master; then
    echo ""
    echo "✅ 推送成功！"
    echo ""
    echo "🎉 恭喜！Agent OS项目已成功上传到GitHub！"
    echo ""
    echo "🔗 您的仓库地址：https://github.com/Oaksean/agent-os"
    echo "📚 文档地址：https://github.com/Oaksean/agent-os#readme"
    echo "⚡ GitHub Actions将自动运行测试"
    echo ""
    echo "下一步："
    echo "1. 访问 https://github.com/Oaksean/agent-os 查看仓库"
    echo "2. 检查GitHub Actions运行状态"
    echo "3. 邀请协作者参与开发"
    echo "4. 创建第一个Release版本"
else
    echo ""
    echo "❌ 推送失败！"
    echo ""
    echo "可能的原因："
    echo "1. 令牌无效或权限不足"
    echo "2. 网络连接问题"
    echo "3. 仓库不存在或没有写入权限"
    echo ""
    echo "解决方案："
    echo "1. 确认令牌有 repo 权限"
    echo "2. 检查网络连接"
    echo "3. 确认仓库 https://github.com/Oaksean/agent-os 存在"
    echo ""
    echo "可以手动尝试："
    echo "git push -u origin master"
    exit 1
fi

# 恢复原始远程URL（安全考虑）
echo ""
echo "恢复原始远程URL..."
git remote set-url origin https://github.com/Oaksean/agent-os.git

echo ""
echo "✅ 脚本执行完成！"
echo "注意：GitHub令牌已从本地配置中移除"
echo "下次推送需要重新输入令牌或配置SSH密钥"
