import pytest
from pydantic import ValidationError
from app import tools
from app.schemas import IncidentCreate

def test_tool_allowlist_denies_unregistered_actions():
    with pytest.raises(tools.ToolDenied):
        tools.call_readonly_tool("delete_source_table", "orders-hourly")

def test_evidence_contract_rejects_malformed_tool_result(monkeypatch):
    monkeypatch.setitem(tools._REGISTRY, "recent_run_status", lambda pipeline: {
        "id": "bad-id", "source": "scheduler", "observed_at": "yesterday", "detail": "x"})
    with pytest.raises(ValueError, match="invalid evidence"):
        tools.call_readonly_tool("recent_run_status", "orders-hourly")

def test_incident_input_rejects_unknown_fields():
    payload = {"pipeline": "orders", "severity": "high", "summary": "pipeline delayed",
               "observed_at": "2026-11-17T14:00:00Z", "labels": {}, "run_shell": True}
    with pytest.raises(ValidationError):
        IncidentCreate.model_validate(payload)
