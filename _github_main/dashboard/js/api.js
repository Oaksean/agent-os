// Agent OS Dashboard - API调用封装

// API基础URL
const API_BASE_URL = 'http://localhost:8000/api/v1';

// API请求配置
const apiConfig = {
    timeout: 30000,
    retries: 3,
    retryDelay: 1000
};

/**
 * 发起HTTP请求
 */
async function request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const config = {
        method: options.method || 'GET',
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        },
        ...options
    };
    
    // 添加认证token
    const token = utils.storage.get('auth_token');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 添加请求体
    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }
    
    try {
        const response = await fetch(url, config);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * Dashboard API
 */
const dashboardAPI = {
    /**
     * 获取统计数据
     */
    async getStats() {
        return await request('/dashboard/stats');
    },
    
    /**
     * 获取活动列表
     */
    async getActivity(limit = 20) {
        return await request(`/dashboard/activity?limit=${limit}`);
    }
};

/**
 * Agent API
 */
const agentAPI = {
    /**
     * 获取Agent列表
     */
    async list(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/agents${query ? '?' + query : ''}`);
    },
    
    /**
     * 获取单个Agent
     */
    async get(agentId) {
        return await request(`/agents/${agentId}`);
    },
    
    /**
     * 创建Agent
     */
    async create(data) {
        return await request('/agents', {
            method: 'POST',
            body: data
        });
    },
    
    /**
     * 更新Agent
     */
    async update(agentId, data) {
        return await request(`/agents/${agentId}`, {
            method: 'PUT',
            body: data
        });
    },
    
    /**
     * 删除Agent
     */
    async delete(agentId) {
        return await request(`/agents/${agentId}`, {
            method: 'DELETE'
        });
    },
    
    /**
     * 执行Agent
     */
    async execute(agentId, input) {
        return await request(`/agents/${agentId}/execute`, {
            method: 'POST',
            body: { input }
        });
    }
};

/**
 * Task API
 */
const taskAPI = {
    /**
     * 获取任务列表
     */
    async list(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/tasks${query ? '?' + query : ''}`);
    },
    
    /**
     * 获取单个任务
     */
    async get(taskId) {
        return await request(`/tasks/${taskId}`);
    },
    
    /**
     * 提交任务
     */
    async submit(data) {
        return await request('/tasks', {
            method: 'POST',
            body: data
        });
    },
    
    /**
     * 取消任务
     */
    async cancel(taskId) {
        return await request(`/tasks/${taskId}/cancel`, {
            method: 'POST'
        });
    },
    
    /**
     * 获取任务统计
     */
    async getStats() {
        return await request('/tasks/stats');
    }
};

/**
 * User API
 */
const userAPI = {
    /**
     * 获取用户列表
     */
    async list(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/users${query ? '?' + query : ''}`);
    },
    
    /**
     * 获取单个用户
     */
    async get(userId) {
        return await request(`/users/${userId}`);
    },
    
    /**
     * 创建用户
     */
    async create(data) {
        return await request('/users', {
            method: 'POST',
            body: data
        });
    },
    
    /**
     * 更新用户
     */
    async update(userId, data) {
        return await request(`/users/${userId}`, {
            method: 'PUT',
            body: data
        });
    },
    
    /**
     * 删除用户
     */
    async delete(userId) {
        return await request(`/users/${userId}`, {
            method: 'DELETE'
        });
    },
    
    /**
     * 获取用户习惯
     */
    async getHabits(userId) {
        return await request(`/users/${userId}/habits`);
    },
    
    /**
     * 获取用户标签
     */
    async getTags(userId) {
        return await request(`/users/${userId}/tags`);
    },
    
    /**
     * 获取用户记忆
     */
    async getMemories(userId, params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/users/${userId}/memories${query ? '?' + query : ''}`);
    }
};

/**
 * Log API
 */
const logAPI = {
    /**
     * 查询日志
     */
    async query(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/logs${query ? '?' + query : ''}`);
    },
    
    /**
     * 查询审计日志
     */
    async queryAudit(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/logs/audit${query ? '?' + query : ''}`);
    }
};

/**
 * Traffic API
 */
const trafficAPI = {
    /**
     * 获取流量指标
     */
    async getMetrics() {
        return await request('/traffic/metrics');
    },
    
    /**
     * 获取速率限制
     */
    async getRateLimits() {
        return await request('/traffic/rate-limits');
    },
    
    /**
     * 设置速率限制
     */
    async setRateLimit(data) {
        return await request('/traffic/rate-limits', {
            method: 'POST',
            body: data
        });
    }
};

/**
 * Permission API
 */
const permissionAPI = {
    /**
     * 分配角色
     */
    async assignRole(userId, role) {
        return await request(`/permissions/assign-role?user_id=${userId}&role=${role}`, {
            method: 'POST'
        });
    },
    
    /**
     * 获取用户权限
     */
    async getUserPermissions(userId) {
        return await request(`/permissions/user/${userId}`);
    }
};

/**
 * Session API
 */
const sessionAPI = {
    /**
     * 获取会话列表
     */
    async list(params = {}) {
        const query = new URLSearchParams(params).toString();
        return await request(`/sessions${query ? '?' + query : ''}`);
    },
    
    /**
     * 获取单个会话
     */
    async get(sessionId) {
        return await request(`/sessions/${sessionId}`);
    },
    
    /**
     * 创建会话
     */
    async create(data) {
        return await request('/sessions', {
            method: 'POST',
            body: data
        });
    },
    
    /**
     * 获取会话消息
     */
    async getMessages(sessionId) {
        return await request(`/sessions/${sessionId}/messages`);
    },
    
    /**
     * 生成会话摘要
     */
    async generateSummary(sessionId) {
        return await request(`/sessions/${sessionId}/summary`, {
            method: 'POST'
        });
    }
};

// 导出API
window.api = {
    request,
    dashboard: dashboardAPI,
    agent: agentAPI,
    task: taskAPI,
    user: userAPI,
    log: logAPI,
    traffic: trafficAPI,
    permission: permissionAPI,
    session: sessionAPI
};
