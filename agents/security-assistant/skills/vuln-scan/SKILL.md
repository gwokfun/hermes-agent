---
name: vuln-scan
description: |
  漏洞扫描管理技能。支持启动例行漏洞扫描、查询扫描任务状态与进度、获取扫描报告、
  对报告中的漏洞进行分类分析，并生成修复建议摘要。
  需要漏洞扫描 MCP Server 或支持 REST API 的扫描工具（OpenVAS / Nessus / 自研）。
version: 1.0.0
author: SecHermes
license: MIT
metadata:
  hermes:
    tags: [security, vulnerability, scanning, openvas, nessus, report]
    category: security
---

# 漏洞扫描管理（Vulnerability Scan Management）

## 适用场景

- 用户要求启动、查询或管理漏洞扫描任务
- 用户要求获取、解读或分析漏洞扫描报告
- 例行漏洞扫描工作的全流程管理

---

## ⚠️ 防止捏造守则

在执行本技能的任何步骤之前，请牢记：

1. **漏洞信息必须来自工具输出**，禁止凭记忆描述漏洞细节。
2. **CVE 编号必须来自扫描工具或权威数据库**，不得推测或补全。
3. **严重等级以工具输出为准**，不得自行调整。
4. 如果工具调用失败，如实报告失败原因，不得编造结果。

---

## 工作流程

### 阶段 1：明确意图

确认用户意图属于以下哪种操作：

| 操作 | 关键词示例 |
|------|-----------|
| 启动新扫描 | "对...执行扫描"、"扫描...范围"、"发起漏洞扫描" |
| 查询进度 | "扫描状态"、"任务 ID xxx 进度"、"还有多久" |
| 获取报告 | "获取报告"、"上次扫描结果"、"扫描完成了吗" |
| 分析报告 | "分析...报告"、"高危漏洞"、"哪些需要修复" |

如果意图不明确，使用 `clarify` 工具询问。

### 阶段 2A：启动新扫描

**前置确认**（在启动前必须向用户确认）：
- 扫描目标范围（IP、主机名、网段）
- 扫描策略（快速/全量/合规检查）
- 计划时间（立即/定时）

**通过 MCP 工具启动扫描**（示例调用，具体工具名称依 MCP Server 配置而定）：

```python
# 通过 MCP Server 调用漏洞扫描 API
result = mcp_call("vuln-scanner", "create_scan", {
    "name": "routine-scan-{date}",
    "target": "<用户指定的目标>",
    "policy": "<扫描策略>",
    "schedule": "immediate"
})
```

**替代方案**（使用 terminal 工具直接调用 CLI）：

```bash
# OpenVAS / GVM CLI 示例
gvm-cli --gmp-username admin --gmp-password <密码> socket \
  --xml "<create_task><name>Routine Scan</name><target id='TARGET_ID'/><config id='CONFIG_ID'/></create_task>"

# Nessus CLI 示例（需配置 NESSUS_URL 和 NESSUS_TOKEN 环境变量）
curl -s -X POST "${NESSUS_URL}/scans" \
  -H "X-ApiKeys: accessKey=${NESSUS_ACCESS_KEY};secretKey=${NESSUS_SECRET_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"uuid": "<template_uuid>", "settings": {"name": "Routine Scan", "text_targets": "<target>"}}'
```

**记录任务**：
- 将任务 ID、目标、开始时间、策略记录到工作日志中
- 向用户报告：任务 ID、预计完成时间

### 阶段 2B：查询扫描进度

```bash
# 通过 MCP Server 查询
result = mcp_call("vuln-scanner", "get_scan_status", {"scan_id": "<任务ID>"})

# 或通过 CLI
curl -s "${NESSUS_URL}/scans/<scan_id>" \
  -H "X-ApiKeys: accessKey=${NESSUS_ACCESS_KEY};secretKey=${NESSUS_SECRET_KEY}"
```

向用户报告：
- 当前状态（运行中/已完成/失败/已暂停）
- 完成百分比（如可用）
- 已发现漏洞数（如可用）
- 预计剩余时间

### 阶段 2C：获取扫描报告

```bash
# 导出报告（JSON 格式便于分析）
result = mcp_call("vuln-scanner", "export_report", {
    "scan_id": "<任务ID>",
    "format": "json"
})

# 保存到本地以备分析
# 文件命名规范：scan-report-{任务ID}-{日期}.json
```

### 阶段 2D：分析扫描报告

分析时必须严格按照工具返回的数据进行，不得凭经验补充：

**漏洞分类汇总**（必须输出）：

```markdown
## 扫描报告摘要

| 严重等级 | 数量 | 说明 |
|---------|------|------|
| Critical | N | ... |
| High     | N | ... |
| Medium   | N | ... |
| Low      | N | ... |
| Info     | N | ... |

**扫描范围**：[来自报告]
**扫描时间**：[来自报告]
**扫描工具**：[来自报告]
```

**高危漏洞详情**（Critical 和 High，必须逐条列出）：

```markdown
### [CVE-XXXX-XXXXX] 漏洞名称

- **严重等级**：Critical / CVSS: X.X
- **受影响主机**：[来自报告]
- **受影响服务/版本**：[来自报告]
- **漏洞描述**：[来自报告，不得扩展]
- **修复建议**：[来自报告]
- **参考链接**：[来自报告]
```

**修复优先级建议**：

按以下原则排序（所有依据必须来自报告数据）：
1. 已公开利用代码的漏洞（在 CISA KEV 中）
2. Critical 级别漏洞
3. High 级别漏洞（暴露在公网的服务优先）
4. Medium 及以下（计划修复周期内处理）

---

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| MCP Server 不可用 | 提示用户检查 MCP Server 连接，提供降级方案（直接调用 CLI）|
| 扫描任务失败 | 如实报告错误信息，不得猜测原因 |
| 报告为空 | 告知用户"未发现漏洞"或"报告数据为空"，注明来源 |
| 无权限访问 | 提示用户确认凭证配置 |

---

## 配置要求

在 `~/.hermes/.env` 或环境变量中配置：

```bash
# Nessus 配置（任选其一）
NESSUS_URL=https://your-nessus-server:8834
NESSUS_ACCESS_KEY=your-access-key
NESSUS_SECRET_KEY=your-secret-key

# OpenVAS 配置（任选其一）
OPENVAS_HOST=localhost
OPENVAS_PORT=9390
OPENVAS_USER=admin
OPENVAS_PASSWORD=your-password

# 或通过 MCP Server 连接（推荐）
# 详见 mcp/README.md
```
