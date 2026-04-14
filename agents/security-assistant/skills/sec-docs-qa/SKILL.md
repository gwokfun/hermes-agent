---
name: sec-docs-qa
description: |
  基于企业内部安全文档（Markdown 格式）进行答疑。从指定文档目录中检索相关内容，
  严格依据文档内容回答问题，不得凭借模型记忆作答。
  支持安全策略、操作规程、合规要求、安全事件处置等文档的查询。
version: 1.0.0
author: SecHermes
license: MIT
metadata:
  hermes:
    tags: [security, documentation, qa, knowledge-base, policy, compliance]
    category: security
---

# 内部安全文档答疑（Security Docs Q&A）

## 适用场景

- 业务侧询问安全策略、合规要求、操作规程
- 询问安全事件处置流程
- 查询特定系统的安全配置要求
- 了解数据分类、访问控制等安全规定

---

## ⚠️ 核心规则：必须基于文档内容作答

**本技能严禁使用模型内部知识回答问题**。所有答案必须来自检索到的文档内容。

- ✅ 允许：引用文档中的原文或对原文的忠实转述
- ✅ 允许：综合多份文档的相关章节给出答案
- ❌ 禁止：基于"通常情况下"、"一般认为"等模糊表述作答
- ❌ 禁止：在文档未涉及的领域给出推断性答案
- ❌ 禁止：混合文档内容与模型记忆

---

## 工作流程

### 步骤 1：理解问题

分析用户问题，提取以下要素：
- 主题领域（如：密码策略、数据分类、访问控制、事件响应）
- 具体系统/服务（如有）
- 问题类型（策略要求/操作步骤/合规条款）

### 步骤 2：定位文档目录

从配置中获取文档根目录（`security.docs_base_path`），默认为 `/opt/sec-docs`：

```bash
# 列出文档目录结构
find "${DOCS_BASE_PATH:-/opt/sec-docs}" -name "*.md" | head -50
```

如果文档目录不存在或为空，**立即告知用户**："未找到内部文档目录，请确认文档路径配置。"

### 步骤 3：搜索相关文档

使用文件搜索工具查找相关内容：

```bash
# 在文档目录中搜索相关关键词
grep -r -l "<关键词>" "${DOCS_BASE_PATH:-/opt/sec-docs}" --include="*.md"

# 读取相关文档的内容
cat "${DOCS_BASE_PATH:-/opt/sec-docs}/<文档路径>"
```

使用 Hermes 的 `file_search` 工具进行语义匹配（如可用）。

### 步骤 4：提取相关章节

阅读匹配文档，定位与问题直接相关的章节。评估相关性时：
- 确认文档标题和章节与问题主题匹配
- 确认内容适用于用户询问的场景
- 如有多份文档，判断哪份更权威/更新

### 步骤 5：构建回答

**回答格式**（必须包含以下结构）：

```markdown
## 答案

[基于文档的直接回答，简洁明确]

## 依据

**文档来源**：{文档名称}，章节：{章节标题}

> [文档原文引用]

## 补充说明（如有）

[如有多份相关文档或补充说明]

---
*注：以上内容来自内部安全文档 {文档名称}，最后更新时间 {文档时间戳（如可获取）}。*
```

### 步骤 6：处理未找到的情况

如果搜索后未找到相关文档内容：

```markdown
## 未找到相关内容

在当前内部安全文档库中，未找到关于"{问题主题}"的相关文档。

**建议您**：
1. 联系信息安全团队获取最新政策文件
2. 查阅 [其他可能的权威来源]
3. 如果这是紧急需求，请通过安全工单系统提交查询

*搜索范围：{DOCS_BASE_PATH}*
*搜索时间：{当前时间}*
```

**不得**在未找到文档内容时凭经验或模型知识作答。

---

## 文档目录约定

推荐的内部文档组织结构（如需自定义，更新 `security.docs_base_path`）：

```
/opt/sec-docs/
├── policies/               # 安全策略文件
│   ├── password-policy.md
│   ├── access-control-policy.md
│   └── data-classification-policy.md
├── procedures/             # 操作规程
│   ├── incident-response.md
│   ├── vulnerability-management.md
│   └── change-management.md
├── runbooks/               # 技术操作手册（供 sec-auto-fix 技能使用）
│   ├── FW-001-firewall-restart.md
│   └── WAF-001-waf-recovery.md
├── compliance/             # 合规要求
│   ├── gdpr-requirements.md
│   └── iso27001-controls.md
└── architecture/           # 安全架构文档
    └── network-security-zones.md
```

---

## 配置

在 `cli-config.yaml` 中设置文档目录：

```yaml
security:
  docs_base_path: "/opt/sec-docs"   # 内部安全文档根目录
```

或通过环境变量：

```bash
export SEC_DOCS_BASE_PATH="/opt/sec-docs"
```
