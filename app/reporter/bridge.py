from __future__ import annotations

from app.reporter.client import ReporterClient


def sync_agent_snapshot(client: ReporterClient, *, run: dict, agent: dict, status: dict) -> dict:
    run_response = client.ensure_run(**run)
    run_id = run_response["data"]["id"]

    agent_response = client.ensure_agent(run_id=run_id, **agent)
    agent_id = agent_response["data"]["id"]

    payload = client.build_status_payload(**status)
    return client.report_status(run_id=run_id, agent_id=agent_id, payload=payload)
