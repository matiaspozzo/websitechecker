from unittest.mock import patch

SITE_PAYLOAD = {
    "name": "Example",
    "url": "https://example.com",
    "type": "laravel",
    "check_interval_seconds": 300,
    "expected_keyword": None,
    "active": True,
}


def test_requires_auth(client):
    resp = client.get("/api/sites")
    assert resp.status_code == 401


def test_create_site_triggers_scheduler_reload(authed_client):
    with patch("app.scheduler.reload_site") as mock_reload:
        resp = authed_client.post("/api/sites", json=SITE_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Example"
    assert body["expected_domain"] == "example.com"
    mock_reload.assert_called_once()


def test_list_and_get_site(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    listed = authed_client.get("/api/sites").json()
    assert len(listed) == 1

    fetched = authed_client.get(f"/api/sites/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "Example"


def test_update_site_recomputes_domain_and_reloads(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    with patch("app.scheduler.reload_site") as mock_reload:
        resp = authed_client.put(f"/api/sites/{created['id']}", json={"url": "https://other.com"})
    assert resp.status_code == 200
    assert resp.json()["expected_domain"] == "other.com"
    mock_reload.assert_called_once()


def test_pause_and_resume(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    with patch("app.scheduler.reload_site") as mock_reload:
        paused = authed_client.post(f"/api/sites/{created['id']}/pause")
    assert paused.json()["active"] is False
    mock_reload.assert_called_once()

    with patch("app.scheduler.reload_site") as mock_reload:
        resumed = authed_client.post(f"/api/sites/{created['id']}/resume")
    assert resumed.json()["active"] is True
    mock_reload.assert_called_once()


def test_delete_site_removes_jobs(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    with patch("app.scheduler.remove_site_jobs") as mock_remove:
        resp = authed_client.delete(f"/api/sites/{created['id']}")
    assert resp.status_code == 204
    mock_remove.assert_called_once_with(created["id"])

    assert authed_client.get(f"/api/sites/{created['id']}").status_code == 404


def test_silence_site(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    resp = authed_client.post(f"/api/sites/{created['id']}/silence", json={"hours": 2})
    assert resp.status_code == 200


def test_create_site_trims_whitespace_from_url_and_client_name(authed_client):
    # Regression: a trailing space in a pasted URL (e.g. "https://example.com ")
    # broke DNS resolution entirely and the site was reported as permanently
    # down with no useful diagnostic -- not a code bug, just untrimmed input.
    payload = {**SITE_PAYLOAD, "url": " https://example.com ", "client_name": " Acme Corp "}
    with patch("app.scheduler.reload_site"):
        resp = authed_client.post("/api/sites", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["url"] == "https://example.com"
    assert body["expected_domain"] == "example.com"
    assert body["client_name"] == "Acme Corp"


def test_update_site_trims_whitespace_from_url(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    with patch("app.scheduler.reload_site"):
        resp = authed_client.put(f"/api/sites/{created['id']}", json={"url": " https://trailing-space.example.com "})

    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://trailing-space.example.com"
    assert body["expected_domain"] == "trailing-space.example.com"


def test_check_now_returns_202(authed_client):
    with patch("app.scheduler.reload_site"):
        created = authed_client.post("/api/sites", json=SITE_PAYLOAD).json()

    with patch("app.checks.runner.run_all_checks_for_site"):
        resp = authed_client.post(f"/api/sites/{created['id']}/check-now")
    assert resp.status_code == 202
