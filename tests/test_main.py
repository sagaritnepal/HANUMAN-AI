from fastapi.testclient import TestClient

from app import storage, tenants
from app.main import app

ADMIN_KEY = "test-admin-key"


def _client() -> TestClient:
    return TestClient(app)


def test_health_no_auth_required():
    resp = _client().get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_admin_endpoints_require_admin_key():
    c = _client()
    assert c.get("/admin/tenants").status_code == 401
    assert c.get("/admin/tenants", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert c.get("/admin/tenants", headers={"X-Admin-Key": ADMIN_KEY}).status_code == 200


def test_admin_create_and_list_tenant():
    c = _client()
    resp = c.post(
        "/admin/tenants",
        json={"company_name": "Test Co"},
        headers={"X-Admin-Key": ADMIN_KEY},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["company_name"] == "Test Co"
    assert body["api_key"].startswith("tk_")

    listed = c.get("/admin/tenants", headers={"X-Admin-Key": ADMIN_KEY}).json()
    assert any(t["tenant_id"] == body["tenant_id"] for t in listed)


def test_portal_requires_valid_tenant_key():
    c = _client()
    assert c.get("/portal/me").status_code == 401
    assert c.get("/portal/me", headers={"X-Tenant-Key": "bogus"}).status_code == 401


def test_portal_editable_fields_are_restricted():
    cfg = tenants.create(company_name="Editable Co", included_minutes=1000)
    c = _client()
    headers = {"X-Tenant-Key": cfg.api_key}

    resp = c.put(
        "/portal/me",
        json={
            "agent_name": "NewName",          # allowed
            "api_key": "tk_hijacked",         # NOT allowed
            "status": "suspended",            # NOT allowed
            "included_minutes": 999999,       # NOT allowed
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["agent_name"] == "NewName"
    assert "api_key" not in body  # never echoed back

    # re-fetch from storage directly to check the disallowed fields didn't change
    fresh = tenants.get(cfg.tenant_id)
    assert fresh.api_key == cfg.api_key
    assert fresh.status == "active"
    assert fresh.included_minutes == 1000


def test_portal_leads_are_tenant_scoped():
    cfg_a = tenants.create(company_name="Portal A")
    cfg_b = tenants.create(company_name="Portal B")

    from app import agent as agent_mod

    session_a = agent_mod.CallSession(call_id="call-a", tenant=cfg_a)
    session_a.lead.name = "Caller A"
    storage.save_session(session_a)

    session_b = agent_mod.CallSession(call_id="call-b", tenant=cfg_b)
    session_b.lead.name = "Caller B"
    storage.save_session(session_b)

    c = _client()
    leads_a = c.get("/portal/leads", headers={"X-Tenant-Key": cfg_a.api_key}).json()
    leads_b = c.get("/portal/leads", headers={"X-Tenant-Key": cfg_b.api_key}).json()

    assert len(leads_a) == 1 and leads_a[0]["data"]["name"] == "Caller A"
    assert len(leads_b) == 1 and leads_b[0]["data"]["name"] == "Caller B"


def test_admin_leads_scoped_by_query_param():
    cfg_a = tenants.create(company_name="Admin Leads A")
    cfg_b = tenants.create(company_name="Admin Leads B")

    from app import agent as agent_mod

    storage.save_session(agent_mod.CallSession(call_id="x1", tenant=cfg_a))
    storage.save_session(agent_mod.CallSession(call_id="x2", tenant=cfg_b))

    c = _client()
    resp = c.get(
        f"/admin/leads?tenant_id={cfg_a.tenant_id}",
        headers={"X-Admin-Key": ADMIN_KEY},
    )
    leads = resp.json()
    assert len(leads) == 1
    assert leads[0]["tenant_id"] == cfg_a.tenant_id
