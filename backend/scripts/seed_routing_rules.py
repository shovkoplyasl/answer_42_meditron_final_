# scripts/seed_routing_rules.py
"""Идемпотентный сид правил маршрутизации.

Источник правил — config/routing.json (синхронизирован с PoC,
один источник правды). Повторный запуск обновляет существующие
правила по trigger_name и не создаёт дубликаты.

Запуск:
    .\.venv\Scripts\python.exe scripts\seed_routing_rules.py

Маппинг поля PoC -> столбец БД:
    concept      -> trigger_name
    categories   -> conditions JSONB {"categories": [...]}
    profile      -> specialist_type
    action       -> next_step
    due_days     -> deadline_days (None = срок не утверждён клиникой)
    version      -> rule_version
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# чтобы `import database` / `import models` работали при запуске
# скрипта напрямую (python scripts/seed_routing_rules.py)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402

from database import AsyncSessionLocal  # noqa: E402
from models import RoutingRule  # noqa: E402


def load_rules() -> list[dict]:
    """Прочитать правила из config/routing.json."""
    config = json.loads(
        (ROOT / "config" / "routing.json").read_text(encoding="utf-8")
    )
    seeded = []
    for rule in config["rules"]:
        seeded.append({
            "trigger_name": rule["concept"],
            "conditions": (
                {"categories": rule["categories"]}
                if "categories" in rule else None
            ),
            "specialist_type": rule.get("profile") or rule["specialist_type"],
            "next_step": rule.get("action") or rule["next_step"],
            "deadline_days": rule.get("due_days", rule.get("deadline_days")),
            "priority": 1,
            "rule_version": config["version"],
            "is_active": True,
        })
    return seeded


async def seed() -> int:
    """Upsert правил по trigger_name. Возвращает количество правил."""
    rules = load_rules()
    async with AsyncSessionLocal() as session:
        for rule in rules:
            existing = (
                await session.execute(
                    select(RoutingRule).where(
                        RoutingRule.trigger_name == rule["trigger_name"]
                    )
                )
            ).scalar_one_or_none()
            if existing:
                for key, value in rule.items():
                    setattr(existing, key, value)
            else:
                session.add(RoutingRule(**rule))
        await session.commit()
    return len(rules)


if __name__ == "__main__":
    count = asyncio.run(seed())
    print(f"seeded {count} routing rules (idempotent upsert by trigger_name)")
