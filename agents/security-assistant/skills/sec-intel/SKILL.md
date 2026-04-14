---
name: sec-intel
description: |
  安全情报获取与分析技能。从 CVE 数据库、NVD、CISA KEV 等权威来源获取漏洞情报，
  分析漏洞可利用性，结合内部软件/资产清单评估影响范围，生成结构化情报报告。
  所有情报必须注明来源，不得推测或捏造。
version: 1.0.0
author: SecHermes
license: MIT
metadata:
  hermes:
    tags: [security, intelligence, cve, nvd, cisa, threat-analysis, patch-management]
    category: security
---

# 安全情报分析（Security Intelligence Analysis）

## 适用场景

- 查询特定 CVE 的详情和可利用性
- 获取 CISA 已知被利用漏洞（KEV）列表
- 分析新发布的安全漏洞对内部环境的影响
- 定期安全情报摘要（周报/月报）

---

## ⚠️ 情报准确性规则

1. **所有 CVE 信息必须来自 NVD 或官方来源**，禁止凭记忆描述漏洞细节。
2. **可利用性评估必须基于 CVSS 分数和 CISA KEV 状态**，不得主观判断。
3. **内部影响评估必须基于实际资产/软件清单**，不得假设环境。
4. 情报报告中区分：已确认事实（来自数据源）vs 推断内容（需标注 `[推断]`）。
5. 如果某个 CVE 在 NVD 中不存在或信息不完整，明确说明而非补全。

---

## 工作流程

### 步骤 1：确定情报需求

| 需求类型 | 关键词示例 |
|---------|-----------|
| 特定 CVE 查询 | "查询 CVE-2024-xxxxx"、"CVE-xxxx 是什么" |
| CISA KEV 查询 | "CISA KEV"、"已知被利用漏洞"、"在野利用" |
| 软件/产品漏洞 | "OpenSSH 漏洞"、"Log4j 影响"、"Windows 最新补丁" |
| 定期情报摘要 | "本周漏洞"、"高危漏洞周报"、"最新安全公告" |

### 步骤 2：从权威来源获取情报

#### 查询 NVD（CVE 详情）

```bash
# 查询特定 CVE
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-XXXXX" \
  | python3 -m json.tool

# 查询近期高危 CVE（CVSS ≥ 9.0）
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cvssV3Severity=CRITICAL&resultsPerPage=20" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('vulnerabilities', []):
    cve = item['cve']
    cve_id = cve['id']
    desc = next((d['value'] for d in cve.get('descriptions', []) if d['lang'] == 'en'), 'N/A')
    metrics = cve.get('metrics', {})
    cvss = metrics.get('cvssMetricV31', [{}])[0].get('cvssData', {}).get('baseScore', 'N/A')
    print(f'[{cve_id}] CVSS: {cvss}')
    print(f'  {desc[:200]}')
    print()
"
```

#### 查询 CISA KEV（已知被利用漏洞）

```bash
# 获取完整 KEV 列表（JSON）
curl -s "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
vulns = data.get('vulnerabilities', [])
# 显示最新 20 条
for v in sorted(vulns, key=lambda x: x.get('dateAdded', ''), reverse=True)[:20]:
    print(f\"[{v['cveID']}] {v['vulnerabilityName']}\")
    print(f\"  Product: {v['product']} ({v['vendor']})\")
    print(f\"  Added: {v['dateAdded']} | Due: {v['dueDate']}\")
    print(f\"  Action: {v['requiredAction']}\")
    print()
"

# 检查特定 CVE 是否在 KEV 中
curl -s "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" \
  | python3 -c "
import sys, json
cve_id = 'CVE-2024-XXXXX'
data = json.load(sys.stdin)
found = [v for v in data.get('vulnerabilities', []) if v['cveID'] == cve_id]
if found:
    print(f'⚠️  {cve_id} 在 CISA KEV 中（已知被积极利用）')
    print(json.dumps(found[0], indent=2, ensure_ascii=False))
else:
    print(f'✅ {cve_id} 不在 CISA KEV 中（截止查询时）')
"
```

#### 使用 web_extract 获取官方安全公告

```python
# 厂商安全公告（按需选择）
web_extract(urls=[
    "https://www.microsoft.com/en-us/msrc/security-update-guide",
    "https://access.redhat.com/security/security-updates/",
    "https://ubuntu.com/security/notices",
    "https://support.apple.com/en-us/HT201222"
])
```

### 步骤 3：内部影响评估

**获取内部软件/资产清单**（通过 MCP Server 或文件）：

```python
# 通过 MCP Server 查询资产清单
result = mcp_call("asset-inventory", "list_installed_software", {
    "filters": {"package_name": "<受影响软件名称>"}
})

# 或读取本地维护的软件清单文件
cat "${SEC_DOCS_BASE_PATH:-/opt/sec-docs}/assets/software-inventory.json"
```

**评估框架**：

| 影响状态 | 判断标准 |
|---------|---------|
| ✅ 不受影响 | 内部未安装该软件，或已安装版本不在受影响范围 |
| ⚠️ 可能受影响（待确认） | 内部有相关软件但版本信息不完整 |
| 🔴 确认受影响 | 内部安装版本明确在受影响范围内 |

### 步骤 4：生成情报报告

**单个 CVE 分析报告格式**：

```markdown
# 安全情报分析报告

**CVE 编号**：CVE-XXXX-XXXXX
**报告时间**：{当前时间}
**数据来源**：NVD API、CISA KEV

---

## 漏洞概览

| 字段 | 详情 |
|------|------|
| 漏洞名称 | {来自 NVD} |
| 影响产品 | {来自 NVD} |
| CVSS 分数 | {来自 NVD}（{严重等级}）|
| 发布时间 | {来自 NVD} |
| CISA KEV 状态 | 是/否（添加日期：{日期}）|
| PoC/Exploit 状态 | 公开 PoC（来源：{链接}）/ 无已知公开利用代码 |

## 漏洞描述

{直接引用 NVD 的英文描述，附中文摘要}

## 可利用性分析

**CVSS 向量**：{完整 CVSS 向量字符串}

| 维度 | 评分 | 说明 |
|------|------|------|
| 攻击向量 | Network/Adjacent/Local/Physical | {说明} |
| 攻击复杂度 | Low/High | {说明} |
| 所需权限 | None/Low/High | {说明} |
| 用户交互 | None/Required | {说明} |

**是否在 CISA KEV**：{'是，说明漏洞已被威胁行为者积极利用' if KEV else '否'}

## 内部影响评估

**受影响系统**：
| 主机名/IP | 软件版本 | 影响状态 |
|-----------|---------|---------|
| {来自资产清单} | {来自清单} | 🔴 确认受影响 |

**未安装该软件的环境**：[推断] 不受影响（需通过资产清单确认）

## 修复建议

{直接引用 NVD 或厂商建议，注明来源}

**补丁链接**：{来自 NVD 或厂商公告}
**临时缓解措施**：{如有，来自厂商建议}

## 参考资料

- NVD：https://nvd.nist.gov/vuln/detail/{CVE_ID}
- CISA KEV：https://www.cisa.gov/known-exploited-vulnerabilities-catalog
- {其他参考链接}
```

---

## 定期情报摘要工作流

```bash
# 1. 获取本周 CISA KEV 新增条目
LAST_WEEK=$(date -d "7 days ago" +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)
curl -s "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json" \
  | python3 -c "
import sys, json
from datetime import datetime, timedelta
data = json.load(sys.stdin)
cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
new_vulns = [v for v in data.get('vulnerabilities', []) if v.get('dateAdded', '') >= cutoff]
print(f'本周 CISA KEV 新增：{len(new_vulns)} 条')
for v in new_vulns:
    print(f\"  [{v['cveID']}] {v['vulnerabilityName']} - Due: {v['dueDate']}\")
"

# 2. 获取本周 NVD Critical 级漏洞
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cvssV3Severity=CRITICAL&resultsPerPage=10" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for item in data.get('vulnerabilities', []):
    cve = item['cve']
    print(f\"[{cve['id']}] {next((d['value'] for d in cve.get('descriptions',[]) if d['lang']=='en'), '')[:150]}\")
"
```

---

## 配置要求

```bash
# 可选：资产清单 MCP Server
# 详见 mcp/README.md

# NVD API Key（提高速率限制，无 key 时也可使用但限速）
NVD_API_KEY=your-nvd-api-key   # 注册：https://nvd.nist.gov/developers/request-an-api-key
```

NVD API Key 配置（有 key 时速率限制从 5 次/30秒 提升到 50 次/30秒）：

```bash
# 带 API Key 的请求
curl -s "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-XXXXX" \
  -H "apiKey: ${NVD_API_KEY}"
```
