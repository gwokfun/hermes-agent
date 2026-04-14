# SecHermes 扩展开发指南

本文档介绍如何为信息安全助手（SecHermes）开发新的**技能（Skill）**、**MCP Server** 和**插件（Plugin）**，以扩展其能力而无需修改 hermes-agent 核心代码。

---

## 目录

1. [开发技能（Skill）](#1-开发技能skill)
2. [开发 MCP Server](#2-开发-mcp-server)
3. [开发内存插件（Memory Plugin）](#3-开发内存插件memory-plugin)
4. [安全开发规范](#4-安全开发规范)
5. [技能审核流程](#5-技能审核流程)

---

## 1. 开发技能（Skill）

技能（Skill）是 hermes-agent 的**程序性记忆**：用 Markdown 写成的操作指南，告诉智能体"如何完成某类特定任务"。技能无需编写代码，只需一个 `SKILL.md` 文件。

### 1.1 技能文件结构

```
my-skill/
├── SKILL.md           # 必须：技能主文件（YAML frontmatter + Markdown 正文）
├── scripts/           # 可选：辅助脚本
│   └── helper.py
├── references/        # 可选：参考文档
│   └── api-docs.md
└── templates/         # 可选：报告/输出模板
    └── report.md
```

### 1.2 SKILL.md 文件格式

```markdown
---
name: my-security-skill          # 技能的唯一标识符（用于 /my-security-skill 命令）
description: |                   # 简短描述（1-2句话）
  做什么，解决什么问题。
version: 1.0.0                   # 语义化版本号
author: your-name
license: MIT
metadata:
  hermes:
    tags: [security, custom]     # 标签，便于 /skills 搜索
    category: security
---

# 技能标题

## 适用场景

- 什么时候使用这个技能
- 用户问了什么样的问题

## ⚠️ 关键规则（如有）

列出必须遵守的安全或准确性规则。

## 工作流程

### 步骤 1：...

### 步骤 2：...

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|

## 配置要求

说明需要哪些环境变量或配置。
```

### 1.3 安全相关技能的额外要求

所有添加到 SecHermes 的安全技能，必须包含：

1. **防止捏造守则**（`⚠️` 部分）：明确禁止凭模型记忆作答
2. **数据来源标注**：每个信息来源必须在流程中注明
3. **错误处理**：所有工具调用失败的场景
4. **审批要求**（如技能执行危险操作）：必须描述审批流程

### 1.4 安装技能

```bash
# 开发/测试阶段：复制到用户技能目录
cp -r my-skill ~/.hermes/skills/

# 验证技能已加载
hermes
> /skills           # 应看到 my-skill 出现在列表中
> /my-security-skill  # 直接调用测试
```

### 1.5 完整示例：自定义合规检查技能

```markdown
---
name: compliance-check
description: |
  根据内部合规策略文档检查指定系统的合规状态，
  输出差距报告和修复建议。
version: 1.0.0
author: SecHermes Team
license: MIT
metadata:
  hermes:
    tags: [security, compliance, audit]
    category: security
---

# 合规检查（Compliance Check）

## 适用场景

- 对指定系统或配置进行合规性检查
- 生成审计报告

## ⚠️ 规则

1. 所有检查项必须来自指定的合规策略文档，禁止凭经验补充
2. 检查结果必须标注依据（文档名称 + 章节）

## 工作流程

### 步骤 1：加载合规策略

使用 file 工具读取 `${SEC_DOCS_BASE_PATH}/compliance/` 下的策略文档。

### 步骤 2：执行检查

[按策略文档逐项检查...]

### 步骤 3：生成报告

[按标准格式输出差距报告...]
```

---

## 2. 开发 MCP Server

MCP Server 将外部工具/API 封装为标准化的工具接口，供 hermes-agent 调用。

### 2.1 选择实现方式

| 方式 | 适用场景 | 复杂度 |
|------|---------|-------|
| Python MCP SDK | 封装现有 Python 客户端 | ⭐⭐ |
| Node.js MCP SDK | 封装 JS 生态工具 | ⭐⭐ |
| HTTP SSE（现有 REST API） | 直接暴露 REST API | ⭐ |
| Proxy 模式 | 聚合多个工具 | ⭐⭐⭐ |

### 2.2 Python MCP Server 开发步骤

**安装依赖**：
```bash
pip install mcp aiohttp
```

**最小实现模板**：

```python
# my_security_mcp/__main__.py
"""我的安全工具 MCP Server"""

import json
import os
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("my-security-tool")

@app.list_tools()
async def list_tools():
    """声明此 MCP Server 提供的工具列表"""
    return [
        Tool(
            name="my_tool",
            description="工具功能描述（智能体会读取此描述来决定是否调用）",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数说明"
                    }
                },
                "required": ["param1"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    """处理工具调用请求"""
    if name == "my_tool":
        # 实现工具逻辑
        result = {"status": "success", "data": arguments["param1"]}
    else:
        result = {"error": f"未知工具：{name}"}
    
    # 必须返回 TextContent 列表，内容必须是 JSON 字符串
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```

**注册到 hermes-agent**：

在 `~/.hermes/config.yaml` 中添加：

```yaml
mcp:
  servers:
    - name: my-security-tool
      command: "python"
      args: ["-m", "my_security_mcp"]
      env:
        MY_API_KEY: "${MY_API_KEY}"
```

### 2.3 MCP Server 开发规范

1. **工具名称**：使用 `snake_case`，清晰描述功能
2. **错误处理**：工具调用失败时返回包含 `error` 字段的 JSON，而非抛出异常
3. **返回格式**：始终返回 JSON 字符串，字段含义清晰
4. **环境变量**：凭证通过环境变量传入，不硬编码
5. **日志**：使用 `logging` 而非 `print`，避免污染 stdio 通信

### 2.4 测试 MCP Server

```bash
# 单元测试
python -m pytest tests/test_my_security_mcp.py

# 手动测试（启动 MCP Server 并发送测试请求）
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python -m my_security_mcp
```

---

## 3. 开发内存插件（Memory Plugin）

内存插件允许将 SecHermes 的记忆存储到自定义后端（如内部知识库、数据库）。

### 3.1 插件结构

```
plugins/memory/my-memory-backend/
├── __init__.py        # 实现 MemoryProvider ABC
└── requirements.txt   # 依赖
```

### 3.2 MemoryProvider 接口

```python
# plugins/memory/my-memory-backend/__init__.py
from plugins.memory import MemoryProvider

class MyMemoryBackend(MemoryProvider):
    """自定义内存后端"""
    
    name = "my-memory-backend"
    description = "将记忆存储到企业知识库"
    
    def __init__(self, config: dict):
        self.api_url = config.get("api_url", "")
        # 初始化连接
    
    def store(self, key: str, value: str, metadata: dict = None) -> bool:
        """存储记忆条目"""
        # 实现存储逻辑
        return True
    
    def retrieve(self, query: str, limit: int = 10) -> list[dict]:
        """检索相关记忆"""
        # 实现检索逻辑
        return []
    
    def delete(self, key: str) -> bool:
        """删除记忆条目"""
        return True
    
    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        """检查后端是否可用"""
        # 检查依赖、连接等
        return True, ""
```

### 3.3 启用内存插件

在 `~/.hermes/config.yaml` 中：

```yaml
memory:
  provider: "my-memory-backend"
  my-memory-backend:
    api_url: "http://your-knowledge-base/api"
```

---

## 4. 安全开发规范

所有为 SecHermes 开发的扩展，必须遵守以下安全规范：

### 4.1 数据安全

- ❌ 禁止在代码中硬编码 API Key、密码、Token
- ❌ 禁止将敏感数据写入日志
- ❌ 禁止将凭证包含在工具返回值中
- ✅ 通过环境变量传入凭证
- ✅ 返回值中的敏感字段做脱敏处理（如 `"token": "****"`）

### 4.2 输入验证

```python
# 示例：验证 IP 地址输入
import ipaddress

def validate_scan_target(target: str) -> bool:
    try:
        ipaddress.ip_network(target, strict=False)
        return True
    except ValueError:
        return False
```

### 4.3 命令注入防护

```python
# ❌ 危险：字符串拼接命令
os.system(f"nmap {user_input}")

# ✅ 安全：使用参数列表
import subprocess
subprocess.run(["nmap", "--", user_input], capture_output=True)
```

### 4.4 技能内容审查清单

提交新技能前，确认：

- [ ] 没有外联不必要的网络地址
- [ ] 没有执行文件下载或代码注入的步骤
- [ ] 危险操作（删除、修改系统配置）有明确的用户确认步骤
- [ ] 涉及凭证的操作不在响应中明文输出

---

## 5. 技能审核流程

SecHermes 的技能审核由管理员负责，分为两类：

### 5.1 官方技能（随 SecHermes 分发）

1. 开发者提交 Pull Request，包含技能文件
2. 安全团队 Code Review（参考安全开发规范）
3. 在测试环境运行最小化测试
4. 管理员批准后合并

### 5.2 用户技能（安装到 `~/.hermes/skills/`）

hermes-agent 内置的技能守卫（`tools/skills_guard.py`）会自动扫描：

- 数据外泄模式
- 提示注入
- 破坏性命令
- 持久化后门
- 混淆代码

**对于 SecHermes，管理员需额外检查**：

- 技能是否符合 SOUL.md 中的行为准则
- 是否绕过了审批机制
- 是否可能导致信息捏造

详细审核流程见 `docs/ADMIN_GUIDE.md`。

---

## 参考资料

- [hermes-agent Skills 文档](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [MCP 官方文档](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [agentskills.io 技能标准](https://agentskills.io)
