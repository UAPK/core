"""System metrics and monitoring endpoints"""
from fastapi import APIRouter
from uapk.audit import get_audit_log

router = APIRouter()

@router.get("/metrics")
def get_metrics():
    """Prometheus-style metrics"""
    audit_log = get_audit_log()
    events = audit_log.get_events()

    # Count events by type
    event_counts = {}
    for event in events:
        event_type = event.get("eventType", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1

    metrics_text = "# HELP opspilotos_events_total Total number of audit events\n"
    metrics_text += "# TYPE opspilotos_events_total counter\n"

    for event_type, count in event_counts.items():
        metrics_text += f'opspilotos_events_total{{type="{event_type}"}} {count}\n'

    metrics_text += f'\nopspilotos_events_total{{type="all"}} {len(events)}\n'

    return metrics_text

@router.get("/healthz")
def healthz():
    """Health check"""
    return {"status": "healthy"}

@router.get("/readyz")
def readyz():
    """Readiness check"""
    # In production, check DB connection, etc.
    return {"status": "ready"}
