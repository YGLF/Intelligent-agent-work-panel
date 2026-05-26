const DASHBOARD_SECTIONS = ["overview", "agents", "risks", "timeline"];
const SECTION_INTERVALS = { overview: 5000, agents: 5000, risks: 5000, timeline: 8000 };
const SECTION_MESSAGES = {
  overview: "Run summary will appear after refresh.",
  agents: "Agent cards will render here.",
  risks: "Risk records will render here.",
  timeline: "Latest events will render here.",
};
const STATUS_OPTIONS = ["pending", "running", "waiting", "blocked", "completed", "failed"];
const PHASE_OPTIONS = ["analysis", "design", "implementation", "test", "integration"];

const dashboardState = {
  config: null,
  failures: { overview: 0, agents: 0, risks: 0, timeline: 0 },
  timers: [],
  detailCache: new Map(),
  lastSuccessfulRefresh: null,
};

function getShell() {
  return document.querySelector("[data-run-id][data-render-mode='dashboard']");
}

function getRunId() {
  return getShell()?.getAttribute("data-run-id") ?? null;
}

function getFlashNode() {
  return document.getElementById("dashboard-flash");
}

function getRefreshStatusNode() {
  return document.getElementById("refresh-status");
}

function getDashboardConfig() {
  if (dashboardState.config) {
    return dashboardState.config;
  }

  const configNode = document.getElementById("dashboard-config");
  if (!configNode?.textContent) {
    dashboardState.config = { apiBase: "/api/v1", authMode: "missing-config" };
    return dashboardState.config;
  }

  try {
    const parsedConfig = JSON.parse(configNode.textContent);
    dashboardState.config = {
      apiBase: typeof parsedConfig.apiBase === "string" && parsedConfig.apiBase ? parsedConfig.apiBase : "/api/v1",
      authMode: typeof parsedConfig.authMode === "string" ? parsedConfig.authMode : "unknown",
    };
  } catch (_error) {
    dashboardState.config = { apiBase: "/api/v1", authMode: "invalid-config" };
  }

  return dashboardState.config;
}

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
  if (Number.isNaN(date.getTime())) {
    return String(value);
  }
  return date.toLocaleString("zh-CN", { hour12: false });
}

function setFlashMessage(message, level = "info") {
  const flashNode = getFlashNode();
  if (!flashNode) {
    return;
  }
  flashNode.textContent = message ?? "";
  flashNode.dataset.level = message ? level : "";
}

function setRefreshStatus(message) {
  const node = getRefreshStatusNode();
  if (node) {
    node.textContent = message;
  }
}

function setSectionStatus(section, status, message = "") {
  const panel = document.querySelector(`[data-refresh-section="${section}"]`);
  const statusNode = document.querySelector(`[data-section-status="${section}"]`);
  const messageNode = document.querySelector(`[data-section-message="${section}"]`);
  if (!panel || !statusNode || !messageNode) {
    return;
  }
  panel.dataset.state = status;
  statusNode.textContent = status;
  messageNode.textContent = message || SECTION_MESSAGES[section] || "";
}

function buildSectionUrl(section) {
  const runId = getRunId();
  if (!runId) {
    return null;
  }
  return `${getDashboardConfig().apiBase}/runs/${runId}/${section}`;
}

function buildAgentDetailUrl(agentId) {
  const runId = getRunId();
  if (!runId || !agentId) {
    return null;
  }
  return `${getDashboardConfig().apiBase}/runs/${runId}/agents/${agentId}`;
}

function buildAgentsQuery() {
  const params = new URLSearchParams();
  const status = document.getElementById("status-filter")?.value ?? "";
  const phase = document.getElementById("phase-filter")?.value ?? "";
  const ownerScope = document.getElementById("owner-scope-filter")?.value?.trim() ?? "";
  const blockedOnly = document.getElementById("blocked-only")?.checked ?? false;

  if (status) {
    params.set("status_filter", status);
  }
  if (phase) {
    params.set("phase", phase);
  }
  if (ownerScope) {
    params.set("owner_scope", ownerScope);
  }
  if (blockedOnly) {
    params.set("blocked_only", "true");
  }
  return params;
}

function buildRequestHeaders(section) {
  return {
    "x-request-id": `dashboard-${section}-${Date.now()}`,
  };
}

function renderKeyValueGrid(items) {
  return `
    <dl class="metric-grid">
      ${items
        .map(
          ([label, value]) => `
            <div class="metric-card">
              <dt>${escapeHtml(label)}</dt>
              <dd>${escapeHtml(value)}</dd>
            </div>
          `,
        )
        .join("")}
    </dl>
  `;
}

function renderOverview(data) {
  const node = document.getElementById("overview-content");
  if (!node) {
    return;
  }
  const phaseDistribution = Object.entries(data.phase_distribution ?? {});
  node.innerHTML = `
    <div class="overview-summary">
      ${renderKeyValueGrid([
        ["Run", `${formatText(data.run_name)} (${formatText(data.run_code)})`],
        ["Status", formatText(data.run_status)],
        ["Total Agents", formatText(data.total_agents, "0")],
        ["Overall Progress", `${formatText(data.overall_progress, "0")}%`],
        ["Running", formatText(data.running_count, "0")],
        ["Blocked", formatText(data.blocked_count, "0")],
        ["Completed", formatText(data.completed_count, "0")],
        ["Failed", formatText(data.failed_count, "0")],
        ["Active Updates 1h", formatText(data.active_updates_last_1h, "0")],
        ["Last Active", formatDate(data.last_active_at)],
      ])}
    </div>
    <section class="subpanel">
      <h3>Phase Distribution</h3>
      ${
        phaseDistribution.length
          ? `<ul class="token-list">${phaseDistribution
              .map(([phase, count]) => `<li><span>${escapeHtml(phase)}</span><strong>${escapeHtml(count)}</strong></li>`)
              .join("")}</ul>`
          : `<p class="empty-state">No phase data yet.</p>`
      }
    </section>
    <section class="subpanel">
      <h3>Staleness</h3>
      <p class="summary-text">${escapeHtml(formatText(data.stale_hint, "No stale signal reported."))}</p>
    </section>
  `;
}

function renderAgents(data) {
  const node = document.getElementById("agents-content");
  if (!node) {
    return;
  }
  if (!data.items?.length) {
    node.innerHTML = `<p class="empty-state">No agents matched the current filters.</p>`;
    return;
  }
  node.innerHTML = data.items
    .map(
      (agent) => `
        <article class="agent-card" data-agent-card="${escapeHtml(agent.id)}">
          <button class="agent-card-button" type="button" data-agent-detail-trigger="${escapeHtml(agent.id)}">
            <div class="agent-card-header">
              <h3>${escapeHtml(agent.agent_name)}</h3>
              <span class="status-pill status-${escapeHtml(agent.status)}">${escapeHtml(agent.status)}</span>
            </div>
            <p class="agent-meta">${escapeHtml(formatText(agent.codex_agent_type, agent.role))} · ${escapeHtml(formatText(agent.owner_scope))}</p>
            <p class="agent-task">${escapeHtml(formatText(agent.current_task, "No current task"))}</p>
            <dl class="agent-stats">
              <div><dt>Phase</dt><dd>${escapeHtml(formatText(agent.phase))}</dd></div>
              <div><dt>Progress</dt><dd>${escapeHtml(formatText(agent.progress_percent, "0"))}%</dd></div>
              <div><dt>Risk</dt><dd>${escapeHtml(formatText(agent.risk_level))}</dd></div>
              <div><dt>Updated</dt><dd>${escapeHtml(formatDate(agent.last_update_at))}</dd></div>
            </dl>
            ${
              agent.blocking_reason
                ? `<p class="inline-warning">Blocked: ${escapeHtml(agent.blocking_reason)}</p>`
                : ""
            }
            ${
              agent.needs_input
                ? `<p class="inline-note">Needs input before next transition.</p>`
                : ""
            }
          </button>
        </article>
      `,
    )
    .join("");
}

function renderRisks(data) {
  const node = document.getElementById("risks-content");
  if (!node) {
    return;
  }
  if (!data.items?.length) {
    node.innerHTML = `<p class="empty-state">No risks recorded for this run.</p>`;
    return;
  }
  node.innerHTML = `
    <div class="list-stack">
      ${data.items
        .map(
          (risk) => `
            <article class="list-card risk-card risk-${escapeHtml(risk.risk_level)}">
              <div class="list-card-header">
                <h3>${escapeHtml(risk.title)}</h3>
                <span class="status-pill status-${escapeHtml(risk.status)}">${escapeHtml(risk.status)}</span>
              </div>
              <p class="summary-text">${escapeHtml(risk.reason)}</p>
              <dl class="compact-grid">
                <div><dt>Type</dt><dd>${escapeHtml(risk.risk_type)}</dd></div>
                <div><dt>Level</dt><dd>${escapeHtml(risk.risk_level)}</dd></div>
                <div><dt>Agent</dt><dd>${escapeHtml(formatText(risk.agent_id))}</dd></div>
                <div><dt>Opened</dt><dd>${escapeHtml(formatDate(risk.opened_at))}</dd></div>
              </dl>
              <p class="summary-text">Suggested action: ${escapeHtml(formatText(risk.suggested_action, "No suggested action"))}</p>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderTimeline(data) {
  const node = document.getElementById("timeline-content");
  if (!node) {
    return;
  }
  if (!data.items?.length) {
    node.innerHTML = `<p class="empty-state">No timeline events captured yet.</p>`;
    return;
  }
  node.innerHTML = `
    <ol class="timeline-list">
      ${data.items
        .map(
          (item) => `
            <li class="timeline-entry">
              <div class="timeline-point"></div>
              <div class="timeline-body">
                <div class="list-card-header">
                  <h3>${escapeHtml(item.summary)}</h3>
                  <time>${escapeHtml(formatDate(item.occurred_at))}</time>
                </div>
                <p class="agent-meta">${escapeHtml(item.event_type)} · Agent ${escapeHtml(item.agent_id)} · ${escapeHtml(item.report_source)}</p>
                <p class="summary-text">
                  Status ${escapeHtml(formatText(item.old_status))} → ${escapeHtml(formatText(item.new_status))}
                  · Phase ${escapeHtml(formatText(item.old_phase))} → ${escapeHtml(formatText(item.new_phase))}
                  · Progress ${escapeHtml(formatText(item.before_progress, "-"))} → ${escapeHtml(formatText(item.after_progress, "-"))}
                </p>
              </div>
            </li>
          `,
        )
        .join("")}
    </ol>
  `;
}

function renderAgentDetail(data) {
  const panel = document.getElementById("agent-detail-panel");
  const body = panel?.querySelector(".agent-detail-body");
  if (!panel || !body) {
    return;
  }
  panel.hidden = false;
  body.innerHTML = `
    <dl class="compact-grid">
      <div><dt>Agent</dt><dd>${escapeHtml(data.agent_name)}</dd></div>
      <div><dt>Status</dt><dd>${escapeHtml(formatText(data.status))}</dd></div>
      <div><dt>Phase</dt><dd>${escapeHtml(formatText(data.phase))}</dd></div>
      <div><dt>Depends On</dt><dd>${escapeHtml((data.depends_on ?? []).join(", ") || "N/A")}</dd></div>
      <div><dt>Handoff To</dt><dd>${escapeHtml(formatText(data.handoff_to))}</dd></div>
      <div><dt>Needs Input</dt><dd>${escapeHtml(String(data.needs_input ?? false))}</dd></div>
      <div><dt>Codex Type</dt><dd>${escapeHtml(formatText(data.codex_agent_type))}</dd></div>
      <div><dt>Started</dt><dd>${escapeHtml(formatDate(data.started_at))}</dd></div>
      <div><dt>Finished</dt><dd>${escapeHtml(formatDate(data.finished_at))}</dd></div>
    </dl>
    <p class="summary-text">Deliverable: ${escapeHtml(formatText(data.deliverable_summary, "No summary"))}</p>
    <p class="summary-text">Conversation: ${escapeHtml(formatText(data.conversation_ref, "No reference"))}</p>
  `;
}

async function refreshSection(section) {
  const baseUrl = buildSectionUrl(section);
  if (!baseUrl) {
    return;
  }
  const url = new URL(baseUrl, window.location.origin);
  if (section === "agents") {
    buildAgentsQuery().forEach((value, key) => url.searchParams.set(key, value));
  }

  setSectionStatus(section, "loading", "Refreshing data from read API...");
  try {
    const response = await fetch(url.toString(), { headers: buildRequestHeaders(section) });
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`);
    }
    const payload = await response.json();
    const data = payload.data ?? {};
    if (section === "overview") {
      renderOverview(data);
    } else if (section === "agents") {
      renderAgents(data);
    } else if (section === "risks") {
      renderRisks(data);
    } else if (section === "timeline") {
      renderTimeline(data);
    }
    dashboardState.failures[section] = 0;
    dashboardState.lastSuccessfulRefresh = new Date();
    setSectionStatus(section, "ready", "Live data loaded.");
    setRefreshStatus(`Last refresh: ${dashboardState.lastSuccessfulRefresh.toLocaleString("zh-CN", { hour12: false })}`);
  } catch (error) {
    dashboardState.failures[section] += 1;
    const message =
      dashboardState.failures[section] >= 3 ? "Refresh failed repeatedly. Showing cached data." : "Refresh failed. Previous data kept.";
    setSectionStatus(section, "stale", message);
    setFlashMessage(`${section} refresh failed: ${error.message}`, "warning");
  }
}

async function showAgentDetail(agentId) {
  if (dashboardState.detailCache.has(agentId)) {
    renderAgentDetail(dashboardState.detailCache.get(agentId));
    return;
  }
  const url = buildAgentDetailUrl(agentId);
  if (!url) {
    return;
  }
  try {
    const response = await fetch(url, { headers: buildRequestHeaders(`agent-${agentId}`) });
    if (!response.ok) {
      throw new Error(`Agent detail failed with status ${response.status}`);
    }
    const payload = await response.json();
    dashboardState.detailCache.set(agentId, payload.data ?? {});
    renderAgentDetail(payload.data ?? {});
  } catch (error) {
    setFlashMessage(`Agent detail refresh failed: ${error.message}`, "warning");
  }
}

function refreshAll() {
  setFlashMessage("");
  DASHBOARD_SECTIONS.forEach((section) => {
    void refreshSection(section);
  });
}

function populateStaticFilters() {
  const statusSelect = document.getElementById("status-filter");
  const phaseSelect = document.getElementById("phase-filter");

  if (statusSelect && statusSelect.options.length <= 1) {
    STATUS_OPTIONS.forEach((status) => {
      statusSelect.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(status)}">${escapeHtml(status)}</option>`);
    });
  }
  if (phaseSelect && phaseSelect.options.length <= 1) {
    PHASE_OPTIONS.forEach((phase) => {
      phaseSelect.insertAdjacentHTML("beforeend", `<option value="${escapeHtml(phase)}">${escapeHtml(phase)}</option>`);
    });
  }
}

function bindEvents() {
  document.getElementById("manual-refresh")?.addEventListener("click", refreshAll);
  document.getElementById("status-filter")?.addEventListener("change", () => void refreshSection("agents"));
  document.getElementById("phase-filter")?.addEventListener("change", () => void refreshSection("agents"));
  document.getElementById("owner-scope-filter")?.addEventListener("change", () => void refreshSection("agents"));
  document.getElementById("blocked-only")?.addEventListener("change", () => void refreshSection("agents"));
  document.getElementById("agents-content")?.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-agent-detail-trigger]");
    if (!trigger) {
      return;
    }
    void showAgentDetail(trigger.getAttribute("data-agent-detail-trigger"));
  });
}

function startPolling() {
  dashboardState.timers.forEach((timerId) => window.clearInterval(timerId));
  dashboardState.timers = DASHBOARD_SECTIONS.map((section) =>
    window.setInterval(() => {
      void refreshSection(section);
    }, SECTION_INTERVALS[section]),
  );
}

function initializeDashboardAuth() {
  const authMode = getDashboardConfig().authMode;
  if (authMode === "dashboard-session") {
    return true;
  }

  DASHBOARD_SECTIONS.forEach((section) => {
    setSectionStatus(section, "stale", "Missing dashboard auth context. Live refresh disabled.");
  });
  setRefreshStatus("Waiting for authenticated dashboard request");
  setFlashMessage("Dashboard session cookie missing; live refresh disabled.", "warning");
  return false;
}

document.addEventListener("DOMContentLoaded", () => {
  populateStaticFilters();
  bindEvents();
  if (!initializeDashboardAuth()) {
    return;
  }
  startPolling();
  refreshAll();
});
