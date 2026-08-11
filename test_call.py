"""
Simulate a phone call in your terminal — no telephony needed.

Usage:
  python test_call.py                 # default tenant (from .env)
  python test_call.py <tenant_id>     # a specific tenant's agent

Type what the "caller" says; the agent replies. Ctrl+C to quit.
"""
import sys

from app import agent, storage, tenants


def main():
    tenant_id = sys.argv[1] if len(sys.argv) > 1 else None
    cfg = tenants.get_or_default(tenant_id)
    print(f"[tenant: {cfg.tenant_id} — {cfg.company_name}, agent {cfg.agent_name}]")

    session = agent.CallSession(
        call_id="test-local", caller_number="+9779800000000", tenant=cfg
    )
    print(f"AGENT: {agent.greeting(session)}")
    try:
        while not session.ended:
            user = input("CALLER: ").strip()
            if not user:
                continue
            print(f"AGENT: {agent.respond(session, user)}")
    except (KeyboardInterrupt, EOFError):
        print("\n[call interrupted]")
    storage.save_session(session)
    print("\n--- Lead captured ---")
    for k, v in session.lead.to_dict().items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
