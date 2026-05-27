const MONITOR_INTERVAL_MS = 5000;

const monitorState = {
  apiToken: window.localStorage.getItem("codex-monitor-api-token") || "",
  timerId: null,
};

const AGENT_PALETTE = ["blue", "teal", "amber", "rose", "emerald", "slate"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function formatText(value, fallback = "N/A") {
  return value === null || value === undefined || value === "" ? fallback : String(value);
}

function formatDate(value) {
  if (!value) {
    return "N/A";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString("zh-CN", { hour12: false });
}

function setMonitorStatus(message) {
  const node = document.getElementById("monitor-refresh-status");
  if (node) {
    node.textContent = message;
  }
}

function setMonitorFlash(message, level = "info") {
  const node = document.getElementById("monitor-flash");
  if (!node) {
    return;
  }
  node.textContent = message || "";
  node.dataset.level = message ? level : "";
}

function pickAgentColor(agent) {
  const key = String(agent.agent_code || agent.agent_name || "").toLowerCase();
  let hash = 0;
  for (let i = 0; i < key.length; i += 1) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return AGENT_PALETTE[hash % AGENT_PALETTE.length];
}

function statusLabel(status) {
  const map = {
    running: "运行中",
    blocked: "阻塞",
    completed: "完成",
    failed: "失败",
    pending: "等待",
    open: "打开",
  };
  return map[status] || formatText(status, "未知");
}

function renderSummary(data) {
  const node = document.getElementById("monitor-summary");
  if (!node) {
    return;
  }
  const recentRuns = (data.recent_active_runs || []).slice(0, 5);
  const blockedRuns = (data.blocked_runs || []).slice(0, 5);
  node.innerHTML = `
    <section class="monitor-overview" aria-label="Codex 状态概览">
      <div class="overview-primary">
        <span class="overview-dot"></span>
        <div>
          <p>Codex 当前状态</p>
          <strong>${escapeHtml(data.active_runs)} 个活跃项目 / ${escapeHtml(data.total_blocked_agents)} 个阻塞智能体</strong>
        </div>
      </div>
      <dl class="overview-metrics">
        <div><dt>项目/run</dt><dd>${escapeHtml(data.total_runs)}</dd></div>
        <div><dt>智能体</dt><dd>${escapeHtml(data.total_agents)}</dd></div>
        <div><dt>子智能体</dt><dd>${escapeHtml(data.total_subagents)}</dd></div>
        <div><dt>Codex 会话</dt><dd>${escapeHtml(data.codex_session_count ?? 0)}</dd></div>
        <div><dt>Codex 工作区</dt><dd>${escapeHtml(data.codex_workspace_count ?? 0)}</dd></div>
        <div><dt>服务刷新</dt><dd>${escapeHtml(formatDate(data.last_refresh_at))}</dd></div>
      </dl>
      <div class="overview-panels">
        <section class="overview-panel">
          <h3>最近活跃</h3>
          ${recentRuns.length ? recentRuns.map((run) => `
            <div class="overview-runline">
              <strong>${escapeHtml(run.run_name)}</strong>
              <span>${escapeHtml(run.total_agents)} agents · ${escapeHtml(formatDate(run.last_active_at))}</span>
            </div>
          `).join("") : `<p class="empty-state">暂无活跃记录。</p>`}
        </section>
        <section class="overview-panel">
          <h3>阻塞聚焦</h3>
          ${blockedRuns.length ? blockedRuns.map((run) => `
            <div class="overview-runline">
              <strong>${escapeHtml(run.run_name)}</strong>
              <span>${escapeHtml(run.blocked_count)} blocked · ${escapeHtml(run.failed_count)} failed</span>
            </div>
          `).join("") : `<p class="empty-state">当前没有阻塞项目。</p>`}
        </section>
      </div>
    </section>
  `;
}

function renderAgentRow(agent, roleLabel) {
  const colorClass = `agent-color-${pickAgentColor(agent)}`;
  const modelText = `${formatText(agent.model_name, "model unknown")} · ${formatText(agent.model_tier, "tier unknown")}`;
  return `
    <article class="monitor-agent-row ${colorClass}">
      <div class="agent-identity">
        <span class="agent-color-mark" aria-hidden="true"></span>
        <div>
          <div class="agent-title-line">
            <strong>${escapeHtml(agent.agent_name)}</strong>
            <span>${escapeHtml(roleLabel)}</span>
          </div>
          <p>${escapeHtml(formatText(agent.current_task, "暂无当前任务"))}</p>
        </div>
      </div>
      <div class="agent-facts">
        <span>${escapeHtml(modelText)}</span>
        <span>${escapeHtml(formatText(agent.phase, "phase unknown"))}</span>
        <span>${escapeHtml(formatText(agent.progress_percent, "0"))}%</span>
        <span>心跳 ${escapeHtml(formatDate(agent.last_heartbeat_at || agent.last_update_at))}</span>
      </div>
      <span class="status-pill status-${escapeHtml(agent.status)}">${escapeHtml(statusLabel(agent.status))}</span>
      ${agent.blocking_reason ? `<p class="inline-warning">阻塞原因：${escapeHtml(agent.blocking_reason)}</p>` : ""}
      ${agent.needs_input ? `<p class="inline-note">需要人工输入后才能继续。</p>` : ""}
    </article>
  `;
}

function renderAgentSection(run) {
  const mainAgents = run.main_agents || [];
  const childAgents = run.child_agents || [];

  if (!mainAgents.length && !childAgents.length) {
    return `<p class="empty-state">该项目/run 暂无智能体状态。同步或注册 agent 后会自动出现。</p>`;
  }

  return `
    <div class="agent-section">
      <div class="agent-section-title">
        <span>主智能体</span>
        <small>${escapeHtml(mainAgents.length)} 个</small>
      </div>
      <div class="agent-row-list">
        ${mainAgents.length ? mainAgents.map((agent) => renderAgentRow(agent, "主控")).join("") : `<p class="empty-state">未标记主智能体。</p>`}
      </div>
      <div class="agent-section-title subagent-title">
        <span>子智能体</span>
        <small>${escapeHtml(childAgents.length)} 个</small>
      </div>
      <div class="agent-row-list subagent-list">
        ${childAgents.length ? childAgents.map((agent) => renderAgentRow(agent, agent.parent_agent_id ? `子智能体 · #${agent.parent_agent_id}` : "子智能体")).join("") : `<p class="empty-state">当前没有子智能体。</p>`}
      </div>
    </div>
  `;
}

function renderRuns(data) {
  const node = document.getElementById("monitor-runs");
  if (!node) {
    return;
  }
  if (!data.items?.length) {
    node.innerHTML = `
      <section class="monitor-run-card empty-card">
        <h2>暂无项目/run</h2>
        <p class="empty-state">运行同步脚本或注册 agent 后，这里会显示 Codex 项目、主智能体和子智能体状态。</p>
      </section>
    `;
    return;
  }

  node.innerHTML = data.items.map((run) => `
    <section class="monitor-run-card">
      <header class="run-card-header">
        <div>
          <p>${escapeHtml(run.run_code)} · run #${escapeHtml(run.run_id)}</p>
          <h2>${escapeHtml(run.run_name)}</h2>
        </div>
        <span class="status-pill status-${escapeHtml(run.run_status)}">${escapeHtml(statusLabel(run.run_status))}</span>
      </header>
      <div class="run-signal-row">
        <span>${escapeHtml(run.source_type)}</span>
        <span>${escapeHtml(run.total_agents)} 智能体</span>
        <span>${escapeHtml(run.subagent_count)} 子智能体</span>
        <span>${escapeHtml(run.overall_progress)}% 进度</span>
        <span>最近活动 ${escapeHtml(formatDate(run.last_active_at))}</span>
      </div>
      <dl class="run-health-grid">
        <div><dt>运行中</dt><dd>${escapeHtml(run.running_count)}</dd></div>
        <div><dt>阻塞</dt><dd>${escapeHtml(run.blocked_count)}</dd></div>
        <div><dt>完成</dt><dd>${escapeHtml(run.completed_count)}</dd></div>
        <div><dt>失败</dt><dd>${escapeHtml(run.failed_count)}</dd></div>
      </dl>
      ${renderAgentSection(run)}
    </section>
  `).join("");
}

async function refreshMonitor() {
  if (!monitorState.apiToken) {
    setMonitorStatus("请输入 API_TOKEN 后开始监测");
    return;
  }
  try {
    const response = await fetch("/api/v1/monitor", {
      headers: {
        "x-api-token": monitorState.apiToken,
        "x-request-id": `monitor-${Date.now()}`,
      },
    });
    if (!response.ok) {
      throw new Error(`monitor request failed with status ${response.status}`);
    }
    const payload = await response.json();
    renderSummary(payload.data || {});
    renderRuns(payload.data || {});
    setMonitorStatus(`最近刷新：${new Date().toLocaleString("zh-CN", { hour12: false })}`);
    setMonitorFlash("");
  } catch (error) {
    setMonitorFlash(`刷新失败：${error.message}`, "warning");
    setMonitorStatus("刷新失败，保留上一帧数据");
  }
}

function startMonitor() {
  const tokenInput = document.getElementById("monitor-token");
  monitorState.apiToken = tokenInput?.value?.trim() || monitorState.apiToken;
  if (!monitorState.apiToken) {
    setMonitorFlash("请输入 API_TOKEN。", "warning");
    return;
  }
  window.localStorage.setItem("codex-monitor-api-token", monitorState.apiToken);
  if (monitorState.timerId) {
    window.clearInterval(monitorState.timerId);
  }
  monitorState.timerId = window.setInterval(refreshMonitor, MONITOR_INTERVAL_MS);
  void refreshMonitor();
}

document.addEventListener("DOMContentLoaded", () => {
  const tokenInput = document.getElementById("monitor-token");
  if (tokenInput && monitorState.apiToken) {
    tokenInput.value = monitorState.apiToken;
  }
  document.getElementById("monitor-start")?.addEventListener("click", startMonitor);
  document.getElementById("monitor-refresh")?.addEventListener("click", () => void refreshMonitor());
  if (monitorState.apiToken) {
    startMonitor();
  }
});
