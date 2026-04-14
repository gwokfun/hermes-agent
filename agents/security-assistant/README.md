# 信息安全助手（SecHermes）— 快速启动指南

## 简介

SecHermes 是基于 hermes-agent 构建的企业级信息安全助手智能体，提供以下核心能力：

- 🔍 **漏洞扫描管理**：启动扫描、查询进度、获取分析报告
- 📖 **内部文档答疑**：基于 Markdown 文档库回答安全相关问题
- 🔧 **安全产品自动修复**：异常检测后按 Runbook 发起审批并执行修复
- 🌐 **安全情报分析**：追踪 CVE/漏洞情报，结合内部软件清单评估影响

---

## 前置要求

1. 已安装并配置 hermes-agent（≥ v0.8.0）
2. 已配置 LLM 提供商（推荐 `anthropic/claude-opus-4.6`）
3. 可选：漏洞扫描 MCP Server、审批 API（用于自动修复功能）

---

## 安装步骤

### 1. 配置智能体身份

将 SOUL.md 路径加入配置，使 Hermes 使用安全助手的人格：

```bash
# 复制配置模板
cp agents/security-assistant/config/config.yaml.example cli-config.yaml

# 或手动在已有配置中添加：
hermes config set agent.soul_file "$(pwd)/agents/security-assistant/SOUL.md"
```

### 2. 安装技能

```bash
# 创建用户技能目录（如不存在）
mkdir -p ~/.hermes/skills

# 安装所有安全助手技能
cp -r agents/security-assistant/skills/vuln-scan ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-docs-qa ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-auto-fix ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-intel ~/.hermes/skills/

echo "技能安装完成"
```

### 3. 配置内部文档路径（sec-docs-qa 技能）

```bash
hermes config set security.docs_base_path "/path/to/your/internal/docs"
```

### 4. 配置 MCP 服务器（可选）

参考 `mcp/README.md` 配置漏洞扫描和审批 API 的 MCP 连接。

### 5. 验证安装

```bash
# 启动 Hermes
hermes

# 在会话中验证技能已加载
/skills

# 测试安全情报功能（无需外部依赖）
/sec-intel 查询 CVE-2024-21626 的影响
```

---

## 快速使用示例

### 漏洞扫描

```
/vuln-scan 对 192.168.1.0/24 执行例行漏洞扫描
```

```
/vuln-scan 查询扫描任务 SCAN-20240101-001 的进度
```

```
/vuln-scan 获取上周扫描报告并分析高危漏洞
```

### 文档答疑

```
/sec-docs-qa 我们的密码策略要求是什么？
```

```
/sec-docs-qa 如何处理数据泄露事件？
```

### 安全情报

```
/sec-intel 分析 CVE-2024-6387 对我们的 Linux 服务器的影响
```

```
/sec-intel 获取本周 CISA 已知被利用漏洞列表
```

### 自动修复（需审批）

```
/sec-auto-fix 防火墙服务异常，按 Runbook FW-001 执行修复
```

---

## 技能管控

**重要**：SecHermes 不允许自动生成技能。所有新技能必须由管理员审核并手动安装。

详见 `docs/ADMIN_GUIDE.md`。

---

## 目录说明

| 文件/目录 | 说明 |
|-----------|------|
| `SOUL.md` | 智能体身份、价值观和行为准则 |
| `AGENT.md` | 技术规格说明书 |
| `skills/` | 安全专属技能（需安装到 `~/.hermes/skills/`） |
| `mcp/` | MCP 服务器集成说明 |
| `config/` | 配置模板 |
| `docs/DEVELOPMENT.md` | 扩展开发指南（技能/MCP/插件） |
| `docs/ADMIN_GUIDE.md` | 管理员操作指南 |

---

## 获取帮助

- 查看完整开发文档：`docs/DEVELOPMENT.md`
- 管理员操作：`docs/ADMIN_GUIDE.md`
- MCP 集成：`mcp/README.md`
- hermes-agent 官方文档：https://hermes-agent.nousresearch.com/docs/
