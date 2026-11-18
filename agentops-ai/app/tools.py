"""Read-only evidence tools. Replace fixture bodies with restricted client calls."""
from typing import Any
from pydantic import BaseModel, Field, ValidationError

class Evidence(BaseModel):
    id: str = Field(pattern=r"^ev-[a-z0-9-]{3,40}$")
    source: str = Field(min_length=1, max_length=80)
    observed_at: str = Field(min_length=10, max_length=40)
    detail: str = Field(min_length=1, max_length=500)

class ToolDenied(Exception):
    pass

# Explicit read-only allowlist. There is intentionally no shell, SQL write, or remediation tool.
ALLOWED_TOOLS = {"recent_run_status", "upstream_health", "recent_log_signals"}

def recent_run_status(pipeline: str) -> dict[str, Any]:
    return {"id": "ev-run-001", "source": "scheduler", "observed_at": "2026-11-17T14:08:00Z",
            "detail": f"{pipeline}: task load_orders failed after 3 retries; exit code 137"}

def upstream_health(pipeline: str) -> dict[str, Any]:
    return {"id": "ev-upstream-001", "source": "upstream_monitor", "observed_at": "2026-11-17T14:05:00Z",
            "detail": f"{pipeline}: upstream source freshness is 47 minutes behind SLA"}

def recent_log_signals(pipeline: str) -> dict[str, Any]:
    return {"id": "ev-log-001", "source": "log_summary", "observed_at": "2026-11-17T14:09:00Z",
            "detail": f"{pipeline}: worker memory limit reached; no credentials or raw records included"}

_REGISTRY = {
    "recent_run_status": recent_run_status,
    "upstream_health": upstream_health,
    "recent_log_signals": recent_log_signals,
}

def call_readonly_tool(name: str, pipeline: str) -> Evidence:
    if name not in ALLOWED_TOOLS or name not in _REGISTRY:
        raise ToolDenied(f"Tool is not authorized: {name}")
    raw = _REGISTRY[name](pipeline)
    try:
        return Evidence.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Tool returned invalid evidence: {exc.errors()[0]['type']}") from exc
