from fastapi.testclient import TestClient

from app import dnc
from app.main import app

ADMIN_KEY = "test-admin-key"


def _client() -> TestClient:
    return TestClient(app)


def test_add_list_remove_round_trip():
    dnc.add("+9779800000001", reason="asked to stop")
    assert dnc.is_listed("+9779800000001")

    listed = dnc.list_all()
    assert any(r["e164"] == "+9779800000001" for r in listed)

    dnc.remove("+9779800000001")
    assert not dnc.is_listed("+9779800000001")


def test_admin_dnc_endpoints_require_admin_key():
    c = _client()
    assert c.get("/admin/dnc").status_code == 401
    assert c.post("/admin/dnc", json={"e164": "+9779800000002"}).status_code == 401
    assert c.delete("/admin/dnc/+9779800000002").status_code == 401


def test_admin_can_add_and_remove_via_api():
    c = _client()
    headers = {"X-Admin-Key": ADMIN_KEY}

    resp = c.post("/admin/dnc", json={"e164": "+9779800000003"}, headers=headers)
    assert resp.status_code == 200
    assert dnc.is_listed("+9779800000003")

    listed = c.get("/admin/dnc", headers=headers).json()
    assert any(r["e164"] == "+9779800000003" for r in listed)

    resp = c.delete("/admin/dnc/+9779800000003", headers=headers)
    assert resp.status_code == 200
    assert not dnc.is_listed("+9779800000003")


def test_test_call_blocked_for_dnc_number(monkeypatch):
    from app import config

    monkeypatch.setattr(config, "TWILIO_ACCOUNT_SID", "sid")
    monkeypatch.setattr(config, "TWILIO_AUTH_TOKEN", "token")
    monkeypatch.setattr(config, "TWILIO_PHONE_NUMBER", "+15550000000")
    monkeypatch.setattr(config, "PUBLIC_BASE_URL", "https://example.test")

    dnc.add("+9779800000004")
    c = _client()
    resp = c.post(
        "/admin/test-call",
        json={"to": "+9779800000004"},
        headers={"X-Admin-Key": ADMIN_KEY},
    )
    assert resp.status_code == 403
    assert "do-not-call" in resp.json()["detail"]
