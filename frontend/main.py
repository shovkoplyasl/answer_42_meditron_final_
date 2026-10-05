# main.py
import io
from datetime import date, datetime, timezone

import docx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

import models
import schemas
from database import get_db

app = FastAPI(title="SM-Clinic Protocol Analysis API")


def parse_generic_docx(file_bytes: bytes) -> dict:
    """Универсальный парсер для любых файлов протоколов от жюри."""
    doc = docx.Document(io.BytesIO(file_bytes))
    full_text = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    joined_text = "\n".join(full_text)

    # Эвристика для поиска раздела заключения
    conclusion = ""
    for text in full_text:
        if "заключение" in text.lower():
            conclusion = text
            break

    return {
        "doc_text": joined_text,
        "conclusion": conclusion or "Заключение не найдено",
    }


@app.get("/")
def read_root():
    return {"status": "ok", "message": "SM-Clinic Backend Service is running!"}


@app.post(
    "/api/v1/analyze",
    response_model=schemas.ProtocolAnalyzeResponse,
    tags=["Анализ протоколов"],
    summary="Отправить протокол на проверку ИИ и сохранить в БД",
)
async def analyze_protocol(
    request: schemas.ProtocolAnalyzeRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
):
    """Эндпоинт принимает текст протокола, симулирует анализ ИИ (проверку расхождений),

    сохраняет пациента и протокол в базу данных PostgreSQL.
    """
    try:
        # 1. Создаем тестового пациента в БД
        db_patient = models.Patient(
            surname="Иванов",
            name_patient=request.patient_id,  # Для демо используем переданную строку как имя
            second_name="Алексеевич",
            birth_date=date(1985, 5, 12),
        )
        db.add(db_patient)
        await db.flush()  # Чтобы получить сгенерированный id пациента
        await db.commit()
        await db.refresh(db_patient)

        # 2. Сохраняем протокол УЗИ в таблицу protocols
        db_protocol = models.Protocol(
            patient_id=db_patient.id,
            file_name="ultrasound_scan_demo.pdf",
            protocol_date=datetime.now(timezone.utc),
            doc_text=request.protocol_text,
        )
        db.add(db_protocol)
        await db.commit()
        await db.refresh(db_protocol)

        # 3. Формируем ответ (моделируем работу ИИ и поиск дефектов)
        mock_issue = schemas.ProtocolIssue(
            item="Аллергоанамнез / Шкала EU-TIRADS",
            description=(
                "В тексте обнаружен узел щитовидной железы, но в итоговом"
                " заключении категория по шкале не указана (is_mismatch=True)."
            ),
            severity="error",
        )

        return schemas.ProtocolAnalyzeResponse(
            status="success",
            checked_items_count=14,
            issues=[mock_issue],
            summary=(
                f"Протокол для пациента {db_patient.name_patient} (ID:"
                f" {db_patient.id}) успешно сохранен в БД и проанализирован."
            ),
        )

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных: {e!s}",
        )


@app.post(
    "/api/v1/evaluate-jury-protocol",
    tags=["Проверка данных жюри"],
    summary="Загрузка протокола жюри, сохранение в PostgreSQL и анализ дефектов",
)
async def evaluate_jury_protocol(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)  # noqa: B008
):
    """Принимает файл протокола (.docx) от жюри, считывает его,

    сохраняет в PostgreSQL и выполняет автоматическую проверку на дефекты.
    """
    if not file.filename.endswith((".docx", ".pdf")):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только документы Word (.docx)",
        )

    try:
        content = await file.read()
        parsed_data = parse_generic_docx(content)

        # 1. Сохраняем пациента в PostgreSQL на основе файла
        db_patient = models.Patient(
            surname="Пациент (из данных жюри)",
            name_patient=file.filename,
            second_name="",
            birth_date=date(1980, 1, 1),
        )
        db.add(db_patient)
        await db.flush()

        # 2. Сохраняем сам протокол в PostgreSQL
        db_protocol = models.Protocol(
            patient_id=db_patient.id,
            file_name=file.filename,
            protocol_date=datetime.now(timezone.utc),
            doc_text=parsed_data["doc_text"],
        )
        db.add(db_protocol)
        await db.commit()
        await db.refresh(db_protocol)

        # 3. Интеллектуальная проверка на дефекты
        issues = []
        text_lower = parsed_data["doc_text"].lower()

        if "узел" in text_lower and "ti-rads" not in text_lower:
            issues.append({
                "item": "Клиническая шкала (TI-RADS)",
                "description": (
                    "Обнаружено описание узла, но в тексте/заключении"
                    " отсутствует шкала TI-RADS."
                ),
                "severity": "error",
            })

        if not parsed_data["conclusion"] or len(parsed_data["conclusion"]) < 5:
            issues.append({
                "item": "Наличие заключения",
                "description": "Итоговое заключение размыто или отсутствует.",
                "severity": "warning",
            })

        return {
            "status": "success",
            "saved_in_db": {
                "patient_id": db_patient.id,
                "protocol_id": db_protocol.id,
            },
            "file_analyzed": file.filename,
            "total_issues": len(issues),
            "issues": issues,
            "summary": (
                "Протокол успешно принят, интегрирован в PostgreSQL и проверен."
            ),
        }

    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка базы данных при сохранении: {e!s}",
        )