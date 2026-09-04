# GitHub个人访问令牌使用指南

## 步骤1：生成令牌

1. 登录GitHub，访问：https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 填写信息：
   - **Note**: `agent-os-push-token`
   - **Expiration**: 选择90天
   - **Select scopes**: 勾选 `repo` 和 `workflow`
4. 点击 "Generate token"
5. **立即复制令牌**（只显示一次！）

## 步骤2：使用令牌推送代码

### 方法A：使用脚本（推荐）

```bash
# 进入项目目录
cd agent-os

# 运行推送脚本
./scripts/push_with_token.sh
```

当提示时，粘贴您的令牌。

### 方法B：手动配置

```bash
cd agent-os

# 设置远程仓库使用令牌
git remote set-url origin https://YOUR_TOKEN@github.com/Oaksean/agent-os.git

# 推送代码
git push -u origin master
```

将 `YOUR_TOKEN` 替换为您的实际令牌。

### 方法C：使用Git凭据管理器

```bash
cd agent-os

# 首次推送时输入凭据
git push -u origin master

# 用户名：Oaksean
# 密码：您的GitHub令牌（不是登录密码）
```

## 步骤3：验证推送成功

1. 访问您的仓库：https://github.com/Oaksean/agent-os
2. 检查文件是否已上传
3. 检查提交历史

## 安全注意事项

1. **不要将令牌提交到代码中**
2. **令牌只用于推送，不要分享给他人**
3. **90天后需要重新生成**
4. **可以在GitHub设置中随时撤销令牌**

## 故障排除

### 问题：认证失败
```bash
# 清除现有凭据
git credential reject
protocol=https
host=github.com

# 重新尝试
git push -u origin master
```

### 问题：权限不足
- 确保令牌有 `repo` 权限
- 确保仓库存在且有写入权限

### 问题：网络连接问题
```bash
# 检查网络连接
ping github.com

# 使用代理（如果需要）
git config --global http.proxy http://proxy.example.com:8080
```

## 成功后的操作

1. **启用GitHub Actions**：自动运行CI/CD
2. **设置仓库描述**：完善项目信息
3. **添加Topics**：如 `ai`, `agent`, `operating-system`, `python`
4. **创建Release**：标记第一个版本 v0.1.0

## 令牌示例格式

您的令牌看起来像这样：`ghp_xx...xxxx`

**重要**：以 `ghp_` 开头的就是您的个人访问令牌。
