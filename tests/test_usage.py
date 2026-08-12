from app import usage


def test_record_call_accumulates_across_calls():
    usage.record_call("tenant-a", 60, cost_usd=0.01)
    usage.record_call("tenant-a", 120, cost_usd=0.02)

    s = usage.summary("tenant-a")
    assert s["calls"] == 2
    assert s["minutes"] == 3.0
    assert s["claude_usd"] == 0.03


def test_summary_for_unknown_tenant_is_zeroed():
    s = usage.summary("nobody")
    assert s == {"month": s["month"], "calls": 0, "minutes": 0.0, "claude_usd": 0.0}


def test_over_cap():
    usage.record_call("tenant-a", 600)  # 10 minutes
    assert usage.over_cap("tenant-a", included_minutes=5) is True
    assert usage.over_cap("tenant-a", included_minutes=20) is False


def test_all_tenants_summary_scopes_correctly():
    usage.record_call("tenant-a", 60, cost_usd=0.01)
    usage.record_call("tenant-b", 120, cost_usd=0.02)

    rows = {r["tenant_id"]: r for r in usage.all_tenants_summary()}
    assert rows["tenant-a"]["calls"] == 1
    assert rows["tenant-b"]["calls"] == 1
    assert rows["tenant-a"]["claude_usd"] == 0.01
    assert rows["tenant-b"]["claude_usd"] == 0.02


def test_record_call_negative_duration_clamped_to_zero():
    usage.record_call("tenant-a", -50)
    s = usage.summary("tenant-a")
    assert s["minutes"] == 0.0
