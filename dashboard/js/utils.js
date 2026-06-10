// Agent OS Dashboard - 工具函数

/**
 * 格式化时间戳
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    // 小于1分钟
    if (diff < 60000) {
        return '刚刚';
    }
    
    // 小于1小时
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return `${minutes}分钟前`;
    }
    
    // 小于24小时
    if (diff < 86400000) {
        const hours = Math.floor(diff / 3600000);
        return `${hours}小时前`;
    }
    
    // 显示具体日期
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * 格式化持续时间
 */
function formatDuration(seconds) {
    if (seconds < 60) {
        return `${seconds}秒`;
    }
    
    if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}分${secs}秒`;
    }
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}小时${minutes}分`;
}

/**
 * 格式化数字
 */
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    
    return num.toString();
}

/**
 * 格式化百分比
 */
function formatPercentage(value, decimals = 1) {
    return value.toFixed(decimals) + '%';
}

/**
 * 格式化字节
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i];
}

/**
 * 防抖函数
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * 节流函数
 */
function throttle(func, limit) {
    let inThrottle;
    return function executedFunction(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * 深拷贝
 */
function deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
}

/**
 * 生成唯一ID
 */
function generateId() {
    return 'id_' + Math.random().toString(36).substr(2, 9);
}

/**
 * 显示通知
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span class="notification-icon">${getNotificationIcon(type)}</span>
        <span class="notification-message">${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    // 3秒后自动消失
    setTimeout(() => {
        notification.classList.add('fade-out');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

/**
 * 获取通知图标
 */
function getNotificationIcon(type) {
    const icons = {
        success: '✓',
        warning: '⚠',
        error: '✗',
        info: 'ℹ'
    };
    return icons[type] || icons.info;
}

/**
 * 复制到剪贴板
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showNotification('已复制到剪贴板', 'success');
    } catch (err) {
        showNotification('复制失败', 'error');
    }
}

/**
 * 解析URL参数
 */
function parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    
    for (const [key, value] of params) {
        result[key] = value;
    }
    
    return result;
}

/**
 * 获取状态颜色
 */
function getStatusColor(status) {
    const colors = {
        active: '#48bb78',
        inactive: '#a0aec0',
        running: '#4299e1',
        pending: '#ed8936',
        completed: '#48bb78',
        failed: '#f56565',
        cancelled: '#a0aec0'
    };
    
    return colors[status.toLowerCase()] || '#a0aec0';
}

/**
 * 获取优先级颜色
 */
function getPriorityColor(priority) {
    const colors = {
        critical: '#f56565',
        high: '#ed8936',
        normal: '#4299e1',
        low: '#a0aec0'
    };
    
    return colors[priority.toLowerCase()] || '#a0aec0';
}

/**
 * 获取日志级别颜色
 */
function getLogLevelColor(level) {
    const colors = {
        DEBUG: '#a0aec0',
        INFO: '#4299e1',
        WARNING: '#ed8936',
        ERROR: '#f56565',
        CRITICAL: '#e53e3e'
    };
    
    return colors[level] || '#a0aec0';
}

/**
 * 创建DOM元素
 */
function createElement(tag, className, attributes = {}) {
    const element = document.createElement(tag);
    
    if (className) {
        element.className = className;
    }
    
    for (const [key, value] of Object.entries(attributes)) {
        if (key === 'text') {
            element.textContent = value;
        } else if (key === 'html') {
            element.innerHTML = value;
        } else {
            element.setAttribute(key, value);
        }
    }
    
    return element;
}

/**
 * 延迟执行
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 重试函数
 */
async function retry(fn, maxRetries = 3, delay = 1000) {
    for (let i = 0; i < maxRetries; i++) {
        try {
            return await fn();
        } catch (error) {
            if (i === maxRetries - 1) {
                throw error;
            }
            await sleep(delay);
        }
    }
}

/**
 * 本地存储封装
 */
const storage = {
    get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch {
            return defaultValue;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch {
            return false;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch {
            return false;
        }
    }
};

// 导出工具函数
window.utils = {
    formatTimestamp,
    formatDuration,
    formatNumber,
    formatPercentage,
    formatBytes,
    debounce,
    throttle,
    deepClone,
    generateId,
    showNotification,
    copyToClipboard,
    parseUrlParams,
    getStatusColor,
    getPriorityColor,
    getLogLevelColor,
    createElement,
    sleep,
    retry,
    storage
};
