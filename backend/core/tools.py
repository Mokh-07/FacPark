"""
FacPark - Tools Catalog
Backend tools for LLM Agent. RBAC enforced server-side.

STUDENT TOOLS (6) - Read Only:
1) get_my_profile, 2) get_my_vehicles, 3) get_my_subscription
4) get_my_slot, 5) get_my_access_history, 6) ask_reglement

ADMIN TOOLS (11) - Read + Write (audit_logs required):
1) list_students, 2) create_student, 3) delete_student
4) add_vehicle, 5) remove_vehicle, 6) create_subscription
7) renew_subscription, 8) assign_slot, 9) suspend_access
10) get_admin_stats, 11) check_plate_access
"""

from datetime import date, timedelta
from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import logging

from backend.config import settings
from backend.db.models import (
    User, Vehicle, Subscription, Slot, SlotAssignment, Suspension,
    AccessEvent, AuditLog, SecurityEvent, UserRole, SubscriptionType, PlateType
)
from backend.core.decision import check_plate_access as decision_check

logger = logging.getLogger(__name__)


# =============================================================================
# TOOL RESPONSE FORMAT
# =============================================================================
def tool_response(success: bool, data: Any = None, message: str = "",
                  error: Optional[str] = None) -> dict:
    """Standard response format for all tools."""
    return {"success": success, "data": data, "message": message, "error": error}


# =============================================================================
# RBAC ENFORCEMENT
# =============================================================================
def require_role(db: Session, user_id: int, required_role: UserRole,
                 action: str, ip: Optional[str] = None) -> Optional[dict]:
    """Check if user has required role. Returns error response if not, None if OK."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return tool_response(False, error="Utilisateur non trouvé.")
    if user.role != required_role:
        _log_security_event(db, "RBAC_VIOLATION", user_id,
            f"Tentative d'action admin '{action}' par {user.role.value}", ip=ip)
        return tool_response(False, error="Accès refusé. Permissions insuffisantes.")
    return None


def _log_audit(db: Session, admin_id: int, action: str, entity_type: str,
               entity_id: Optional[int] = None, details: Optional[dict] = None,
               ip: Optional[str] = None):
    """Log admin action to audit_logs."""
    log = AuditLog(admin_id=admin_id, action=action, entity_type=entity_type,
                   entity_id=entity_id, details=json.dumps(details) if details else None,
                   ip_address=ip)
    db.add(log)
    db.commit()


def _log_security_event(db: Session, event_type: str, user_id: Optional[int],
                        description: str, payload: Optional[str] = None,
                        pattern: Optional[str] = None, severity: str = "MEDIUM",
                        ip: Optional[str] = None, user_agent: Optional[str] = None):
    """Log security incident to security_events."""
    event = SecurityEvent(event_type=event_type, user_id=user_id,
        description=description, payload=payload, pattern_matched=pattern,
        severity=severity, ip_address=ip, user_agent=user_agent)
    db.add(event)
    db.commit()


# =============================================================================
# STUDENT TOOLS (6) - READ ONLY
# =============================================================================
def get_my_profile(db: Session, user_id: int) -> dict:
    """Get current user's profile."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return tool_response(False, error="Profil non trouvé.")
    return tool_response(True, data={
        "id": user.id, "email": user.email, "full_name": user.full_name,
        "role": user.role.value, "is_active": user.is_active,
        "created_at": user.created_at.isoformat()
    }, message="Profil récupéré.")


def get_my_vehicles(db: Session, user_id: int) -> dict:
    """Get current user's vehicles."""
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == user_id).all()
    data = [{"id": v.id, "plate": v.plate, "plate_type": v.plate_type.value,
             "make": v.make, "model": v.model, "color": v.color} for v in vehicles]
    return tool_response(True, data=data,
        message=f"{len(data)} véhicule(s) trouvé(s). Max autorisé: 3.")


def get_my_subscription(db: Session, user_id: int) -> dict:
    """Get current user's active subscription."""
    sub = db.query(Subscription).filter(
        Subscription.user_id == user_id, Subscription.is_active == 1).first()
    if not sub:
        return tool_response(True, data=None,
            message="Aucun abonnement actif. Contactez l'administration.")
    days_left = (sub.end_date - date.today()).days
    return tool_response(True, data={
        "id": sub.id, "type": sub.subscription_type.value,
        "start_date": sub.start_date.isoformat(), "end_date": sub.end_date.isoformat(),
        "days_remaining": max(0, days_left), "is_expired": sub.is_expired
    }, message=f"Abonnement {sub.subscription_type.value} actif. {days_left} jours restants.")


def get_my_slot(db: Session, user_id: int) -> dict:
    """Get current user's assigned parking slot."""
    assign = db.query(SlotAssignment).filter(
        SlotAssignment.user_id == user_id, SlotAssignment.is_active == 1).first()
    if not assign:
        return tool_response(True, data=None, message="Aucune place attribuée.")
    return tool_response(True, data={
        "slot_code": assign.slot.code, "zone": assign.slot.zone,
        "assigned_at": assign.assigned_at.isoformat()
    }, message=f"Place {assign.slot.code} dans la zone {assign.slot.zone}.")


def get_my_access_history(db: Session, user_id: int, limit: int = 10) -> dict:
    """Get user's recent access events."""
    events = db.query(AccessEvent).filter(AccessEvent.user_id == user_id)\
        .order_by(AccessEvent.created_at.desc()).limit(min(limit, 50)).all()
    data = [{"plate": e.plate, "decision": e.decision.value, "ref_code": e.ref_code,
             "message": e.message, "created_at": e.created_at.isoformat()} for e in events]
    return tool_response(True, data=data, message=f"{len(data)} événement(s) récent(s).")


def get_my_suspension_status(db: Session, user_id: int) -> dict:
    """Check if user has an active suspension."""
    suspension = db.query(Suspension).filter(
        Suspension.user_id == user_id,
        Suspension.start_date <= date.today(),
        Suspension.end_date >= date.today()
    ).first()
    
    if suspension:
        return tool_response(True, data={
            "is_suspended": True,
            "reason": suspension.reason,
            "end_date": suspension.end_date.isoformat(),
            "days_remaining": (suspension.end_date - date.today()).days
        }, message=f"⚠️ Accès suspendu jusqu'au {suspension.end_date}. Raison: {suspension.reason}")
    
    return tool_response(True, data={
        "is_suspended": False
    }, message="Aucune suspension active.")


def ask_reglement(db: Session, user_id: int, query: str, top_k: int = 5) -> dict:
    """Query the parking regulations via RAG. Citations validated server-side."""
    # Import here to avoid circular imports
    from backend.core.rag import query_rag
    result = query_rag(query, top_k=top_k)
    return tool_response(True, data=result,
        message="Réponse basée sur le règlement du parking.")
