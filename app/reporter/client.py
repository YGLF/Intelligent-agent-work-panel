from dataclasses import dataclass
from datetime import UTC, datetime

import httpx


@dataclass(slots=True)
class ReporterClient:
    base_url: str
    api_token: str
    timeout: float = 10.0

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}{path}"

    def _headers(self, request_id: str) -> dict[str, str]:
        return {
            "x-api-token": self.api_token,
            "x-request-id": request_id,
        }

    def create_run(self, *, request_id: str, **payload) -> dict:
        response = httpx.post(
            self._url("/api/v1/runs"),
            headers=self._headers(request_id),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_run_by_code(self, *, run_code: str, request_id: str) -> dict:
        response = httpx.get(
            self._url(f"/api/v1/runs/by-code/{run_code}"),
            headers=self._headers(request_id),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def ensure_run(self, *, request_id: str, **payload) -> dict:
        try:
            return self.create_run(request_id=request_id, **payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 409:
                raise
            return self.get_run_by_code(run_code=payload["run_code"], request_id=f"{request_id}-lookup")

    def register_agent(self, *, run_id: int, request_id: str, **payload) -> dict:
        response = httpx.post(
            self._url(f"/api/v1/runs/{run_id}/agents/register"),
            headers=self._headers(request_id),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def get_agent_by_code(self, *, run_id: int, agent_code: str, request_id: str) -> dict:
        response = httpx.get(
            self._url(f"/api/v1/runs/{run_id}/agents/by-code/{agent_code}"),
            headers=self._headers(request_id),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def ensure_agent(self, *, run_id: int, request_id: str, **payload) -> dict:
        try:
            return self.register_agent(run_id=run_id, request_id=request_id, **payload)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code != 409:
                raise
            return self.get_agent_by_code(run_id=run_id, agent_code=payload["agent_code"], request_id=f"{request_id}-lookup")

    def build_status_payload(self, **kwargs) -> dict:
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        return {
            "reported_at": kwargs.get("reported_at", now),
            "last_update_at": kwargs.get("last_update_at", now),
            "risk_level": kwargs.get("risk_level", "low"),
            **kwargs,
        }

    def report_status(self, run_id: int, agent_id: int, payload: dict) -> dict:
        response = httpx.post(
            self._url(f"/api/v1/runs/{run_id}/agents/{agent_id}/status"),
            headers=self._headers(payload["request_id"]),
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
