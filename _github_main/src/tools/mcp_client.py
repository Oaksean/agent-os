"""
MCP (Model Context Protocol) 客户端

参考 Codex Harness 对 MCP 的原生支持设计。MCP 允许动态发现和加载外部
工具与服务——开发者编写标准的 MCP Server，将数据库、API、内部系统等
暴露给 Agent，极大扩展能力边界。

本模块实现一个基于 JSON-RPC 2.0 的 MCP 客户端，支持：
    - initialize          握手（能力协商）
    - tools/list          工具发现
    - tools/call          工具调用
    - resources/list      资源发现
    - resources/read      资源读取

传输层：
    - StdioTransport     通过子进程 stdin/stdout 通信（最常见）
    - InMemoryTransport  进程内直连（测试/演示）
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """MCP 协议错误"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(f"MCP Error [{code}]: {message}")


@dataclass
class MCPMessage:
    """MCP JSON-RPC 消息"""

    id: Optional[str]
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        payload: Dict[str, Any] = {"jsonrpc": "2.0", "method": self.method}
        if self.id is not None:
            payload["id"] = self.id
        if self.params:
            payload["params"] = self.params
        if self.error is not None:
            payload["error"] = self.error
        if self.result is not None:
            payload["result"] = self.result
        return json.dumps(payload, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        data = json.loads(json_str)
        return cls(
            id=data.get("id"),
            method=data.get("method", ""),
            params=data.get("params", {}),
            result=data.get("result"),
            error=data.get("error"),
        )


class MCPTransport(ABC):
    """MCP 传输层抽象"""

    @abstractmethod
    def send(self, json_str: str) -> None:
        """发送一条 JSON-RPC 消息"""
        ...

    @abstractmethod
    def receive(self) -> str:
        """接收一条 JSON-RPC 消息（阻塞）"""
        ...

    @abstractmethod
    def close(self) -> None:
        """关闭传输"""
        ...


class InMemoryTransport(MCPTransport):
    """
    进程内传输 —— 用于测试或内嵌 MCP Server。

    handler: 接收 MCPMessage，返回 MCPMessage（同步处理）。
    """

    def __init__(self, handler: Any):
        self.handler = handler
        self._outbox: List[str] = []
        self._lock = threading.Condition()

    def send(self, json_str: str) -> None:
        # 同步调用 handler 并缓存响应
        request = MCPMessage.from_json(json_str)
        response = self.handler(request)
        if response is not None:
            with self._lock:
                self._outbox.append(response.to_json())
                self._lock.notify_all()

    def receive(self) -> str:
        with self._lock:
            while not self._outbox:
                self._lock.wait()
            return self._outbox.pop(0)

    def close(self) -> None:
        pass


class StdioTransport(MCPTransport):
    """stdio 传输 —— 通过子进程启动 MCP Server 并通信"""

    def __init__(self, command: List[str]):
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

    def send(self, json_str: str) -> None:
        assert self.process.stdin is not None
        self.process.stdin.write(json_str + "\n")
        self.process.stdin.flush()

    def receive(self) -> str:
        assert self.process.stdout is not None
        return self.process.stdout.readline().strip()

    def close(self) -> None:
        self.process.terminate()


class MCPClient:
    """MCP 客户端（JSON-RPC 2.0）"""

    def __init__(self, transport: MCPTransport, client_name: str = "agent-os"):
        self.transport = transport
        self.client_name = client_name
        self.initialized = False
        self.server_info: Dict[str, Any] = {}
        self.capabilities: Dict[str, Any] = {}

    # ==================== 协议方法 ====================

    def initialize(self) -> Dict[str, Any]:
        """握手：能力协商"""
        result = self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": self.client_name, "version": "0.1.0"},
            },
        )
        self.initialized = True
        self.server_info = result.get("serverInfo", {})
        self.capabilities = result.get("capabilities", {})
        logger.info(
            f"MCP 握手成功：server={self.server_info.get('name', 'unknown')} "
            f"capabilities={list(self.capabilities.keys())}"
        )
        return result

    def list_tools(self) -> List[Dict[str, Any]]:
        """发现可用工具"""
        result = self._request("tools/list", {})
        tools = result.get("tools", [])
        logger.info(f"MCP 工具发现：{len(tools)} 个工具")
        return tools

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError"):
            raise MCPError(-32000, f"工具调用失败: {name}", result.get("content"))
        return result.get("content")

    def list_resources(self) -> List[Dict[str, Any]]:
        """发现可用资源"""
        result = self._request("resources/list", {})
        return result.get("resources", [])

    def read_resource(self, uri: str) -> Any:
        """读取资源"""
        result = self._request("resources/read", {"uri": uri})
        return result.get("contents")

    # ==================== 底层请求 ====================

    def _request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """发送请求并等待响应"""
        msg_id = str(uuid.uuid4())
        message = MCPMessage(id=msg_id, method=method, params=params)
        self.transport.send(message.to_json())

        # 等待匹配 id 的响应
        while True:
            raw = self.transport.receive()
            if not raw:
                raise MCPError(-32000, "传输通道关闭")
            response = MCPMessage.from_json(raw)
            if response.id == msg_id:
                if response.error:
                    raise MCPError(
                        response.error.get("code", -32000),
                        response.error.get("message", "unknown"),
                        response.error.get("data"),
                    )
                return response.result if response.result is not None else {}

    def close(self) -> None:
        self.transport.close()


class MCPToolAdapter:
    """
    把 MCP 工具适配到本地 ToolExecutor 接口（供 Agent Loop 调用）。
    """

    def __init__(self, client: MCPClient):
        self.client = client
        self._tools: Dict[str, Dict[str, Any]] = {}

    def refresh(self) -> None:
        """刷新工具缓存"""
        for tool in self.client.list_tools():
            self._tools[tool["name"]] = tool

    async def execute(self, tool_name: str, params: Dict[str, Any]) -> Any:
        if tool_name not in self._tools:
            raise KeyError(f"MCP 工具不存在: {tool_name}")
        # MCP call_tool 是同步的，在异步场景可放到线程池执行
        import asyncio

        return await asyncio.to_thread(self.client.call_tool, tool_name, params)

    def list_tools(self) -> List[Dict[str, Any]]:
        return list(self._tools.values())


# ==================== 演示 ====================

def _mock_server(request: MCPMessage) -> Optional[MCPMessage]:
    """进程内 Mock MCP Server（演示用）"""
    if request.method == "initialize":
        return MCPMessage(
            id=request.id,
            method=request.method,
            result={
                "serverInfo": {"name": "mock-server", "version": "1.0"},
                "capabilities": {"tools": {}},
            },
        )
    if request.method == "tools/list":
        return MCPMessage(
            id=request.id,
            method=request.method,
            result={
                "tools": [
                    {"name": "web_search", "description": "搜索网页"},
                    {"name": "get_weather", "description": "查询天气"},
                ]
            },
        )
    if request.method == "tools/call":
        name = request.params.get("name")
        return MCPMessage(
            id=request.id,
            method=request.method,
            result={"content": f"mock 结果: {name}({request.params.get('arguments')})", "isError": False},
        )
    return None


def demo():
    """演示 MCP 客户端完整流程"""
    transport = InMemoryTransport(_mock_server)
    client = MCPClient(transport)

    print("=== 1. 握手 ===")
    info = client.initialize()
    print(f"  服务器: {info['serverInfo']['name']}")

    print("\n=== 2. 工具发现 ===")
    tools = client.list_tools()
    for t in tools:
        print(f"  - {t['name']}: {t['description']}")

    print("\n=== 3. 工具调用 ===")
    result = client.call_tool("get_weather", {"city": "北京"})
    print(f"  结果: {result}")

    client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    demo()
