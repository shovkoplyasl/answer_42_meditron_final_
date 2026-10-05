"""Read DOCX in XML order; never duplicate merged table cells."""
from __future__ import annotations
import hashlib
import io
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
MAX_FILE = 12 * 1024 * 1024
MAX_TEXT = 150_000


def read_docx(source: bytes | Path) -> str:
    raw = source if isinstance(source, bytes) else source.read_bytes()
    if len(raw) > MAX_FILE:
        raise ValueError("Файл превышает 12 МБ")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        member = z.getinfo("word/document.xml")
        if member.file_size > MAX_FILE:
            raise ValueError("Распакованный XML превышает допустимый размер")
        xml = z.read(member)
        if b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
            raise ValueError("XML с объявлениями сущностей не поддерживается")
        root = ET.fromstring(xml)
        lines = []
        for p in root.iter(W + "p"):
            line = "".join(t.text or "" for t in p.iter(W + "t"))
            if line.strip():
                lines.append(line)
    text = "\n".join(lines)
    if not text.strip() or len(text) > MAX_TEXT:
        raise ValueError("Документ пуст или слишком длинный; автоматическое усечение запрещено")
    return text


def clinical_text(text: str) -> str:
    """Minimise metadata for the local UI. NOT certified anonymisation."""
    text = text.replace("\xa0", " ")
    # Prefer explicit clinical section; otherwise first examination heading.
    m = re.search(r"(?im)^Описание\s*$", text)
    if m:
        text = text[m.end():].strip()
    else:
        starts = list(re.finditer(
            r"(?im)^(?:ПРОТОКОЛ УЛЬТРАЗВУКОВОГО|Протокол ультразвукового|"
            r"УЛЬТРАЗВУКОВОЕ ИССЛЕДОВАНИЕ|ДУПЛЕКСНОЕ СКАНИРОВАНИЕ|"
            r"УЗИ[ \t]+(?:органов|Щитовидной|Молочных|желчного)|Заключение\s*$)", text))
        if starts:
            text = text[starts[0].start():]
    text = re.split(r"(?im)^Подпись\s+врача\s*:", text)[0]
    lines, skip = [], False
    for line in text.splitlines():
        if re.match(r"(?i)^(?:Пациент|ФИО пациента|Дата рождения|Врач|Телефон|Адрес|Номер карты|Дата выполнения|Время выполнения)\s*:", line):
            skip = not bool(line.split(":", 1)[1].strip())
            continue
        if skip:
            skip = False
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

