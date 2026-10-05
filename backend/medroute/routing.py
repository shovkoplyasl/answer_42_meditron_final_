from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def route(analysis: dict) -> dict:
    config = json.loads(
        (ROOT / "config/routing.json").read_text(encoding="utf-8")
    )

    proposals = []
    review_reasons = list(analysis.get("warnings", []))

    for fact in analysis["facts"]:
        status = fact["assertion"]

        if status in ("negated", "historical"):
            continue

        if status in ("uncertain", "suspected"):
            review_reasons.append(
                f"{fact['label']}: {status}; требуется проверка персоналом"
            )
            continue

        if fact["concept"] == "venous_thrombosis":
            review_reasons.append(
                "Упоминание тромбоза: эскалация персоналу, "
                "без автоматического сообщения пациенту"
            )
            continue

        matches = [
            rule
            for rule in config["rules"]
            if rule["concept"] == fact["concept"]
            and (
                "categories" not in rule
                or fact.get("category") in rule["categories"]
            )
        ]

        for rule in matches:
            # Сохраняем исходные поля routing.json
            # и одновременно приводим их к единому контракту для mapper.py.
            profile = rule.get("profile") or rule.get("specialist_type")
            action = rule.get("action") or rule.get("next_step")
            due_days = rule.get("due_days")

            if due_days is None:
                due_days = rule.get("deadline_days")

            proposals.append(
                {
                    **rule,

                    # Старый контракт тестов / routing
                    "profile": profile,

                    # Контракт mapper.py / Route
                    "specialist_type": profile,
                    "next_step": action,
                    "deadline_days": due_days,

                    "rule_version": config["version"],
                    "evidence": fact["evidence"],
                    "category": fact.get("category"),
                    "side": fact.get("side"),
                }
            )

        if not matches and fact["concept"] != "birads":
            review_reasons.append(
                f"{fact['label']}: "
                "автоматическая матрица для этого признака ещё не утверждена"
            )

        if (
            fact["concept"] == "birads"
            and fact.get("category") in ("0", "6")
        ):
            review_reasons.append(
                "Категория BI-RADS вне демонстрационных правил: "
                "требуется персонал"
            )

    # Unknown/urgent evidence on a supported trigger
    # blocks automatic outreach.
    blocking = any(
        f["assertion"] in ("uncertain", "suspected")
        and f["concept"]
        in (
            "endometrial_polyp",
            "gallbladder_stone",
            "birads",
            "venous_thrombosis",
        )
        for f in analysis["facts"]
    )

    blocking |= any(
        f["concept"] == "venous_thrombosis"
        and f["assertion"] == "affirmed"
        for f in analysis["facts"]
    )

    if blocking:
        decision = "manual_review"
    elif proposals:
        decision = "consultation"
    elif review_reasons:
        decision = "manual_review"
    else:
        decision = "no_supported_trigger"

    profiles = sorted(
        {
            p["profile"]
            for p in proposals
            if p.get("profile")
        }
    ) if decision == "consultation" else []

    return {
        "decision": decision,
        "proposals": proposals,
        "profiles": profiles,
        "review_reasons": list(dict.fromkeys(review_reasons)),
        "rule_version": config["version"],
        "clinical_status": config["clinical_status"],
        "notice": (
            "Демонстрационные маршруты. "
            "Не диагноз и не назначение лечения."
        ),
    }