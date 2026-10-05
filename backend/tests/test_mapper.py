from services.mapper import findings_from_facts, triggers_from_facts, match_rule
from models import RoutingRule

def test_finding_from_fact():
    facts = [{"concept": "endometrial_polyp", "assertion": "affirmed", "organ": "Эндометрий", "quote": "Полип эндометрия"}]
    findings = findings_from_facts(1, facts)
    assert len(findings) == 1
    assert findings[0].finding_type == "endometrial_polyp"
    assert findings[0].negated == False

def test_negated_finding():
    facts = [{"concept": "gallbladder_stone", "assertion": "negated", "organ": "Желчный пузырь", "quote": "Конкременты не выявлены"}]
    findings = findings_from_facts(1, facts)
    assert findings[0].negated == True

def test_trigger_only_for_affirmed():
    facts = [
        {"concept": "endometrial_polyp", "assertion": "affirmed", "quote": "Полип эндометрия"},
        {"concept": "gallbladder_stone", "assertion": "negated", "quote": "Конкременты не выявлены"},
    ]
    triggers = triggers_from_facts(1, facts)
    assert len(triggers) == 1
    assert triggers[0].trigger_name == "endometrial_polyp"

def test_match_rule_with_categories():
    rule = RoutingRule(
        trigger_name="birads",
        conditions={"categories": ["3", "4", "4A", "4B", "4C", "5"]},
        specialist_type="Маммолог / онколог",
        next_step="Консультация",
        deadline_days=None,
    )
    proposal = {"trigger": "birads", "category": "4", "specialist": "Маммолог / онколог", "next_step": "Консультация"}
    assert match_rule(proposal, [rule]) == rule

def test_no_match_when_category_not_in_list():
    rule = RoutingRule(
        trigger_name="birads",
        conditions={"categories": ["3", "4", "4A", "4B", "4C", "5"]},
        specialist_type="Маммолог / онколог",
        next_step="Консультация",
        deadline_days=None,
    )
    proposal = {"trigger": "birads", "category": "2", "specialist": "Маммолог / онколог", "next_step": "Консультация"}
    assert match_rule(proposal, [rule]) is None