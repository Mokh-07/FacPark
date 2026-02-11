"""
FacPark - Admin API
Administrative endpoints for user/vehicle/subscription management.
All endpoints require ADMIN role.
"""

from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.db.session import get_db
from backend.db.models import (
    User, Vehicle, Subscription, Slot, SlotAssignment, 
    Suspension, AccessEvent, AuditLog, SecurityEvent, UserRole
)
from backend.api.auth import get_current_admin
from backend.core.tools_admin import (
    list_students, create_student, delete_student,
    add_vehicle, remove_vehicle, create_subscription,
    renew_subscription, assign_slot, suspend_access,
    get_admin_stats
)

router = APIRouter()


# =============================================================================
# SCHEMAS
# =============================================================================
class StudentCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str = "changeme123"


class VehicleAdd(BaseModel):
    student_email: EmailStr
    plate: str
    plate_type: str = "TN"


class SubscriptionCreate(BaseModel):
    student_email: EmailStr
    sub_type: str  # MENSUEL, SEMESTRIEL, ANNUEL


class SubscriptionRenew(BaseModel):
    student_email: EmailStr
    days: int


class SlotAssign(BaseModel):
    student_email: EmailStr
    slot_code: str


class SuspensionCreate(BaseModel):
    student_email: EmailStr
    days: int
    reason: str


class SlotResponse(BaseModel):
    id: int
    code: str
    zone: str
    is_available: bool


class AuditLogResponse(BaseModel):
    id: int
    admin_email: str
    action: str
    entity_type: str
    details: Optional[str]
    created_at: str


class SecurityEventResponse(BaseModel):
    id: int
    event_type: str
    user_email: Optional[str]
    description: str
    severity: str
    created_at: str


# =============================================================================
# STUDENT MANAGEMENT
# =============================================================================
@router.get("/students")
async def get_students(
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    request: Request = None,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all students with optional search."""
    ip = request.client.host if request.client else None
    return list_students(db, admin.id, search, limit, ip)


@router.post("/students")
async def add_student(
    data: StudentCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a new student account."""
    ip = request.client.host if request.client else None
    return create_student(db, admin.id, data.email, data.full_name, data.password, ip)


@router.delete("/students/{email}")
async def remove_student(
    email: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a student account."""
    ip = request.client.host if request.client else None
    return delete_student(db, admin.id, email, ip)


# =============================================================================
# VEHICLE MANAGEMENT
# =============================================================================
@router.post("/vehicles")
async def add_student_vehicle(
    data: VehicleAdd,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Add a vehicle to a student."""
    ip = request.client.host if request.client else None
    return add_vehicle(db, admin.id, data.student_email, data.plate, data.plate_type, ip)


@router.delete("/vehicles/{plate}")
async def remove_student_vehicle(
    plate: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Remove a vehicle by plate."""
    ip = request.client.host if request.client else None
    return remove_vehicle(db, admin.id, plate, ip)


# =============================================================================
# SUBSCRIPTION MANAGEMENT
# =============================================================================
@router.post("/subscriptions")
async def create_student_subscription(
    data: SubscriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Create a subscription for a student."""
    ip = request.client.host if request.client else None
    return create_subscription(db, admin.id, data.student_email, data.sub_type, ip)


@router.post("/subscriptions/renew")
async def renew_student_subscription(
    data: SubscriptionRenew,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Extend a student's subscription."""
    ip = request.client.host if request.client else None
    return renew_subscription(db, admin.id, data.student_email, data.days, ip)


# =============================================================================
# SLOT MANAGEMENT
# =============================================================================
@router.get("/slots", response_model=List[SlotResponse])
async def get_slots(
    available_only: bool = Query(False),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all parking slots."""
    query = db.query(Slot)
    if available_only:
        query = query.filter(Slot.is_available == True)
    slots = query.order_by(Slot.code).all()
    return [SlotResponse(id=s.id, code=s.code, zone=s.zone, is_available=s.is_available) for s in slots]


@router.post("/slots/assign")
async def assign_student_slot(
    data: SlotAssign,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Assign a slot to a student."""
    ip = request.client.host if request.client else None
    return assign_slot(db, admin.id, data.student_email, data.slot_code, ip)


# =============================================================================
# SUSPENSION MANAGEMENT
# =============================================================================
@router.post("/suspensions")
async def suspend_student(
    data: SuspensionCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Suspend a student's access."""
    ip = request.client.host if request.client else None
    return suspend_access(db, admin.id, data.student_email, data.days, data.reason, ip)


@router.get("/suspensions/active")
async def get_active_suspensions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """List all active suspensions."""
    today = date.today()
    suspensions = db.query(Suspension).filter(
        Suspension.start_date <= today,
        Suspension.end_date >= today
    ).all()
    
    return [{
        "id": s.id,
        "student_id": s.user_id,
        "student_email": s.user.email,
        "student_name": s.user.full_name,
        "reason": s.reason,
        "start_date": s.start_date.isoformat(),
        "end_date": s.end_date.isoformat()
    } for s in suspensions]


# =============================================================================
# DASHBOARD & STATS
# =============================================================================
@router.get("/stats")
async def get_dashboard_stats(
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get dashboard statistics."""
    ip = request.client.host if request.client else None
    return get_admin_stats(db, admin.id, ip)


# =============================================================================
# AUDIT & SECURITY LOGS
# =============================================================================
@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(50, le=200),
    action: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get admin audit logs."""
    query = db.query(AuditLog).join(User, AuditLog.admin_id == User.id)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
    
    return [{
        "id": log.id,
        "admin_id": log.admin_id,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": log.entity_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat()
    } for log in logs]


@router.get("/security-events")
async def get_security_events(
    limit: int = Query(50, le=200),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get security events (injections, RBAC violations, etc.)."""
    query = db.query(SecurityEvent)
    if event_type:
        query = query.filter(SecurityEvent.event_type == event_type)
    if severity:
        query = query.filter(SecurityEvent.severity == severity)
    events = query.order_by(SecurityEvent.created_at.desc()).limit(limit).all()
    
    return [{
        "id": e.id,
        "event_type": e.event_type,
        "user_id": e.user_id,
        "description": e.description,
        "payload": e.payload[:200] if e.payload else None,  # Truncate
        "pattern_matched": e.pattern_matched,
        "severity": e.severity,
        "ip_address": e.ip_address,
        "created_at": e.created_at.isoformat()
    } for e in events]


@router.get("/access-events")
async def get_access_events(
    limit: int = Query(50, le=200),
    decision: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Get access check events."""
    query = db.query(AccessEvent)
    if decision:
        query = query.filter(AccessEvent.decision == decision)
    events = query.order_by(AccessEvent.created_at.desc()).limit(limit).all()
    
    return [{
        "id": e.id,
        "plate": e.plate,
        "decision": e.decision.value,
        "ref_code": e.ref_code,
        "message": e.message,
        "user_id": e.user_id,
        "created_at": e.created_at.isoformat()
    } for e in events]
