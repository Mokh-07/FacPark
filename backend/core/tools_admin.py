"""
FacPark - Admin Tools (13)
All write operations require ADMIN role and log to audit_logs.

1) list_students, 2) create_student, 3) delete_student
4) add_vehicle, 5) remove_vehicle, 6) create_subscription
7) renew_subscription, 8) assign_slot, 9) suspend_access
10) get_admin_stats, 11) check_plate_access
12) list_slots, 13) list_available_slots
"""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from passlib.context import CryptContext

from backend.config import settings
from backend.db.models import (
    User, Vehicle, Subscription, Slot, SlotAssignment, Suspension,
    AccessEvent, UserRole, SubscriptionType, PlateType
)
from backend.core.tools import (
    tool_response, require_role, _log_audit, _log_security_event
)
from backend.core.decision import check_plate_access as decision_check

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# ADMIN TOOLS (11) - REQUIRE ADMIN ROLE + AUDIT
# =============================================================================
def list_students(db: Session, admin_id: int, search: Optional[str] = None,
                  limit: int = 50, ip: Optional[str] = None) -> dict:
    """List all students, optionally filtered by search."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "list_students", ip)
    if rbac_err:
        return rbac_err
    
    query = db.query(User).filter(User.role == UserRole.STUDENT)
    if search:
        query = query.filter(User.email.ilike(f"%{search}%") | 
                            User.full_name.ilike(f"%{search}%"))
    students = query.limit(min(limit, 100)).all()
    data = [{"id": s.id, "email": s.email, "full_name": s.full_name,
             "is_active": s.is_active, "created_at": s.created_at.isoformat()} 
            for s in students]
    return tool_response(True, data=data, message=f"{len(data)} étudiant(s) trouvé(s).")


def create_student(db: Session, admin_id: int, email: str, full_name: str,
                   password: str = "changeme123", ip: Optional[str] = None) -> dict:
    """Create a new student account."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "create_student", ip)
    if rbac_err:
        return rbac_err
    
    if db.query(User).filter(User.email == email).first():
        return tool_response(False, error=f"L'email '{email}' existe déjà.")
    
    user = User(email=email, full_name=full_name, role=UserRole.STUDENT,
                password_hash=pwd_context.hash(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    
    _log_audit(db, admin_id, "CREATE_STUDENT", "user", user.id,
               {"email": email, "full_name": full_name}, ip)
    return tool_response(True, data={"id": user.id, "email": user.email},
        message=f"Étudiant '{full_name}' créé avec succès.")


def delete_student(db: Session, admin_id: int, student_email: str,
                   ip: Optional[str] = None) -> dict:
    """Delete a student and all associated data."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "delete_student", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"Étudiant '{student_email}' non trouvé.")
    
    student_id = student.id
    db.delete(student)
    db.commit()
    
    _log_audit(db, admin_id, "DELETE_STUDENT", "user", student_id,
               {"email": student_email}, ip)
    return tool_response(True, message=f"Étudiant '{student_email}' supprimé.")


def add_vehicle(db: Session, admin_id: int, student_email: str, plate: str,
                plate_type: str = "TN", ip: Optional[str] = None) -> dict:
    """Add a vehicle to a student. Max 3 enforced by DB trigger."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "add_vehicle", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"Étudiant '{student_email}' non trouvé.")
    
    vehicle_count = db.query(Vehicle).filter(Vehicle.user_id == student.id).count()
    if vehicle_count >= settings.MAX_VEHICLES_PER_STUDENT:
        return tool_response(False, error=f"Maximum {settings.MAX_VEHICLES_PER_STUDENT} véhicules atteint.")
    
    if db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first():
        return tool_response(False, error=f"Plaque '{plate}' déjà enregistrée.")
    
    try:
        ptype = PlateType(plate_type.upper())
    except ValueError:
        return tool_response(False, error=f"Type de plaque invalide. Utiliser: TN, RS, ETAT.")
    
    vehicle = Vehicle(user_id=student.id, plate=plate.upper(), plate_type=ptype)
    db.add(vehicle)
    db.commit()
    
    _log_audit(db, admin_id, "ADD_VEHICLE", "vehicle", vehicle.id,
               {"student_email": student_email, "plate": plate}, ip)
    return tool_response(True, data={"id": vehicle.id, "plate": vehicle.plate},
        message=f"Véhicule '{plate}' ajouté à {student_email}.")


def remove_vehicle(db: Session, admin_id: int, plate: str,
                   ip: Optional[str] = None) -> dict:
    """Remove a vehicle by plate."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "remove_vehicle", ip)
    if rbac_err:
        return rbac_err
    
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first()
    if not vehicle:
        return tool_response(False, error=f"Véhicule '{plate}' non trouvé.")
    
    vehicle_id = vehicle.id
    db.delete(vehicle)
    db.commit()
    
    _log_audit(db, admin_id, "REMOVE_VEHICLE", "vehicle", vehicle_id,
               {"plate": plate}, ip)
    return tool_response(True, message=f"Véhicule '{plate}' supprimé.")


def create_subscription(db: Session, admin_id: int, student_email: str,
                        sub_type: str, ip: Optional[str] = None) -> dict:
    """Create a subscription for a student. Deactivates any existing."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "create_subscription", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"❌ Étudiant '{student_email}' non trouvé.\n\n💡 Conseil: Vérifiez l'orthographe de l'email ou créez d'abord l'étudiant:\n   'créer étudiant email={student_email} nom=\"Prénom Nom\" password=xxx'")
    
    # ====== NOUVELLE VALIDATION: Vérifier qu'il a un véhicule ======
    from backend.db.models import Vehicle
    vehicles = db.query(Vehicle).filter(Vehicle.user_id == student.id).all()
    if not vehicles:
        return tool_response(
            False,
            error=f"❌ Impossible de créer un abonnement pour {student_email}.\n\n"
                  f"⚠️ Raison: Aucun véhicule enregistré.\n\n"
                  f"✅ Solution: Ajoutez d'abord un véhicule:\n"
                  f"   'ajouter véhicule 123 تونس 4567 à {student_email}'"
        )
    # ====== FIN VALIDATION ======
    
    try:
        stype = SubscriptionType(sub_type.upper())
    except ValueError:
        # Amélioration du message d'erreur avec mapping
        sub_type_help = {
            "monthly": "mensuel", "mensuel": "mensuel",
            "semester": "semestriel", "semestriel": "semestriel",
            "annual": "annuel", "annuel": "annuel"
        }
        suggestion = sub_type_help.get(sub_type.lower(), "")
        error_msg = f"❌ Type d'abonnement '{sub_type}' invalide.\n\n"
        error_msg += "✅ Types acceptés:\n"
        error_msg += "• **mensuel** ou **monthly** → 30 jours\n"
        error_msg += "• **semestriel** ou **semester** → 180 jours\n"
        error_msg += "• **annuel** ou **annual** → 365 jours\n\n"
        if suggestion:
            error_msg += f"💡 Vouliez-vous dire '{suggestion}' ?\n\n"
        error_msg += f"💡 Exemple: 'créer abonnement mensuel pour {student_email}'"
        return tool_response(False, error=error_msg)
    
    # Deactivate existing subscription
    db.query(Subscription).filter(Subscription.user_id == student.id,
                                  Subscription.is_active == 1).update({"is_active": None})
    
    start = date.today()
    end = start + timedelta(days=settings.SUBSCRIPTION_DURATIONS[stype.value])
    
    sub = Subscription(user_id=student.id, subscription_type=stype,
                       start_date=start, end_date=end, is_active=1)
    db.add(sub)
    db.commit()
    
    _log_audit(db, admin_id, "CREATE_SUBSCRIPTION", "subscription", sub.id,
               {"student_email": student_email, "type": stype.value}, ip)
    return tool_response(True, data={"id": sub.id, "end_date": end.isoformat()},
        message=f"✅ Abonnement {stype.value} créé pour {student_email}.\nDurée: {settings.SUBSCRIPTION_DURATIONS[stype.value]} jours\nDate d'expiration: {end.isoformat()}")


def renew_subscription(db: Session, admin_id: int, student_email: str,
                       days: int, ip: Optional[str] = None) -> dict:
    """Extend a student's subscription by X days."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "renew_subscription", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"Étudiant '{student_email}' non trouvé.")
    
    sub = db.query(Subscription).filter(Subscription.user_id == student.id,
                                        Subscription.is_active == 1).first()
    if not sub:
        return tool_response(False, error="Aucun abonnement actif à renouveler.")
    
    sub.end_date = sub.end_date + timedelta(days=days)
    db.commit()
    
    _log_audit(db, admin_id, "RENEW_SUBSCRIPTION", "subscription", sub.id,
               {"student_email": student_email, "days_added": days}, ip)
    return tool_response(True, data={"new_end_date": sub.end_date.isoformat()},
        message=f"Abonnement prolongé de {days} jours. Expire le {sub.end_date}.")


def assign_slot(db: Session, admin_id: int, student_email: str,
                slot_code: str, ip: Optional[str] = None) -> dict:
    """Assign a parking slot to a student."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "assign_slot", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"❌ Étudiant '{student_email}' non trouvé.")
    
    import re
    
    # Normalize slot code: remove spaces, optional hyphen handling
    slot_code = slot_code.upper().strip()
    
    # Helper to format slot like "A01" (DB format) from "A-01" or "A 01"
    match = re.search(r'^([ABC])[-_]?0?(\d{1,2})$', slot_code)
    if match:
        zone_l, num = match.groups()
        slot_code = f"{zone_l}{int(num):02d}"  # A-1 -> A01 (DB format confirmed via SELECT)
        
    slot = db.query(Slot).filter(Slot.code == slot_code).first()
    if not slot:
        return tool_response(False, error=f"❌ Place '{slot_code}' non trouvée.\n\n💡 Conseil: Les codes de place sont au format: A01 à A40, B01 à B40, C01 à C20 (sans tiret)")
    
    if not slot.is_available:
        # Suggérer des places alternatives
        available_slots = db.query(Slot).filter(Slot.is_available == True).limit(5).all()
        alternatives = ", ".join([s.code for s in available_slots]) if available_slots else "Aucune"
        return tool_response(
            False, 
            error=f"❌ La place '{slot_code}' est déjà occupée.\n\n"
                  f"✅ Places disponibles (échantillon): {alternatives}\n\n"
                  f"💡 Conseil: Tapez 'statistiques' pour voir le nombre total de places disponibles."
        )
    
    # Deactivate existing assignment
    db.query(SlotAssignment).filter(SlotAssignment.user_id == student.id,
                                    SlotAssignment.is_active == 1).update({"is_active": None})
    
    assign = SlotAssignment(user_id=student.id, slot_id=slot.id, is_active=1)
    slot.is_available = False
    db.add(assign)
    db.commit()
    
    _log_audit(db, admin_id, "ASSIGN_SLOT", "slot_assignment", assign.id,
               {"student_email": student_email, "slot_code": slot_code}, ip)
    return tool_response(True, data={"slot_code": slot.code},
        message=f"✅ Place {slot_code} attribuée avec succès à {student_email}.")


def suspend_access(db: Session, admin_id: int, student_email: str,
                   days: int, reason: str, ip: Optional[str] = None) -> dict:
    """Suspend a student's access for X days."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "suspend_access", ip)
    if rbac_err:
        return rbac_err
    
    student = db.query(User).filter(User.email == student_email,
                                    User.role == UserRole.STUDENT).first()
    if not student:
        return tool_response(False, error=f"Étudiant '{student_email}' non trouvé.")
    
    admin = db.query(User).filter(User.id == admin_id).first()
    start = date.today()
    end = start + timedelta(days=days)
    
    suspension = Suspension(user_id=student.id, reason=reason,
                           start_date=start, end_date=end, created_by=admin_id)
    db.add(suspension)
    db.commit()
    
    _log_audit(db, admin_id, "SUSPEND_ACCESS", "suspension", suspension.id,
               {"student_email": student_email, "days": days, "reason": reason}, ip)
    return tool_response(True, data={"end_date": end.isoformat()},
        message=f"{student_email} suspendu jusqu'au {end}. Raison: {reason}")


def get_admin_stats(db: Session, admin_id: int, ip: Optional[str] = None) -> dict:
    """Get dashboard statistics for admin."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "get_admin_stats", ip)
    if rbac_err:
        return rbac_err
    
    stats = {
        "total_students": db.query(User).filter(User.role == UserRole.STUDENT).count(),
        "active_subscriptions": db.query(Subscription).filter(Subscription.is_active == 1).count(),
        "total_vehicles": db.query(Vehicle).count(),
        "total_slots": db.query(Slot).count(),
        "available_slots": db.query(Slot).filter(Slot.is_available == True).count(),
        "active_suspensions": db.query(Suspension).filter(
            Suspension.start_date <= date.today(),
            Suspension.end_date >= date.today()).count(),
        "today_accesses": db.query(AccessEvent).filter(
            func.date(AccessEvent.created_at) == date.today()).count()
    }
    return tool_response(True, data=stats, message="Statistiques du tableau de bord.")


def list_slots(db: Session, admin_id: int, zone: Optional[str] = None,
               ip: Optional[str] = None) -> dict:
    """List all parking slots with their status. Optional: filter by zone (A, B, C)."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "list_slots", ip)
    if rbac_err:
        return rbac_err
    
    query = db.query(Slot)
    if zone:
        zone_upper = zone.upper()
        if zone_upper in ["A", "B", "C"]:
            query = query.filter(Slot.code.like(f"{zone_upper}-%"))
        else:
            return tool_response(False, error=f"❌ Zone '{zone}' invalide. Zones valides: A, B, C")
    
    slots = query.order_by(Slot.code).all()
    
    if not slots:
        return tool_response(False, error="❌ Aucune place de parking trouvée dans la base de données.\n\n💡 Exécutez le script 'populate_slots.py' pour créer les places.")
    
    # Group by zone
    zones_data = {}
    for slot in slots:
        zone_letter = slot.code[0]  # A, B, or C
        if zone_letter not in zones_data:
            zones_data[zone_letter] = {"total": 0, "available": 0, "occupied": 0, "slots": []}
        
        status = "✅ Disponible" if slot.is_available else "🔴 Occupée"
        zones_data[zone_letter]["slots"].append({
            "code": slot.code,
            "zone": slot.zone,
            "is_available": slot.is_available,
            "status": status
        })
        zones_data[zone_letter]["total"] += 1
        if slot.is_available:
            zones_data[zone_letter]["available"] += 1
        else:
            zones_data[zone_letter]["occupied"] += 1
    
    # Calculate totals
    total_slots = len(slots)
    total_available = sum(z["available"] for z in zones_data.values())
    total_occupied = sum(z["occupied"] for z in zones_data.values())
    
    message = f"📊 **Statistiques des places de parking:**\n\n"
    message += f"**Total:** {total_slots} places\n"
    message += f"**Disponibles:** ✅ {total_available} places\n"
    message += f"**Occupées:** 🔴 {total_occupied} places\n\n"
    
    for zone_letter in sorted(zones_data.keys()):
        zone_info = zones_data[zone_letter]
        message += f"**Zone {zone_letter}:** {zone_info['total']} places (✅ {zone_info['available']} disponibles, 🔴 {zone_info['occupied']} occupées)\n"
    
    return tool_response(True, data={
        "zones": zones_data,
        "summary": {
            "total_slots": total_slots,
            "total_available": total_available,
            "total_occupied": total_occupied
        }
    }, message=message)


def list_available_slots(db: Session, admin_id: int, zone: Optional[str] = None,
                        limit: int = 50, ip: Optional[str] = None) -> dict:
    """List available parking slots only. Optional: filter by zone (A, B, C)."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "list_available_slots", ip)
    if rbac_err:
        return rbac_err
    
    query = db.query(Slot).filter(Slot.is_available == True)
    if zone:
        zone_upper = zone.upper()
        if zone_upper in ["A", "B", "C"]:
            query = query.filter(Slot.code.like(f"{zone_upper}-%"))
        else:
            return tool_response(False, error=f"❌ Zone '{zone}' invalide. Zones valides: A, B, C")
    
    slots = query.order_by(Slot.code).limit(min(limit, 100)).all()
    
    if not slots:
        zone_msg = f" dans la zone {zone.upper()}" if zone else ""
        return tool_response(False, error=f"❌ Aucune place disponible{zone_msg}.\n\n💡 Toutes les places sont actuellement occupées.")
    
    # Group by zone
    zones_data = {}
    for slot in slots:
        zone_letter = slot.code[0]  # A, B, or C
        if zone_letter not in zones_data:
            zones_data[zone_letter] = []
        zones_data[zone_letter].append(slot.code)
    
    message = f"✅ **Places disponibles:** {len(slots)} place(s)\n\n"
    for zone_letter in sorted(zones_data.keys()):
        codes = zones_data[zone_letter]
        message += f"**Zone {zone_letter}:** {', '.join(codes)}\n"
    
    return tool_response(True, data={
        "available_slots": [{"code": s.code, "zone": s.zone} for s in slots],
        "count": len(slots)
    }, message=message)


def admin_check_plate_access(db: Session, admin_id: int, plate: str,
                              ip: Optional[str] = None) -> dict:
    """Check plate access - uses Decision Engine."""
    rbac_err = require_role(db, admin_id, UserRole.ADMIN, "check_plate_access", ip)
    if rbac_err:
        return rbac_err
    
    result = decision_check(db, plate, checked_by=admin_id, ip_address=ip)
    return tool_response(True, data=result.to_dict(),
        message=f"{result.decision.value}: {result.message}")
