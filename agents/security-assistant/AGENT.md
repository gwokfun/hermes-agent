# 信息安全助手智能体 — AGENT.md

## 概述

本文件是**信息安全助手（SecHermes）**的技术规格说明书。该智能体基于 [hermes-agent](https://github.com/NousResearch/hermes-agent) 底座构建，通过 Skill、MCP Server 和配置文件进行扩展，**不修改核心源码**。

---

## 能力矩阵

| 能力 | 实现方式 | 技能/工具文件 |
|------|---------|--------------|
| 漏洞扫描管理（启动、查询、报告） | Skill + MCP | `skills/vuln-scan/SKILL.md` |
| 内部文档答疑 | Skill + 文件工具 | `skills/sec-docs-qa/SKILL.md` |
| 安全产品自动修复（含审批） | Skill + MCP（审批 API） | `skills/sec-auto-fix/SKILL.md` |
| 安全资讯情报分析 | Skill + Web 工具 | `skills/sec-intel/SKILL.md` |

---

## 架构图

```
┌─────────────────────────────────────────────────────┐
│                  用户 / 业务侧                        │
│         (CLI / Telegram / Slack / Web)              │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│               Hermes Agent Core                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  SOUL.md    │  │  AGENT.md    │  │  config    │ │
│  │ (身份/行为) │  │  (技术规格)  │  │  .yaml     │ │
│  └─────────────┘  └──────────────┘  └────────────┘ │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │              已启用的技能（Skills）            │   │
│  │  vuln-scan │ sec-docs-qa │ sec-auto-fix      │   │
│  │  sec-intel                                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │            Hermes 核心工具集                  │   │
│  │  terminal │ file │ web │ mcp_client          │   │
│  └──────────────────────────────────────────────┘   │
└──────────────────────┬──────────────────────────────┘
                       │ MCP / API 调用
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌─────▼──────┐ ┌───▼──────────┐
│  漏洞扫描    │ │  审批 API  │ │  CVE/NVD    │
│  MCP Server  │ │  (远程审批) │ │  数据源      │
│  (OpenVAS/  │ │            │ │  (MCP/HTTP) │
│   Nessus/   │ └────────────┘ └─────────────┘
│   自研)     │
└─────────────┘
```

---

## 目录结构

```
agents/security-assistant/
├── SOUL.md                      # 智能体身份、价值观与行为准则
├── AGENT.md                     # 技术规格（本文件）
├── README.md                    # 快速启动指南
├── skills/                      # 安全专属技能
│   ├── vuln-scan/
│   │   └── SKILL.md             # 漏洞扫描工作流
│   ├── sec-docs-qa/
│   │   └── SKILL.md             # 内部文档答疑工作流
│   ├── sec-auto-fix/
│   │   └── SKILL.md             # 自动修复工作流（含审批）
│   └── sec-intel/
│       └── SKILL.md             # 安全情报分析工作流
├── mcp/
│   └── README.md                # MCP 服务器集成说明
├── config/
│   └── config.yaml.example      # 智能体配置模板
└── docs/
    ├── DEVELOPMENT.md           # 扩展开发指南
    └── ADMIN_GUIDE.md           # 管理员操作指南
```

---

## 部署要求

### 最低运行环境

| 组件 | 要求 |
|------|------|
| hermes-agent | ≥ v0.8.0 |
| Python | ≥ 3.11 |
| LLM 提供商 | Anthropic Claude / OpenRouter（推荐 claude-opus-4.6） |
| 网络访问 | 需访问 NVD / CISA KEV API（可配置代理） |

### 可选组件（按能力）

| 能力 | 依赖 |
|------|------|
| 漏洞扫描 | 漏洞扫描 MCP Server（支持 OpenVAS / Nessus / 自研） |
| 自动修复 | 审批 API（企业内部审批系统） |
| 内部文档答疑 | 内部文档目录（Markdown 格式） |

---

## 技能加载方式

安全助手的技能需手动复制到 Hermes 的用户技能目录后才会激活：

```bash
# 将技能复制到 Hermes 用户技能目录
cp -r agents/security-assistant/skills/vuln-scan ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-docs-qa ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-auto-fix ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-intel ~/.hermes/skills/
```

复制后，在 Hermes 会话中使用 `/skills` 命令确认技能已加载，或直接调用：

```
/vuln-scan
/sec-docs-qa
/sec-auto-fix
/sec-intel
```

---

## 技能管控策略

### 自动生成技能的限制

根据 `SOUL.md` 中的行为准则，**SecHermes 不允许自动生成技能**。所有技能必须经管理员审核后才能安装。

实现方式：
1. 在 `config.yaml` 中配置 `agent.auto_skill_creation: false`（详见 `config/config.yaml.example`）
2. 使用 Hermes 内置的技能审批机制（`tools/skills_guard.py`）
3. 管理员工作流详见 `docs/ADMIN_GUIDE.md`

---

## MCP 服务器集成

通过 MCP（Model Context Protocol）协议连接外部工具，无需修改核心代码。详见 `mcp/README.md`。

核心 MCP 集成点：
- **漏洞扫描 MCP Server**：封装 OpenVAS/Nessus API，提供标准化的扫描管理工具
- **审批 MCP Server**：封装企业审批系统 API，提供 `request_approval` / `check_approval_status` 工具
- **资产清单 MCP Server**（可选）：提供 `list_installed_software` 工具，支持漏洞影响范围分析

---

## 配置要点

关键配置项（详见 `config/config.yaml.example`）：

```yaml
model:
  default: "anthropic/claude-opus-4.6"

agent:
  soul_file: "agents/security-assistant/SOUL.md"
  auto_skill_creation: false      # 禁止智能体自动生成技能

security:
  approval_required: true         # 修复操作必须审批
  docs_base_path: "/opt/sec-docs" # 内部安全文档根目录
```
