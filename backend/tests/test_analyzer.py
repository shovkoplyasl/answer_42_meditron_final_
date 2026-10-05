import pytest
from services.analyzer import analyze_text

def test_engine_is_not_stub():
    result = analyze_text("УЗИ малого таза. Полип эндометрия.")
    assert result["engine"] == "rules-nlp-0.1"

def test_empty_text_raises():
    with pytest.raises(ValueError):
        analyze_text("")

def test_affirmed_finding():
    result = analyze_text("УЗИ малого таза. Полип эндометрия.")
    assert any(f["concept"] == "endometrial_polyp" for f in result["facts"])

def test_negated_finding():
    result = analyze_text("УЗИ желчного пузыря. Конкременты не выявлены.")
    assert any(f["concept"] == "gallbladder_stone" and f["assertion"] == "negated" for f in result["facts"])

def test_decision_consultation():
    result = analyze_text("УЗИ малого таза. Полип эндометрия.")
    assert result["decision"] == "consultation"

def test_decision_no_supported_trigger():
    result = analyze_text("УЗИ почек. Без особенностей.")
    assert result["decision"] == "no_supported_trigger"