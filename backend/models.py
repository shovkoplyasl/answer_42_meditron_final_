# models.py
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocols = relationship("Protocol", back_populates="patient", cascade="all, delete-orphan")
    routes = relationship("Route", back_populates="patient", cascade="all, delete-orphan")


class Protocol(Base):
    __tablename__ = "protocols"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_protocol_patient"), nullable=False)
    file_name = Column(String(255), nullable=True)
    protocol_date = Column(DateTime(timezone=True), nullable=True)
    doc_text = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    patient = relationship("Patient", back_populates="protocols")
    findings = relationship("Finding", back_populates="protocol", cascade="all, delete-orphan")
    ml_predictions = relationship("MLPrediction", back_populates="protocol", cascade="all, delete-orphan")
    ground_truths = relationship("GroundTruth", back_populates="protocol", cascade="all, delete-orphan")
    triggers = relationship("Trigger", back_populates="protocol", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id", name="fk_finding_protocol"), nullable=False)
    finding_type = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    numeric_value = Column(Numeric, nullable=True)
    unit = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    side = Column(String(50), nullable=True)
    category = Column(String(50), nullable=True)
    negated = Column(Boolean, default=False)
    evidence_text = Column(Text, nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocol = relationship("Protocol", back_populates="findings")


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id", name="fk_ml_prediction_protocol"), nullable=False)
    model_version = Column(String(100), nullable=False)
    prediction = Column(String(255), nullable=False)
    probability = Column(Numeric(5, 4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocol = relationship("Protocol", back_populates="ml_predictions")


class GroundTruth(Base):
    __tablename__ = "ground_truth"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id", name="fk_ground_truth_protocol"), nullable=False)
    finding_type = Column(String(100), nullable=False)
    true_value = Column(Text, nullable=True)
    true_numeric_value = Column(Numeric, nullable=True)
    true_unit = Column(String(50), nullable=True)
    true_route = Column(String(255), nullable=True)
    evidence = Column(Text, nullable=True)
    verified_by = Column(String(255), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    protocol = relationship("Protocol", back_populates="ground_truths")


class Trigger(Base):
    __tablename__ = "triggers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    protocol_id = Column(Integer, ForeignKey("protocols.id", name="fk_trigger_protocol"), nullable=False)
    trigger_name = Column(String(255), nullable=False)
    type_diagnosis = Column(String(100), nullable=True)
    confidence = Column(Numeric(5, 4), nullable=True)
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
    trigger_name = Column(String(255), nullable=False)
    conditions = Column(JSONB, nullable=True)
    specialist_type = Column(String(255), nullable=False)
    next_step = Column(String(255), nullable=False)
    deadline_days = Column(Integer, nullable=True)  # NULL = срок не утверждён клиникой
    priority = Column(Integer, default=1)
    rule_version = Column(String(50), default="1.0")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    routes = relationship("Route", back_populates="rule")


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id", name="fk_route_patient"), nullable=False)
    rule_id = Column(Integer, ForeignKey("routing_rules.id", name="fk_route_rule"), nullable=True)
    status = Column(String(100), nullable=False)
    next_step = Column(String(255), nullable=False)
    specialist_type = Column(String(255), nullable=False)
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    deadline_date = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    patient = relationship("Patient", back_populates="routes")
    rule = relationship("RoutingRule", back_populates="routes")
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
    status = Column(String(100), nullable=False)
    message_text = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="notifications")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_appointment_route"), nullable=False)
    doctor_name = Column(String(255), nullable=False)
    doctor_type = Column(String(255), nullable=False)
    clinic = Column(String(255), nullable=True)
    appointment_type = Column(String(100), nullable=True)
    external_slot_id = Column(String(255), nullable=True)
    appointment_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(100), nullable=False)
    is_previous_doctor = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Связи
    route = relationship("Route", back_populates="appointments")


class RouteEvent(Base):
    __tablename__ = "route_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    route_id = Column(Integer, ForeignKey("routes.id", name="fk_route_event_route"), nullable=False)
    event_type = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    external_event_id = Column(String(255), unique=True, nullable=True)
    event_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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