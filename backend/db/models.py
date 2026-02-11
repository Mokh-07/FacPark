"""
FacPark - SQLAlchemy ORM Models
Defines all database entities with relationships.
Note: Constraints like is_active uniqueness and max vehicles are enforced via MySQL triggers.
"""

from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Boolean, DateTime, Date, Text, Enum, ForeignKey,
    UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from backend.db.session import Base


# =============================================================================
# ENUMS
# =============================================================================
class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "ADMIN"
    STUDENT = "STUDENT"


class SubscriptionType(str, enum.Enum):
    """Available subscription types."""
    MENSUEL = "MENSUEL"
    SEMESTRIEL = "SEMESTRIEL"
    ANNUEL = "ANNUEL"


class PlateType(str, enum.Enum):
    """Tunisian plate types."""
    TN = "TN"       # Ordinary (تونس)
    RS = "RS"       # Dealer/Négociant
    ETAT = "ETAT"   # Government


class AccessDecision(str, enum.Enum):
    """Access decision results."""
    ALLOW = "ALLOW"
    DENY = "DENY"


# =============================================================================
# USERS
# =============================================================================
class User(Base):
    """
    User entity (ADMIN or STUDENT).
    Admins manage the system, students use parking services.
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    vehicles: Mapped[List["Vehicle"]] = relationship(
        "Vehicle", back_populates="owner", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    slot_assignments: Mapped[List["SlotAssignment"]] = relationship(
        "SlotAssignment", back_populates="user", cascade="all, delete-orphan"
    )
    suspensions: Mapped[List["Suspension"]] = relationship(
        "Suspension",
        foreign_keys="Suspension.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    # Relation pour les suspensions créées par cet admin
    created_suspensions: Mapped[List["Suspension"]] = relationship(
        "Suspension",
        foreign_keys="Suspension.created_by",
        back_populates="creator"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role={self.role.value})>"


# =============================================================================
# VEHICLES
# =============================================================================
class Vehicle(Base):
    """
    Vehicle entity linked to a student.
    Max 3 vehicles per student (enforced via MySQL trigger).
    """
    __tablename__ = "vehicles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    plate_type: Mapped[PlateType] = mapped_column(
        Enum(PlateType), nullable=False, default=PlateType.TN
    )
    make: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Brand
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="vehicles")
    
    def __repr__(self) -> str:
        return f"<Vehicle(id={self.id}, plate='{self.plate}', type={self.plate_type.value})>"


# =============================================================================
# SUBSCRIPTIONS
# =============================================================================
class Subscription(Base):
    """
    Subscription entity (MENSUEL, SEMESTRIEL, ANNUEL).
    Only ONE active subscription per user (enforced via is_active + unique + trigger).
    """
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        Enum(SubscriptionType), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=active, NULL=inactive
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    
    # Unique constraint: only one active subscription per user
    __table_args__ = (
        UniqueConstraint("user_id", "is_active", name="uq_user_active_subscription"),
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, type={self.subscription_type.value}, active={self.is_active})>"
    
    @property
    def is_expired(self) -> bool:
        return date.today() > self.end_date


# =============================================================================
# PARKING SLOTS
# =============================================================================
class Slot(Base):
    """
    Parking slot entity.
    Each slot has a unique code (e.g., A01, B12).
    """
    __tablename__ = "slots"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    zone: Mapped[str] = mapped_column(String(50), nullable=False, default="GENERAL")
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    assignments: Mapped[List["SlotAssignment"]] = relationship(
        "SlotAssignment", back_populates="slot"
    )
    
    def __repr__(self) -> str:
        return f"<Slot(id={self.id}, code='{self.code}', available={self.is_available})>"


# =============================================================================
# SLOT ASSIGNMENTS
# =============================================================================
class SlotAssignment(Base):
    """
    Links a student to a parking slot.
    Only ONE active assignment per user (enforced via is_active + unique + trigger).
    """
    __tablename__ = "slot_assignments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("slots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1=active, NULL=inactive
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="slot_assignments")
    slot: Mapped["Slot"] = relationship("Slot", back_populates="assignments")
    
    # Unique constraint: only one active assignment per user
    __table_args__ = (
        UniqueConstraint("user_id", "is_active", name="uq_user_active_slot"),
    )
    
    def __repr__(self) -> str:
        return f"<SlotAssignment(id={self.id}, user={self.user_id}, slot={self.slot_id})>"


# =============================================================================
# SUSPENSIONS
# =============================================================================
class Suspension(Base):
    """
    Suspension record for a student.
    During suspension period, access is denied.
    """
    __tablename__ = "suspensions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="suspensions")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="created_suspensions")
    
    def __repr__(self) -> str:
        return f"<Suspension(id={self.id}, user={self.user_id}, until={self.end_date})>"
    
    @property
    def is_active(self) -> bool:
        today = date.today()
        return self.start_date <= today <= self.end_date


# =============================================================================
# ACCESS EVENTS (Decision Engine Logs)
# =============================================================================
class AccessEvent(Base):
    """
    Log of every access check performed by the Decision Engine.
    Records plate, decision (ALLOW/DENY), and REF code.
    """
    __tablename__ = "access_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plate: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    decision: Mapped[AccessDecision] = mapped_column(Enum(AccessDecision), nullable=False)
    ref_code: Mapped[str] = mapped_column(String(10), nullable=False)  # REF-XX
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    checked_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<AccessEvent(id={self.id}, plate='{self.plate}', decision={self.decision.value})>"


# =============================================================================
# AUDIT LOGS (Admin Actions)
# =============================================================================
class AuditLog(Base):
    """
    Audit log for all admin write operations.
    Every admin action creates an entry here for accountability.
    """
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    admin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)  # user, vehicle, subscription, etc.
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON details
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action='{self.action}', admin={self.admin_id})>"


# =============================================================================
# SECURITY EVENTS (Incidents)
# =============================================================================
class SecurityEvent(Base):
    """
    Security incident log.
    Records prompt injections, unauthorized tool access attempts, etc.
    SEPARATE FROM audit_logs - this is for security incidents only.
    """
    __tablename__ = "security_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # INJECTION, RBAC_VIOLATION, etc.
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # The offending content
    pattern_matched: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self) -> str:
        return f"<SecurityEvent(id={self.id}, type='{self.event_type}', severity={self.severity})>"


# =============================================================================
# INDEXES (defined in models for SQLAlchemy awareness)
# =============================================================================
# Additional composite indexes are defined in 03_indexes.sql for MySQL optimization
