# Agent OS Dashboard 使用指南

## 概述

Agent OS Dashboard 是一个实时监控和管理界面，用于监控和管理 Agent OS 系统的所有组件。

## 功能特性

### 1. 概览页面

- **统计卡片**：显示活跃Agent数量、运行任务数、活跃用户数、请求数等关键指标
- **图表监控**：
  - 流量趋势图（实时请求数）
  - 任务执行统计（饼图）
  - 资源使用情况（柱状图）
  - 响应时间分布（折线图）
- **实时活动流**：显示系统最新动态

### 2. Agent 管理

- Agent 列表展示
- 创建新 Agent
- 查看Agent详情
- Agent状态监控

### 3. 任务管理

- 任务列表展示（支持筛选）
- 任务状态跟踪
- 任务详情查看
- 取消运行中任务

### 4. 日志查看

- 系统日志查询
- 多级别日志过滤（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- 分类日志过滤
- 日志实时更新

### 5. 用户管理

- 用户列表展示
- 创建新用户
- 查看用户详情
- 用户权限管理

## 技术栈

- **前端框架**：原生JavaScript (ES6+)
- **图表库**：Chart.js 4.4.0
- **样式**：CSS3 + CSS Variables
- **实时通信**：WebSocket
- **API调用**：Fetch API

## 快速开始

### 1. 启动后端API服务

```bash
cd agent-os
python src/api/main_complete.py
```

API服务将在 `http://localhost:8000` 启动。

### 2. 打开Dashboard

在浏览器中打开 `dashboard/index.html` 文件，或使用本地服务器：

```bash
cd dashboard
python -m http.server 8080
```

然后访问 `http://localhost:8080`

### 3. 配置API地址

如果API服务不在localhost，需要修改 `js/api.js` 中的 `API_BASE_URL`：

```javascript
const API_BASE_URL = 'http://your-api-server:8000/api/v1';
```

## API端点

Dashboard使用的主要API端点：

### Dashboard API
- `GET /api/v1/dashboard/stats` - 获取统计数据
- `GET /api/v1/dashboard/activity` - 获取活动列表

### Agent API
- `GET /api/v1/agents` - 获取Agent列表
- `POST /api/v1/agents` - 创建Agent
- `GET /api/v1/agents/{id}` - 获取Agent详情
- `PUT /api/v1/agents/{id}` - 更新Agent
- `DELETE /api/v1/agents/{id}` - 删除Agent

### Task API
- `GET /api/v1/tasks` - 获取任务列表
- `POST /api/v1/tasks` - 提交任务
- `GET /api/v1/tasks/{id}` - 获取任务详情
- `POST /api/v1/tasks/{id}/cancel` - 取消任务
- `GET /api/v1/tasks/stats` - 获取任务统计

### User API
- `GET /api/v1/users` - 获取用户列表
- `POST /api/v1/users` - 创建用户
- `GET /api/v1/users/{id}` - 获取用户详情
- `PUT /api/v1/users/{id}` - 更新用户
- `DELETE /api/v1/users/{id}` - 删除用户

### Log API
- `GET /api/v1/logs` - 查询日志
- `GET /api/v1/logs/audit` - 查询审计日志

### Traffic API
- `GET /api/v1/traffic/metrics` - 获取流量指标
- `GET /api/v1/traffic/rate-limits` - 获取速率限制
- `POST /api/v1/traffic/rate-limits` - 设置速率限制

## WebSocket实时推送

Dashboard支持WebSocket实时推送，提供以下主题订阅：

- `stats` - 统计数据更新
- `activity` - 活动更新
- `alert` - 告警通知

## 键盘快捷键

- `Ctrl/Cmd + 1` - 切换到概览页面
- `Ctrl/Cmd + 2` - 切换到Agent页面
- `Ctrl/Cmd + 3` - 切换到任务页面
- `Ctrl/Cmd + 4` - 切换到日志页面
- `Ctrl/Cmd + 5` - 切换到用户页面
- `Escape` - 关闭侧边栏和模态框

## 自定义主题

Dashboard支持CSS变量自定义主题，修改 `css/style.css` 中的变量：

```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #48bb78;
    --warning-color: #ed8936;
    --danger-color: #f56565;
    --info-color: #4299e1;
    
    --bg-color: #1a202c;
    --card-bg: #2d3748;
    --border-color: #4a5568;
    --text-primary: #e2e8f0;
    --text-secondary: #a0aec0;
}
```

## 性能优化

1. **自动刷新**：Dashboard每10秒自动刷新数据
2. **图表优化**：图表更新使用`update('none')`避免动画
3. **数据限制**：活动流最多保持50条记录，图表最多30个数据点
4. **懒加载**：只有切换到对应页面才加载该页面数据

## 浏览器兼容性

- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 故障排除

### 1. 无法连接API

- 检查API服务是否启动
- 检查API地址配置是否正确
- 检查浏览器控制台是否有CORS错误

### 2. WebSocket连接失败

- 确认API服务支持WebSocket
- 检查WebSocket URL配置
- Dashboard会自动降级为轮询模式

### 3. 图表不显示

- 检查Chart.js是否正确加载
- 检查浏览器控制台错误信息
- 尝试刷新页面

## 扩展开发

### 添加新的图表

```javascript
// 在 js/charts.js 中添加初始化函数
function initNewChart() {
    const ctx = document.getElementById('new-chart').getContext('2d');
    // 创建图表实例
}

// 在 initCharts() 中调用
function initCharts() {
    // ...其他图表初始化
    initNewChart();
}
```

### 添加新的API调用

```javascript
// 在 js/api.js 中添加新的API方法
const customAPI = {
    async customMethod(params) {
        return await request('/custom-endpoint', {
            method: 'POST',
            body: params
        });
    }
};

// 导出
window.api.custom = customAPI;
```

### 添加新的页面

1. 在 `index.html` 中添加新的section
2. 在导航栏添加对应链接
3. 在 `js/app.js` 中添加加载函数
4. 更新 `switchSection()` 函数

## 安全注意事项

1. **认证**：生产环境需要添加用户认证
2. **HTTPS**：生产环境建议使用HTTPS
3. **CORS**：正确配置CORS策略
4. **敏感信息**：不要在客户端存储敏感信息

## 许可证

MIT License

---

**版本**: 0.3.0  
**更新日期**: 2026-06-09
