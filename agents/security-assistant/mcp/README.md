# MCP 服务器集成指南

SecHermes 通过 MCP（Model Context Protocol）协议连接外部工具，无需修改 hermes-agent 核心代码。

---

## 概述

MCP 是一个开放协议，允许 AI 助手通过标准接口调用外部服务。hermes-agent 内置了 MCP 客户端（`tools/mcp_tool.py`），支持通过 `stdio` 或 `sse` 方式连接 MCP Server。

SecHermes 定义了三类 MCP Server：

| MCP Server | 用途 | 对应技能 |
|-----------|------|---------|
| `vuln-scanner` | 漏洞扫描工具 API 封装 | vuln-scan |
| `approval-api` | 企业审批系统 API 封装 | sec-auto-fix |
| `asset-inventory` | 资产/软件清单查询 | sec-intel |

---

## 配置 MCP Server

在 `~/.hermes/config.yaml` 中添加 MCP Server 配置：

```yaml
mcp:
  servers:
    # 漏洞扫描 MCP Server
    - name: vuln-scanner
      command: "python"
      args: ["-m", "vuln_scanner_mcp"]
      env:
        SCANNER_URL: "https://your-scanner:8834"
        SCANNER_API_KEY: "${NESSUS_ACCESS_KEY}"
      # 或使用 SSE 模式（HTTP 长连接）
      # url: "http://localhost:8080/sse"

    # 审批 API MCP Server
    - name: approval-api
      command: "python"
      args: ["-m", "approval_mcp_server"]
      env:
        APPROVAL_API_URL: "${APPROVAL_API_URL}"
        APPROVAL_API_TOKEN: "${APPROVAL_API_TOKEN}"

    # 资产清单 MCP Server（可选）
    - name: asset-inventory
      url: "http://your-asset-server:9090/sse"
```

或通过命令行配置（hermes 0.8+）：

```bash
hermes mcp add vuln-scanner --command "python -m vuln_scanner_mcp" \
  --env SCANNER_URL=https://your-scanner:8834
```

---

## MCP Server 开发指南

### 基本结构

每个 MCP Server 需实现 MCP 协议标准。推荐使用官方 Python SDK：

```bash
pip install mcp
```

### 漏洞扫描 MCP Server 示例

以下是针对 Nessus/Tenable 的示例 MCP Server，供参考实现：

```python
# vuln_scanner_mcp/__main__.py
"""漏洞扫描 MCP Server — Nessus/Tenable 封装示例"""

import json
import os
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

SCANNER_URL = os.environ.get("SCANNER_URL", "https://localhost:8834")
ACCESS_KEY = os.environ.get("SCANNER_ACCESS_KEY", "")
SECRET_KEY = os.environ.get("SCANNER_SECRET_KEY", "")

app = Server("vuln-scanner")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="create_scan",
            description="创建并启动漏洞扫描任务",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "扫描任务名称"},
                    "target": {"type": "string", "description": "扫描目标（IP/网段/主机名）"},
                    "policy": {"type": "string", "description": "扫描策略", "enum": ["quick", "full", "compliance"]}
                },
                "required": ["name", "target"]
            }
        ),
        Tool(
            name="get_scan_status",
            description="查询扫描任务状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string", "description": "扫描任务 ID"}
                },
                "required": ["scan_id"]
            }
        ),
        Tool(
            name="export_report",
            description="导出扫描报告",
            inputSchema={
                "type": "object",
                "properties": {
                    "scan_id": {"type": "string", "description": "扫描任务 ID"},
                    "format": {"type": "string", "enum": ["json", "pdf", "csv"], "default": "json"}
                },
                "required": ["scan_id"]
            }
        ),
        Tool(
            name="list_scans",
            description="列出所有扫描任务",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    import aiohttp

    headers = {
        "X-ApiKeys": f"accessKey={ACCESS_KEY};secretKey={SECRET_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        if name == "create_scan":
            payload = {
                "uuid": "ad629e16-03b6-8c1d-cef6-ef8c9dd3c658d24bd260ef5f9e66",  # Nessus 默认"Basic Network Scan"模板 UUID（各组织实例可能不同，请通过 GET /editor/scan/templates 确认正确的 UUID 后替换）
                "settings": {
                    "name": arguments["name"],
                    "text_targets": arguments["target"]
                }
            }
            async with session.post(
                f"{SCANNER_URL}/scans",
                headers=headers,
                json=payload,
                ssl=False
            ) as resp:
                data = await resp.json()
                scan_id = data.get("scan", {}).get("id", "unknown")
                # 立即启动
                await session.post(f"{SCANNER_URL}/scans/{scan_id}/launch", headers=headers, ssl=False)
                result = {"scan_id": str(scan_id), "status": "launched", "name": arguments["name"]}

        elif name == "get_scan_status":
            async with session.get(
                f"{SCANNER_URL}/scans/{arguments['scan_id']}",
                headers=headers,
                ssl=False
            ) as resp:
                data = await resp.json()
                info = data.get("info", {})
                result = {
                    "scan_id": arguments["scan_id"],
                    "status": info.get("status", "unknown"),
                    "progress": info.get("scanner_progress", 0),
                    "vulnerabilities": data.get("vulnerabilities", [])
                }

        elif name == "list_scans":
            async with session.get(f"{SCANNER_URL}/scans", headers=headers, ssl=False) as resp:
                data = await resp.json()
                result = {"scans": data.get("scans", [])}

        elif name == "export_report":
            # 触发导出
            async with session.post(
                f"{SCANNER_URL}/scans/{arguments['scan_id']}/export",
                headers=headers,
                json={"format": arguments.get("format", "json")},
                ssl=False
            ) as resp:
                export_data = await resp.json()
                file_id = export_data.get("file")
                result = {"file_id": file_id, "scan_id": arguments["scan_id"]}
        else:
            result = {"error": f"未知工具：{name}"}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

### 审批 MCP Server 示例

```python
# approval_mcp_server/__main__.py
"""企业审批 MCP Server 示例"""

import json
import os
import asyncio
import aiohttp
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

APPROVAL_API_URL = os.environ.get("APPROVAL_API_URL", "")
APPROVAL_API_TOKEN = os.environ.get("APPROVAL_API_TOKEN", "")

app = Server("approval-api")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="request_approval",
            description="发起修复操作审批申请",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "runbook_id": {"type": "string"},
                    "target_service": {"type": "string"},
                    "impact": {"type": "string"},
                    "urgency": {"type": "string", "enum": ["normal", "high", "critical"]}
                },
                "required": ["title", "description", "runbook_id"]
            }
        ),
        Tool(
            name="get_approval_status",
            description="查询审批申请状态",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string"}
                },
                "required": ["ticket_id"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    headers = {
        "Authorization": f"Bearer {APPROVAL_API_TOKEN}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        if name == "request_approval":
            async with session.post(
                f"{APPROVAL_API_URL}/requests",
                headers=headers,
                json=arguments
            ) as resp:
                result = await resp.json()
        elif name == "get_approval_status":
            async with session.get(
                f"{APPROVAL_API_URL}/requests/{arguments['ticket_id']}",
                headers=headers
            ) as resp:
                result = await resp.json()
        else:
            result = {"error": f"未知工具：{name}"}

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 使用现有 MCP Server

如果已有支持 MCP 协议的工具，可直接配置：

```yaml
mcp:
  servers:
    # 示例：使用公开的 CVE MCP Server
    - name: cve-search
      url: "https://your-mcp-server/sse"
      
    # 示例：本地运行的资产管理系统
    - name: asset-inventory
      command: "node"
      args: ["path/to/asset-mcp-server/index.js"]
```

---

## 验证 MCP 连接

```bash
# 在 Hermes 会话中验证 MCP 工具已加载
hermes
> /tools

# 应看到 MCP 工具列表，包括：
# vuln-scanner__create_scan
# vuln-scanner__get_scan_status
# approval-api__request_approval
# 等
```

---

## 参考资料

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [hermes-agent MCP 配置](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)
