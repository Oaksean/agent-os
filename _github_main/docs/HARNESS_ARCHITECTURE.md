# Agent OS · Harness 核心机制架构文档

> 本文档描述 Agent OS 的 **Harness（执行编排内核）** 核心机制，对标 Claude Code 与
> OpenAI Codex 的 Agent Runtime 设计。这些机制回答了同一个问题：**如何让一个自主
> Agent 可靠、安全、可观测地执行长任务？**

## 目录

1. [总体架构](#1-总体架构)
2. [Agent Loop 状态机（OTA 循环）](#2-agent-loop-状态机ota-循环)
3. [缓存友好型上下文工程](#3-缓存友好型上下文工程)
4. [TurnDiffTracker 文件差异跟踪](#4-turndifftracker-文件差异跟踪)
5. [分级审批护栏与沙箱](#5-分级审批护栏与沙箱)
6. [Manager-Subagent 并行编排](#6-manager-subagent-并行编排)
7. [长期记忆与记忆巩固](#7-长期记忆与记忆巩固)
8. [MCP 协议客户端](#8-mcp-协议客户端)
9. [端到端演示](#9-端到端演示)

---

## 1. 总体架构

Agent OS 的 Harness 内核由六个相互解耦的子系统组成，围绕一个核心的
**Agent Loop** 状态机运转：

```
                    ┌─────────────────────────────────────┐
                    │            Agent Loop (OTA)          │
                    │   IDLE → PLANNING → EXECUTING → ...  │
                    └──────────────┬──────────────────────┘
                                   │ 每步 (Step) 调用
        ┌──────────────┬───────────┼────────────┬──────────────┐
        ▼              ▼           ▼            ▼              ▼
  ContextBuilder  Guardrails   TurnDiff    LongTermMemory   Subagent
  (上下文构建)     (审批护栏)   Tracker     (长期记忆)       Manager
                              (差异跟踪)                     (并行编排)
        │              │           │            │              │
        └──────────────┴─────┬─────┴────────────┴──────────────┘
                             ▼
                     MCP Client (工具协议适配)
```

| 模块 | 文件 | 职责 |
|------|------|------|
| Agent Loop | `src/kernel/agent_loop.py` | Observe-Think-Act 状态机、停滞检测、指数退避 |
| 上下文工程 | `src/prompts/context_builder.py` | 静态前缀缓存、追加式历史、易失状态分离 |
| 差异跟踪 | `src/tools/diff_tracker.py` | 基线快照、UUID 映射、统一 Diff、提交/回滚 |
| 审批护栏 | `src/security/guardrails.py` | 三级审批、命令/文件写入评估、OverlayFS |
| 并行编排 | `src/communication/subagent.py` | 任务拆解、依赖分层并行、冲突检测 |
| 长期记忆 | `src/memory/long_term_memory.py` | TF-IDF 语义检索、时间衰减、选择性遗忘 |
| 记忆巩固 | `src/memory/memory_consolidator.py` | 触发条件判断、摘要、遗忘 |
| MCP 客户端 | `src/tools/mcp_client.py` | JSON-RPC 2.0、Stdio/InMemory 传输 |

---

## 2. Agent Loop 状态机（OTA 循环）

参考 Claude Code / Codex 的 `while` 循环 ReAct 执行范式，将一次任务执行建模为
**Observe → Think → Act** 的有限状态机。

### 2.1 状态定义

```
IDLE ──► PLANNING ──► EXECUTING ──► COMPLETED
                          │  ▲
                          │  │ (继续下一步)
                          ▼  │
                    WAITING_APPROVAL
                          │
                          ▼
                        ERROR（终态）
```

### 2.2 核心防护机制

- **最大步数限制**：`max_steps` 防止 Agent 陷入死循环，超出即判定失败。
- **停滞检测（StallDetector）**：连续 N 步无实质进展（重复相同 Action 或上下文无
  增量）时触发，避免 Agent 原地打转。
- **指数退避重试（ExponentialBackoff）**：工具调用失败时按 `base * 2^n` 递增等待
  时间重试，设 `max_retries` 与 `max_delay` 上限。
- **进度验证（_verify_progress）**：每步结束时校验是否产生可观测进展（文件变更、
  状态迁移、信息增益），据此更新停滞计数器。

### 2.3 关键接口

```python
from src.kernel.agent_loop import AgentLoop, AgentLoopConfig

loop = AgentLoop(
    tool_executor=...,   # 实现 ToolExecutor 接口
    model_client=...,    # 实现 ModelClient 接口
    approval_handler=...,# 实现 ApprovalHandler 接口
    config=AgentLoopConfig(max_steps=20, stall_threshold=3),
)
result = loop.run("任务描述")  # Step 序列 + 终态
```

---

## 3. 缓存友好型上下文工程

工业级 Agent 与 Demo 的核心区别在于 **Token 效率与缓存命中率**。

### 3.1 三段式结构

| 区段 | 内容 | 变化频率 | 缓存策略 |
|------|------|----------|----------|
| 静态前缀 | 系统指令 + 工具定义 | 几乎不变 | 固定头部，命中缓存 |
| 追加式历史 | 对话记录 | 只增不减 | 尾部追加，不破坏前缀 |
| 易失状态 | 审批模式、进度、临时变量 | 高频 | 本地管理，按需注入 |

### 3.2 缓存哈希稳定

`set_tool_definitions` 内部**按工具名排序**后再序列化，保证跨请求的静态前缀字节
一致，从而稳定 `static_hash`，最大化 LLM 提供商的前缀缓存命中。

### 3.3 上下文压缩（compact）

当历史超过阈值时，保留最近 `keep_last` 条，将更早历史压缩为摘要文本，供调用方
回灌到长期记忆或摘要记忆。

---

## 4. TurnDiffTracker 文件差异跟踪

精确追踪 Agent 在一次任务（Turn）中对文件系统的所有变更。

### 4.1 核心概念

- **基线快照（Baseline Snapshot）**：Agent 首次访问文件时记录内容哈希、大小、权限。
  新文件基线为空（等价 `/dev/null`）。
- **UUID 映射**：维护 `external_path ↔ UUID ↔ current_path` 双向映射，重命名/移动
  也能追踪同一文件的变更历史，生成准确的 Rename Diff 而非「删除+新增」误判。
- **统一 Diff**：任务结束对比当前磁盘与基线，生成聚合统一 Diff。

### 4.2 变更类型

| ChangeType | 判定条件 |
|------------|----------|
| `ADDED` | 基线为空，当前有内容 |
| `MODIFIED` | 内容哈希变化 |
| `DELETED` | 基线有内容，当前不存在 |

### 4.3 Overlay 语义

`commit()` 将变更合并入基线；`rollback()` 把被修改/删除的文件恢复到基线内容，
实现 Copy-on-Write Overlay 的原子性保证。

---

## 5. 分级审批护栏与沙箱

### 5.1 三级审批模型

| 审批级别 | 语义 | 示例 |
|----------|------|------|
| `AUTO` | 自动放行，无需询问 | 读取文件、查询状态 |
| `INTERACTIVE` | 需人工确认 | 删除子目录、修改配置 |
| `FORBIDDEN` | 绝对禁止 | `rm -rf /`、写入系统目录 |

### 5.2 CommandPolicy 正则分层

```python
CommandPolicy.forbidden = r"rm\s+-rf\s+/(\s|$|\*)"   # 根目录破坏
CommandPolicy.dangerous = [r"rm\s+-rf", r"mkfs", ...]  # 危险但可确认
CommandPolicy.caution   = [r"sudo", r"chmod", ...]     # 需注意
```

注意：`rm -rf /tmp/cache` 会被正确归为 `DANGEROUS`（需确认），而非误判为
`FORBIDDEN`——forbidden 仅匹配根目录 `/` 后跟空白/结尾/星号。

### 5.3 OverlayFS（写时复制）

所有写操作先落盘到隔离 Overlay，`commit()` 原子合并，`rollback()` 一键回滚，
并内置路径穿越防护（`..` 逃逸检测）。

---

## 6. Manager-Subagent 并行编排

将复杂任务拆解为子任务，按**依赖关系分层并行**执行，最后合并结果。

### 6.1 执行流程

1. **依赖图构建**：根据 `Subtask.dependencies` 建立 DAG。
2. **分层调度**：无依赖的子任务作为第一层并行执行，完成后解锁下一层。
3. **冲突检测（ConflictDetector）**：两个子任务触碰同一文件（`touches` 重叠）时
   标记冲突并记录，避免并行写坏文件。
4. **结果合并**：汇总所有子任务结果，输出统一报告。

```python
from src.communication.subagent import SubagentManager, Subtask

subtasks = [
    Subtask(subtask_id="a", name="读配置", touches=["config.yaml"]),
    Subtask(subtask_id="b", name="读数据", touches=["data.csv"]),
    Subtask(subtask_id="c", name="汇总", dependencies=["a", "b"]),
]
result = await SubagentManager(worker=worker_fn).execute(subtasks)
# result: {"success": True, "completed": 3, ...}
```

---

## 7. 长期记忆与记忆巩固

### 7.1 长期记忆（LongTermMemory）

- **TF-IDF 轻量级语义检索**：无需外部向量库，用余弦相似度做关键词级语义匹配。
- **重要性加权**：高重要性记忆检索排序靠前。
- **选择性遗忘**：`forget_low_importance(threshold)` 清理低价值记忆。

### 7.2 情景记忆（EpisodicMemory）

记录「任务 → 操作 → 结果 → 教训」四元组，`reflect()` 提取失败教训用于后续反思。

### 7.3 记忆巩固（MemoryConsolidator）

模拟人类记忆的海马体巩固机制：

- **触发判断（should_consolidate）**：记忆量或时间衰减达到阈值才触发。
- **摘要（summarize）**：将多条相关记忆合并为精炼表达。
- **遗忘（forget）**：按时间衰减 × 重要性，选择性遗忘低价值条目。

---

## 8. MCP 协议客户端

实现 Model Context Protocol（JSON-RPC 2.0）客户端，对接外部工具/资源。

- **MCPTransport（抽象）**：`InMemoryTransport`（进程内测试）与 `StdioTransport`
  （子进程 stdio）两种传输。
- **握手**：`initialize` 协商协议版本与能力。
- **工具调用**：`list_tools` / `call_tool` 完整往返。
- **资源访问**：`list_resources` / `read_resource`。
- **MCPToolAdapter**：将 MCP 工具适配为 Agent Loop 的 `ToolExecutor` 接口。

---

## 9. 端到端演示

`examples/basic/harness_demo.py` 将上述模块串联为一次完整工作流：

```
用户任务 ─► AgentLoop ─► Guardrails 评估 ─► OverlayFS 写入
                │                              │
                └──── TurnDiffTracker 记录 ────┘
                              │
                ContextBuilder 构建上下文 ─► LongTermMemory 沉淀
```

运行方式：

```bash
# 单个模块离线演示（无外部依赖）
python src/kernel/agent_loop.py
python src/tools/diff_tracker.py
python src/security/guardrails.py
python src/communication/subagent.py
python src/memory/long_term_memory.py
python src/memory/memory_consolidator.py
python src/tools/mcp_client.py

# 端到端演示
python examples/basic/harness_demo.py

# 运行测试套件
python -m pytest tests/unit -q
```

---

## 设计原则总结

1. **可靠性优先**：停滞检测、最大步数、退避重试，三管齐下防止失控。
2. **缓存意识**：静态前缀稳定哈希、追加式历史，把 Token 成本当一等公民。
3. **可回滚**：TurnDiffTracker + OverlayFS 双保险，任何一步都可撤销。
4. **安全默认拒绝**：FORBIDDEN 黑名单 + INTERACTIVE 人工确认，宁可不做不可做错。
5. **记忆分层**：工作记忆（短）+ 长期记忆（中）+ 情景记忆（反思），各司其职。
