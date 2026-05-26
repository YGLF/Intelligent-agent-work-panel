from app.reporter.client import ReporterClient
from app.reporter.bridge import sync_agent_snapshot


def test_reporter_builds_status_request_payload():
    client = ReporterClient(base_url="http://localhost:8000", api_token="dev-token")

    payload = client.build_status_payload(
        agent_name="Infra Agent",
        status="running",
        phase="implementation",
        progress_percent=60,
        current_task="Creating dashboard route",
        reported_by="codex-orchestrator",
        report_source="codex-orchestrator",
        request_id="req-321",
        idempotency_key="idem-321",
    )

    assert payload["status"] == "running"
    assert payload["phase"] == "implementation"
    assert payload["reported_by"] == "codex-orchestrator"
    assert payload["risk_level"] == "low"
    assert payload["request_id"] == "req-321"
    assert "reported_at" in payload
    assert "last_update_at" in payload


def test_reporter_posts_status_update_with_request_headers(monkeypatch):
    captured = {}

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"success": True, "code": "OK"}

    def fake_post(url, *, headers, json, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return DummyResponse()

    monkeypatch.setattr("app.reporter.client.httpx.post", fake_post)

    client = ReporterClient(base_url="http://localhost:8000/", api_token="dev-token")
    payload = client.build_status_payload(
        agent_name="Infra Agent",
        status="blocked",
        phase="test",
        progress_percent=70,
        current_task="Waiting for test environment",
        blocking_reason="Need deployment slot",
        risk_level="high",
        reported_by="codex-orchestrator",
        report_source="codex-orchestrator",
        request_id="req-456",
        idempotency_key="idem-456",
    )

    result = client.report_status(run_id=11, agent_id=7, payload=payload)

    assert result["success"] is True
    assert captured["url"] == "http://localhost:8000/api/v1/runs/11/agents/7/status"
    assert captured["headers"]["x-api-token"] == "dev-token"
    assert captured["headers"]["x-request-id"] == "req-456"
    assert captured["json"]["blocking_reason"] == "Need deployment slot"
    assert captured["timeout"] == 10.0


def test_bridge_syncs_run_agent_and_status_snapshot():
    calls = []

    class DummyClient:
        def ensure_run(self, **payload):
            calls.append(("ensure_run", payload))
            return {"data": {"id": 11}}

        def ensure_agent(self, *, run_id, **payload):
            calls.append(("ensure_agent", run_id, payload))
            return {"data": {"id": 7}}

        def build_status_payload(self, **payload):
            calls.append(("build_status_payload", payload))
            return {"request_id": payload["request_id"], **payload}

        def report_status(self, *, run_id, agent_id, payload):
            calls.append(("report_status", run_id, agent_id, payload))
            return {"success": True, "data": {"id": agent_id}}

    result = sync_agent_snapshot(
        DummyClient(),
        run={"request_id": "req-run", "run_code": "run-bridge", "run_name": "Bridge Run", "source_type": "codex"},
        agent={
            "request_id": "req-agent",
            "agent_code": "agent-bridge",
            "agent_name": "Bridge Agent",
            "role": "worker",
            "owner_scope": "codex",
        },
        status={
            "request_id": "req-status",
            "agent_name": "Bridge Agent",
            "status": "running",
            "phase": "implementation",
            "progress_percent": 10,
            "risk_level": "low",
            "reported_by": "codex-orchestrator",
            "report_source": "reporter",
        },
    )

    assert result["success"] is True
    assert calls[0][0] == "ensure_run"
    assert calls[1][0] == "ensure_agent"
    assert calls[1][1] == 11
    assert calls[-1][0] == "report_status"
    assert calls[-1][1] == 11
    assert calls[-1][2] == 7
