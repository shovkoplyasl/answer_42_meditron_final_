"""Адаптер анализа медицинских протоколов.

Единственная граница между API (main.py) и NLP-движком:
main.py работает только с контрактом этого адаптера и не зависит
от внутренней реализации NLP и routing.

Контракт:
    analyze_text(text) -> {
        "engine":          str,
        "study_type":      str | None,
        "facts":           [...],
        "warnings":        [str],
        "decision":        str,
        "proposals":       [...],
        "profiles":        [str],
        "review_reasons":  [str],
        "notice":          str,
    }

Реализация использует ядро PoC:
    medroute/nlp.py
    medroute/routing.py

API и main.py при этом не зависят от внутренней реализации
NLP-движка.
"""


def analyze_text(text: str) -> dict:
    """Проанализировать текст медицинского протокола."""

    from medroute.nlp import extract
    from medroute.routing import route

    analysis = extract(text)
    result = route(analysis)

    return {
        "engine": analysis["engine"],
        "study_type": analysis["study_type"],
        "facts": [{**f, "quote": f.get("quote") or f.get("evidence", {}).get("quote")} for f in analysis["facts"]],
        "warnings": analysis["warnings"],
        "decision": result["decision"],
        "proposals": [{**p, "trigger": p.get("trigger") or p.get("concept"),
                       "specialist": p.get("specialist") or p.get("specialist_type") or p.get("profile")}
                      for p in result["proposals"]],
        "profiles": result["profiles"],
        "review_reasons": result["review_reasons"],
        "notice": result["notice"],
    }
