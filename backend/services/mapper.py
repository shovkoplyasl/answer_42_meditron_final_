# services/mapper.py
"""Маппинг результата анализа (контракт services/analyzer.py) в таблицы БД.

Чистые функции: адаптер -> ORM-объекты. В БД всё попадает только через
одну транзакцию в main.py. Правила маршрутизации (routing_rules) здесь
только читаются — не создаются на каждый запрос.
"""

from datetime import datetime, timedelta, timezone

from models import Finding, Route, RouteEvent, RouteTrigger, RoutingRule, Trigger

# Утверждения, которые могут вести к действию (маршруту).
ACTION_ASSERTIONS = ("affirmed", "suspected")


def findings_from_facts(protocol_id: int, facts: list[dict]) -> list[Finding]:
    """Каждый fact -> finding.

    type=concept, value=assertion, location=organ, side, category
    (например, категория BI-RADS), evidence_text=quote,
    negated=(утверждение отрицательное).
    """
    return [
        Finding(
            protocol_id=protocol_id,
            finding_type=fact.get("concept") or "",
            value=fact.get("assertion"),
            location=fact.get("organ"),
            side=fact.get("side"),
            category=fact.get("category"),
            evidence_text=fact.get("quote"),
            negated=(fact.get("assertion") == "negated") or bool(fact.get("negated", False)),
            confidence=None,  # confidence пока null (пункт 4 плана)
        )
        for fact in facts
    ]


def warnings_as_findings(protocol_id: int, warnings: list[str]) -> list[Finding]:
    """Предупреждения адаптера -> finding с type='warning'."""
    return [
        Finding(protocol_id=protocol_id, finding_type="warning", value=w)
        for w in warnings
    ]


def triggers_from_facts(protocol_id: int, facts: list[dict]) -> list[Trigger]:
    """affirmed/suspected факты -> triggers.

    trigger_name=concept, type_diagnosis=assertion, evidence=quote.
    negated/historical — триггера не создают. При противоречии
    (один concept и affirmed, и negated) триггер создаётся
    с is_mismatch=True.
    """
    by_concept: dict[str, dict] = {}
    for fact in facts:
        assertion = (fact.get("assertion") or "").strip().lower()
        concept = fact.get("concept") or ""
        if assertion in ACTION_ASSERTIONS:
            by_concept[concept] = {"fact": fact, "negated": False}
        elif assertion == "negated":
            # запоминаем отрицание, но не перезаписываем affirmed-факт
            entry = by_concept.setdefault(concept, {"fact": None, "negated": True})
            entry["negated"] = True

    triggers = []
    for concept, entry in by_concept.items():
        if entry["fact"] is None:
            continue  # только negated — к действию не ведёт
        triggers.append(Trigger(
            protocol_id=protocol_id,
            trigger_name=concept,
            type_diagnosis=entry["fact"].get("assertion"),
            evidence=entry["fact"].get("quote"),
            is_mismatch=entry["negated"],
        ))
    return triggers


def match_rule(proposal: dict, rules: list[RoutingRule]) -> RoutingRule | None:
    """Найти активное правило для предложения маршрута.

    Сопоставление по trigger_name; если у правила есть фильтр
    conditions.categories, category предложения должна быть в списке.
    """
    trigger = (proposal.get("trigger") or "").strip().lower()
    for rule in rules:
        if (rule.trigger_name or "").strip().lower() != trigger:
            continue
        categories = (rule.conditions or {}).get("categories")
        if categories:
            category = str(proposal.get("category") or "")
            if category not in [str(c) for c in categories]:
                continue
        return rule
    return None


def route_from_proposal(patient_id: int, proposal: dict, rule: RoutingRule | None) -> Route:
    """decision=consultation + profile -> маршрут (по правилу, если нашлось)."""
    deadline_date = None
    if rule is not None and rule.deadline_days:
        deadline_date = datetime.now(timezone.utc) + timedelta(days=int(rule.deadline_days))
    return Route(
        patient_id=patient_id,
        rule_id=rule.id if rule is not None else None,
        status="planned",
        next_step=proposal.get("next_step") or (rule.next_step if rule else "Консультация"),
        specialist_type=proposal.get("specialist") or (rule.specialist_type if rule else "Координатор"),
        deadline_date=deadline_date,
    )


def manual_review_route(patient_id: int, reasons: list[str]) -> Route:
    """decision=manual_review -> маршрут со статусом manual_review, специалист Координатор."""
    next_step = "Ручная проверка координатором"
    if reasons:
        next_step += ": " + "; ".join(reasons)
    return Route(
        patient_id=patient_id,
        status="manual_review",
        next_step=next_step,
        specialist_type="Координатор",
    )


def link_triggers(route_id: int, triggers: list[Trigger], proposal: dict) -> list[RouteTrigger]:
    """Связать маршрут с триггерами протокола по имени триггера."""
    name = (proposal.get("trigger") or "").strip().lower()
    return [
        RouteTrigger(route_id=route_id, trigger_id=trigger.id)
        for trigger in triggers
        if (trigger.trigger_name or "").strip().lower() == name
    ]


def protocol_analyzed_event(route_id: int) -> RouteEvent:
    """Событие на маршруте: протокол проанализирован."""
    return RouteEvent(
        route_id=route_id,
        event_type="protocol.analyzed",
        description="Протокол проанализирован, маршрут создан",
        source="analyzer",
    )
