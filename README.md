# Codex 智能体状态面板

这是一个基于 FastAPI 的多智能体状态面板，用于 Codex 风格的协作运行监测。

当前已实现：
- run 创建
- agent 注册
- agent 状态更新，包含 Codex 元数据与审计日志追加
- 时间线与风险读取接口
- artifact 与人工日志写入接口
- 风险生命周期写接口
- 支持真实数据轮询的 dashboard 页面
- 供 Codex 子智能体同步快照的 Python reporter 客户端与桥接辅助工具

## 快速开始

1. 创建并激活 Python 3.12 虚拟环境。
2. 使用 `.\\.venv\\Scripts\\python.exe -m pip install -e .[dev]` 安装依赖。
3. 使用 `Copy-Item .env.example .env` 从示例生成 `.env`。
4. 使用 `.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload` 启动服务。
5. 创建一个真实 run，然后通过 `GET /runs/{run_id}/dashboard-token` 获取短期 dashboard 令牌。
6. 打开 `http://127.0.0.1:8000/runs/{run_id}/dashboard?access_token=...`。
7. dashboard 浏览器端轮询使用已签发的读取令牌，不再需要共享写 token。

## 配置

环境变量从 `.env` 加载。

必需运行参数：
- `APP_ENV`
- `DATABASE_URL`
- `API_TOKEN`

本地开发默认值保持保守：
- local/test 可使用 SQLite
- 非本地环境必须覆盖开发 token

示例文件见 [`.env.example`](D:/Object/python_object/ANXIN/PHPTutorial/WWW/Agent_Work_Panel/.env.example)。

## HTTP API

写接口：
- `POST /api/v1/runs`
- `POST /api/v1/runs/{run_id}/agents/register`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/status`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/log`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/artifact`

读接口：
- `GET /api/v1/runs/{run_id}/overview`
- `GET /api/v1/runs/{run_id}/agents`
- `GET /api/v1/runs/{run_id}/agents/{agent_id}`
- `GET /api/v1/runs/{run_id}/timeline`
- `GET /api/v1/runs/{run_id}/risks`

写接口当前要求：
- `x-api-token`
- `x-request-id`

读接口当前要求：
- `x-request-id`
- `x-api-token`、dashboard 只读令牌或 dashboard 会话 cookie 三者之一

## phpStudy 本机部署

本项目是 Python FastAPI 应用，不是 PHP 应用。phpStudy 在本方案中负责 MySQL 和 Nginx 入口，Python 服务由 Uvicorn 在本机 `127.0.0.1:8000` 独立承载，phpStudy Nginx 再反向代理到该端口。

### 1. 准备 phpStudy MySQL

1. 在 phpStudy 中启动 MySQL。
2. 打开 phpStudy 的 MySQL 管理工具或命令行。
3. 复制并执行 [deploy/phpstudy/mysql-init.sql](D:/Object/python_object/ANXIN/PHPTutorial/WWW/Agent_Work_Panel/deploy/phpstudy/mysql-init.sql)。
4. 执行前必须把 SQL 里的 `change-me-strong-password` 替换成本机专用强密码。
5. 兼容 phpStudy 的常见连接方式，模板同时创建 `localhost` 和 `127.0.0.1` 两个账号。
6. 如果 phpStudy 自带的 MySQL/MariaDB 不接受 `CREATE USER`，可以先手动创建账号，再执行后面的 `GRANT`。

该 SQL 会创建：
- 数据库：`codex_agent_panel`
- 应用账号：`codex_panel_app`@`127.0.0.1`
- 最小必要表级权限：`SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP`

### 2. 生成 phpStudy 环境配置

```powershell
Copy-Item .env.phpstudy.example .env
```

然后修改 `.env`：

```env
APP_ENV=local
DATABASE_URL=mysql+pymysql://codex_panel_app:你的数据库密码@127.0.0.1:3306/codex_agent_panel
API_TOKEN=替换成本机专用强随机值
DASHBOARD_TOKEN_TTL_SECONDS=3600
```

注意：
- 不要把真实 `.env` 提交到仓库。
- 不要在公网或生产环境使用示例 token 或示例密码。
- `APP_ENV=local` 表示本机部署；生产环境必须另行配置 HTTPS、强身份认证和安全 token。

### 3. 安装 Python 依赖

```powershell
.\scripts\phpstudy\install.ps1
```

脚本会检查 Python、创建或复用 `.venv`，并安装项目依赖。

### 4. 执行数据库迁移

```powershell
.\scripts\phpstudy\migrate.ps1
```

该脚本读取 `.env`，并执行：

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

如果 `alembic upgrade head` 因 phpStudy MySQL 的版本表状态异常失败，脚本会自动尝试 `alembic stamp head` 修复版本表。这只是在版本表和实际结构已一致时的修复手段，不等于重新执行迁移逻辑。

### 5. 启动 Python 服务

```powershell
.\scripts\phpstudy\start.ps1
```

服务默认监听：

```text
http://127.0.0.1:8000
```

停止服务：

```powershell
.\scripts\phpstudy\stop.ps1
```

### 6. 配置 phpStudy Nginx

在 phpStudy 中创建或编辑 Nginx 站点，域名使用：

```text
localhost
```

把 [deploy/phpstudy/nginx-agent-panel.conf](D:/Object/python_object/ANXIN/PHPTutorial/WWW/Agent_Work_Panel/deploy/phpstudy/nginx-agent-panel.conf) 中的 `server` 配置复制到 phpStudy 对应站点配置中，或按 phpStudy 支持方式 include 该文件。

核心反向代理配置为：

```nginx
server_name localhost;

location / {
    proxy_pass http://127.0.0.1:8000;
}
```

配置后重启 phpStudy Nginx。

### 7. 检查部署状态

```powershell
.\scripts\phpstudy\check.ps1
```

脚本会检查：
- `http://127.0.0.1:8000/health`
- `http://localhost/health`

两者都返回成功，说明 Uvicorn 服务和 phpStudy Nginx 反向代理都正常。

### 8. dashboard 验证

1. 通过 API 创建 run、注册 agent、提交状态。
2. 获取 dashboard 令牌：

```powershell
curl http://localhost/runs/1/dashboard-token `
  -H "x-api-token: 你的API_TOKEN" `
  -H "x-request-id: req-dashboard-token-001"
```

3. 浏览器打开：

```text
http://localhost/runs/1/dashboard?access_token=<token>
```

打开后，dashboard 会通过 Nginx 入口轮询后端真实数据。

## 验证运行手册

1. 安装依赖。
2. 运行 `.\\.venv\\Scripts\\python.exe -m pytest -q`。
3. 用 `.\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload` 启动应用。
4. 验证 `GET /health`。
5. 通过 `GET /runs/{run_id}/dashboard-token` 获取令牌，再打开 `/runs/{run_id}/dashboard?access_token=<token>` 验证 dashboard。
6. 验证核心写读流程：

dashboard 页面请求与认证轮询上下文：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-run-dashboard-001" `
  -H "Content-Type: application/json" `
  -d "{\"run_code\":\"run-dashboard\",\"run_name\":\"Dashboard Run\",\"source_type\":\"codex\"}"
```

```powershell
curl http://127.0.0.1:8000/runs/1/dashboard-token `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-dashboard-token-001"
```

```powershell
curl "http://127.0.0.1:8000/runs/1/dashboard?access_token=<token>"
```

创建 run：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-run-001" `
  -H "Content-Type: application/json" `
  -d "{\"run_code\":\"run-001\",\"run_name\":\"Codex Demo Run\",\"source_type\":\"codex\"}"
```

注册 agent：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs/1/agents/register `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-agent-001" `
  -H "Content-Type: application/json" `
  -d "{\"agent_code\":\"agent-ui\",\"agent_name\":\"UI Agent\",\"role\":\"frontend\",\"owner_scope\":\"dashboard\"}"
```

提交状态更新：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs/1/agents/1/status `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-status-001" `
  -H "Content-Type: application/json" `
  -d "{\"agent_name\":\"UI Agent\",\"status\":\"running\",\"phase\":\"implementation\",\"progress_percent\":50,\"current_task\":\"Rendering cards\",\"blocking_reason\":null,\"risk_level\":\"low\",\"reported_at\":\"2026-05-26T10:00:00Z\",\"last_update_at\":\"2026-05-26T10:00:00Z\",\"reported_by\":\"codex-orchestrator\",\"report_source\":\"reporter\",\"idempotency_key\":\"idem-status-001\"}"
```

从 Python 同步 Codex 子智能体快照：

```python
from app.reporter import ReporterClient
from app.reporter.bridge import sync_agent_snapshot

client = ReporterClient(base_url="http://127.0.0.1:8000", api_token="dev-token")

sync_agent_snapshot(
    client,
    run={
        "request_id": "req-run-bridge-001",
        "run_code": "codex-run-001",
        "run_name": "Codex Run",
        "source_type": "codex",
    },
    agent={
        "request_id": "req-agent-bridge-001",
        "agent_code": "subagent-001",
        "agent_name": "Codex Subagent 001",
        "role": "worker",
        "owner_scope": "codex",
        "codex_agent_type": "worker",
        "conversation_ref": "thread-001",
    },
    status={
        "request_id": "req-status-bridge-001",
        "idempotency_key": "idem-status-bridge-001",
        "agent_name": "Codex Subagent 001",
        "status": "running",
        "phase": "implementation",
        "progress_percent": 35,
        "current_task": "Implementing monitored task",
        "blocking_reason": None,
        "risk_level": "low",
        "reported_by": "codex-orchestrator",
        "report_source": "reporter",
        "codex_agent_type": "worker",
        "conversation_ref": "thread-001",
        "last_heartbeat_at": "2026-05-26T10:10:00Z",
    },
)
```

追加人工日志：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs/1/agents/1/log `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-log-001" `
  -H "Content-Type: application/json" `
  -d "{\"event_type\":\"comment\",\"summary\":\"Manual checkpoint\",\"detail_json\":{\"remark\":\"healthy\"},\"reported_by\":\"codex-orchestrator\",\"report_source\":\"reporter\",\"occurred_at\":\"2026-05-26T10:05:00Z\",\"idempotency_key\":\"idem-log-001\"}"
```

注册 artifact：

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/runs/1/agents/1/artifact `
  -H "x-api-token: dev-token" `
  -H "x-request-id: req-artifact-001" `
  -H "Content-Type: application/json" `
  -d "{\"artifact_type\":\"summary\",\"artifact_name\":\"Integration summary\",\"artifact_uri\":\"https://example.invalid/artifacts/summary-001\",\"artifact_version\":\"v1\",\"summary\":\"Collected validation notes\",\"idempotency_key\":\"idem-artifact-001\"}"
```

读取 overview/timeline/risks：

```powershell
curl -H "x-api-token: dev-token" -H "x-request-id: req-read-001" http://127.0.0.1:8000/api/v1/runs/1/overview
curl -H "x-api-token: dev-token" -H "x-request-id: req-read-002" http://127.0.0.1:8000/api/v1/runs/1/timeline
curl -H "x-api-token: dev-token" -H "x-request-id: req-read-003" http://127.0.0.1:8000/api/v1/runs/1/risks
```

## 审计与幂等说明

当前行为：
- 状态更新会追加审计日志
- 人工日志追加会形成时间线事实
- artifact 注册会追加审计日志，并可通过记录的 artifact id 回放
- 相同 `idempotency_key` 和相同 agent 的重复 status/log/artifact 请求会在服务层去重
- `run_agent_logs(agent_id, idempotency_key)` 已通过数据库唯一约束保护
- 现有写接口都要求 `x-request-id` 做请求追踪

当前缺口：
- artifact 回放历史上依赖审计日志锚点模式，而不是独立的 artifact 表幂等键
- 拒绝的 create-run 和 register-agent 请求会写结构化服务器审计日志，包含 `request_id`、主体类别、原因和目标标识
- 在尚未建立持久化 run/agent 主体之前，拒绝写请求仍未统一落为数据库时间线事实

## 已知限制

- API token 认证只是开发期最低安全保障，不是完整企业身份体系。
- `reported_by` 仍由调用方提供，在引入更强身份集成前只能算弱审计主体。
- dashboard 轮询现在使用短期只读令牌。
- `server_time` 还未进入共享 API 响应封装。
