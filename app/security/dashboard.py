from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

DASHBOARD_SESSION_COOKIE_NAME = "dashboard_session"


def _b64encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _b64decode(payload: str) -> bytes:
    padding = "=" * (-len(payload) % 4)
    return base64.urlsafe_b64decode(f"{payload}{padding}")


def create_dashboard_token(*, run_id: int, secret: str, ttl_seconds: int) -> str:
    expires_at = int(time.time()) + ttl_seconds
    payload = {"run_id": run_id, "exp": expires_at}
    payload_segment = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_segment}.{_b64encode(signature)}"


def verify_dashboard_token(*, token: str, run_id: int, secret: str) -> bool:
    try:
        payload_segment, signature_segment = token.split(".", 1)
        expected = hmac.new(secret.encode("utf-8"), payload_segment.encode("ascii"), hashlib.sha256).digest()
        actual = _b64decode(signature_segment)
        if not hmac.compare_digest(expected, actual):
            return False
        payload: dict[str, Any] = json.loads(_b64decode(payload_segment))
        return int(payload.get("run_id", -1)) == run_id and int(payload.get("exp", 0)) >= int(time.time())
    except Exception:
        return False
