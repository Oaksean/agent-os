# Agent OS GitHub上传 - 分步指南

## 第1步：在GitHub网页创建仓库

1. **登录GitHub**：访问 https://github.com 并登录您的账户
2. **创建新仓库**：点击右上角 "+" 图标 → "New repository"
3. **填写仓库信息**：
   - **Repository name**: `agent-os`
   - **Description**: `Agent OS - 智能体操作系统，为AI智能体提供运行、感知、规划、记忆、行动、协作与自我进化的统一环境`
   - **Public**（选择公开）
   - **不要勾选**任何初始化选项（我们已有完整代码）
4. **点击"Create repository"**

## 第2步：配置本地Git

在终端中运行以下命令（替换YOUR_GITHUB_USERNAME和YOUR_EMAIL）：

```bash
# 进入项目目录
cd agent-os

# 设置Git用户信息
git config --global user.name "YOUR_GITHUB_USERNAME"
git config --global user.email "YOUR_EMAIL"

# 添加远程仓库（替换YOUR_GITHUB_USERNAME）
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/agent-os.git

# 验证配置
git remote -v
git config --global user.name
git config --global user.email
```

## 第3步：推送代码到GitHub

```bash
# 推送代码（可能需要输入GitHub用户名和密码/令牌）
git push -u origin master
```

**注意**：如果提示认证失败，您可能需要：
1. 使用GitHub个人访问令牌（PAT）作为密码
2. 或在GitHub设置中启用双重认证后使用令牌

## 第4步：验证上传成功

1. 访问您的仓库：`https://github.com/YOUR_GITHUB_USERNAME/agent-os`
2. 检查所有文件是否已上传
3. GitHub Actions会自动运行CI/CD测试

## 备选方案：使用GitHub CLI

如果您安装了GitHub CLI，可以更简单：

```bash
# 登录GitHub CLI
gh auth login

# 创建仓库
gh repo create agent-os --public --source=. --remote=origin --push
```

## 故障排除

### 问题1：认证失败
```bash
# 使用令牌替代密码
# 1. 生成令牌：https://github.com/settings/tokens
# 2. 使用令牌作为密码
git push -u origin master
# 用户名：您的GitHub用户名
# 密码：您的个人访问令牌
```

### 问题2：远程仓库已存在
```bash
# 移除现有远程仓库
git remote remove origin

# 重新添加
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/agent-os.git

# 强制推送
git push -u origin master --force
```

### 问题3：文件太大
```bash
# 如果某些文件太大，可以忽略
echo "*.log" >> .gitignore
echo "*.db" >> .gitignore
echo "__pycache__/" >> .gitignore

git add .
git commit -m "chore: 更新.gitignore"
git push origin master
```

## 成功后的操作

1. **启用GitHub Pages**（可选）：
   - Settings → Pages → Source: `master` branch → `/docs` folder
   - 访问：`https://YOUR_GITHUB_USERNAME.github.io/agent-os`

2. **设置徽章**：
   - README.md中已有徽章代码，会自动显示

3. **邀请协作者**：
   - Settings → Collaborators → Add people

4. **创建第一个Release**：
   - Code → Releases → Create a new release
   - Tag: `v0.1.0`
   - Title: `Agent OS v0.1.0 - 初始版本`

## 快速测试项目

上传后，您可以：

```bash
# 克隆您的仓库
git clone https://github.com/YOUR_GITHUB_USERNAME/agent-os.git
cd agent-os

# 运行启动脚本
./scripts/start.sh

# 或使用Docker
docker-compose up -d
```

## 获取帮助

如果遇到问题：
1. 查看GitHub官方文档：https://docs.github.com
2. 检查Git配置：`git config --list`
3. 查看Git错误信息：`git push --verbose`

## 恭喜！

完成以上步骤后，您的Agent OS项目将正式开源！🎉

您的仓库将包含：
- ✅ 完整的六大层次架构代码
- ✅ 可立即运行的API服务
- ✅ Docker容器化部署
- ✅ GitHub Actions CI/CD
- ✅ 详细的文档和示例
- ✅ MIT开源许可证

现在全世界都可以看到和使用您的Agent OS项目了！🚀