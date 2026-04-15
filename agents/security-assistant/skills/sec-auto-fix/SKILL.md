---
name: sec-auto-fix
description: |
  安全产品服务异常自动修复技能。检测到安全产品（防火墙、WAF、IDS 等）异常后，
  按照预定义的操作手册（Runbook）通过企业审批 API 发起修复申请，
  审批通过后执行修复命令，并记录完整操作日志。
  所有修复操作必须经过审批，不得绕过。
version: 1.0.0
author: SecHermes
license: MIT
metadata:
  hermes:
    tags: [security, auto-fix, runbook, approval, remediation, incident-response]
    category: security
---

# 安全产品自动修复（Security Auto-Fix with Approval）

## 适用场景

- 安全产品服务异常（防火墙宕机、WAF 停止响应、IDS 告警失效）
- 基于监控告警触发的自动修复流程
- 按照操作手册执行标准化修复步骤

---

## ⚠️ 强制性安全规则

**以下规则不得在任何情况下绕过：**

1. **审批前禁止执行任何修复命令**。即使用户明确要求立即执行，也必须先通过审批 API。
2. **严格按照 Runbook 执行**，不得擅自修改操作步骤或参数。
3. **每一步操作必须记录日志**（操作人、时间、命令、结果）。
4. **执行失败时立即停止**，不得尝试替代方案，报告失败并等待人工介入。
5. **禁止删除日志**或修改操作记录。

---

## 工作流程

### 阶段 0：异常识别

明确以下信息（通过用户输入或监控告警）：
- 异常的安全产品/服务名称
- 异常现象描述
- 告警时间
- 对应的 Runbook 编号（如 `FW-001`）

如果 Runbook 编号未知，在内部文档中查找：

```bash
grep -r "Runbook\|runbook\|操作手册" "${SEC_DOCS_BASE_PATH:-/opt/sec-docs}/runbooks/" -l
```

### 阶段 1：加载 Runbook

从内部文档目录读取操作手册：

```bash
cat "${SEC_DOCS_BASE_PATH:-/opt/sec-docs}/runbooks/<RUNBOOK_ID>.md"
```

**验证 Runbook**：
- 确认 Runbook 适用于当前异常场景
- 记录 Runbook 版本和最后更新时间
- 如果 Runbook 不存在，**停止流程并通知用户**

### 阶段 2：影响评估

在申请审批前，向用户呈现影响评估：

```markdown
## 修复操作影响评估

**异常服务**：{服务名称}
**Runbook**：{Runbook ID} - {Runbook 标题}
**操作步骤数**：{N} 步
**预计影响**：{来自 Runbook 的影响说明}
**预计耗时**：{来自 Runbook}
**可回滚**：是/否

**操作步骤预览**：
1. {步骤 1 简述}
2. {步骤 2 简述}
...
```

### 阶段 3：发起审批申请

通过审批 MCP Server 或 API 发起申请：

```python
# 通过 MCP Server 发起审批（推荐）
result = mcp_call("approval-api", "request_approval", {
    "title": f"安全产品修复：{服务名称}",
    "description": f"按照 Runbook {RUNBOOK_ID} 修复 {服务名称} 异常",
    "runbook_id": "<RUNBOOK_ID>",
    "target_service": "<服务名称>",
    "impact": "<影响说明>",
    "requester": "sec-hermes-agent",
    "urgency": "high"  # normal / high / critical
})
approval_ticket = result["ticket_id"]
```

**替代方案**（直接调用审批 API）：

```bash
curl -s -X POST "${APPROVAL_API_URL}/requests" \
  -H "Authorization: Bearer ${APPROVAL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "安全产品修复申请",
    "runbook_id": "<RUNBOOK_ID>",
    "requester": "sec-hermes-agent",
    "details": "<详情>"
  }'
```

向用户报告：审批工单号、审批流程链接、预计审批时间。

### 阶段 4：等待审批结果

轮询审批状态（每 60 秒检查一次，最多等待 30 分钟）：

```python
result = mcp_call("approval-api", "get_approval_status", {
    "ticket_id": approval_ticket
})
# 状态：pending / approved / rejected / expired
```

- **approved**：进入阶段 5 执行
- **rejected**：记录拒绝原因，停止流程，通知用户
- **expired**：通知用户重新发起申请
- **pending**：继续等待，定期向用户更新状态

### 阶段 5：执行修复

审批通过后，**严格按照 Runbook 步骤顺序执行**：

```python
# 记录执行开始
log_entry = {
    "ticket_id": approval_ticket,
    "runbook_id": RUNBOOK_ID,
    "executor": "sec-hermes-agent",
    "start_time": current_timestamp(),
    "steps": []
}

# 逐步执行（不跳过任何步骤）
for step in runbook.steps:
    result = terminal(command=step.command, timeout=step.timeout)
    log_entry["steps"].append({
        "step": step.id,
        "command": step.command,
        "output": result.output,
        "exit_code": result.exit_code,
        "timestamp": current_timestamp()
    })
    
    if result.exit_code != 0:
        # 执行失败：立即停止，记录日志，通知用户
        log_failure_and_stop(step, result, log_entry)
        break
```

**每步执行前**，向用户报告："正在执行步骤 N：{步骤描述}"。

### 阶段 6：验证修复结果

执行 Runbook 中定义的验证步骤（如有）：

```bash
# 示例验证：检查服务状态
systemctl status <service_name>
curl -s -o /dev/null -w "%{http_code}" http://localhost/health
```

### 阶段 7：汇报结果

```markdown
## 修复操作完成报告

**审批工单**：{ticket_id}
**Runbook**：{RUNBOOK_ID}
**执行时间**：{开始时间} → {结束时间}
**执行结果**：✅ 成功 / ❌ 失败（步骤 N）

### 执行步骤记录

| 步骤 | 操作 | 结果 | 时间 |
|------|------|------|------|
| 1 | {步骤描述} | 成功 | {时间} |
| 2 | {步骤描述} | 成功 | {时间} |

### 服务验证

{验证步骤输出}

*操作日志已保存至：{日志路径}*
```

---

## 配置要求

```bash
# 审批 API 配置
APPROVAL_API_URL=https://your-approval-system/api/v1
APPROVAL_API_TOKEN=your-api-token

# 内部文档目录（包含 Runbooks）
SEC_DOCS_BASE_PATH=/opt/sec-docs
```

或通过 MCP Server（推荐，详见 `mcp/README.md`）：

```yaml
mcp:
  servers:
    - name: approval-api
      command: "python -m approval_mcp_server"
      env:
        APPROVAL_API_URL: "${APPROVAL_API_URL}"
        APPROVAL_API_TOKEN: "${APPROVAL_API_TOKEN}"
```
