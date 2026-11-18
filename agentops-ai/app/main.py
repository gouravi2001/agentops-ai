from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import engine, get_db
from app.graph import investigate
from app.models import AuditEvent, Base, Incident
from app.observability import configure_telemetry
from app.schemas import DecisionRequest, IncidentCreate, IncidentOut

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title="AgentOps AI", version="0.1.0", lifespan=lifespan)
configure_telemetry(app)
DASHBOARD = Path(__file__).resolve().parent.parent / "web" / "index.html"

def _audit(db: Session, incident_id: str, event_type: str, actor: str, payload: dict) -> None:
    db.add(AuditEvent(incident_id=incident_id, event_type=event_type, actor=actor, payload=payload))

def _out(row: Incident) -> IncidentOut:
    return IncidentOut(id=row.id, pipeline=row.pipeline, severity=row.severity, summary=row.summary,
                       observed_at=row.observed_at, status=row.status, labels=row.labels or {},
                       investigation=row.investigation, created_at=row.created_at, updated_at=row.updated_at)

@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(DASHBOARD)

@app.get("/health")
def health():
    return {"status": "ok", "service": "agentops-ai"}

@app.post("/incidents", response_model=IncidentOut, status_code=201)
def create_incident(body: IncidentCreate, db: Session = Depends(get_db)):
    row = Incident(id=str(uuid4()), pipeline=body.pipeline, severity=body.severity.value,
                   summary=body.summary, observed_at=body.observed_at, status="open", labels=body.labels)
    db.add(row)
    _audit(db, row.id, "incident.created", "monitor", {"pipeline": row.pipeline, "severity": row.severity})
    db.commit()
    db.refresh(row)
    return _out(row)

@app.get("/incidents", response_model=list[IncidentOut])
def list_incidents(status: str | None = Query(default=None), db: Session = Depends(get_db)):
    stmt = select(Incident).order_by(Incident.created_at.desc()).limit(200)
    if status:
        stmt = stmt.where(Incident.status == status)
    return [_out(row) for row in db.scalars(stmt).all()]

@app.get("/incidents/{incident_id}", response_model=IncidentOut)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    row = db.get(Incident, incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")
    return _out(row)

@app.post("/incidents/{incident_id}/investigate", response_model=IncidentOut)
def run_investigation(incident_id: str, db: Session = Depends(get_db)):
    row = db.get(Incident, incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")
    if row.status in {"approved", "rejected"}:
        raise HTTPException(409, "A reviewed incident cannot be investigated again")
    row.status = "investigating"
    _audit(db, row.id, "investigation.started", "api", {"workflow": "langgraph-v1"})
    db.commit()
    try:
        result = investigate({"pipeline": row.pipeline, "severity": row.severity, "summary": row.summary,
                             "observed_at": row.observed_at.isoformat(), "labels": row.labels or {}})
        row.investigation = result.model_dump(mode="json")
        row.status = "awaiting_review"
        _audit(db, row.id, "investigation.completed", "agent", {
            "confidence": result.confidence, "tool_calls": result.tool_calls,
            "recommendation": result.recommendation.model_dump(mode="json")})
        db.commit()
        db.refresh(row)
        return _out(row)
    except Exception as exc:
        row.status = "failed"
        _audit(db, row.id, "investigation.failed", "agent", {"error_type": type(exc).__name__})
        db.commit()
        raise HTTPException(500, "Investigation failed; see audit record") from exc

@app.post("/incidents/{incident_id}/decision", response_model=IncidentOut)
def record_decision(incident_id: str, body: DecisionRequest, db: Session = Depends(get_db)):
    row = db.get(Incident, incident_id)
    if not row:
        raise HTTPException(404, "Incident not found")
    if row.status != "awaiting_review" or not row.investigation:
        raise HTTPException(409, "Incident is not awaiting review")
    row.status = body.decision.value
    _audit(db, row.id, f"review.{body.decision.value}", body.reviewer,
           {"comment": body.comment, "recommendation_action": row.investigation["recommendation"]["action"],
            "remediation_dispatched": False})
    db.commit()
    db.refresh(row)
    return _out(row)

@app.get("/incidents/{incident_id}/audit")
def get_audit(incident_id: str, db: Session = Depends(get_db)):
    if not db.get(Incident, incident_id):
        raise HTTPException(404, "Incident not found")
    events = db.scalars(select(AuditEvent).where(AuditEvent.incident_id == incident_id)
                        .order_by(AuditEvent.created_at)).all()
    return [{"id": e.id, "incident_id": e.incident_id, "event_type": e.event_type,
             "actor": e.actor, "payload": e.payload, "created_at": e.created_at} for e in events]
