from app.graph import investigate

SAMPLE = {
    "pipeline": "orders-hourly", "severity": "high",
    "summary": "Freshness SLA missed after retries", "observed_at": "2026-11-17T14:10:00Z",
    "labels": {"team": "warehouse"},
}

def test_workflow_is_bounded_and_returns_structured_review():
    result = investigate(SAMPLE)
    assert result.tool_calls <= 3
    assert result.tool_calls == len(result.evidence)
    assert result.recommendation.requires_approval is True
    assert set(result.recommendation.evidence_ids) == {row["id"] for row in result.evidence}
    assert result.recommendation.action in {
        "retry_failed_task", "pause_pipeline", "notify_owner", "inspect_upstream"
    }

def test_workflow_evidence_is_schema_validated():
    result = investigate(SAMPLE)
    assert result.evidence
    assert all(row["id"].startswith("ev-") and row["detail"] for row in result.evidence)
