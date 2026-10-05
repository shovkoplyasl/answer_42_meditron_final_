"""Dictionary and context NLP. No labels, filenames or corpus IDs at inference."""
from __future__ import annotations
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
CONCEPTS = json.loads((ROOT / "config/concepts.json").read_text(encoding="utf-8"))
VERSION = "rules-nlp-0.1"


def normalise(text: str) -> str:
    # Length-preserving normalisation: offsets always address original text.
    return text.lower().translate(str.maketrans({"ё": "е", "\xa0": " ", "–": "-", "—": "-", "‑": "-"}))


PATTERNS = {
    "endometrial_polyp": r"\bполип(?:оз|а|ы|ов|ом|у|е)?\s+эндометри\w*|эндометри\w*\s*\(\s*полип\w*\s*\)",
    "uterine_fibroid": r"\bмиом(?:а|ы|у|ой|е|ами|ах)?\b|\bмиоматозн\w*\s+уз\w+|\bлейомиом\w+",
    "gallbladder_stone": r"\bконкремент\w*|\bхолецистолитиаз\w*|\bкалькулезн\w*\s+холецистит\w*|\bжкб\b|\bкам(?:ень|ни|ней|ня|нем)\b",
    "gallbladder_polyp": r"\bполип(?:оз|а|ы|ов|ом|у|е)?\b",
    "thyroid_nodule": r"\bуз(?:ел|лы|ла|лов|лом|лу|ле|лами)\b|\bузлов(?:ое|ые|ых|ого)\s+образован\w*|\bузловой\s+зоб\b",
    "prostate_hyperplasia": r"\bдгпж\b|\bгиперплази\w*|\bаденом(?:а|ы|у|ой)\s+простат\w*|\bаденоматозн\w*\s+уз\w+",
    "varicose_veins": r"\bварикозн\w*\s+(?:расширени\w*|трансформаци\w*|деформаци\w*|приток\w*)",
    "arterial_atherosclerosis": r"\bатеросклероз\w*",
    "venous_thrombosis": r"\b(?:флеботромбоз|тромбофлебит|тромбоз)\w*"
}
ANATOMY = re.compile(r"желчн\w*\s+пузыр\w*|эндометри\w*|щитовидн\w*\s+желез\w*|"
                     r"предстательн\w*\s+желез\w*|поджелудочн\w*\s+желез\w*|"
                     r"мочев\w*\s+пузыр\w*|\bпочки\b|\bпочка\b|\bпечень\b|\bселезенка\b")


def study_type(t: str) -> str:
    # Only document text, never filename / directory label.
    head = t[:900]
    for name, pattern in [("breast", r"молочн\w*\s+желез"), ("thyroid", r"щитовидн|тиреоид|\bщж\b"),
                          ("prostate", r"предстательн|трузи|простаты"), ("vascular", r"нижних конечност|нижней конечност|нижняя конечность|бедренн|подколенн|артерий голени"),
                          ("pelvis", r"матк|миометри|яичник|малого таза"), ("abdominal", r"желчн|брюшн|гепатобилиар")]:
        if re.search(pattern, head):
            return name
    return "unknown"


def bounds(t: str, start: int, end: int) -> tuple[int, int]:
    # Decimal points do not terminate a sentence. Keep colons, including fields.
    breaks = list(re.finditer(r"[;!\n]|(?<!\d)\.(?!\d)", t))
    left = max((m.end() for m in breaks if m.end() <= start), default=0)
    right = min((m.start() for m in breaks if m.start() >= end), default=len(t))
    return max(left, start-190), min(right, end+190)


def eligible(concept: str, t: str, m: re.Match, study: str) -> bool:
    a, b = bounds(t, m.start(), m.end())
    around = t[max(0, m.start()-130):min(len(t), m.end()+120)]
    if concept.startswith("gallbladder"):
        if re.search(r"холецистолитиаз|калькулезн|\bжкб\b", m.group()):
            return True
        if re.search(r"желчн\w*\s+пузыр", t[m.start():b]):
            return True
        anatomical = list(ANATOMY.finditer(t[:m.start()]))
        if anatomical:
            return bool(re.match(r"желчн", anatomical[-1].group()))
        return study == "abdominal"
    if concept == "thyroid_nodule":
        if study != "thyroid":
            return False
        if re.search(r"лимфатическ\w*\s*$|лимф\s*$|псевдо\s*$", t[max(a, m.start()-40):m.start()]):
            return False
        # A bare form heading is not a positive finding.
        if re.fullmatch(r"узловые образования\s*:?\s*", t[m.start():b]):
            return False
    if concept == "prostate_hyperplasia":
        return study == "prostate" or bool(re.search(r"предстательн|простат", around))
    if concept in ("varicose_veins", "arterial_atherosclerosis", "venous_thrombosis"):
        return study == "vascular" and not re.search(r"малого таза", t[m.end():m.end()+60])
    return True


def assertion(t: str, m: re.Match, concept: str) -> tuple[str, str]:
    a, b = bounds(t, m.start(), m.end())
    before, after = t[a:m.start()], t[m.end():b]
    # Separate coordinated findings: '?' for cervical polyp must not affect endometrial polyp.
    after_clause = re.split(r",|\bно\b|\bоднако\b", after, maxsplit=1)[0]
    before_clause = re.split(r",|\bно\b|\bоднако\b", before)[-1]
    if re.search(r"(?:не исключ\w*|нельзя исключ\w*|подозрени\w* на|возможно|вероятно)\s*(?:наличие\s+)?$", before_clause) or re.match(r"\s*\?", after_clause):
        return "suspected", "В тексте выражено предположение"
    if re.search(r"без\s+(?:(?:эхо|уз)[- ]?)?(?:признаков\s+|данных\s+за\s+)?$", before_clause) or re.search(r"не\s+выявлен\w*\s*$", before_clause):
        return "negated", "Отрицание перед упоминанием"
    if re.search(r"^(?:[\s:()\-]|\bи\b|\bдостоверно\b)*(?:нет\b|не\s+(?:выявл|определ|лоцир|обнаруж|получен))", after_clause):
        return "negated", "Отрицание после упоминания"
    if re.search(r"данных\s+за\s*$", before_clause) and re.search(r"не\s+получено", after):
        return "negated", "Данных за находку не получено"
    if concept == "venous_thrombosis" and re.search(r"не\s+(?:выявлено|получено)", after_clause):
        return "negated", "Венозный тромбоз явно отрицается"
    if re.search(r"(?:анамнез\w*|ранее|истори\w*|состояние после|удалени\w*)[^.;\n]{0,60}$", before_clause) or re.match(r"\s+(?:удален\w*|ранее удален\w*)", after_clause):
        return "historical", "Упоминание относится к анамнезу / удалению"
    if concept == "endometrial_polyp" and re.search(r"состояние после\s+гистерорезектоскоп", t[max(0,m.start()-150):m.end()+150]):
        return "uncertain", "Полип упомянут рядом с ранее проведённым вмешательством; нужна проверка актуальности"
    return "affirmed", "Находка утверждается в тексте"


def evidence(text: str, start: int, end: int) -> dict:
    return {"start": start, "end": end, "quote": text[start:end]}


def birads_mentions(text: str, t: str) -> list[dict]:
    mentions = []
    # Include written-out system plus category; handle coordinated left/right assignments.
    for sysmatch in re.finditer(r"\b(?:bi\s*[- ]?\s*rads|би\s*[- ]?\s*радс)\b", t):
        p = sysmatch.start()
        tail = t[sysmatch.end():sysmatch.end()+95]
        # Only continue inside this assessment, not into a later unrelated sentence.
        tail = re.split(r"[\n.;]", tail, maxsplit=1)[0]
        tail = re.split(r"\bbi\s*[- ]?\s*rads\b",tail,maxsplit=1)[0]
        categories = list(re.finditer(r"(?<!\d)([0-6](?:[abcабс])?)(?!\d)", tail))
        if not categories:
            continue
        for num in categories[:2]:
            end = sysmatch.end()+num.end()
            startnum = sysmatch.end()+num.start()
            pre = t[max(0,p-55):startnum]
            post = t[end:end+50]
            # Don't steal a side from a previous sentence.
            # A period in 'мол.железа' is an abbreviation, not a boundary.
            pre = re.split(r"[\n;,]|(?<!мол)\.", pre)[-1]
            post = re.split(r"[\n.;,]", post)[0]
            pre_sides = list(re.finditer(r"справа|слева|прав\w*|лев\w*", pre))
            post_side = re.match(r"\s*\(?\s*(справа|слева|прав\w*|лев\w*)", post)
            side_token = post_side.group(1) if post_side else pre_sides[-1].group() if pre_sides else ""
            side = "right" if side_token.startswith(("прав", "справ")) else "left" if side_token.startswith(("лев", "слев")) else None
            cat = num.group(1).upper().translate(str.maketrans({"А":"A", "Б":"B", "С":"C"}))
            if len(cat)>1 and cat[0] != "4":
                continue
            estart = max(0,p-55)
            breaks = list(re.finditer(r"[\n;]|(?<!\d)\.(?!\d)", t[estart:p]))
            if breaks:
                estart += breaks[-1].end()
            eend = end + (post_side.end() if post_side else 0)
            if post_side:
                closing = text.find(")", end, end+60)
                if closing >= 0:
                    eend = closing+1
            mentions.append({"concept":"birads", "assertion":"affirmed", "side":side, "category":cat,
                             "reason":"Явно указана категория BI-RADS", "evidence":evidence(text,estart,eend),
                             "keyword":evidence(text,p,end)})
    for m in re.finditer(r"\bbr\s*([0-6])\b", t):
        mentions.append({"concept":"birads", "assertion":"uncertain", "side":None,"category":m.group(1),
                         "reason":"Неоднозначное сокращение BR; требуется проверка", "evidence":evidence(text,m.start(),m.end()),
                         "keyword":evidence(text,m.start(),m.end())})
    return mentions


def extract(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Нужен непустой текст протокола")
    if len(text) > 150_000:
        raise ValueError("Слишком длинный текст; усечение запрещено")
    t = normalise(text)
    study = study_type(t)
    mentions = birads_mentions(text, t)
    for concept, pattern in PATTERNS.items():
        for m in re.finditer(pattern, t):
            if not eligible(concept, t, m, study):
                continue
            status, reason = assertion(t, m, concept)
            a,b = bounds(t,m.start(),m.end())
            mentions.append({"concept":concept,"assertion":status,"category":None,"side":None,
                             "reason":reason,"keyword":evidence(text,m.start(),m.end()),"evidence":evidence(text,a,b)})
    grouped = defaultdict(list)
    for mention in mentions:
        grouped[(mention['concept'],mention['category'],mention['side'])].append(mention)
    facts=[]
    for (concept, category, side), ms in grouped.items():
        statuses = {m['assertion'] for m in ms}
        if "uncertain" in statuses or {"affirmed","negated"} <= statuses:
            status="uncertain"
        elif "affirmed" in statuses:
            status="affirmed"
        elif "suspected" in statuses:
            status="suspected"
        elif "historical" in statuses:
            status="historical"
        else:
            status="negated"
        representative=next((m for m in ms if m['assertion']==status),ms[0])
        facts.append({"concept":concept,"label":CONCEPTS[concept]['label'],"organ":CONCEPTS[concept]['organ'],
                      "assertion":status,"category":category,"side":side,"evidence":representative['evidence'],
                      "reason":representative['reason'] if len(statuses)==1 else "Несколько упоминаний; проверен контекст и возможное противоречие",
                      "mentions":ms})
    warnings=[]
    if study=="breast" and not any(f['concept']=="birads" for f in facts) and re.search(r"фиброаденом|очагов\w*\s+образован",t):
        warnings.append("Есть описание очагового образования молочной железы без категории BI-RADS. Нужна ручная проверка.")
    return {"engine":VERSION,"study_type":study,"facts":facts,"warnings":warnings,
            "unmentioned_concepts":[c for c in CONCEPTS if c not in {f['concept'] for f in facts}],
            "scope_note":"Отсутствие целевого триггера не означает норму. Размеры автоматически не интерпретируются."}

