# Codex 智能体状态面板实施计划

> **给执行智能体的要求：** 按任务逐项执行本计划。推荐使用 `superpowers:subagent-driven-development`，也可以使用 `superpowers:executing-plans`。步骤使用复选框语法便于跟踪。

**目标：** 构建一个基于 Python 的 Codex 多智能体状态面板，将智能体状态持久化到 MySQL，提供带审计能力的 HTTP API，并渲染可轮询的 dashboard，用于监测 Codex 上报的智能体。

**架构：** 使用单体 FastAPI 应用，包含 SQLAlchemy 模型、服务层状态更新逻辑、Jinja2 dashboard 页面和轻量 JavaScript 轮询模块。MySQL 持久化当前智能体快照、追加式审计事件、风险和产出物，并提供轻量 Python reporter 客户端用于 Codex 侧状态上报。

**技术栈：** Python 3.12、FastAPI、SQLAlchemy 2.x、Alembic、MySQL、Jinja2、pytest、httpx、Pydantic settings、原生 JavaScript。

---

## 文件结构

- `pyproject.toml`：Python 包元数据、依赖和 pytest 配置。
- `.gitignore`：忽略虚拟环境、缓存、本地环境文件和测试数据库。
- `.env.example`：MySQL 与 API token 的运行配置示例。
- `README.md`：本地启动、MySQL 设置和验证命令。
- `alembic.ini`：Alembic 配置。
- `alembic/env.py`：迁移环境，加载应用配置和元数据。
- `alembic/versions/0001_create_agent_status_tables.py`：runs、agents、logs、artifacts、risks 初始表结构。
- `app/main.py`：FastAPI 应用工厂和路由注册。
- `app/config.py`：环境变量驱动的配置。
- `app/db.py`：数据库引擎、会话工厂和元数据暴露。
- `app/models/*`：run、agent、log、artifact、risk ORM 模型与枚举。
- `app/schemas/*`：API 请求和响应结构。
- `app/services/*`：审计、状态更新、读取聚合、风险、日志和 artifact 服务。
- `app/api/*`：依赖注入、鉴权、request-id 和业务路由。
- `app/templates/*`：dashboard 页面模板。
- `app/static/*`：dashboard 样式和轮询脚本。
- `app/reporter/*`：Codex 侧上报客户端和桥接辅助工具。
- `tests/*`：健康检查、run、agent、dashboard、reporter、风险与日志 artifact 测试。

## 任务 1：启动 Python 服务骨架

**涉及文件：**
- 创建：`pyproject.toml`
- 创建：`.gitignore`
- 创建：`.env.example`
- 创建：`README.md`
- 创建：`app/__init__.py`
- 创建：`app/main.py`
- 创建：`tests/conftest.py`
- 创建：`tests/test_health_and_bootstrap.py`

- [ ] **步骤 1：编写失败的启动测试**

```python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_service_metadata():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "code": "OK",
        "message": "service healthy",
        "data": {
            "service": "codex-agent-status-panel",
            "version": "0.1.0",
        },
    }
```

- [ ] **步骤 2：运行测试确认失败**

运行：`pytest tests/test_health_and_bootstrap.py::test_health_endpoint_returns_service_metadata -v`

预期：失败，提示缺少 `app` 模块或缺少 `create_app`。

- [ ] **步骤 3：实现最小启动代码**

创建最小 FastAPI 应用、依赖声明、`.gitignore`、`.env.example` 和本地启动说明，保证 `/health` 返回服务元数据。

- [ ] **步骤 4：运行测试确认通过**

运行：`pytest tests/test_health_and_bootstrap.py::test_health_endpoint_returns_service_metadata -v`

预期：通过。

- [ ] **步骤 5：提交启动骨架**

```bash
git add pyproject.toml .gitignore .env.example README.md app/__init__.py app/main.py tests/conftest.py tests/test_health_and_bootstrap.py
git commit -m "chore: bootstrap FastAPI status panel service"
```

## 任务 2：增加配置、数据库连接和初始迁移

**涉及文件：**
- 修改：`app/main.py`
- 创建：`app/config.py`
- 创建：`app/db.py`
- 创建：`app/models/base.py`
- 创建：`app/models/enums.py`
- 创建：`app/models/run.py`
- 创建：`app/models/agent.py`
- 创建：`app/models/log.py`
- 创建：`app/models/artifact.py`
- 创建：`app/models/risk.py`
- 创建：`alembic.ini`
- 创建：`alembic/env.py`
- 创建：`alembic/versions/0001_create_agent_status_tables.py`
- 创建：`tests/test_run_api.py`

- [ ] **步骤 1：编写失败的元数据测试**

测试 `Base.metadata.tables` 是否包含 `runs`、`run_agents`、`run_agent_logs`、`run_agent_artifacts`、`run_risks`。

- [ ] **步骤 2：运行测试确认失败**

运行：`pytest tests/test_run_api.py::test_metadata_contains_expected_tables -v`

预期：失败，因为数据库模块或模型模块尚未存在。

- [ ] **步骤 3：增加配置、SQLAlchemy 基类和表模型**

实现 `Settings`、`Base`、数据库 session、五类核心表模型、枚举和初始 Alembic 迁移。模型字段以审计、幂等、状态快照和事件回放为核心。

- [ ] **步骤 4：运行表结构测试**

运行：`pytest tests/test_run_api.py -v`

预期：通过。

- [ ] **步骤 5：提交数据库骨架**

```bash
git add app/config.py app/db.py app/models alembic.ini alembic tests/test_run_api.py
git commit -m "feat: add status panel data model"
```

## 任务 3：实现 run 创建和鉴权基础能力

**目标：** 增加 `POST /api/v1/runs`，所有写接口必须要求 `x-api-token` 和 `x-request-id`。

**验收标准：**
- 缺少 `x-request-id` 返回 `400`。
- 缺少或错误 `x-api-token` 返回 `401/403`。
- `run_code` 重复返回 `409`。
- 成功创建时返回统一 API 响应并带回 `request_id`。

## 任务 4：实现 agent 注册和状态更新

**目标：** 支持 agent 注册、状态更新、Codex 元数据、乱序保护和审计日志追加。

**验收标准：**
- 同一 run 下 `agent_code` 唯一。
- 状态更新覆盖快照并追加日志。
- `progress_percent` 限制在 `0-100`。
- `blocked` 需要阻塞原因。
- stale event 不覆盖快照，但要保留审计事实。

## 任务 5：实现日志、artifact 和风险生命周期

**目标：** 支持人工日志追加、artifact 注册、风险开启和风险关闭。

**验收标准：**
- 日志按时间线可读。
- artifact 注册可审计、可幂等。
- 风险开启与关闭记录责任主体、时间和结果。
- 重复 `idempotency_key` 返回首次处理结果。

## 任务 6：实现读取聚合接口

**目标：** 提供 dashboard 所需的 overview、agents、agent detail、timeline、risks 读取接口。

**验收标准：**
- overview 能返回总数、运行中、阻塞、完成、失败、阶段分布、整体进度和最近活跃时间。
- agent 列表支持状态、阶段、责任域和阻塞筛选。
- agent 详情包含依赖、产出物、最近日志和 Codex 元数据。
- timeline 按发生时间倒序返回。
- risks 返回打开和已处理风险。

## 任务 7：构建 dashboard 页面、轮询、筛选和 stale 状态

**涉及文件：**
- 创建：`app/templates/base.html`
- 创建：`app/templates/dashboard.html`
- 创建：`app/static/css/dashboard.css`
- 创建：`app/static/js/dashboard.js`
- 修改：`app/main.py`
- 创建：`tests/test_dashboard_page.py`

- [ ] **步骤 1：编写失败的 dashboard 页面测试**

验证页面包含 `Agent Status Dashboard`、overview、agents、risks、timeline 四个刷新区块和筛选控件。

- [ ] **步骤 2：运行测试确认失败**

运行：`pytest tests/test_dashboard_page.py -v`

预期：失败，通常为 404 或缺少模板内容。

- [ ] **步骤 3：增加模板、静态资源和 dashboard 路由**

实现页面结构、筛选控件、区块级状态、轮询逻辑、失败保留上次状态和连续失败 stale 标记。

- [ ] **步骤 4：运行 dashboard 测试**

运行：`pytest tests/test_dashboard_page.py -v`

预期：通过。

- [ ] **步骤 5：提交 dashboard UI**

```bash
git add app/templates app/static app/main.py tests/test_dashboard_page.py
git commit -m "feat: add polling dashboard UI"
```

## 任务 8：增加 Codex 侧 Python reporter 客户端

**涉及文件：**
- 创建：`app/reporter/__init__.py`
- 创建：`app/reporter/client.py`
- 创建：`tests/test_reporter_client.py`
- 修改：`README.md`

- [ ] **步骤 1：编写失败的 reporter 契约测试**

验证 reporter 能构造状态上报 payload，并能发送状态、日志和 artifact 请求。

- [ ] **步骤 2：运行测试确认失败**

运行：`pytest tests/test_reporter_client.py -v`

预期：失败，因为 reporter 模块尚未存在。

- [ ] **步骤 3：实现 reporter 客户端**

封装 base url、API token、`x-request-id`、状态 payload 默认值、run 创建、agent 注册、状态上报、日志追加和 artifact 注册。

- [ ] **步骤 4：运行 reporter 测试**

运行：`pytest tests/test_reporter_client.py -v`

预期：通过。

- [ ] **步骤 5：提交 reporter 集成**

```bash
git add app/reporter README.md tests/test_reporter_client.py
git commit -m "feat: add Codex reporter client"
```

## 任务 9：最终验证、迁移检查和运行手册更新

**涉及文件：**
- 修改：`README.md`
- 修改：`.env.example`

- [ ] **步骤 1：补充端到端验证说明**

README 需要包含：
- 数据库准备
- `alembic upgrade head`
- `pytest -v`
- `uvicorn app.main:app --reload`
- `/health`
- 创建 run、注册 agent、提交状态、打开 dashboard 的完整流程

- [ ] **步骤 2：运行完整验证套件**

```bash
alembic upgrade head
pytest -v
uvicorn app.main:app --reload
```

预期：迁移成功、测试通过、应用可访问 `/health` 和 dashboard。

- [ ] **步骤 3：手工验证核心流程**

用 curl 创建 run、注册 agent、提交状态更新、读取 overview/timeline/risks，并确认 dashboard 约 5 秒内看到变化。

- [ ] **步骤 4：记录未解决风险**

README 必须记录：
- API token 只是最低开发防护。
- `reported_by` 在接入真实身份前仍是调用方自报。
- dashboard 是 HTTP 轮询，不是推送。
- 未完整接入统一身份、细粒度权限和多租户隔离前，不应直接作为强监管最终形态。

- [ ] **步骤 5：提交验证文档**

```bash
git add README.md .env.example
git commit -m "docs: add verification runbook and known limitations"
```
