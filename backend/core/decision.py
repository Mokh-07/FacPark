"""
FacPark - Decision Engine
THE ONLY AUTHORITY for access decisions (ALLOW/DENY).
LLM NEVER decides - only this engine.

REF Codes:
- REF-00: ALLOW
- REF-01: Plate detection failed
- REF-02: Plate not registered
- REF-03: No active subscription
- REF-04: Student suspended
- REF-05: Subscription expired
- REF-06: No slot assigned
- REF-07: Outside parking hours
- REF-99: System error
"""

from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
import logging

from backend.config import settings
from backend.db.models import (
    Vehicle, Subscription, SlotAssignment, Suspension,
    AccessEvent, AccessDecision
)

logger = logging.getLogger(__name__)


@dataclass
class DecisionResult:
    """Structured result from the Decision Engine."""
    decision: AccessDecision
    ref_code: str
    message: str
    user_id: Optional[int] = None
    plate: Optional[str] = None
    slot_code: Optional[str] = None
    subscription_type: Optional[str] = None
    expires_at: Optional[date] = None
    
    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "ref_code": self.ref_code,
            "message": self.message,
            "user_id": self.user_id,
            "plate": self.plate,
            "slot_code": self.slot_code,
            "subscription_type": self.subscription_type,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class DecisionEngine:
    """Central authority for access decisions. LLM and API MUST defer to this."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_plate_access(self, plate: str, checked_by: Optional[int] = None,
                           ip_address: Optional[str] = None) -> DecisionResult:
        """Main entry: Check if a plate is allowed access."""
        try:
            normalized = self._normalize_plate(plate)
            if not normalized:
                return self._log_decision(plate, AccessDecision.DENY,
                    settings.REF_CODES["PLATE_NOT_FOUND"], "Format invalide.",
                    checked_by=checked_by, ip_address=ip_address)
            
            vehicle = self.db.query(Vehicle).filter(Vehicle.plate == normalized).first()
            if not vehicle:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["PLATE_NOT_REGISTERED"],
                    f"Plaque '{normalized}' non enregistrée.", checked_by=checked_by, ip_address=ip_address)
            
            user = vehicle.owner
            if not user.is_active:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["STUDENT_SUSPENDED"], "Compte désactivé.",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            suspension = self._get_active_suspension(user.id)
            if suspension:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["STUDENT_SUSPENDED"],
                    f"Suspendu jusqu'au {suspension.end_date}. Raison: {suspension.reason}",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            sub = self._get_active_subscription(user.id)
            if not sub:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["NO_ACTIVE_SUBSCRIPTION"], "Aucun abonnement actif.",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            if sub.is_expired:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["SUBSCRIPTION_EXPIRED"],
                    f"Abonnement expiré le {sub.end_date}.",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            slot = self._get_active_slot(user.id)
            if not slot:
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["NO_SLOT_ASSIGNED"], "Aucune place attribuée.",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            if not self._is_within_hours():
                return self._log_decision(normalized, AccessDecision.DENY,
                    settings.REF_CODES["OUTSIDE_HOURS"], "Hors horaires (7h-22h, Lun-Sam).",
                    user_id=user.id, checked_by=checked_by, ip_address=ip_address)
            
            return self._log_decision(normalized, AccessDecision.ALLOW,
                settings.REF_CODES["ALLOW"], f"Accès autorisé. Place: {slot.slot.code}",
                user_id=user.id, slot_code=slot.slot.code,
                subscription_type=sub.subscription_type.value, expires_at=sub.end_date,
                checked_by=checked_by, ip_address=ip_address)
        except Exception as e:
            logger.exception(f"Decision error: {e}")
            return self._log_decision(plate, AccessDecision.DENY,
                settings.REF_CODES["SYSTEM_ERROR"], "Erreur système.",
                checked_by=checked_by, ip_address=ip_address)
    
    def _normalize_plate(self, plate: str) -> Optional[str]:
        """
        Normalize Tunisian plate to canonical format: "SERIE تونس NUMERO".
        Handles both OCR output "176 7413 تونس" and DB format "176 تونس 7413".
        """
        if not plate:
            return None
        
        # Basic cleanup
        normalized = plate.strip()
        normalized = " ".join(normalized.split())  # Single spaces
        
        if len(normalized) < 3:
            return None
        
        # Parse Tunisian plate components
        # Expected formats:
        # - DB:  "176 تونس 7413" (SERIE ARABIC NUMERO)
        # - OCR: "176 7413 تونس" (SERIE NUMERO ARABIC)
        
        parts = normalized.split()
        if len(parts) < 2:
            return normalized
        
        # Identify Arabic part (تونس, نت, RS, etc.)
        arabic_keywords = {'تونس', 'نت', 'RS', 'ETAT'}
        
        arabic_part = None
        numeric_parts = []
        
        for part in parts:
            # Check if part is Arabic keyword or contains Arabic chars
            if part in arabic_keywords or any('\u0600' <= c <= '\u06FF' for c in part):
                arabic_part = part
            else:
                numeric_parts.append(part)
        
        # Reconstruct to canonical format: SERIE ARABIC NUMERO
        if arabic_part and len(numeric_parts) >= 2:
            # Format: "SERIE تونس NUMERO"
            canonical = f"{numeric_parts[0]} {arabic_part} {numeric_parts[1]}"
            logger.debug(f"Normalized plate: '{plate}' -> '{canonical}'")
            return canonical
        elif arabic_part and len(numeric_parts) == 1:
            # Only one numeric part - keep as is but with arabic
            canonical = f"{numeric_parts[0]} {arabic_part}"
            return canonical
        
        return normalized
    
    def _get_active_subscription(self, user_id: int) -> Optional[Subscription]:
        return self.db.query(Subscription).filter(
            Subscription.user_id == user_id, Subscription.is_active == 1).first()
    
    def _get_active_suspension(self, user_id: int) -> Optional[Suspension]:
        today = date.today()
        return self.db.query(Suspension).filter(
            Suspension.user_id == user_id,
            Suspension.start_date <= today, Suspension.end_date >= today).first()
    
    def _get_active_slot(self, user_id: int) -> Optional[SlotAssignment]:
        return self.db.query(SlotAssignment).filter(
            SlotAssignment.user_id == user_id, SlotAssignment.is_active == 1).first()
    
    def _is_within_hours(self) -> bool:
        if getattr(settings, "DEMO_MODE", False):
            return True
            
        now = datetime.now()
        if now.weekday() not in settings.PARKING_OPEN_DAYS:
            return False
        return settings.PARKING_OPEN_HOUR <= now.hour < settings.PARKING_CLOSE_HOUR
    
    def _log_decision(self, plate: str, decision: AccessDecision, ref_code: str,
                      message: str, user_id: Optional[int] = None,
                      slot_code: Optional[str] = None, subscription_type: Optional[str] = None,
                      expires_at: Optional[date] = None, checked_by: Optional[int] = None,
                      ip_address: Optional[str] = None) -> DecisionResult:
        event = AccessEvent(plate=plate, decision=decision, ref_code=ref_code,
                           message=message, user_id=user_id, checked_by=checked_by,
                           ip_address=ip_address)
        self.db.add(event)
        self.db.commit()
        logger.log(logging.INFO if decision == AccessDecision.ALLOW else logging.WARNING,
                  f"Access {decision.value} for '{plate}' - {ref_code}: {message}")
        return DecisionResult(decision=decision, ref_code=ref_code, message=message,
                             user_id=user_id, plate=plate, slot_code=slot_code,
                             subscription_type=subscription_type, expires_at=expires_at)


def check_plate_access(db: Session, plate: str, checked_by: Optional[int] = None,
                       ip_address: Optional[str] = None) -> DecisionResult:
    """Convenience function for checking plate access."""
    return DecisionEngine(db).check_plate_access(plate, checked_by, ip_address)
