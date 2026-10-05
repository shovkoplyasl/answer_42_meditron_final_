# SM-Clinic Meditron (backend)

Бэкенд сервиса анализа медицинских протоколов: **FastAPI + SQLAlchemy (PostgreSQL / SQLite)**.

Текущая фаза — честный бэкенд: запуск, БД, контракт API, запись в таблицы. NLP подключено через адаптер (`services/analyzer.py`) — ядро из PoC (`medroute/nlp.py` + `medroute/routing.py`), обезличенные протоколы, только ID пациентов.

## Структура

```text
main.py              # API (FastAPI): эндпоинты, оркестрация
database.py          # Подключение к БД (DATABASE_URL из .env), ping
models.py            # ORM-модели — только отражают schema.sql
schemas.py           # Pydantic-контракты запросов/ответов
services/
  analyzer.py        # Адаптер анализа (граница к NLP)
  mapper.py          # Маппинг результата анализа в таблицы БД
medroute/
  nlp.py             # Ядро NLP из PoC (regex-правила, утверждения, BI-RADS)
  routing.py         # Маршрутизация на основе config/routing.json
  documents.py       # Чтение DOCX (read_docx, clinical_text)
config/
  concepts.json      # Концепты для NLP (label, organ)
  routing.json       # Правила маршрутизации (сид в БД)
database/schema.sql  # Источник правды по схеме БД
scripts/
  seed_routing_rules.py # Идемпотентный сид правил маршрутизации
tests/
  conftest.py        # Фикстуры pytest
  test_analyzer.py   # Тесты адаптера анализа
  test_mapper.py     # Тесты маппинга
  test_api.py        # Тесты API
data/private/        # Корпус данных для оценки (опционально)
```

> **Важно:** Таблицы НЕ создаются из ORM «на лету». Источник правды — `database/schema.sql`, применяется вручную или через скрипты инициализации.
> Живые таблицы первой итерации: `patients`, `protocols`, `findings`, `triggers`, `routing_rules`, `routes`, `route_triggers`, `route_events`.
> Остальные таблицы схемы (`appointments`, `hospitalizations`, `ml_predictions` и т.д.) — не трогаем, пока `analyze` не стабилен.

## Подготовка окружения

* Python 3.11+
* Установка зависимостей:

```bash
# виртуальное окружение
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# установка зависимостей (включая aiosqlite для SQLite и multipart для файлов)
pip install -r requirements.txt
pip install aiosqlite python-multipart pytest pytest-asyncio httpx

# конфиг: скопировать шаблон и указать свою строку подключения
copy .env.example .env
```

## База данных

Для локальной разработки и тестов вы можете использовать SQLite (быстрый старт без установки СУБД) либо PostgreSQL.

### Вариант А: SQLite (Рекомендуется для локальных тестов)
В файле `.env` укажите строку подключения:
```env
DATABASE_URL=sqlite+aiosqlite:///./test.db
```

### Вариант Б: PostgreSQL (15+)
Нужен локальный PostgreSQL на порту 5432.
```bash
# создать БД (один раз)
createdb -U postgres sm_clinic_db

# применить схему
# ВНИМАНИЕ: schema.sql дропает таблицы (drop ... cascade) — только на dev!
psql "postgresql://postgres:postgres@localhost:5432/sm_clinic_db" -f database/schema.sql
```

> **Примечание для тестов с SQLite:** Чтобы `pytest` успешно видел локальную базу при тестировании, убедитесь, что в начале файла `tests/test_api.py` задана переменная окружения:
> `os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"`

## Сид правил маршрутизации

Запуск идемпотентного сида правил из `config/routing.json`:
```bash
python scripts/seed_routing_rules.py
```

Проверка: `GET /ready` должен вернуть `{"status":"ok","database":"up"}`.

## Запуск приложения

```bash
python -m uvicorn main:app --reload
```

* Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* `GET /health` — liveness (приложение отвечает)
* `GET /ready` — readiness (пингует БД, 503 если БД недоступна)
* `GET /` — информационный корень

## API

* `POST /api/v1/patients` — создать пациента (возвращает ID)
* `POST /api/v1/analyze` — анализ протокола: `patient_id` (обязательный) + `protocol_text` (опционально `file_name`, `protocol_date`)
* `POST /api/v1/analyze/file` — загрузка DOCX протокола: передается `patient_id` (query) + файл через `multipart/form-data` (`file`)
* `GET /api/v1/protocols/{id}` — получить протокол + findings + routes

Пример запроса JSON (Git Bash):
```bash
echo '{"patient_id":1,"protocol_text":"УЗИ малого таза. Полип эндометрия."}' > /tmp/req.json
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze -H "Content-Type: application/json" --data-binary @/tmp/req.json
```

Пример загрузки DOCX файла:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/analyze/file?patient_id=1" \
  -F "file=@/path/to/protocol.docx"
```

> **Примечание:** Если при старте в логе предупреждение о недоступности базы данных — проверьте `DATABASE_URL` в `.env`. Приложение при этом всё равно стартует и отвечает на `/` и `/health`.

## Тесты

Запуск автоматических тестов через pytest:
```bash
python -m pytest tests/ -v
```

## Оценка качества (опционально)

Корпус данных из PoC (89 документов):
```bash
mkdir data/private
cp /path/to/SM-Clinic-PoC/data/private/corpus.json data/private/
cp /path/to/SM-Clinic-PoC/data/private/gold.json data/private/
python -m medroute.evaluate --split test
```

## Примечания

* Пациенты обезличены — только ID, без ФИО.
* NLP — regex-правила (не ML), ядро из PoC.
* PoC не трогать — только копировать файлы из него.
* Таблицы создаются по схеме (`schema.sql`) — не из ORM.