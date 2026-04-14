# SecHermes 管理员操作指南

本文档面向信息安全助手（SecHermes）的管理员，涵盖技能管控、权限配置、系统审计等操作。

---

## 目录

1. [角色与权限模型](#1-角色与权限模型)
2. [技能管控操作](#2-技能管控操作)
3. [审批 API 管理](#3-审批-api-管理)
4. [系统配置管理](#4-系统配置管理)
5. [日志与审计](#5-日志与审计)
6. [故障处理](#6-故障处理)

---

## 1. 角色与权限模型

SecHermes 定义两种角色：

| 角色 | 权限 |
|------|------|
| **管理员（Admin）** | 审核/安装/删除技能；配置 MCP Server；查看审计日志；管理审批规则 |
| **普通用户（User）** | 使用已安装的技能；发起扫描、情报查询；通过审批发起修复 |

**关键限制**：普通用户**不得**安装新技能，所有技能安装必须经管理员审核。

---

## 2. 技能管控操作

### 2.1 技能安装原则

- **所有技能安装必须由管理员执行**，不允许用户自行安装
- 安装前必须完成安全审查（见 2.3）
- 安装后记录到技能清单（见 2.4）

### 2.2 安装官方技能

```bash
# 安装 SecHermes 随附的安全技能
sudo -u hermes-agent cp -r /opt/sechermes/agents/security-assistant/skills/vuln-scan \
    /opt/sechermes/.hermes/skills/

sudo -u hermes-agent cp -r /opt/sechermes/agents/security-assistant/skills/sec-docs-qa \
    /opt/sechermes/.hermes/skills/

sudo -u hermes-agent cp -r /opt/sechermes/agents/security-assistant/skills/sec-auto-fix \
    /opt/sechermes/.hermes/skills/

sudo -u hermes-agent cp -r /opt/sechermes/agents/security-assistant/skills/sec-intel \
    /opt/sechermes/.hermes/skills/
```

### 2.3 新技能安全审查清单

管理员在安装任何新技能之前，必须完成以下检查：

#### 内容审查（手动）

- [ ] 阅读完整的 `SKILL.md` 文件
- [ ] 确认技能描述与实际操作一致（无误导性描述）
- [ ] 确认技能遵守 `SOUL.md` 中的行为准则
- [ ] 检查是否有绕过审批机制的步骤
- [ ] 检查是否有可能导致信息捏造的指令
- [ ] 检查所有外部 URL 是否为可信来源

#### 脚本文件审查（如有）

- [ ] 检查 `scripts/` 中的所有脚本文件
- [ ] 确认无命令注入风险
- [ ] 确认无网络外联到未知地址
- [ ] 确认无凭证硬编码

#### 自动扫描

hermes-agent 内置的技能守卫提供自动扫描：

```bash
# 激活虚拟环境
source /opt/hermes-agent/venv/bin/activate

# 手动调用技能守卫扫描（在 Python 中执行）
python3 << 'EOF'
from tools.skills_guard import scan_skill, format_scan_report
from pathlib import Path

skill_dir = Path("/tmp/new-skill-to-review")
result = scan_skill(skill_dir, source="community")
print(format_scan_report(result))
print(f"\n允许安装: {result.verdict}")
EOF
```

扫描结果解读：
- `safe`：可以安装
- `caution`：需要管理员人工复核后决定
- `dangerous`：拒绝安装，向提交者说明原因

### 2.4 技能清单管理

维护已安装技能的记录文件（建议存放在 `/opt/sechermes/skill-inventory.md`）：

```markdown
# SecHermes 已安装技能清单

最后更新：YYYY-MM-DD

| 技能名称 | 版本 | 安装时间 | 审核人 | 安全扫描结果 | 备注 |
|---------|------|---------|--------|------------|------|
| vuln-scan | 1.0.0 | 2024-01-01 | admin | safe | 官方随附 |
| sec-docs-qa | 1.0.0 | 2024-01-01 | admin | safe | 官方随附 |
| sec-auto-fix | 1.0.0 | 2024-01-01 | admin | safe | 官方随附 |
| sec-intel | 1.0.0 | 2024-01-01 | admin | safe | 官方随附 |
```

### 2.5 禁用/卸载技能

```bash
# 临时禁用（移到备份目录）
sudo -u hermes-agent mv ~/.hermes/skills/problematic-skill \
    ~/.hermes/skills/.disabled/problematic-skill

# 永久卸载
sudo -u hermes-agent rm -rf ~/.hermes/skills/problematic-skill

# 记录操作
echo "$(date): 卸载技能 problematic-skill，原因：xxx，操作人：admin" >> /var/log/sechermes/admin.log
```

### 2.6 阻止智能体自动创建技能

hermes-agent 的技能管理工具（`skill_manager_tool`）允许智能体创建技能。对于 SecHermes，必须通过以下方式阻止：

**方式 1：在 SOUL.md 中明确禁止**（已实现）

SOUL.md 已包含"禁止自动生成技能"的行为准则。

**方式 2：通过工具配置禁用技能管理工具**

在 `cli-config.yaml` 中：

```yaml
tools:
  disabled:
    - skill_manager  # 禁用技能管理工具
```

**方式 3：系统级文件权限控制**

```bash
# 将技能目录权限设为只读（智能体运行用户无写权限）
chmod 555 ~/.hermes/skills/
# 只有管理员才能临时赋予写权限安装新技能
```

---

## 3. 审批 API 管理

### 3.1 配置审批 API

将 API 凭证安全地配置在环境变量中：

```bash
# 在 .hermes/.env 中配置（不提交到版本控制）
echo "APPROVAL_API_URL=https://your-approval-system/api/v1" >> ~/.hermes/.env
echo "APPROVAL_API_TOKEN=your-secure-token" >> ~/.hermes/.env
chmod 600 ~/.hermes/.env
```

### 3.2 审批规则配置

在企业审批系统中配置以下规则（具体步骤依审批系统而异）：

| 操作类型 | 审批级别 | 审批人 | 超时 |
|---------|---------|-------|------|
| 服务重启 | L1（单人审批）| 安全工程师 | 30分钟 |
| 配置修改 | L2（双人审批）| 安全主管 | 60分钟 |
| 删除操作 | L3（团队审批）| 安全团队 | 2小时 |

### 3.3 测试审批流程

```bash
# 测试审批 API 连通性
curl -s "${APPROVAL_API_URL}/health" \
  -H "Authorization: Bearer ${APPROVAL_API_TOKEN}"

# 发起测试审批申请
curl -s -X POST "${APPROVAL_API_URL}/requests" \
  -H "Authorization: Bearer ${APPROVAL_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"title": "测试申请", "runbook_id": "TEST-001", "requester": "admin-test"}'
```

---

## 4. 系统配置管理

### 4.1 关键配置检查清单

定期（至少每月）检查以下配置：

- [ ] SOUL.md 内容是否需要更新
- [ ] 已安装技能是否需要版本更新
- [ ] MCP Server 凭证是否需要轮换
- [ ] 审批 API Token 是否过期
- [ ] 内部文档目录是否有新文件加入

### 4.2 文档目录同步

```bash
# 同步内部安全文档到 SecHermes 文档目录
rsync -avz --delete \
  /path/to/internal-security-wiki/ \
  /opt/sec-docs/

# 设置正确权限（只读，智能体可读）
chmod -R 444 /opt/sec-docs/
chown -R sechermes-agent:security /opt/sec-docs/
```

### 4.3 MCP Server 健康检查

```bash
#!/bin/bash
# /opt/sechermes/scripts/check-mcp-health.sh

echo "检查 MCP Server 状态..."

# 检查漏洞扫描 MCP Server
if python -m vuln_scanner_mcp --health-check 2>/dev/null; then
    echo "✅ vuln-scanner MCP: 正常"
else
    echo "❌ vuln-scanner MCP: 异常"
fi

# 检查审批 API 连通性
STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
  "${APPROVAL_API_URL}/health" \
  -H "Authorization: Bearer ${APPROVAL_API_TOKEN}")
if [ "$STATUS" = "200" ]; then
    echo "✅ approval-api: 正常"
else
    echo "❌ approval-api: 异常（HTTP $STATUS）"
fi
```

---

## 5. 日志与审计

### 5.1 关键事件日志

需要记录的关键事件：

| 事件类型 | 日志级别 | 保留期限 |
|---------|---------|---------|
| 技能安装/卸载 | INFO | 1年 |
| 修复操作（含审批状态）| INFO | 2年 |
| 审批拒绝 | WARN | 1年 |
| MCP Server 错误 | ERROR | 6个月 |
| 未授权操作尝试 | CRITICAL | 3年 |

### 5.2 日志目录结构

```
/var/log/sechermes/
├── admin.log          # 管理员操作记录
├── auto-fix.log       # 自动修复操作记录（含审批）
├── scan.log           # 扫描任务记录
└── agent.log          # 智能体运行日志
```

### 5.3 定期审计

每月审计项目：

```bash
#!/bin/bash
# 生成月度审计摘要

MONTH=$(date +%Y-%m)
echo "=== SecHermes 月度审计报告 ${MONTH} ==="

echo "## 已安装技能"
ls ~/.hermes/skills/ 2>/dev/null

echo "## 本月修复操作"
grep "${MONTH}" /var/log/sechermes/auto-fix.log 2>/dev/null | grep -c "执行完成"

echo "## 本月审批拒绝"
grep "${MONTH}" /var/log/sechermes/auto-fix.log 2>/dev/null | grep -c "rejected"

echo "## 未授权操作尝试"
grep "${MONTH}" /var/log/sechermes/agent.log 2>/dev/null | grep -c "UNAUTHORIZED"
```

---

## 6. 故障处理

### 6.1 MCP Server 连接失败

**现象**：智能体报告"工具 xxx 不可用"或 MCP 调用失败

**处理步骤**：

1. 检查 MCP Server 进程状态
2. 检查凭证配置是否正确（`~/.hermes/.env`）
3. 手动测试连接（见 4.3 健康检查）
4. 查看 MCP Server 日志
5. 必要时重启 MCP Server

```bash
# 重启 MCP Server（stdio 模式由 hermes 管理，重启 hermes 即可）
# 对于 SSE 模式的独立 MCP Server
systemctl restart vuln-scanner-mcp
```

### 6.2 审批 API 不可用

**现象**：修复请求无法提交，审批 API 返回错误

**处理步骤**：

1. 检查 API 服务状态
2. 检查 Token 是否过期
3. 通知用户暂时停止自动修复操作
4. 修复 API 服务后重新验证

**临时措施**：如需紧急修复，由人工直接按 Runbook 操作，记录操作日志。

### 6.3 技能行为异常

**现象**：智能体的回答与技能预期不符

**处理步骤**：

1. 确认 SOUL.md 已正确加载
2. 检查技能文件是否被意外修改
3. 对比技能文件与版本控制中的内容
4. 必要时重新安装技能
5. 记录异常情况供分析

```bash
# 检查技能文件完整性
sha256sum ~/.hermes/skills/vuln-scan/SKILL.md
# 对比期望的哈希值（需提前建立基线）
```

---

## 紧急联系

| 情况 | 联系方式 |
|------|---------|
| 疑似安全事件 | 安全团队 on-call |
| 审批系统故障 | IT 运维 |
| 智能体行为异常 | 安全助手管理员组 |
