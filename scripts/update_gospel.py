#!/usr/bin/env python3
"""Fetch the daily Gospel reference and a short excerpt from Vatican News."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json
import re
import urllib.request

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "evangelio.json"
TODAY = datetime.now(ZoneInfo("Europe/Madrid")).date()
DATE_PATH = TODAY.strftime("%Y/%m/%d")
SOURCE_URL = f"https://www.vaticannews.va/es/evangelio-de-hoy/{DATE_PATH}.html"

request = urllib.request.Request(
    SOURCE_URL,
    headers={"User-Agent": "EnCaminoCatequesis/1.0 (daily Gospel reference updater)"}
)
with urllib.request.urlopen(request, timeout=30) as response:
    html = response.read()

soup = BeautifulSoup(html, "html.parser")
page_text = soup.get_text(" ", strip=True)
if "Evangelio del Día" not in page_text or "Las palabras de los Papas" not in page_text:
    raise RuntimeError("No se ha encontrado la sección del Evangelio en Vatican News.")

section = page_text.split("Evangelio del Día", 1)[1].split("Las palabras de los Papas", 1)[0]
reference_pattern = re.compile(
    r"\b(?:Mateo|Marcos|Lucas|Juan)\s+\d{1,3},\s*\d{1,3}[a-z]?"
    r"(?:\s*[-–—]\s*\d{1,3}[a-z]?)?"
    r"(?:\s*;\s*\d{1,3}[a-z]?(?:\s*[-–—]\s*\d{1,3}[a-z]?)?)*"
)
match = reference_pattern.search(section)
if not match:
    raise RuntimeError("No se ha podido identificar la cita bíblica del Evangelio.")

reference = match.group(0).strip()
after_reference = section[match.end():].strip(" :–—")
words = after_reference.split()
if len(words) < 8:
    raise RuntimeError("El texto del Evangelio no parece estar completo.")
excerpt = " ".join(words[:25]).strip()

OUT.parent.mkdir(parents=True, exist_ok=True)
payload = {
    "date": TODAY.isoformat(),
    "reference": reference,
    "excerpt": excerpt,
    "source": SOURCE_URL,
    "provider": "Vatican News"
}
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Evangelio actualizado: {TODAY.isoformat()} · {reference}")
