# Pydantic-контракты запросов и ответов FastAPI

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

# Дисклеймер по умолчанию (если адаптер не вернул notice)
NOTICE_TEXT = "Демонстрационный анализ. Не диагноз и не назначение лечения."


# Схема входящего запроса на анализ протокола
class ProtocolAnalyzeRequest(BaseModel):
    patient_id: int = Field(..., description="ID пациента в БД (patients.id)")
    protocol_text: str = Field(..., min_length=1, description="Текст медицинского протокола")
    file_name: str | None = Field(None, max_length=255, description="Имя исходного файла, если есть")
    protocol_date: datetime | None = Field(None, description="Дата протокола; если не передана — время запроса")


# Схема находки — так, как она сохранена в findings
class FindingOut(BaseModel):
    id: int
    finding_type: str = Field(..., description="Концепт (finding_type=concept)")
    value: str | None = Field(None, description="Утверждение (assertion)")
    location: str | None = Field(None, description="Орган / участок")
    side: str | None = Field(None, description="Сторона (left / right)")
    category: str | None = Field(None, description="Категория, например BI-RADS")
    negated: bool = Field(False, description="Отрицание")
    evidence_text: str | None = Field(None, description="Цитата из протокола")
    confidence: float | None = Field(None, description="Пока всегда null")


# Схема триггера — так, как он сохранён в triggers
class TriggerOut(BaseModel):
    id: int
    trigger_name: str
    type_diagnosis: str | None = Field(None, description="Тип утверждения (affirmed / suspected)")
    evidence: str | None = Field(None, description="Цитата из протокола")
    is_mismatch: bool = Field(False, description="Противоречие affirmed + negated")


# Схема маршрута — так, как он сохранён в routes
class RouteOut(BaseModel):
    id: int
    specialist: str = Field(..., description="Тип специалиста (specialist_type)")
    next_step: str
    deadline: datetime | None = Field(None, description="deadline_date; null = без срока")
    status: str = Field(..., description="planned | manual_review")


# Схема ответа на анализ протокола (контракт фронта)
class ProtocolAnalyzeResponse(BaseModel):
    status: str = "success"
    protocol_id: int
    patient_id: int
    engine: str = Field(..., description="Движок анализа (сейчас: stub)")
    study_type: str | None = Field(None, description="Тип исследования (УЗИ, МРТ, ...)")
    findings: list[FindingOut] = Field(default_factory=list)
    triggers: list[TriggerOut] = Field(default_factory=list)
    decision: str = Field(..., description="consultation | manual_review | no_supported_trigger")
    routes: list[RouteOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    review_reasons: list[str] = Field(default_factory=list)
    notice: str = Field(..., description="Не диагноз и не назначение лечения")


# Детали протокола: протокол + findings + routes
class ProtocolDetail(BaseModel):
    id: int
    patient_id: int
    file_name: str | None = None
    protocol_date: datetime | None = None
    doc_text: str
    created_at: datetime | None = None
    findings: list[FindingOut] = Field(default_factory=list)
    routes: list[RouteOut] = Field(default_factory=list)

class PatientResponse(BaseModel):
    id: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True

# ============================================================
# Дополнительные API-схемы
# ============================================================


# -----------------------------
# Протоколы
# -----------------------------

class ProtocolResponse(BaseModel):
    id: int
    patient_id: int
    file_name: str | None = None
    protocol_date: datetime | None = None
    doc_text: str
    created_at: datetime | None = None

    class Config:
        from_attributes = True


# -----------------------------
# Маршруты
# -----------------------------

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


# -----------------------------
# Записи на приём
# -----------------------------

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


# -----------------------------
# Уведомления
# -----------------------------

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


# -----------------------------
# События маршрута
# -----------------------------

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


# -----------------------------
# Эталонная разметка
# -----------------------------

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