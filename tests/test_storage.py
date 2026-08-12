from app import agent, storage, tenants, usage


def _session(tenant_id: str, company_name: str) -> agent.CallSession:
    cfg = tenants.TenantConfig(tenant_id=tenant_id, company_name=company_name)
    session = agent.CallSession(call_id=f"call-{tenant_id}", tenant=cfg)
    session.lead.name = "Test Caller"
    session.usage_totals["input_tokens"] = 1_000_000
    session.usage_totals["output_tokens"] = 1_000_000
    return session


def test_save_session_persists_lead():
    session = _session("tenant-a", "A Co")
    storage.save_session(session)

    leads = storage.list_leads(tenant_id="tenant-a")
    assert len(leads) == 1
    assert leads[0]["data"]["name"] == "Test Caller"


def test_list_leads_is_tenant_scoped():
    storage.save_session(_session("tenant-a", "A Co"))
    storage.save_session(_session("tenant-b", "B Co"))

    leads_a = storage.list_leads(tenant_id="tenant-a")
    leads_b = storage.list_leads(tenant_id="tenant-b")

    assert len(leads_a) == 1
    assert len(leads_b) == 1
    assert leads_a[0]["tenant_id"] == "tenant-a"
    assert leads_b[0]["tenant_id"] == "tenant-b"
    # no cross-tenant leakage
    assert all(l["tenant_id"] == "tenant-a" for l in leads_a)
    assert all(l["tenant_id"] == "tenant-b" for l in leads_b)


def test_list_leads_without_tenant_id_returns_all():
    storage.save_session(_session("tenant-a", "A Co"))
    storage.save_session(_session("tenant-b", "B Co"))

    leads = storage.list_leads()
    assert len(leads) == 2


def test_portal_test_calls_are_not_metered():
    cfg = tenants.TenantConfig(tenant_id="tenant-a", company_name="A Co")
    session = agent.CallSession(
        call_id="portal-test-1", caller_number="portal-test", tenant=cfg
    )
    storage.save_session(session)

    assert usage.summary("tenant-a")["calls"] == 0


def test_save_session_records_cost_into_usage():
    session = _session("tenant-a", "A Co")
    storage.save_session(session)

    s = usage.summary("tenant-a")
    assert s["calls"] == 1
    assert s["claude_usd"] > 0
    assert s["claude_usd"] == round(session.cost_usd, 4)
