import asyncio
import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from database import check_db_connection, engine, get_db
from services import analyzer, mapper
from medroute.documents import read_docx

logger = logging.getLogger("sm-clinic")


def _analysis_event(route_id, protocol_id):
    event = mapper.protocol_analyzed_event(route_id)
    event.description = json.dumps({"protocol_id": protocol_id}, ensure_ascii=False)
    return event


def _finding_out(f: models.Finding) -> schemas.FindingOut:
    """ORM Finding -> контракт ответа."""
    return schemas.FindingOut(
        id=f.id,
        finding_type=f.finding_type,
        value=f.value,
        location=f.location,
        side=f.side,
        category=f.category,
        negated=f.negated,
        evidence_text=f.evidence_text,
        confidence=float(f.confidence) if f.confidence is not None else None,
    )


def _trigger_out(t: models.Trigger) -> schemas.TriggerOut:
    """ORM Trigger -> контракт ответа."""
    return schemas.TriggerOut(
        id=t.id,
        trigger_name=t.trigger_name,
        type_diagnosis=t.type_diagnosis,
        evidence=t.evidence,
        is_mismatch=t.is_mismatch,
    )


def _route_out(r: models.Route) -> schemas.RouteOut:
    """ORM Route -> контракт ответа."""
    return schemas.RouteOut(
        id=r.id,
        specialist=r.specialist_type,
        next_step=r.next_step,
        deadline=r.deadline_date,
        status=r.status,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Проверяем соединение с БД при старте, чтобы дать понятный лог,
    а не 500 на каждый запрос."""
    app.state.db_ready = await check_db_connection()
    if app.state.db_ready:
        logger.info("PostgreSQL: соединение установлено.")
    else:
        logger.warning(
            "PostgreSQL недоступна. Проверьте DATABASE_URL в .env "
            "и что сервер PostgreSQL запущен. Приложение стартовало, "
            "но эндпоинты, работающие с БД, будут возвращать ошибку."
        )
    yield
    await engine.dispose()


app = FastAPI(title="SM-Clinic Protocol Analysis API", lifespan=lifespan)


@app.get("/", tags=["Сервис"])
def read_root():
    return {"status": "ok", "message": "SM-Clinic Backend Service is running!"}


@app.get("/health", tags=["Сервис"])
def health():
    """Liveness: приложение отвечает (БД не проверяем)."""
    return {"status": "ok"}


@app.get("/ready", tags=["Сервис"])
async def ready():
    """Readiness: проверяет доступность PostgreSQL."""
    db_ok = await check_db_connection()
    app.state.db_ready = db_ok
    if db_ok:
        return {"status": "ok", "database": "up"}
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="PostgreSQL недоступна. Проверьте DATABASE_URL в .env.",
    )


@app.post(
    "/api/v1/analyze",
    response_model=schemas.ProtocolAnalyzeResponse,
    tags=["Анализ протоколов"],
    summary="Отправить протокол на анализ и сохранить в БД"
)
async def analyze_protocol(
    request: schemas.ProtocolAnalyzeRequest,
    db: AsyncSession = Depends(get_db)  # noqa: B008
):
    """
    Определяет пациента (по patient_id — существующего), сохраняет протокол
    с реальным текстом и именем файла.

    Один запрос = одна транзакция: пациент + протокол + находки +
    триггеры + маршруты. Ошибка -> rollback всего.
    """
    try:
        # 1. Анализ текста через адаптер (NLP из PoC).
        result = await asyncio.to_thread(analyzer.analyze_text, request.protocol_text)

        # 2. Пациент: ищем по patient_id (обязательный)
        db_patient = await db.get(models.Patient, request.patient_id)
        if db_patient is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Пациент с patient_id={request.patient_id} не найден в БД",
            )

        # 3. Сохраняем протокол с реальным текстом и именем файла
        db_protocol = models.Protocol(
            patient_id=db_patient.id,
            file_name=request.file_name,
            protocol_date=request.protocol_date or datetime.now(timezone.utc),
            doc_text=request.protocol_text,
        )
        db.add(db_protocol)
        await db.flush()

        # 4. Маппинг результата анализа: findings и triggers
        findings = mapper.findings_from_facts(db_protocol.id, result["facts"])
        findings += mapper.warnings_as_findings(db_protocol.id, result["warnings"])
        triggers = mapper.triggers_from_facts(db_protocol.id, result["facts"])
        db.add_all(findings)
        db.add_all(triggers)
        await db.flush()

        # 5. Маршруты. Активные правила только читаем (routing_rules),
        #    не создаём на каждый запрос.
        rules = (await db.scalars(
            select(models.RoutingRule).where(models.RoutingRule.is_active.is_(True))
        )).all()

        routes = []
        if result["decision"] == "consultation":
            for proposal in result["proposals"]:
                rule = mapper.match_rule(proposal, rules)
                route = mapper.route_from_proposal(db_patient.id, proposal, rule)
                db.add(route)
                await db.flush()
                db.add_all(mapper.link_triggers(route.id, triggers, proposal))
                db.add(_analysis_event(route.id, db_protocol.id))
                routes.append(route)
        elif result["decision"] == "manual_review":
            route = mapper.manual_review_route(db_patient.id, result["review_reasons"])
            db.add(route)
            await db.flush()
            db.add(_analysis_event(route.id, db_protocol.id))
            routes.append(route)
        # no_supported_trigger: маршрут не создаём, ответ объясняет почему

        # 6. Одна транзакция на запрос: ошибка -> rollback всего
        await db.commit()
        await db.refresh(db_patient)
        await db.refresh(db_protocol)

        # 7. Ответ формирует адаптер (result) + сохранённые объекты.
        return schemas.ProtocolAnalyzeResponse(
            status="success",
            protocol_id=db_protocol.id,
            patient_id=db_patient.id,
            engine=result["engine"],
            study_type=result.get("study_type"),
            findings=[_finding_out(f) for f in findings],
            triggers=[_trigger_out(t) for t in triggers],
            decision=result["decision"],
            routes=[_route_out(r) for r in routes],
            warnings=list(result["warnings"]),
            review_reasons=list(result["review_reasons"]),
            notice=result.get("notice") or schemas.NOTICE_TEXT,
        )

    except HTTPException:
        await db.rollback()
        raise
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=422, detail=str(e)) from e
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {e!s}"
        )


@app.post(
    "/api/v1/analyze/file",
    response_model=schemas.ProtocolAnalyzeResponse,
    tags=["Анализ протоколов"],
    summary="Загрузить DOCX и анализировать"
)
async def analyze_file(
    file: UploadFile,
    patient_id: int,
    protocol_date: datetime | None = None,
    db: AsyncSession = Depends(get_db)
):
    content = await file.read(12 * 1024 * 1024 + 1)
    try:
        text = read_docx(content)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Не удалось прочитать DOCX. Проверьте формат и размер файла (до 12 МБ).") from exc

    request = schemas.ProtocolAnalyzeRequest(
        patient_id=patient_id,
        protocol_text=text,
        file_name=file.filename,
        protocol_date=protocol_date,
    )
    return await analyze_protocol(request, db)


@app.get(
    "/api/v1/protocols/{protocol_id}",
    response_model=schemas.ProtocolDetail,
    tags=["Протоколы"],
    summary="Протокол + находки + маршруты по ID",
)
async def get_protocol(
    protocol_id: int,
    db: AsyncSession = Depends(get_db)  # noqa: B008
):
    """Протокол с находками и маршрутами, созданными по триггерам.

    Маршруты берутся через route_triggers -> triggers протокола.
    manual_review-маршруты привязаны к пациенту, а не к протоколу
    (ограничение схемы — фаза 2).
    """
    protocol = await db.get(models.Protocol, protocol_id)
    if protocol is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Протокол с id={protocol_id} не найден",
        )
    findings = (
        await db.scalars(
            select(models.Finding)
            .where(models.Finding.protocol_id == protocol_id)
            .order_by(models.Finding.id)
        )
    ).all()
    routes = (
        await db.scalars(
            select(models.Route)
            .join(
                models.RouteTrigger,
                models.RouteTrigger.route_id == models.Route.id,
            )
            .join(models.Trigger, models.Trigger.id == models.RouteTrigger.trigger_id)
            .where(models.Trigger.protocol_id == protocol_id)
            .order_by(models.Route.id)
        )
    ).all()
    return schemas.ProtocolDetail(
        id=protocol.id,
        patient_id=protocol.patient_id,
        file_name=protocol.file_name,
        protocol_date=protocol.protocol_date,
        doc_text=protocol.doc_text,
        created_at=protocol.created_at,
        findings=[_finding_out(f) for f in findings],
        routes=[_route_out(r) for r in routes],
    )


@app.post("/api/v1/patients", tags=["Пациенты"])
async def create_patient(db: AsyncSession = Depends(get_db)):
    """Создать пациента (только ID, без ФИО)."""
    try:
        patient = models.Patient()
        db.add(patient)
        await db.commit()
        await db.refresh(patient)
        return {"id": patient.id}

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка: {e!s}"
        )


@app.get(
    "/api/v1/patients/{patient_id}",
    response_model=schemas.PatientResponse,
    tags=["Пациенты"],
    summary="Получить пациента по ID",
)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить пациента по его ID."""

    patient = await db.get(models.Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент с id={patient_id} не найден",
        )

    return patient

@app.get(
    "/api/v1/patients/{patient_id}/protocols",
    response_model=list[schemas.ProtocolResponse],
    tags=["Протоколы"],
    summary="Получить протоколы пациента",
)
async def get_patient_protocols(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(models.Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент с id={patient_id} не найден",
        )

    result = await db.scalars(
        select(models.Protocol)
        .where(models.Protocol.patient_id == patient_id)
        .order_by(models.Protocol.id.desc())
    )

    return result.all()

@app.post(
    "/api/v1/routes",
    response_model=schemas.RouteResponse,
    tags=["Маршруты"],
    summary="Создать маршрут пациента",
)
async def create_route(
    request: schemas.RouteCreate,
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(models.Patient, request.patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент с id={request.patient_id} не найден",
        )

    if request.rule_id is not None:
        rule = await db.get(models.RoutingRule, request.rule_id)

        if rule is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Правило маршрутизации с id={request.rule_id} не найдено",
            )

    route = models.Route(
        patient_id=request.patient_id,
        rule_id=request.rule_id,
        status=request.status,
        next_step=request.next_step,
        specialist_type=request.specialist_type,
        deadline_date=request.deadline_date,
    )

    db.add(route)

    try:
        await db.commit()
        await db.refresh(route)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )

    return route

@app.get(
    "/api/v1/routes/{route_id}",
    response_model=schemas.RouteResponse,
    tags=["Маршруты"],
    summary="Получить маршрут",
)
async def get_route(
    route_id: int,
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(models.Route, route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Маршрут с id={route_id} не найден",
        )

    return route

@app.get(
    "/api/v1/patients/{patient_id}/routes",
    response_model=list[schemas.RouteResponse],
    tags=["Маршруты"],
    summary="Получить маршруты пациента",
)
async def get_patient_routes(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    patient = await db.get(models.Patient, patient_id)

    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Пациент с id={patient_id} не найден",
        )

    result = await db.scalars(
        select(models.Route)
        .where(models.Route.patient_id == patient_id)
        .order_by(models.Route.id.desc())
    )

    return result.all()

@app.post(
    "/api/v1/appointments",
    response_model=schemas.AppointmentResponse,
    tags=["Записи"],
    summary="Создать запись на приём",
)
async def create_appointment(
    request: schemas.AppointmentCreate,
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(models.Route, request.route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Маршрут с id={request.route_id} не найден",
        )

    appointment = models.Appointment(
        route_id=request.route_id,
        doctor_name=request.doctor_name,
        doctor_type=request.doctor_type,
        clinic=request.clinic,
        appointment_type=request.appointment_type,
        external_slot_id=request.external_slot_id,
        appointment_date=request.appointment_date,
        status=request.status,
        is_previous_doctor=request.is_previous_doctor,
    )

    db.add(appointment)

    try:
        await db.commit()
        await db.refresh(appointment)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )

    return appointment

@app.get(
    "/api/v1/routes/{route_id}/appointments",
    response_model=list[schemas.AppointmentResponse],
    tags=["Записи"],
    summary="Получить записи по маршруту",
)
async def get_route_appointments(
    route_id: int,
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(models.Route, route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Маршрут с id={route_id} не найден",
        )

    result = await db.scalars(
        select(models.Appointment)
        .where(models.Appointment.route_id == route_id)
        .order_by(models.Appointment.appointment_date)
    )

    return result.all()

@app.post(
    "/api/v1/notifications",
    response_model=schemas.NotificationResponse,
    tags=["Уведомления"],
    summary="Создать уведомление",
)
async def create_notification(
    request: schemas.NotificationCreate,
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(models.Route, request.route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Маршрут с id={request.route_id} не найден",
        )

    notification = models.Notification(
        route_id=request.route_id,
        channel=request.channel,
        status=request.status,
        message_text=request.message_text,
    )

    db.add(notification)

    try:
        await db.commit()
        await db.refresh(notification)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )

    return notification

@app.post(
    "/api/v1/events",
    response_model=schemas.RouteEventResponse,
    tags=["События"],
    summary="Добавить событие маршрута",
)
async def create_route_event(
    request: schemas.RouteEventCreate,
    db: AsyncSession = Depends(get_db),
):
    route = await db.get(models.Route, request.route_id)

    if route is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Маршрут с id={request.route_id} не найден",
        )

    event = models.RouteEvent(
        route_id=request.route_id,
        event_type=request.event_type,
        description=request.description,
        source=request.source,
        external_event_id=request.external_event_id,
    )

    db.add(event)

    try:
        await db.commit()
        await db.refresh(event)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )

    return event

@app.post(
    "/api/v1/ground-truth",
    response_model=schemas.GroundTruthResponse,
    tags=["Оценка"],
    summary="Добавить эталонную разметку протокола",
)
async def create_ground_truth(
    request: schemas.GroundTruthCreate,
    db: AsyncSession = Depends(get_db),
):
    protocol = await db.get(models.Protocol, request.protocol_id)

    if protocol is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Протокол с id={request.protocol_id} не найден",
        )

    truth = models.GroundTruth(
        protocol_id=request.protocol_id,
        finding_type=request.finding_type,
        true_value=request.true_value,
        true_numeric_value=request.true_numeric_value,
        true_unit=request.true_unit,
        true_route=request.true_route,
        evidence=request.evidence,
        verified_by=request.verified_by,
    )

    db.add(truth)

    try:
        await db.commit()
        await db.refresh(truth)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )

    return truth

