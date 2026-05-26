def _create_dashboard_run(client):
    run_response = client.post(
        "/api/v1/runs",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dashboard-run"},
        json={
            "run_code": "run-dashboard",
            "run_name": "Dashboard Run",
            "source_type": "codex",
        },
    )
    assert run_response.status_code == 201
    return run_response.json()["data"]


def test_dashboard_page_requires_dashboard_token(client):
    run = _create_dashboard_run(client)

    response = client.get(f"/runs/{run['id']}/dashboard")

    assert response.status_code == 401
    assert response.json() == {"detail": "dashboard access token is required"}


def test_dashboard_page_sets_http_only_session_cookie(client):
    run = _create_dashboard_run(client)

    token_response = client.get(
        f"/runs/{run['id']}/dashboard-token",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dashboard-token-cookie"},
    )

    assert token_response.status_code == 200
    cookie_header = token_response.headers.get("set-cookie", "")
    assert "dashboard_session=" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "SameSite=lax" in cookie_header

    page_response = client.get(f"/runs/{run['id']}/dashboard")
    assert page_response.status_code == 200
    assert "window.__DASHBOARD_TOKEN__" not in page_response.text
    assert '"dashboardToken":' not in page_response.text

    client.cookies.clear()
    response = client.get(
        f"/runs/{run['id']}/dashboard",
        headers={"x-dashboard-token": "invalid"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "dashboard access token is required"}


def test_dashboard_token_route_issues_token_for_existing_run(client):
    run = _create_dashboard_run(client)

    token_response = client.get(
        f"/runs/{run['id']}/dashboard-token",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dashboard-token"},
    )

    assert token_response.status_code == 200
    payload = token_response.json()
    assert payload["data"]["expires_in"] > 0
    assert payload["data"]["access_token"]

    page_response = client.get(
        f"/runs/{run['id']}/dashboard?access_token={payload['data']['access_token']}",
    )

    assert page_response.status_code == 200
    html = page_response.text
    assert "Agent Status Dashboard" in html
    assert 'data-refresh-section="overview"' in html
    assert 'data-refresh-section="agents"' in html
    assert 'data-refresh-section="risks"' in html
    assert 'data-refresh-section="timeline"' in html
    assert 'id="status-filter"' in html
    assert 'id="phase-filter"' in html
    assert 'id="owner-scope-filter"' in html
    assert 'id="blocked-only"' in html
    assert 'id="manual-refresh"' in html
    assert 'id="refresh-status"' in html
    assert 'id="dashboard-flash"' in html
    assert 'data-endpoint="overview"' in html
    assert 'data-endpoint="agents"' in html
    assert 'data-endpoint="risks"' in html
    assert 'data-endpoint="timeline"' in html
    assert 'id="overview-content"' in html
    assert 'id="agents-content"' in html
    assert 'id="risks-content"' in html
    assert 'id="timeline-content"' in html
    assert 'id="agent-detail-panel"' in html
    assert 'data-render-mode="dashboard"' in html
    assert 'id="dashboard-config"' in html
    assert '"apiBase": "/api/v1"' in html
    assert '"authMode": "dashboard-session"' in html
    assert 'data-config-source="page-config"' in html
    assert '/static/js/dashboard.js' in html
    assert '"x-api-token": "dev-token"' not in html
    assert 'window.__DASHBOARD_TOKEN__' not in html


def test_dashboard_token_route_requires_api_headers(client):
    run = _create_dashboard_run(client)

    response = client.get(
        f"/runs/{run['id']}/dashboard-token",
        headers={"x-request-id": "req-dashboard-token-missing-api-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "x-api-token header is required"}


def test_dashboard_token_allows_read_only_polling(client):
    run = _create_dashboard_run(client)

    token_response = client.get(
        f"/runs/{run['id']}/dashboard-token",
        headers={"x-api-token": "dev-token", "x-request-id": "req-dashboard-token-read"},
    )
    token = token_response.json()["data"]["access_token"]

    overview_response = client.get(
        f"/api/v1/runs/{run['id']}/overview",
        headers={"x-dashboard-token": token, "x-request-id": "req-dashboard-overview"},
    )

    assert overview_response.status_code == 200
    assert overview_response.json()["data"]["run_id"] == run["id"]
