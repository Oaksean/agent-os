// Agent OS Dashboard - 图表管理

// 图表配置
const chartConfig = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
        legend: {
            display: true,
            labels: {
                color: '#e2e8f0',
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(45, 55, 72, 0.95)',
            titleColor: '#e2e8f0',
            bodyColor: '#a0aec0',
            borderColor: '#4a5568',
            borderWidth: 1,
            padding: 12,
            displayColors: true
        }
    },
    scales: {
        x: {
            ticks: {
                color: '#a0aec0',
                font: {
                    size: 11
                }
            },
            grid: {
                color: 'rgba(74, 85, 104, 0.3)',
                drawBorder: false
            }
        },
        y: {
            ticks: {
                color: '#a0aec0',
                font: {
                    size: 11
                }
            },
            grid: {
                color: 'rgba(74, 85, 104, 0.3)',
                drawBorder: false
            }
        }
    }
};

// 图表实例
let trafficChart = null;
let tasksChart = null;
let resourcesChart = null;
let responseTimeChart = null;
let cacheChart = null; // 新增：缓存统计图表
let workerChart = null; // 新增：Worker状态图表

/**
 * 初始化所有图表
 */
function initCharts() {
    initTrafficChart();
    initTasksChart();
    initResourcesChart();
    initResponseTimeChart();
    initCacheChart(); // 新增
    initWorkerChart(); // 新增
}

/**
 * 初始化流量趋势图表
 */
function initTrafficChart() {
    const ctx = document.getElementById('traffic-chart').getContext('2d');
    
    trafficChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '请求数/分钟',
                data: [],
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                pointHoverRadius: 5,
                pointHoverBackgroundColor: '#667eea'
            }]
        },
        options: {
            ...chartConfig,
            plugins: {
                ...chartConfig.plugins,
                title: {
                    display: false
                }
            },
            scales: {
                ...chartConfig.scales,
                y: {
                    ...chartConfig.scales.y,
                    beginAtZero: true
                }
            },
            animation: {
                duration: 500
            }
        }
    });
}

/**
 * 初始化任务执行统计图表
 */
function initTasksChart() {
    const ctx = document.getElementById('tasks-chart').getContext('2d');
    
    tasksChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['运行中', '等待中', '已完成', '失败'],
            datasets: [{
                data: [0, 0, 0, 0],
                backgroundColor: [
                    '#4299e1',
                    '#ed8936',
                    '#48bb78',
                    '#f56565'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e2e8f0',
                        font: {
                            size: 11
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    ...chartConfig.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

/**
 * 初始化资源使用图表
 */
function initResourcesChart() {
    const ctx = document.getElementById('resources-chart').getContext('2d');
    
    resourcesChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['CPU', '内存', '磁盘', '网络'],
            datasets: [{
                label: '使用率 (%)',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(72, 187, 120, 0.8)',
                    'rgba(237, 137, 54, 0.8)',
                    'rgba(66, 153, 225, 0.8)'
                ],
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            ...chartConfig,
            indexAxis: 'y',
            plugins: {
                ...chartConfig.plugins,
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    ...chartConfig.scales.x,
                    max: 100,
                    beginAtZero: true
                },
                y: {
                    ...chartConfig.scales.y,
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * 初始化响应时间分布图表
 */
function initResponseTimeChart() {
    const ctx = document.getElementById('response-time-chart').getContext('2d');
    
    responseTimeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '平均响应时间 (ms)',
                data: [],
                borderColor: '#ed8936',
                backgroundColor: 'rgba(237, 137, 54, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 2,
                pointBackgroundColor: '#ed8936'
            }]
        },
        options: {
            ...chartConfig,
            plugins: {
                ...chartConfig.plugins,
                legend: {
                    display: true
                }
            },
            scales: {
                ...chartConfig.scales,
                y: {
                    ...chartConfig.scales.y,
                    beginAtZero: true
                }
            }
        }
    });
}

/**
 * 初始化缓存统计图表（新增）
 */
function initCacheChart() {
    const ctx = document.getElementById('cache-chart');
    if (!ctx) return;
    
    cacheChart = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['缓存命中', '缓存未命中'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    '#48bb78',
                    '#f56565'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#e2e8f0',
                        font: {
                            size: 11
                        },
                        padding: 15,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    ...chartConfig.plugins.tooltip,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            },
            cutout: '60%'
        }
    });
}

/**
 * 初始化Worker状态图表（新增）
 */
function initWorkerChart() {
    const ctx = document.getElementById('worker-chart');
    if (!ctx) return;
    
    workerChart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Worker 0', 'Worker 1', 'Worker 2', 'Worker 3'],
            datasets: [{
                label: '任务数',
                data: [0, 0, 0, 0],
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(72, 187, 120, 0.8)',
                    'rgba(237, 137, 54, 0.8)',
                    'rgba(66, 153, 225, 0.8)'
                ],
                borderWidth: 0,
                borderRadius: 4
            }]
        },
        options: {
            ...chartConfig,
            plugins: {
                ...chartConfig.plugins,
                legend: {
                    display: false
                }
            },
            scales: {
                ...chartConfig.scales,
                y: {
                    ...chartConfig.scales.y,
                    beginAtZero: true,
                    ticks: {
                        ...chartConfig.scales.y.ticks,
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * 更新流量图表
 */
function updateTrafficChart(data) {
    if (!trafficChart || !data) return;
    
    // 更新数据
    trafficChart.data.labels = data.timestamps || [];
    trafficChart.data.datasets[0].data = data.requests || [];
    
    trafficChart.update('none');
}

/**
 * 更新任务图表
 */
function updateTasksChart(stats) {
    if (!tasksChart || !stats) return;
    
    tasksChart.data.datasets[0].data = [
        stats.running || 0,
        stats.pending || 0,
        stats.completed || 0,
        stats.failed || 0
    ];
    
    tasksChart.update('none');
}

/**
 * 更新资源图表
 */
function updateResourcesChart(data) {
    if (!resourcesChart || !data) return;
    
    resourcesChart.data.datasets[0].data = [
        data.cpu || 0,
        data.memory || 0,
        data.disk || 0,
        data.network || 0
    ];
    
    resourcesChart.update('none');
}

/**
 * 更新响应时间图表
 */
function updateResponseTimeChart(data) {
    if (!responseTimeChart || !data) return;
    
    responseTimeChart.data.labels = data.timestamps || [];
    responseTimeChart.data.datasets[0].data = data.responseTimes || [];
    
    responseTimeChart.update('none');
}

/**
 * 添加实时数据点
 */
function addTrafficDataPoint(timestamp, requestCount) {
    if (!trafficChart) return;
    
    trafficChart.data.labels.push(timestamp);
    trafficChart.data.datasets[0].data.push(requestCount);
    
    // 保持最近30个数据点
    if (trafficChart.data.labels.length > 30) {
        trafficChart.data.labels.shift();
        trafficChart.data.datasets[0].data.shift();
    }
    
    trafficChart.update('none');
}

/**
 * 添加响应时间数据点
 */
function addResponseTimeDataPoint(timestamp, responseTime) {
    if (!responseTimeChart) return;
    
    responseTimeChart.data.labels.push(timestamp);
    responseTimeChart.data.datasets[0].data.push(responseTime);
    
    // 保持最近30个数据点
    if (responseTimeChart.data.labels.length > 30) {
        responseTimeChart.data.labels.shift();
        responseTimeChart.data.datasets[0].data.shift();
    }
    
    responseTimeChart.update('none');
}

/**
 * 更新缓存图表（新增）
 */
function updateCacheChart(stats) {
    if (!cacheChart || !stats) return;
    
    const hits = stats.hits || 0;
    const misses = stats.misses || 0;
    
    cacheChart.data.datasets[0].data = [hits, misses];
    cacheChart.update('none');
}

/**
 * 更新Worker状态图表（新增）
 */
function updateWorkerChart(workerStatus) {
    if (!workerChart || !workerStatus) return;
    
    // 统计每个worker的任务数
    const workerLoads = {};
    for (let i = 0; i < 4; i++) {
        workerLoads[i] = workerStatus[i] === 'busy' ? 1 : 0;
    }
    
    workerChart.data.datasets[0].data = [
        workerLoads[0] || 0,
        workerLoads[1] || 0,
        workerLoads[2] || 0,
        workerLoads[3] || 0
    ];
    
    workerChart.update('none');
}

/**
 * 销毁所有图表
 */
function destroyCharts() {
    if (trafficChart) {
        trafficChart.destroy();
        trafficChart = null;
    }
    
    if (tasksChart) {
        tasksChart.destroy();
        tasksChart = null;
    }
    
    if (resourcesChart) {
        resourcesChart.destroy();
        resourcesChart = null;
    }
    
    if (responseTimeChart) {
        responseTimeChart.destroy();
        responseTimeChart = null;
    }
    
    if (cacheChart) {
        cacheChart.destroy();
        cacheChart = null;
    }
    
    if (workerChart) {
        workerChart.destroy();
        workerChart = null;
    }
}

// 导出图表函数
window.charts = {
    initCharts,
    updateTrafficChart,
    updateTasksChart,
    updateResourcesChart,
    updateResponseTimeChart,
    addTrafficDataPoint,
    addResponseTimeDataPoint,
    updateCacheChart, // 新增
    updateWorkerChart, // 新增
    destroyCharts
};
