drop table if exists follow_ups cascade;
drop table if exists operations cascade;
drop table if exists hospitalizations cascade;
drop table if exists doctor_decisions cascade;
drop table if exists route_events cascade;
drop table if exists appointments cascade;
drop table if exists notifications cascade;
drop table if exists route_triggers cascade;
drop table if exists routes cascade;
drop table if exists routing_rules cascade;
drop table if exists ground_truth cascade;
drop table if exists ml_predictions cascade;
drop table if exists findings cascade;
drop table if exists triggers cascade;
drop table if exists protocols cascade;
drop table if exists patients cascade;


create table patients (
    id serial primary key,
    created_at timestamptz default current_timestamp
);


create table protocols (
    id serial primary key,
    patient_id integer not null,
    file_name varchar(255),
    protocol_date timestamptz,
    doc_text text not null,
    created_at timestamptz default current_timestamp,

    constraint fk_protocol_patient
        foreign key (patient_id)
        references patients(id)
);


create table findings (
    id serial primary key,
    protocol_id integer not null,
    finding_type varchar(100) not null,
    value text,
    numeric_value numeric,
    unit varchar(50),
    location varchar(255),
    side varchar(50),
    category varchar(50),
    negated boolean default false,
    evidence_text text,
    confidence numeric(5,4),
    created_at timestamptz default current_timestamp,

    constraint fk_finding_protocol
        foreign key (protocol_id)
        references protocols(id)
);


create table ml_predictions (
    id serial primary key,
    protocol_id integer not null,
    model_version varchar(100) not null,
    prediction varchar(255) not null,
    probability numeric(5,4),
    created_at timestamptz default current_timestamp,

    constraint fk_ml_prediction_protocol
        foreign key (protocol_id)
        references protocols(id)
);


create table ground_truth (
    id serial primary key,
    protocol_id integer not null,
    finding_type varchar(100) not null,
    true_value text,
    true_numeric_value numeric,
    true_unit varchar(50),
    true_route varchar(255),
    evidence text,
    verified_by varchar(255),
    verified_at timestamptz,
    created_at timestamptz default current_timestamp,

    constraint fk_ground_truth_protocol
        foreign key (protocol_id)
        references protocols(id)
);


create table triggers (
    id serial primary key,
    protocol_id integer not null,
    trigger_name varchar(255) not null,
    type_diagnosis varchar(100),
    confidence numeric(5,4),
    evidence text,
    source_section varchar(50),
    is_mismatch boolean default false,
    created_at timestamptz default current_timestamp,

    constraint fk_trigger_protocol
        foreign key (protocol_id)
        references protocols(id)
);


create table routing_rules (
    id serial primary key,
    trigger_name varchar(255) not null,
    conditions jsonb,
    specialist_type varchar(255) not null,
    next_step varchar(255) not null,
    deadline_days integer,  -- NULL = срок не утверждён клиникой (в PoC due_days: null)
    priority integer default 1,
    rule_version varchar(50) default '1.0',
    is_active boolean default true,
    created_at timestamptz default current_timestamp
);


create table routes (
    id serial primary key,
    patient_id integer not null,
    rule_id integer,
    status varchar(100) not null,
    next_step varchar(255) not null,
    specialist_type varchar(255) not null,
    start_date timestamptz default current_timestamp,
    deadline_date timestamptz,
    cancellation_reason varchar(255),
    created_at timestamptz default current_timestamp,

    constraint fk_route_patient
        foreign key (patient_id)
        references patients(id),

    constraint fk_route_rule
        foreign key (rule_id)
        references routing_rules(id)
);
create table route_triggers (
    id serial primary key,
    route_id integer not null,
    trigger_id integer not null,
    priority integer default 1,
    created_at timestamptz default current_timestamp,

    constraint fk_route_trigger_route
        foreign key (route_id)
        references routes(id),

    constraint fk_route_trigger_trigger
        foreign key (trigger_id)
        references triggers(id),

    constraint uq_route_trigger
        unique (route_id, trigger_id)
);


create table notifications (
    id serial primary key,
    route_id integer not null,
    channel varchar(50) not null,
    status varchar(100) not null,
    message_text text not null,
    sent_at timestamptz,
    read_at timestamptz,
    created_at timestamptz default current_timestamp,

    constraint fk_notification_route
        foreign key (route_id)
        references routes(id)
);


create table appointments (
    id serial primary key,
    route_id integer not null,
    doctor_name varchar(255) not null,
    doctor_type varchar(255) not null,
    clinic varchar(255),
    appointment_type varchar(100),
    external_slot_id varchar(255),
    appointment_date timestamptz not null,
    status varchar(100) not null,
    is_previous_doctor boolean default false,
    created_at timestamptz default current_timestamp,

    constraint fk_appointment_route
        foreign key (route_id)
        references routes(id)
);


create table route_events (
    id serial primary key,
    route_id integer not null,
    event_type varchar(100) not null,
    description text,
    source varchar(100),
    external_event_id varchar(255),
    event_date timestamptz default current_timestamp,
    created_at timestamptz default current_timestamp,

    constraint fk_route_event_route
        foreign key (route_id)
        references routes(id),

    constraint uq_external_event
        unique (external_event_id)
);


create table doctor_decisions (
    id serial primary key,
    route_id integer not null,
    decision_type varchar(100) not null,
    decision_date timestamptz default current_timestamp,
    notes text,
    cancellation_reason varchar(255),
    created_at timestamptz default current_timestamp,

    constraint fk_doctor_decision_route
        foreign key (route_id)
        references routes(id)
);


create table hospitalizations (
    id serial primary key,
    route_id integer not null,
    planned_date timestamptz,
    actual_date timestamptz,
    status varchar(100) not null,
    created_at timestamptz default current_timestamp,

    constraint fk_hospitalization_route
        foreign key (route_id)
        references routes(id)
);


create table operations (
    id serial primary key,
    hospitalization_id integer not null,
    operation_date timestamptz not null,
    operation_type varchar(255) not null,
    notes text,
    created_at timestamptz default current_timestamp,

    constraint fk_operation_hospitalization
        foreign key (hospitalization_id)
        references hospitalizations(id)
);


create table follow_ups (
    id serial primary key,
    operation_id integer not null,
    planned_date timestamptz,
    actual_date timestamptz,
    status varchar(100) not null,
    notes text,
    created_at timestamptz default current_timestamp,

    constraint fk_follow_up_operation
        foreign key (operation_id)
        references operations(id)
);


create index idx_protocols_patient_id
    on protocols(patient_id);

create index idx_findings_protocol_id
    on findings(protocol_id);

create index idx_ml_predictions_protocol_id
    on ml_predictions(protocol_id);

create index idx_triggers_protocol_id
    on triggers(protocol_id);

create index idx_routes_patient_id
    on routes(patient_id);

create index idx_routes_status
    on routes(status);

create index idx_route_triggers_route_id
    on route_triggers(route_id);

create index idx_route_triggers_trigger_id
    on route_triggers(trigger_id);

create index idx_notifications_route_id
    on notifications(route_id);

create index idx_appointments_route_id
    on appointments(route_id);

create index idx_route_events_route_id
    on route_events(route_id);

create index idx_route_events_event_type
    on route_events(event_type);

# ============================================================
# CRUD-схемы для API
# ============================================================

class PatientCreate(BaseModel):
    """
    Создание пациента.

    ВАЖНО:
    Эти поля сейчас НЕ сохраняются в Patient,
    потому что текущая модель БД хранит только id и created_at.
    Поэтому пока схема используется только как API-контракт
    для будущего расширения.
    """
    surname: str | None = None
    name_patient: str | None = None
    second_name: str | None = None
    birth_date: date | None = None


class PatientResponse(BaseModel):
    id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProtocolCreate(BaseModel):
    patient_id: int
    file_name: str | None = None
    protocol_date: datetime | None = None
    doc_text: str


class ProtocolResponse(BaseModel):
    id: int
    patient_id: int
    file_name: str | None = None
    protocol_date: datetime | None = None
    doc_text: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class RouteCreate(BaseModel):
    patient_id: int
    rule_id: int | None = None
    status: str = "planned"
    next_step: str
    specialist_type: str
    deadline_date: datetime | None = None


class RouteResponse(BaseModel):
    id: int
    patient_id: int
    rule_id: int | None = None
    status: str
    next_step: str
    specialist_type: str
    deadline_date: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class AppointmentCreate(BaseModel):
    route_id: int
    doctor_name: str
    doctor_type: str
    clinic: str | None = None
    appointment_type: str | None = None
    external_slot_id: str | None = None
    appointment_date: datetime
    status: str = "planned"
    is_previous_doctor: bool = False


class AppointmentResponse(BaseModel):
    id: int
    route_id: int
    doctor_name: str
    doctor_type: str
    clinic: str | None = None
    appointment_type: str | None = None
    external_slot_id: str | None = None
    appointment_date: datetime
    status: str
    is_previous_doctor: bool = False
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    route_id: int
    channel: str
    status: str = "pending"
    message_text: str


class NotificationResponse(BaseModel):
    id: int
    route_id: int
    channel: str
    status: str
    message_text: str
    sent_at: datetime | None = None
    read_at: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class RouteEventCreate(BaseModel):
    route_id: int
    event_type: str
    description: str | None = None
    source: str | None = None
    external_event_id: str | None = None


class RouteEventResponse(BaseModel):
    id: int
    route_id: int
    event_type: str
    description: str | None = None
    source: str | None = None
    external_event_id: str | None = None
    event_date: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class GroundTruthCreate(BaseModel):
    protocol_id: int
    finding_type: str
    true_value: str | None = None
    true_numeric_value: float | None = None
    true_unit: str | None = None
    true_route: str | None = None
    evidence: str | None = None
    verified_by: str | None = None


class GroundTruthResponse(BaseModel):
    id: int
    protocol_id: int
    finding_type: str
    true_value: str | None = None
    true_numeric_value: float | None = None
    true_unit: str | None = None
    true_route: str | None = None
    evidence: str | None = None
    verified_by: str | None = None

    class Config:
        from_attributes = True