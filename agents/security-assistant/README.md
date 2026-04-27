# 信息安全助手（SecHermes）

> 基于 [hermes-agent](https://github.com/NousResearch/hermes-agent) 构建的企业级安全智能体，
> 记忆系统采用 [OpenViking](https://github.com/volcengine/openviking) 上下文数据库。

---

## 架构概览

```
┌──────────────────────────────────────────────────────────────┐
│                       用户交互层                              │
│          CLI  ·  Telegram  ·  Slack  ·  Discord              │
└─────────────────────────┬────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────┐
│                   Hermes Agent Core                           │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ SOUL.md  │ │ AGENT.md │ │ config   │ │  OpenViking    │  │
│  │ 身份行为 │ │ 技术规格 │ │  .yaml   │ │  记忆系统      │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────┬─────────┘  │
│                                                 │            │
│  ┌──────────────────────────────────────────────┴────────┐   │
│  │  viking_search · viking_read · viking_browse          │   │
│  │  viking_remember · viking_add_resource                │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  安全技能 Skills                                       │   │
│  │  /vuln-scan  /sec-docs-qa  /sec-auto-fix  /sec-intel  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │  核心工具集 terminal · file · web · mcp_client        │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────┬───────────────────────────────────────────────┘
               │ MCP / API
     ┌─────────┼────────────┬────────────┐
     ▼         ▼            ▼            ▼
 ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
 │ 漏洞   │ │ 审批   │ │ CVE /  │ │OpenViking│
 │ 扫描器 │ │ API    │ │ NVD    │ │  Server  │
 │ MCP    │ │        │ │ CISA   │ │ :1933    │
 └────────┘ └────────┘ └────────┘ └──────────┘
```

---

## 核心能力

| 能力 | 技能 | 说明 |
|------|------|------|
| 🔍 **漏洞扫描管理** | `/vuln-scan` | 启动扫描、查询进度、获取分析报告 |
| 📖 **内部文档答疑** | `/sec-docs-qa` | 基于 Markdown 文档库回答安全相关问题 |
| 🔧 **安全产品修复** | `/sec-auto-fix` | 异常检测 → Runbook → 审批 → 执行修复 |
| 🌐 **安全情报分析** | `/sec-intel` | 追踪 CVE/漏洞情报，结合资产清单评估影响 |
| 🧠 **长期记忆** | OpenViking | 自动提取 6 类记忆，语义检索，分层加载 |

---

## 记忆系统：OpenViking

SecHermes 采用 **OpenViking** 作为记忆后端，替代默认的 MEMORY.md 文件存储，
提供以下增强能力：

### 为什么选择 OpenViking

| 特性 | 默认 MEMORY.md | OpenViking |
|------|----------------|------------|
| 存储方式 | 纯文本文件 | 结构化数据库 + 向量索引 |
| 检索方式 | 全文匹配 | 语义搜索（embedding） |
| 容量 | 受上下文窗口限制 | 无限扩展 |
| 记忆分类 | 无 | 6 类（profile/preferences/entities/events/cases/patterns） |
| 上下文加载 | 整体加载 | 分层加载（abstract → overview → full） |
| 多用户/多智能体 | 不支持 | 多租户隔离 |
| 知识浏览 | 不支持 | 文件系统式 `viking://` URI |

### 记忆工具

| 工具 | 用途 |
|------|------|
| `viking_search` | 语义搜索知识库（fast/deep 模式） |
| `viking_read` | 按 URI 读取内容（abstract/overview/full 三级详情） |
| `viking_browse` | 像文件系统一样浏览知识库（list/tree/stat） |
| `viking_remember` | 显式存储重要事实 |
| `viking_add_resource` | 导入 URL/文档到知识库 |

### 安全运营场景中的价值

- **漏洞扫描历史**：自动记忆历次扫描结果、已修复漏洞、未解决问题
- **事件处置经验**：积累处置流程和 Runbook 执行记录
- **资产变更追踪**：记录软件版本变更、配置调整
- **情报分析积累**：CVE 分析报告自动索引，支持回溯查询
- **团队知识沉淀**：安全策略问答记录自动形成知识库

---

## 前置要求

| 组件 | 要求 | 必选 |
|------|------|------|
| hermes-agent | ≥ v0.8.0 | ✅ |
| Python | ≥ 3.11 | ✅ |
| LLM 提供商 | Anthropic Claude（推荐 `claude-opus-4.6`） | ✅ |
| OpenViking | 最新版 | ✅ |
| httpx | Python HTTP 客户端 | ✅ |
| 漏洞扫描 MCP Server | OpenVAS / Nessus / 自研 | 可选 |
| 审批 API | 企业内部审批系统 | 可选 |
| NVD API Key | 提高情报查询速率 | 可选 |

---

## 安装步骤

### 方式 A：Docker Compose（推荐）

使用 SecHermes 专用的轻量镜像（无 Playwright/Node.js/Voice，约 500MB vs 2GB+）：

```bash
# 1. 准备环境变量
cp agents/security-assistant/.env.sechermes.example agents/security-assistant/.env.sechermes
# 编辑 .env.sechermes — 填入 ANTHROPIC_API_KEY（必须）

# 2. 一键启动 SecHermes + OpenViking
docker compose -f agents/security-assistant/docker-compose.yml up -d

# 3. 进入交互模式
docker attach sechermes-agent

# 或发送单次查询
docker exec -it sechermes-agent hermes -m "查询 CVE-2024-21626 的影响"
```

**构建自定义镜像**（如需修改）：

```bash
docker build -t sechermes -f agents/security-assistant/Dockerfile .
```

**挂载内部安全文档**：

```bash
SEC_DOCS_HOST_PATH=/path/to/your/docs \
  docker compose -f agents/security-assistant/docker-compose.yml up -d
```

**配置方式**：所有配置通过 `.env.sechermes` 环境变量注入，首次启动时自动生成
`config.yaml`（含 OpenViking 记忆、安全技能），无需手动配置。

### 方式 B：手动安装

#### 1. 安装并启动 OpenViking

```bash
# 安装 OpenViking
pip install openviking

# 使用交互式安装脚本（推荐）
./scripts/setup-openviking.sh

# 或手动启动
./scripts/start-openviking.sh start

# 验证 OpenViking 已启动
curl http://localhost:1933/health
```

#### 2. 配置环境变量

```bash
# 复制并编辑 OpenViking 环境配置
cp .env.openviking.example ~/.hermes/.env

# 关键配置项：
# OPENVIKING_ENDPOINT=http://127.0.0.1:1933
# OPENVIKING_EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5  （中文场景推荐）
# OPENVIKING_AGENT=sechermes  （标识此智能体）
```

#### 3. 配置智能体

```bash
# 复制 SecHermes 配置模板
cp agents/security-assistant/config/config.yaml.example cli-config.yaml

# 或手动设置 SOUL 文件
hermes config set agent.soul_file "$(pwd)/agents/security-assistant/SOUL.md"
```

#### 4. 激活 OpenViking 记忆

```bash
hermes memory setup
# 选择 openviking
```

#### 5. 安装安全技能

```bash
# 创建技能目录
mkdir -p ~/.hermes/skills

# 安装所有安全技能
cp -r agents/security-assistant/skills/vuln-scan ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-docs-qa ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-auto-fix ~/.hermes/skills/
cp -r agents/security-assistant/skills/sec-intel ~/.hermes/skills/
```

#### 6. 配置内部文档路径

```bash
# sec-docs-qa 技能需要指定文档目录
hermes config set security.docs_base_path "/path/to/your/internal/docs"
```

#### 7. 验证安装

```bash
hermes

# 检查记忆系统状态
hermes memory status
# 应显示：Provider: openviking, Status: connected

# 检查技能已加载
/skills
# 应看到 vuln-scan, sec-docs-qa, sec-auto-fix, sec-intel

# 测试安全情报功能
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

### 记忆系统

```
# 智能体自动使用 OpenViking 记忆工具：
# - 搜索历史漏洞扫描结果
# - 查阅过去的事件处置记录
# - 浏览知识库结构
# - 主动记忆重要的安全事件

# 也可在对话中直接要求：
上次我们扫描 192.168.1.0/24 发现了哪些高危漏洞？
```

---

## OpenViking 配置参考

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENVIKING_ENDPOINT` | `http://127.0.0.1:1933` | OpenViking 服务器地址 |
| `OPENVIKING_API_KEY` | （空） | API 认证密钥（本地开发可留空） |
| `OPENVIKING_ACCOUNT` | `default` | 多租户账户 ID |
| `OPENVIKING_USER` | `default` | 账户内用户 ID |
| `OPENVIKING_AGENT` | `hermes` | 智能体 ID（建议设为 `sechermes`） |
| `OPENVIKING_EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 向量嵌入模型 |
| `OPENVIKING_EMBEDDING_DEVICE` | `cpu` | 嵌入模型运行设备（cpu/cuda/mps） |
| `OPENVIKING_VLM_MODEL` | `Qwen/Qwen2-VL-2B-Instruct` | 视觉语言模型 |
| `OPENVIKING_VLM_DEVICE` | `cpu` | VLM 运行设备 |

### Embedding 模型选择

| 模型 | 大小 | 语言 | 推荐场景 |
|------|------|------|----------|
| `BAAI/bge-small-zh-v1.5` | 小 | 中文 | 默认，中文安全文档 |
| `BAAI/bge-base-zh-v1.5` | 中 | 中文 | 文档量大，需更高精度 |
| `BAAI/bge-large-zh-v1.5` | 大 | 中文 | 最高检索质量 |
| `sentence-transformers/all-MiniLM-L6-v2` | 小 | 英文 | 英文环境 |

### 多智能体场景

多个安全智能体共享同一 OpenViking 实例时，通过 `OPENVIKING_AGENT` 隔离：

```bash
# 漏洞扫描专用智能体
OPENVIKING_AGENT=sechermes-scanner

# 情报分析专用智能体
OPENVIKING_AGENT=sechermes-intel

# 共享同一 account + user 可实现知识共享
```

---

## 技能管控

> **重要**：SecHermes **不允许自动生成技能**。所有新技能必须由管理员审核并手动安装。

详见 [管理员操作指南](docs/ADMIN_GUIDE.md)。

---

## 目录结构

```
agents/security-assistant/
├── SOUL.md                        # 智能体身份、价值观和行为准则
├── AGENT.md                       # 技术规格说明书
├── README.md                      # 本文件
├── Dockerfile                     # 轻量 Docker 镜像（多阶段构建）
├── Dockerfile.dockerignore        # Docker 构建上下文过滤
├── docker-compose.yml             # SecHermes + OpenViking 一键部署
├── .env.sechermes.example         # 环境变量模板
├── docker/entrypoint.sh           # 容器启动脚本
├── skills/                        # 安全专属技能
│   ├── vuln-scan/SKILL.md         #   漏洞扫描管理
│   ├── sec-docs-qa/SKILL.md       #   内部文档答疑
│   ├── sec-auto-fix/SKILL.md      #   安全产品自动修复
│   └── sec-intel/SKILL.md         #   安全情报分析
├── mcp/README.md                  # MCP 服务器集成说明
├── config/config.yaml.example     # 配置模板（OpenViking 记忆）
└── docs/
    ├── DEVELOPMENT.md             # 扩展开发指南
    └── ADMIN_GUIDE.md             # 管理员操作指南
```

### 项目根目录相关文件

```
secops-agent/
├── docker-compose.openviking.yml  # Docker Compose 部署（含 OpenViking）
├── .env.openviking.example        # OpenViking 环境变量模板
├── openviking-config.yaml.example # 完整配置模板（含 OpenViking）
├── scripts/setup-openviking.sh    # 交互式 OpenViking 安装脚本
├── scripts/start-openviking.sh    # OpenViking 服务管理脚本
├── plugins/memory/openviking/     # OpenViking 记忆插件实现
└── docs/openviking-setup.md       # OpenViking 完整安装指南
```

---

## 故障排查

### OpenViking 连接失败

```bash
# 检查服务状态
curl http://localhost:1933/health

# 查看日志
./scripts/start-openviking.sh logs

# 重启服务
./scripts/start-openviking.sh restart
```

### 记忆插件未激活

```bash
# 确认配置
hermes memory status

# 重新激活
hermes memory setup  # 选择 openviking
```

### 技能未加载

```bash
# 确认技能文件存在
ls ~/.hermes/skills/

# 在会话中检查
/skills
```

更多问题请参考 [OpenViking 完整安装指南](../../docs/openviking-setup.md)。

---

## 获取帮助

| 资源 | 路径 |
|------|------|
| 完整开发文档 | [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) |
| 管理员操作指南 | [docs/ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md) |
| MCP 集成指南 | [mcp/README.md](mcp/README.md) |
| OpenViking 安装指南 | [docs/openviking-setup.md](../../docs/openviking-setup.md) |
| hermes-agent 官方文档 | https://hermes-agent.nousresearch.com/docs/ |
| OpenViking 项目 | https://github.com/volcengine/openviking |
