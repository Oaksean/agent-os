// Agent OS Dashboard - 主应用逻辑

// 应用状态
const appState = {
    currentSection: 'overview',
    agents: [],
    tasks: [],
    users: [],
    logs: [],
    stats: {},
    refreshInterval: null,
    autoRefresh: true
};

/**
 * 应用初始化
 */
async function initApp() {
    console.log('Initializing Agent OS Dashboard...');
    
    // 初始化图表
    charts.initCharts();
    
    // 初始化WebSocket
    initWebSocketConnection();
    
    // 加载初始数据
    await loadInitialData();
    
    // 设置事件监听
    setupEventListeners();
    
    // 启动自动刷新
    startAutoRefresh();
    
    // 更新时间
    updateTime();
    setInterval(updateTime, 1000);
    
    console.log('Dashboard initialized successfully');
}

/**
 * 初始化WebSocket连接
 */
function initWebSocketConnection() {
    const wsUrl = 'ws://localhost:8000/ws';
    
    try {
        ws.init(wsUrl);
    } catch (error) {
        console.warn('WebSocket connection failed, using polling only');
    }
}

/**
 * 加载初始数据
 */
async function loadInitialData() {
    try {
        // 并行加载所有数据
        const [stats, agents, tasks, users] = await Promise.all([
            api.dashboard.getStats().catch(() => null),
            api.agent.list().catch(() => ({ agents: [] })),
            api.task.list().catch(() => ({ tasks: [] })),
            api.user.list().catch(() => ({ users: [] }))
        ]);
        
        // 更新状态
        if (stats) {
            appState.stats = stats;
            updateDashboardStats(stats);
        }
        
        if (agents) {
            appState.agents = agents.agents || agents || [];
            renderAgentsList();
        }
        
        if (tasks) {
            appState.tasks = tasks.tasks || tasks || [];
            renderTasksTable();
        }
        
        if (users) {
            appState.users = users.users || users || [];
            renderUsersTable();
        }
        
    } catch (error) {
        console.error('Failed to load initial data:', error);
        utils.showNotification('加载数据失败', 'error');
    }
}

/**
 * 设置事件监听
 */
function setupEventListeners() {
    // 导航切换
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const section = link.getAttribute('href').substring(1);
            switchSection(section);
        });
    });
    
    // 键盘快捷键
    document.addEventListener('keydown', handleKeyboard);
    
    // 窗口大小变化
    window.addEventListener('resize', utils.debounce(() => {
        charts.initCharts();
    }, 500));
}

/**
 * 切换部分
 */
function switchSection(sectionName) {
    // 更新导航
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    const activeLink = document.querySelector(`.nav-link[href="#${sectionName}"]`);
    if (activeLink) {
        activeLink.classList.add('active');
    }
    
    // 更新内容
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    const activeSection = document.getElementById(sectionName);
    if (activeSection) {
        activeSection.classList.add('active');
    }
    
    // 更新状态
    appState.currentSection = sectionName;
    
    // 加载对应数据
    switch (sectionName) {
        case 'overview':
            loadDashboardData();
            break;
        case 'agents':
            loadAgentsData();
            break;
        case 'tasks':
            loadTasksData();
            break;
        case 'logs':
            loadLogsData();
            break;
        case 'users':
            loadUsersData();
            break;
    }
}

/**
 * 更新Dashboard统计数据
 */
function updateDashboardStats(stats) {
    // Agent统计
    const activeAgents = stats.agents?.active || 0;
    const totalAgents = stats.agents?.total || 0;
    document.getElementById('active-agents').textContent = activeAgents;
    document.getElementById('total-agents').textContent = totalAgents;
    
    // 任务统计
    const runningTasks = stats.tasks?.running || 0;
    const pendingTasks = stats.tasks?.pending || 0;
    document.getElementById('running-tasks').textContent = runningTasks;
    document.getElementById('pending-tasks').textContent = pendingTasks;
    
    // 用户统计
    const activeUsers = stats.users?.active || 0;
    const totalUsers = stats.users?.total || 0;
    document.getElementById('active-users').textContent = activeUsers;
    document.getElementById('total-users').textContent = totalUsers;
    
    // 流量统计
    const requestsPerMinute = stats.traffic?.current_rps ? 
        Math.round(stats.traffic.current_rps * 60) : 0;
    const successRate = stats.traffic?.requests_total > 0 ?
        ((stats.traffic.requests_success / stats.traffic.requests_total) * 100).toFixed(1) : 100;
    
    document.getElementById('requests-per-minute').textContent = requestsPerMinute;
    document.getElementById('success-rate').textContent = `${successRate}%`;
    
    // 更新图表
    if (stats.traffic) {
        charts.updateTrafficChart({
            timestamps: generateTimestamps(30),
            requests: generateRandomData(30, requestsPerMinute)
        });
    }
    
    if (stats.tasks) {
        charts.updateTasksChart({
            running: runningTasks,
            pending: pendingTasks,
            completed: stats.tasks.completed || 0,
            failed: stats.tasks.failed || 0
        });
    }
    
    if (stats.resources) {
        charts.updateResourcesChart(stats.resources);
    }
}

/**
 * 渲染Agent列表
 */
function renderAgentsList() {
    const container = document.getElementById('agents-list');
    
    if (!container) return;
    
    if (appState.agents.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🤖</div>
                <div class="empty-state-text">暂无Agent</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = appState.agents.map(agent => `
        <div class="agent-card" onclick="showAgentDetails('${agent.agent_id || agent.id}')">
            <div class="agent-header">
                <span class="agent-name">${agent.name || 'Unnamed Agent'}</span>
                <span class="badge ${getAgentStatusBadge(agent.status)}">${agent.status || 'inactive'}</span>
            </div>
            <div class="agent-info">
                <p><strong>ID:</strong> ${agent.agent_id || agent.id}</p>
                <p><strong>类型:</strong> ${agent.type || 'assistant'}</p>
                <p><strong>创建时间:</strong> ${utils.formatTimestamp(agent.created_at)}</p>
            </div>
        </div>
    `).join('');
}

/**
 * 渲染任务表格
 */
function renderTasksTable() {
    const tbody = document.getElementById('tasks-body');
    
    if (!tbody) return;
    
    if (appState.tasks.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">暂无任务</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = appState.tasks.map(task => `
        <tr>
            <td><code>${task.task_id || task.id}</code></td>
            <td>${task.name}</td>
            <td><span class="badge" style="background-color: ${utils.getPriorityColor(task.priority)}">${task.priority}</span></td>
            <td><span class="badge ${getTaskStatusBadge(task.status)}">${task.status}</span></td>
            <td>${utils.formatTimestamp(task.created_at)}</td>
            <td>${task.started_at ? utils.formatTimestamp(task.started_at) : '-'}</td>
            <td>
                <button class="btn-secondary" onclick="showTaskDetails('${task.task_id || task.id}')">查看</button>
                ${task.status === 'running' ? `<button class="btn-secondary" onclick="cancelTask('${task.task_id || task.id}')">取消</button>` : ''}
            </td>
        </tr>
    `).join('');
}

/**
 * 渲染用户表格
 */
function renderUsersTable() {
    const tbody = document.getElementById('users-body');
    
    if (!tbody) return;
    
    if (appState.users.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">暂无用户</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = appState.users.map(user => `
        <tr>
            <td><code>${user.user_id}</code></td>
            <td>${user.username}</td>
            <td>${user.email || '-'}</td>
            <td><span class="badge info">${user.role}</span></td>
            <td>${utils.formatTimestamp(user.created_at)}</td>
            <td>
                <div class="activity-bar" style="width: ${Math.random() * 100}%"></div>
            </td>
            <td>
                <button class="btn-secondary" onclick="showUserDetails('${user.user_id}')">查看</button>
                <button class="btn-secondary" onclick="editUser('${user.user_id}')">编辑</button>
            </td>
        </tr>
    `).join('');
}

/**
 * 渲染日志
 */
function renderLogs(logs) {
    const container = document.getElementById('logs-container');
    
    if (!container) return;
    
    if (logs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📜</div>
                <div class="empty-state-text">暂无日志</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = logs.map(log => `
        <div class="log-entry ${log.level.toLowerCase()}">
            <div class="log-header">
                <span class="log-level" style="background-color: ${utils.getLogLevelColor(log.level)}">${log.level}</span>
                <span class="log-timestamp">${utils.formatTimestamp(log.timestamp)}</span>
            </div>
            <div class="log-message">${log.message}</div>
            ${log.extra ? `<div class="log-details"><pre>${JSON.stringify(log.extra, null, 2)}</pre></div>` : ''}
        </div>
    `).join('');
}

/**
 * 添加活动项
 */
function addActivity(activity) {
    const feed = document.getElementById('activity-feed');
    
    if (!feed) return;
    
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `
        <div class="activity-time">${utils.formatTimestamp(activity.timestamp)}</div>
        <div class="activity-message">${activity.message}</div>
        ${activity.details ? `<div class="activity-details">${activity.details}</div>` : ''}
    `;
    
    // 插入到最前面
    feed.insertBefore(item, feed.firstChild);
    
    // 保持最多50条记录
    while (feed.children.length > 50) {
        feed.removeChild(feed.lastChild);
    }
}

/**
 * 启动自动刷新
 */
function startAutoRefresh() {
    if (appState.refreshInterval) {
        clearInterval(appState.refreshInterval);
    }
    
    appState.refreshInterval = setInterval(async () => {
        if (appState.autoRefresh) {
            await refreshData();
        }
    }, 10000); // 每10秒刷新一次
}

/**
 * 刷新数据
 */
async function refreshData() {
    try {
        const stats = await api.dashboard.getStats();
        
        if (stats) {
            appState.stats = stats;
            updateDashboardStats(stats);
        }
        
        // 根据当前页面刷新对应数据
        switch (appState.currentSection) {
            case 'agents':
                const agents = await api.agent.list();
                if (agents) {
                    appState.agents = agents.agents || agents || [];
                    renderAgentsList();
                }
                break;
                
            case 'tasks':
                const tasks = await api.task.list();
                if (tasks) {
                    appState.tasks = tasks.tasks || tasks || [];
                    renderTasksTable();
                }
                break;
                
            case 'users':
                const users = await api.user.list();
                if (users) {
                    appState.users = users.users || users || [];
                    renderUsersTable();
                }
                break;
        }
        
    } catch (error) {
        console.error('Refresh failed:', error);
    }
}

/**
 * 数据加载函数
 */
async function loadDashboardData() {
    const stats = await api.dashboard.getStats().catch(() => null);
    if (stats) {
        updateDashboardStats(stats);
    }
}

async function loadAgentsData() {
    const result = await api.agent.list().catch(() => null);
    if (result) {
        appState.agents = result.agents || result || [];
        renderAgentsList();
    }
}

async function loadTasksData() {
    const result = await api.task.list().catch(() => null);
    if (result) {
        appState.tasks = result.tasks || result || [];
        renderTasksTable();
    }
}

async function loadUsersData() {
    const result = await api.user.list().catch(() => null);
    if (result) {
        appState.users = result.users || result || [];
        renderUsersTable();
    }
}

async function loadLogsData() {
    const result = await api.log.query({ limit: 100 }).catch(() => null);
    if (result) {
        appState.logs = result.logs || [];
        renderLogs(appState.logs);
    }
}

/**
 * 更新Dashboard统计数据
 */
function updateDashboardStats(stats) {
    if (!stats) return;
    
    // 更新统计卡片
    const elements = {
        'total-requests': stats.traffic?.total_requests || 0,
        'active-users': stats.traffic?.active_users || 0,
        'running-tasks': stats.tasks?.running_tasks || 0,
        'total-agents': stats.agents?.total_agents || 0
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
    
    // 更新图表
    if (stats.traffic) {
        const requestsPerMinute = stats.traffic.requests_per_minute || 0;
        const runningTasks = stats.tasks?.running_tasks || 0;
        const pendingTasks = stats.tasks?.pending_tasks || 0;
        
        charts.updateTrafficChart({
            timestamps: generateTimestamps(30),
            requests: generateRandomData(30, requestsPerMinute)
        });
    }
    
    if (stats.tasks) {
        charts.updateTasksChart({
            running: stats.tasks.running_tasks || 0,
            pending: stats.tasks.pending_tasks || 0,
            completed: stats.tasks.completed_tasks || 0,
            failed: stats.tasks.failed_tasks || 0
        });
        
        // 更新Worker状态图表（新增）
        if (stats.tasks.worker_status) {
            charts.updateWorkerChart(stats.tasks.worker_status);
        }
    }
    
    if (stats.resources) {
        charts.updateResourcesChart(stats.resources);
    }
    
    // 更新缓存统计图表（新增）
    if (stats.cache) {
        charts.updateCacheChart(stats.cache);
        
        // 更新缓存统计卡片
        const cacheHitRate = document.getElementById('cache-hit-rate');
        if (cacheHitRate && stats.cache.hit_rate) {
            cacheHitRate.textContent = stats.cache.hit_rate;
        }
        
        const cacheKeys = document.getElementById('cache-keys');
        if (cacheKeys && stats.cache.total_keys !== undefined) {
            cacheKeys.textContent = stats.cache.total_keys;
        }
    }
}

/**
 * 工具函数
 */
function getAgentStatusBadge(status) {
    const badges = {
        active: 'success',
        inactive: 'warning',
        error: 'danger'
    };
    return badges[status] || 'info';
}

function getTaskStatusBadge(status) {
    const badges = {
        running: 'info',
        pending: 'warning',
        completed: 'success',
        failed: 'danger',
        cancelled: 'info'
    };
    return badges[status] || 'info';
}

function generateTimestamps(count) {
    const timestamps = [];
    const now = new Date();
    
    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now - i * 60000);
        timestamps.push(time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
    }
    
    return timestamps;
}

function generateRandomData(count, base) {
    const data = [];
    for (let i = 0; i < count; i++) {
        data.push(Math.max(0, base + Math.floor((Math.random() - 0.5) * base * 0.5)));
    }
    return data;
}

function updateTime() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        timeElement.textContent = new Date().toLocaleString('zh-CN');
    }
}

/**
 * 键盘快捷键处理
 */
function handleKeyboard(e) {
    // Ctrl/Cmd + 1-5: 切换标签页
    if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '5') {
        e.preventDefault();
        const sections = ['overview', 'agents', 'tasks', 'logs', 'users'];
        const index = parseInt(e.key) - 1;
        if (sections[index]) {
            switchSection(sections[index]);
        }
    }
    
    // Escape: 关闭侧边栏和模态框
    if (e.key === 'Escape') {
        closeSidebar();
        closeModal();
    }
}

/**
 * 侧边栏操作
 */
function openSidebar(title, content) {
    const sidebar = document.getElementById('sidebar');
    const titleEl = document.getElementById('sidebar-title');
    const contentEl = document.getElementById('sidebar-content');
    
    if (titleEl) titleEl.textContent = title;
    if (contentEl) contentEl.innerHTML = content;
    
    sidebar.classList.add('open');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('open');
}

/**
 * 模态框操作
 */
function openModal(title, content) {
    const modal = document.getElementById('modal');
    const titleEl = document.getElementById('modal-title');
    const contentEl = document.getElementById('modal-body');
    
    if (titleEl) titleEl.textContent = title;
    if (contentEl) contentEl.innerHTML = content;
    
    modal.classList.add('open');
}

function closeModal() {
    const modal = document.getElementById('modal');
    modal.classList.remove('open');
}

/**
 * Agent操作
 */
async function createAgent() {
    openModal('创建Agent', `
        <form onsubmit="submitCreateAgent(event)">
            <div class="form-group">
                <label>名称</label>
                <input type="text" name="name" required placeholder="Agent名称">
            </div>
            <div class="form-group">
                <label>类型</label>
                <select name="type">
                    <option value="assistant">助手</option>
                    <option value="executor">执行器</option>
                    <option value="planner">规划器</option>
                </select>
            </div>
            <div class="form-group">
                <label>描述</label>
                <textarea name="description" rows="3" placeholder="Agent描述"></textarea>
            </div>
            <div class="form-actions">
                <button type="button" class="btn-secondary" onclick="closeModal()">取消</button>
                <button type="submit" class="btn-primary">创建</button>
            </div>
        </form>
    `);
}

async function submitCreateAgent(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
        await api.agent.create(data);
        utils.showNotification('Agent创建成功', 'success');
        closeModal();
        loadAgentsData();
    } catch (error) {
        utils.showNotification('创建失败: ' + error.message, 'error');
    }
}

async function showAgentDetails(agentId) {
    try {
        const agent = await api.agent.get(agentId);
        
        openSidebar('Agent详情', `
            <div class="detail-section">
                <h4>基本信息</h4>
                <p><strong>ID:</strong> ${agent.agent_id || agent.id}</p>
                <p><strong>名称:</strong> ${agent.name}</p>
                <p><strong>类型:</strong> ${agent.type}</p>
                <p><strong>状态:</strong> <span class="badge ${getAgentStatusBadge(agent.status)}">${agent.status}</span></p>
            </div>
            <div class="detail-section">
                <h4>统计信息</h4>
                <p><strong>创建时间:</strong> ${utils.formatTimestamp(agent.created_at)}</p>
                <p><strong>最后活跃:</strong> ${agent.last_active ? utils.formatTimestamp(agent.last_active) : '-'}</p>
                <p><strong>任务数:</strong> ${agent.task_count || 0}</p>
            </div>
        `);
    } catch (error) {
        utils.showNotification('加载失败', 'error');
    }
}

/**
 * 任务操作
 */
async function showTaskDetails(taskId) {
    try {
        const task = await api.task.get(taskId);
        
        openSidebar('任务详情', `
            <div class="detail-section">
                <h4>基本信息</h4>
                <p><strong>ID:</strong> ${task.task_id || task.id}</p>
                <p><strong>名称:</strong> ${task.name}</p>
                <p><strong>优先级:</strong> <span class="badge" style="background-color: ${utils.getPriorityColor(task.priority)}">${task.priority}</span></p>
                <p><strong>状态:</strong> <span class="badge ${getTaskStatusBadge(task.status)}">${task.status}</span></p>
            </div>
            <div class="detail-section">
                <h4>执行信息</h4>
                <p><strong>创建时间:</strong> ${utils.formatTimestamp(task.created_at)}</p>
                <p><strong>开始时间:</strong> ${task.started_at ? utils.formatTimestamp(task.started_at) : '-'}</p>
                <p><strong>完成时间:</strong> ${task.completed_at ? utils.formatTimestamp(task.completed_at) : '-'}</p>
                <p><strong>执行时长:</strong> ${task.duration ? utils.formatDuration(task.duration) : '-'}</p>
            </div>
            ${task.result ? `
                <div class="detail-section">
                    <h4>执行结果</h4>
                    <pre>${JSON.stringify(task.result, null, 2)}</pre>
                </div>
            ` : ''}
        `);
    } catch (error) {
        utils.showNotification('加载失败', 'error');
    }
}

async function cancelTask(taskId) {
    if (!confirm('确定要取消这个任务吗？')) return;
    
    try {
        await api.task.cancel(taskId);
        utils.showNotification('任务已取消', 'success');
        loadTasksData();
    } catch (error) {
        utils.showNotification('取消失败: ' + error.message, 'error');
    }
}

/**
 * 用户操作
 */
async function createUser() {
    openModal('创建用户', `
        <form onsubmit="submitCreateUser(event)">
            <div class="form-group">
                <label>用户名</label>
                <input type="text" name="username" required placeholder="用户名">
            </div>
            <div class="form-group">
                <label>邮箱</label>
                <input type="email" name="email" placeholder="邮箱地址">
            </div>
            <div class="form-group">
                <label>角色</label>
                <select name="role">
                    <option value="user">普通用户</option>
                    <option value="power_user">高级用户</option>
                    <option value="admin">管理员</option>
                </select>
            </div>
            <div class="form-actions">
                <button type="button" class="btn-secondary" onclick="closeModal()">取消</button>
                <button type="submit" class="btn-primary">创建</button>
            </div>
        </form>
    `);
}

async function submitCreateUser(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    try {
        await api.user.create(data);
        utils.showNotification('用户创建成功', 'success');
        closeModal();
        loadUsersData();
    } catch (error) {
        utils.showNotification('创建失败: ' + error.message, 'error');
    }
}

async function showUserDetails(userId) {
    try {
        const user = await api.user.get(userId);
        
        openSidebar('用户详情', `
            <div class="detail-section">
                <h4>基本信息</h4>
                <p><strong>ID:</strong> ${user.user_id}</p>
                <p><strong>用户名:</strong> ${user.username}</p>
                <p><strong>邮箱:</strong> ${user.email || '-'}</p>
                <p><strong>角色:</strong> <span class="badge info">${user.role}</span></p>
                <p><strong>创建时间:</strong> ${utils.formatTimestamp(user.created_at)}</p>
            </div>
        `);
    } catch (error) {
        utils.showNotification('加载失败', 'error');
    }
}

/**
 * 日志操作
 */
async function refreshLogs() {
    await loadLogsData();
    utils.showNotification('日志已刷新', 'info');
}

async function filterLogs() {
    const level = document.getElementById('log-level-filter').value;
    const category = document.getElementById('log-category-filter').value;
    
    const params = { limit: 100 };
    if (level !== 'all') params.level = level;
    if (category !== 'all') params.category = category;
    
    const result = await api.log.query(params).catch(() => null);
    if (result) {
        appState.logs = result.logs || [];
        renderLogs(appState.logs);
    }
}

/**
 * 搜索功能
 */
function searchAgents() {
    const query = document.getElementById('agent-search').value.toLowerCase();
    const filtered = appState.agents.filter(agent => 
        agent.name?.toLowerCase().includes(query) ||
        agent.agent_id?.toLowerCase().includes(query)
    );
    renderAgentsList(filtered);
}

function searchUsers() {
    const query = document.getElementById('user-search').value.toLowerCase();
    const filtered = appState.users.filter(user => 
        user.username?.toLowerCase().includes(query) ||
        user.email?.toLowerCase().includes(query) ||
        user.user_id?.toLowerCase().includes(query)
    );
    renderUsersTable(filtered);
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);

// 导出全局函数
window.app = {
    updateStats,
    addActivity,
    createAgent,
    showAgentDetails,
    showTaskDetails,
    cancelTask,
    createUser,
    showUserDetails,
    editUser: showUserDetails,
    refreshLogs,
    filterLogs,
    searchAgents,
    searchUsers
};
