# models.py
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    surname = Column(String(255), nullable=False)
    name_patient = Column(String(255), nullable=False)
    second_name = Column(String(255), nullable=False)
    birth_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocols = relationship("Protocol", back_populates="patient", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="patient", cascade="all, delete-orphan")


class Protocol(Base):
    __tablename__ = "protocols"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_protocol_patient"), nullable=False)
    file_name = Column(String(255), nullable=True)
    protocol_date = Column(DateTime(timezone=True), nullable=False)
    doc_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    patient = relationship("Patient", back_populates="protocols")
    triggers = relationship("Trigger", back_populates="protocol", cascade="all, delete-orphan")


class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocols_id = Column(Integer, ForeignKey("protocols.id", name="fk_trigger_protocol_version"), nullable=False)
    name_file = Column(String(255), nullable=False)
    type_diagnosis = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    evidence = Column(Text, nullable=True)
    source_section = Column(String(50), nullable=True)
    is_mismatch = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocol = relationship("Protocol", back_populates="triggers")
    route_triggers = relationship("RouteTrigger", back_populates="trigger", cascade="all, delete-orphan")


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    trigger_name = Column(String(255), unique=True, nullable=False)
    specialist_type = Column(String(255), nullable=False)
    next_step = Column(String(255), nullable=False)
    deadline_days = Column(Integer, nullable=False)
    priority = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_route_patient"), nullable=False)
    status = Column(String(100), nullable=False)
    next_step = Column(String(255), nullable=False)
    specialist_type = Column(String(255), nullable=False)
    deadline_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    patient = relationship("Patient", back_populates="routes")
    route_triggers = relationship("RouteTrigger", back_populates="route", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="route", cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="route", cascade="all, delete-orphan")
    events = relationship("RouteEvent", back_populates="route", cascade="all, delete-orphan")
    doctor_decisions = relationship("DoctorDecision", back_populates="route", cascade="all, delete-orphan")
    hospitalizations = relationship("Hospitalization", back_populates="route", cascade="all, delete-orphan")


class RouteTrigger(Base):
    __tablename__ = "route_triggers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_route_trigger_route"), nullable=False)
    trigger_id = Column(Integer, ForeignKey("triggers.id", name="fk_route_trigger_trigger"), nullable=False)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="route_triggers")
    trigger = relationship("Trigger", back_populates="route_triggers")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_notification_route"), nullable=False)
    channel = Column(String(50), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(100), nullable=False)
    message_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="notifications")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_appointment_route"), nullable=False)
    doctor_name = Column(String(255), nullable=False)
    doctor_type = Column(String(255), nullable=False)
    is_previous_doctor = Column(Boolean, default=False)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="appointments")


class RouteEvent(Base):
    __tablename__ = "route_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_route_event_route"), nullable=False)
    event_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    event_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at =Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="events")


class DoctorDecision(Base):
    __tablename__ = "doctor_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_doctor_decision_route"), nullable=False)
    decision_type = Column(String(100), nullable=False)
    decision_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="doctor_decisions")


class Hospitalization(Base):
    __tablename__ = "hospitalizations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_hospitalization_route"), nullable=False)
    planned_date = Column(DateTime(timezone=True), nullable=True)
    actual_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="hospitalizations")
    operations = relationship("Operation", back_populates="hospitalization", cascade="all, delete-orphan")


class Operation(Base):
    __tablename__ = "operations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    hospitalization_id = Column(Integer, ForeignKey("hospitalizations.id", name="fk_operation_hospitalization"), nullable=False)
    operation_date = Column(DateTime(timezone=True), nullable=False)
    operation_type = Column(String(255), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    hospitalization = relationship("Hospitalization", back_populates="operations")
    follow_ups = relationship("FollowUp", back_populates="operation", cascade="all, delete-orphan")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    operation_id = Column(Integer, ForeignKey("operations.id", name="fk_follow_up_operation"), nullable=False)
    planned_date = Column(DateTime(timezone=True), nullable=True)
    actual_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(100), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    operation = relationship("Operation", back_populates="follow_ups")