from app import tenants


def test_create_and_get_roundtrip():
    cfg = tenants.create(company_name="Acme Travel")
    fetched = tenants.get(cfg.tenant_id)
    assert fetched is not None
    assert fetched.company_name == "Acme Travel"
    assert fetched.api_key.startswith("tk_")


def test_get_missing_tenant_returns_none():
    assert tenants.get("does-not-exist") is None


def test_get_or_default_falls_back_to_env_defaults():
    cfg = tenants.get_or_default(None)
    assert cfg.tenant_id == tenants.DEFAULT_TENANT_ID

    cfg2 = tenants.get_or_default("nonexistent-tenant")
    assert cfg2.tenant_id == tenants.DEFAULT_TENANT_ID


def test_get_or_default_returns_real_tenant_when_present():
    created = tenants.create(company_name="Real Co")
    fetched = tenants.get_or_default(created.tenant_id)
    assert fetched.tenant_id == created.tenant_id
    assert fetched.company_name == "Real Co"


def test_get_by_api_key():
    created = tenants.create(company_name="Keyed Co")
    fetched = tenants.get_by_api_key(created.api_key)
    assert fetched is not None
    assert fetched.tenant_id == created.tenant_id


def test_get_by_api_key_invalid_returns_none():
    assert tenants.get_by_api_key("tk_bogus") is None
    assert tenants.get_by_api_key("") is None


def test_delete_removes_tenant_and_numbers():
    created = tenants.create(company_name="Gone Co")
    tenants.map_number("+9779800000001", created.tenant_id)

    tenants.delete(created.tenant_id)

    assert tenants.get(created.tenant_id) is None
    assert tenants.tenant_for_number("+9779800000001") is None


def test_number_mapping_resolves_to_tenant():
    created = tenants.create(company_name="Mapped Co")
    tenants.map_number("+9779800000002", created.tenant_id)
    assert tenants.tenant_for_number("+9779800000002") == created.tenant_id


def test_list_all_includes_created_tenants():
    tenants.create(company_name="List Co A")
    tenants.create(company_name="List Co B")
    names = {t["company_name"] for t in tenants.list_all()}
    assert {"List Co A", "List Co B"} <= names
