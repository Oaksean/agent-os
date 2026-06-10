// Agent OS Dashboard - WebSocket实时通信

class WebSocketManager {
    constructor(url) {
        this.url = url || 'ws://localhost:8000/ws';
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.heartbeatInterval = null;
        this.subscriptions = new Map();
        this.isConnected = false;
        
        this.connect();
    }
    
    /**
     * 连接WebSocket
     */
    connect() {
        try {
            this.ws = new WebSocket(this.url);
            
            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                
                // 更新连接状态
                this.updateConnectionStatus('online');
                
                // 启动心跳
                this.startHeartbeat();
                
                // 重新订阅
                this.resubscribe();
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleMessage(data);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };
            
            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnected = false;
                
                // 更新连接状态
                this.updateConnectionStatus('offline');
                
                // 停止心跳
                this.stopHeartbeat();
                
                // 尝试重连
                this.reconnect();
            };
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.reconnect();
        }
    }
    
    /**
     * 重连
     */
    reconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`Reconnecting... Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectDelay * this.reconnectAttempts);
    }
    
    /**
     * 启动心跳
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected) {
                this.send({ type: 'ping' });
            }
        }, 30000); // 每30秒发送一次心跳
    }
    
    /**
     * 停止心跳
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    /**
     * 发送消息
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(data));
        }
    }
    
    /**
     * 订阅主题
     */
    subscribe(topic, callback) {
        if (!this.subscriptions.has(topic)) {
            this.subscriptions.set(topic, new Set());
        }
        
        this.subscriptions.get(topic).add(callback);
        
        // 发送订阅消息
        this.send({
            type: 'subscribe',
            topic: topic
        });
    }
    
    /**
     * 取消订阅
     */
    unsubscribe(topic, callback) {
        if (this.subscriptions.has(topic)) {
            const callbacks = this.subscriptions.get(topic);
            callbacks.delete(callback);
            
            if (callbacks.size === 0) {
                this.subscriptions.delete(topic);
                
                // 发送取消订阅消息
                this.send({
                    type: 'unsubscribe',
                    topic: topic
                });
            }
        }
    }
    
    /**
     * 重新订阅所有主题
     */
    resubscribe() {
        for (const [topic] of this.subscriptions) {
            this.send({
                type: 'subscribe',
                topic: topic
            });
        }
    }
    
    /**
     * 处理消息
     */
    handleMessage(data) {
        const { type, topic, payload } = data;
        
        // 心跳响应
        if (type === 'pong') {
            return;
        }
        
        // 分发消息给订阅者
        if (topic && this.subscriptions.has(topic)) {
            const callbacks = this.subscriptions.get(topic);
            callbacks.forEach(callback => {
                try {
                    callback(payload);
                } catch (error) {
                    console.error('Callback error:', error);
                }
            });
        }
        
        // 全局消息处理
        switch (type) {
            case 'stats':
                this.handleStatsUpdate(payload);
                break;
            case 'activity':
                this.handleActivityUpdate(payload);
                break;
            case 'alert':
                this.handleAlert(payload);
                break;
        }
    }
    
    /**
     * 处理统计数据更新
     */
    handleStatsUpdate(stats) {
        if (window.app && window.app.updateStats) {
            window.app.updateStats(stats);
        }
    }
    
    /**
     * 处理活动更新
     */
    handleActivityUpdate(activity) {
        if (window.app && window.app.addActivity) {
            window.app.addActivity(activity);
        }
    }
    
    /**
     * 处理告警
     */
    handleAlert(alert) {
        utils.showNotification(alert.message, alert.level || 'warning');
    }
    
    /**
     * 更新连接状态
     */
    updateConnectionStatus(status) {
        const indicator = document.querySelector('.status-indicator');
        const statusText = document.getElementById('connection-status');
        
        if (indicator) {
            indicator.className = `status-indicator ${status}`;
        }
        
        if (statusText) {
            statusText.textContent = status === 'online' ? '已连接' : '未连接';
        }
    }
    
    /**
     * 关闭连接
     */
    close() {
        this.stopHeartbeat();
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
    }
}

// 创建全局WebSocket实例
let wsManager = null;

/**
 * 初始化WebSocket
 */
function initWebSocket(url) {
    if (wsManager) {
        wsManager.close();
    }
    
    wsManager = new WebSocketManager(url);
    
    // 订阅关键主题
    wsManager.subscribe('stats', (data) => {
        console.log('Stats update:', data);
    });
    
    wsManager.subscribe('activity', (data) => {
        console.log('Activity update:', data);
    });
    
    return wsManager;
}

/**
 * 获取WebSocket实例
 */
function getWebSocket() {
    return wsManager;
}

// 导出WebSocket函数
window.ws = {
    init: initWebSocket,
    get: getWebSocket
};
