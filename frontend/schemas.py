# описание модели с помощью Pydantic для валидации входящих и исходящих данных в FastAPI

from pydantic import BaseModel, Field


# Схема входящего запроса на анализ протокола
class ProtocolAnalyzeRequest(BaseModel):
    patient_id: str = Field(..., description="Идентификатор или ФИО пациента")
    protocol_text: str = Field(..., description="Текст медицинского протокола для проверки по чек-листу")


# Схема отдельной рекомендации или найденного отклонения
class ProtocolIssue(BaseModel):
    item: str = Field(..., description="Пункт чек-листа или категория проверки")
    description: str = Field(..., description="Описание несоответствия или замечания")
    severity: str = Field("warning", description="Важность: warning, error или info")


# Схема ответа бэкенда с результатами проверки
class ProtocolAnalyzeResponse(BaseModel):
    status: str = "success"
    checked_items_count: int = Field(..., description="Количество проверенных пунктов")
    issues: list[ProtocolIssue] = Field(default=[], description="Список найденных нарушений/замечаний")
    summary: str = Field(..., description="Общий вывод ИИ по протоколу")