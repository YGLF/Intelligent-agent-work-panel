# Codex 多智能体实时状态面板设计

## 1. 目标与范围

### 1.1 目标
- 搭建一个基于 Python 的多智能体实时状态面板第一版。
- 第一版采用 `HTTP + 轮询刷新`，优先保证实现简单、状态一致、便于排障。
- 第一版优先服务 `Codex 多智能体协作`，同时保留扩展到普通异步任务、批处理和作业编排监控的边界。
- 系统需满足开发测试可用，并按高监管、强审计、生产级企业系统思路预留审计、身份、幂等和兼容能力。

### 1.2 非目标
- 第一版不做复杂任务编排引擎。
- 第一版不直接接入 WebSocket/SSE。
- 第一版不直接侵入 Codex 内部私有运行时或依赖不稳定内部数据源。
- 第一版不实现完整审批流、统一身份体系和生产级多租户隔离，但必须预留接入边界。

## 2. 总体方案

### 2.1 推荐技术栈
- 后端：`FastAPI`
- ORM：`SQLAlchemy`
- 数据库：`MySQL`
- 页面模板：`Jinja2`
- 前端：`HTML + CSS + 原生 JavaScript`

### 2.2 架构分层
- 表现层：页面路由和 REST API 路由。
- 应用层：overview 聚合、agent 查询、timeline 聚合、risk 聚合、status/reporting 服务。
- 领域层：run、agent、log、artifact、risk 模型，以及 status/phase/risk 枚举。
- 基础设施层：MySQL 持久化、配置管理、时间与序列化处理、审计写入。

### 2.3 核心架构原则
- 采用“当前快照 + 事件追加”双层模型。
- 面板展示优先查询快照，保证读轻量。
- 审计追踪优先查询事件日志，保证事实可回放。
- Codex 通过主动上报接入，不要求面板直接解析 Codex 内部数据。

## 3. 数据模型设计

### 3.1 runs
用于记录一轮协作任务。

关键字段：
- `id`
- `run_code`
- `run_name`
- `source_type`
- `status`
- `started_at`
- `finished_at`
- `last_activity_at`
- `created_by`
- `created_at`
- `updated_at`

建议索引：
- `uk_run_code`
- `idx_status_last_activity_at(status, last_activity_at)`
- `idx_started_at(started_at)`

### 3.2 run_agents
用于记录某个 `run` 下每个智能体的当前状态快照，是面板读模型。

关键字段：
- `id`
- `run_id`
- `agent_code`
- `agent_name`
- `role`
- `owner_scope`
- `status`
- `phase`
- `progress_percent`
- `current_task`
- `risk_level`
- `blocking_reason`
- `depends_on_json`
- `handoff_to`
- `needs_input`
- `deliverable_summary`
- `codex_agent_type`
- `conversation_ref`
- `started_at`
- `finished_at`
- `last_update_at`
- `last_heartbeat_at`
- `version_no`
- `created_at`
- `updated_at`

建议索引：
- `uk_run_agent(run_id, agent_code)`
- `idx_run_status(run_id, status)`
- `idx_run_phase(run_id, phase)`
- `idx_run_owner_scope(run_id, owner_scope)`
- `idx_run_last_update(run_id, last_update_at)`
- `idx_run_risk(run_id, risk_level)`

### 3.3 run_agent_logs
用于记录状态变更、阶段推进、进度日志、阻塞变化、人工备注，是核心审计表。

关键字段：
- `id`
- `run_id`
- `agent_id`
- `event_type`
- `old_status`
- `new_status`
- `old_phase`
- `new_phase`
- `before_progress`
- `after_progress`
- `summary`
- `detail_json`
- `reported_by`
- `operator_type`
- `report_source`
- `request_id`
- `idempotency_key`
- `source_event_id`
- `trace_id`
- `occurred_at`
- `server_received_at`
- `server_processed_at`
- `result_status`
- `result_message`
- `created_at`

建议索引：
- `idx_agent_occurred(agent_id, occurred_at desc)`
- `idx_run_occurred(run_id, occurred_at desc)`
- `idx_event_type(event_type, occurred_at)`

### 3.4 run_agent_artifacts
用于记录智能体产出物。

关键字段：
- `id`
- `run_id`
- `agent_id`
- `artifact_type`
- `artifact_name`
- `artifact_uri`
- `artifact_version`
- `summary`
- `idempotency_key`
- `created_by`
- `created_at`

建议索引：
- `uk_run_agent_artifact_idempotency(agent_id, idempotency_key)`
- `idx_agent_created(agent_id, created_at desc)`
- `idx_run_type(run_id, artifact_type)`

### 3.5 run_risks
用于记录阻塞项和高风险项的独立生命周期。

关键字段：
- `id`
- `run_id`
- `agent_id`
- `risk_type`
- `risk_level`
- `title`
- `reason`
- `suggested_action`
- `status`
- `opened_at`
- `resolved_at`
- `duration_seconds_snapshot`
- `reported_by`
- `resolved_by`
- `created_at`
- `updated_at`

建议索引：
- `idx_run_open_risk(run_id, status, risk_level)`
- `idx_agent_opened(agent_id, opened_at desc)`
- `idx_status_updated(status, updated_at)`

## 4. 视图模型

### 4.1 agent_run
前端面板按统一 `agent_run` 视图模型渲染。

字段：
- `agent_id`
- `agent_name`
- `role`
- `owner_scope`
- `status`
- `phase`
- `progress_percent`
- `current_task`
- `last_update_at`
- `started_at`
- `finished_at`
- `blocking_reason`
- `depends_on`
- `artifacts`
- `recent_logs`
- `risk_level`
- `codex_agent_type`
- `conversation_ref`
- `handoff_to`
- `needs_input`
- `deliverable_summary`
- `ready_for_integration`

### 4.2 run_overview
字段：
- `total_agents`
- `running_count`
- `completed_count`
- `blocked_count`
- `failed_count`
- `phase_distribution`
- `overall_progress`
- `active_updates_last_1h`
- `last_active_at`
- `auto_refresh_status`
- `stale_hint`

## 5. 接口设计

API 前缀固定为 `/api/v1`。

### 5.1 读接口
- `GET /api/v1/runs/{run_id}/overview`
- `GET /api/v1/runs/{run_id}/agents`
- `GET /api/v1/runs/{run_id}/agents/{agent_id}`
- `GET /api/v1/runs/{run_id}/timeline`
- `GET /api/v1/runs/{run_id}/risks`

列表查询支持参数：
- `status`
- `phase`
- `owner_scope`
- `risk_level`
- `blocked_only`
- `updated_since`
- `limit`
- `cursor`

统一响应结构：
- `success`
- `code`
- `message`
- `data`
- `request_id`
- `server_time`

建议增量响应额外返回：
- `next_updated_since`
- `next_cursor`
- `has_more`

### 5.2 写接口
- `POST /api/v1/runs`
- `POST /api/v1/runs/{run_id}/agents/register`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/status`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/log`
- `POST /api/v1/runs/{run_id}/agents/{agent_id}/artifact`

## 6. 状态上报协议

### 6.1 必填字段
- `run_id`
- `agent_id`
- `agent_name`
- `reported_at`
- `request_id`
- `idempotency_key`

### 6.2 核心状态字段
- `status`：`pending|running|waiting|blocked|completed|failed`
- `phase`：`analysis|design|implementation|test|integration`
- `progress_percent`
- `current_task`
- `blocking_reason`
- `depends_on`
- `risk_level`：`low|medium|high`
- `started_at`
- `finished_at`
- `last_update_at`

### 6.3 Codex 扩展字段
- `codex_agent_type`
- `conversation_ref`
- `handoff_to`
- `needs_input`
- `deliverable_summary`
- `ready_for_integration`

### 6.4 审计字段
- `reported_by`
- `report_source`
- `source_event_id`
- `trace_id`
- `operator_type`
- `remark`

### 6.5 可选附带字段
- `recent_log_entry`
- `artifacts`
- `risk_action_suggestion`

### 6.6 约束规则
- `completed/failed` 必须带 `finished_at`。
- `blocked` 必须带 `blocking_reason`。
- `progress_percent` 仅允许 `0-100`。
- `depends_on` 第一版使用字符串数组。

## 7. 刷新与增量拉取策略

### 7.1 轮询频率
- `overview`：`5s`
- `agent cards`：`5s`
- `risks`：`5s`
- `timeline`：`8s`
- 页面后台：统一降为 `15s`
- 已展开详情：`3s`
- 已完成/失败且稳定的详情：可降为 `10s`

### 7.2 增量拉取
- `agents` 按快照更新时间拉取变化的 agent。
- `timeline` 按事件时间拉取新增事件。
- `risks` 按风险更新时间拉取变更项。
- 第一版支持 `updated_since + cursor`。
- 若实现复杂度受限，可先使用 `updated_since >= watermark_time` 并由前端按 `id` 去重。

### 7.3 失败处理
- 接口失败时不清空页面。
- 保留上次成功快照。
- 单次失败提示：`刷新异常，已保留上次状态`。
- 连续 3 次失败提示：`状态可能已过期`。
- 区块级失败使用区块级 stale 标记，不做全局误报。

## 8. 前端页面设计

### 8.1 页面分区
1. `Overview`
2. `Agent Cards`
3. `Risks`
4. `Timeline`

### 8.2 卡片区主展示字段
- `agent_name`
- `codex_agent_type`
- `status`
- `phase`
- `progress_percent`
- `current_task`
- `handoff_to`
- `needs_input`
- `last_update_at`

### 8.3 强提示项
- `blocked`
- `high risk`
- `needs_input`
- `waiting too long`

### 8.4 详情区展示字段
- `owner_scope`
- `depends_on`
- `artifacts`
- `recent_logs`
- `deliverable_summary`
- `conversation_ref`

### 8.5 交互
- 按状态筛选。
- 按阶段筛选。
- 按责任域筛选。
- 只看阻塞项。
- 点击卡片内联展开详情。
- 手动刷新。
- 自动轮询开关。

## 9. Codex 对接方案

### 9.1 对接方式
采用 `Codex 主智能体/调用方主动上报`。

### 9.2 第一版达标标准
满足以下条件即视为已能监测 Codex：
- 能创建一轮 `run`。
- 能注册多个 Codex agent。
- agent 能持续上报状态、阶段、任务、进度、阻塞、交接、输入需求、产出摘要。
- 页面能在约 `5s` 内看到变化。
- 时间线可查看最近推进。
- 风险区可查看阻塞与高风险。
- 详情可查看最近日志和产出物。

### 9.3 Reporter 建议
项目内提供轻量 Python reporter，用于封装：
- `create_run`
- `register_agent`
- `report_status`
- `append_log`
- `register_artifact`

## 10. 审计、安全与一致性

### 10.1 审计要求
- 写接口成功与失败都要留痕。
- 记录谁、何时、来源、请求号、链路号、结果码。
- 快照表保存当前值。
- 事件表保存变更事实。

### 10.2 幂等与防重
- 写请求必须带 `idempotency_key`。
- 唯一键建议：`run_id + agent_id + idempotency_key`。
- 同键重复提交返回首次处理结果。
- 同键但 payload 不一致返回冲突。

### 10.3 乱序保护
- 建议使用 `source_event_id` 或 `source_version`。
- 对旧事件可保留审计记录，但默认不覆盖快照。

### 10.4 最低安全边界
- 第一版写接口至少使用简单 API Token 校验。
- 匿名写入不得固化为正式契约。
- 未接入统一身份前，`reported_by` 只能作为弱身份线索，不可视为强审计主体。
- dashboard 浏览器访问应使用短期只读会话 cookie，不应把写 token 暴露给浏览器。

## 11. 错误码与兼容性

### 11.1 HTTP 状态建议
- `200`
- `400`
- `401`
- `403`
- `404`
- `409`
- `422`
- `429`
- `500`

### 11.2 业务错误码建议
- `RUN_NOT_FOUND`
- `AGENT_NOT_FOUND`
- `INVALID_STATUS`
- `INVALID_PHASE`
- `INVALID_PROGRESS`
- `INVALID_TRANSITION`
- `IDEMPOTENCY_CONFLICT`
- `STALE_EVENT_REJECTED`
- `AUDIT_FIELDS_MISSING`
- `RATE_LIMITED`
- `INTERNAL_ERROR`

### 11.3 兼容边界
- 路径使用 `/api/v1`。
- 响应新增字段需向后兼容。
- 新增请求可选字段兼容旧客户端。
- 新增请求必填字段时应升级版本。
- 未知字段可忽略并记录审计。
- 未知枚举值必须拒绝，防止语义漂移。

## 12. 验证方案

### 12.1 功能验证
- 创建 run 后可展示全部智能体。
- 单个 agent 状态变化后 5 秒内卡片更新。
- agent 进入 `blocked` 后风险区同步出现。
- agent 完成后 overview 同步变化。
- 时间线按更新时间倒序展示。
- 产出物登记后详情可查看。

### 12.2 刷新验证
- 后端短时失败时页面保留上次状态。
- 恢复后自动继续刷新。
- 后台标签页时自动降频。
- 多个智能体同时更新时不闪烁、不乱序。

### 12.3 交互验证
- 状态筛选、阶段筛选、只看阻塞项生效。
- 点击卡片可展开详情。
- 手动刷新不影响自动轮询。

### 12.4 可运维性验证
- 所有状态更新接口写入更新时间。
- 可查某个 agent 最近一次状态变化。
- 可定位长时间未更新的 agent。
- 可区分“正在执行”和“失去心跳”。

## 13. 风险与后续增强

### 13.1 当前已知缺口
- `reported_by` 第一版仍可能是调用方自报，真实性有限。
- 未接入统一鉴权前，写接口存在伪造上报风险。
- 若仅存摘要日志，完整字段级回放能力有限。
- 当前未设计完整状态流转审批约束。

### 13.2 后续增强建议
- 接入真实鉴权体系。
- 为关键更新增加 `before_json/after_json` 或字段差异摘要。
- 为日志表做冷热分层或分区。
- 增加客户端 IP、环境标识、租户标识。
- 强化状态流转约束与异常回滚策略。
- 评估从 HTTP 轮询升级到 SSE 或 WebSocket，但不改变当前读模型和事件模型。

## 14. 结论
- 第一版采用 `FastAPI + SQLAlchemy + MySQL + Jinja2/原生 HTML`。
- 面板采用 `overview + agent cards + risks + timeline`。
- 存储采用 `快照表 + 事件表 + 风险表 + 产出物表`。
- Codex 采用主动上报方式接入。
- 系统以开发测试可用为第一目标，同时保留审计、安全、幂等和兼容边界。
