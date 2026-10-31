#!/usr/bin/env python3
"""Fetch the daily Gospel and prepare a reflection linked to its actual content."""
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
import json
import re
import unicodedata
import urllib.request

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "data" / "evangelio.json"
TODAY = datetime.now(ZoneInfo("Europe/Madrid")).date()
DATE_PATH = TODAY.strftime("%Y/%m/%d")
SOURCE_URL = f"https://www.vaticannews.va/es/evangelio-de-hoy/{DATE_PATH}.html"

# Reflections are curated for identifiable Gospel passages.
# Unknown passages use a neutral prompt instead of a guessed interpretation.
PASSAGE_REFLECTIONS = {
    "lucas 14, 1.7-11": {
        "reflection": "Jesús está en casa de un fariseo y se fija en cómo los invitados eligen los primeros puestos. A partir de esa escena, les enseña que no necesitan colocarse por encima de los demás para tener valor. Invita a elegir el último lugar y recuerda que quien se engrandece será humillado, y quien se humilla será enaltecido. Jesús propone una humildad que no busca reconocimiento ni convierte las relaciones en una competición.",
        "question": "¿En qué momentos intentas destacar, quedar por encima o recibir reconocimiento? ¿Cómo cambiaría tu manera de tratar a los demás si no necesitaras demostrar que eres más importante?",
        "commitment_title": "Haz sitio a los demás.",
        "commitment": "Hoy deja que otra persona tenga protagonismo: escucha sin interrumpir, reconoce algo bueno que haya hecho o cede tu lugar sin esperar que te lo agradezcan."
    }
}

def normalize(text):
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(char for char in text if unicodedata.category(char) != "Mn")

request = urllib.request.Request(
    SOURCE_URL,
    headers={"User-Agent": "Mozilla/5.0 (compatible; EnCaminoCatequesis/1.0)"}
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
    r"(?:\s*[.;]\s*\d{1,3}[a-z]?(?:\s*[-–—]\s*\d{1,3}[a-z]?)?)?"
    r"(?:\s*[-–—]\s*\d{1,3}[a-z]?)?"
    r"(?:\s*;\s*\d{1,3}[a-z]?(?:\s*[-–—]\s*\d{1,3}[a-z]?)?)*"
)
match = reference_pattern.search(section)
if not match:
    raise RuntimeError("No se ha podido identificar la cita bíblica del Evangelio.")

reference = match.group(0).strip()
passage = section[match.end():].strip(" :–—")
# Vatican News puede incluir al principio el rango de versículos (por ejemplo, "7-11").
# Se elimina para que no aparezca como si formara parte de la lectura.
passage = re.sub(
    r"^\s*[.·,;:–—-]*\s*\d{1,3}[a-z]?(?:\s*[-–—]\s*\d{1,3}[a-z]?)?\s+",
    "",
    passage,
    count=1,
).strip()
words = passage.split()
if len(words) < 8:
    raise RuntimeError("El texto del Evangelio no parece estar completo.")

# Mostrar frases completas: nunca cortar el fragmento en mitad de una oración.
sentences = re.findall(r".*?[.!?](?:[»”\"']|(?=\s|$))", passage)
if sentences:
    excerpt = ""
    for sentence in sentences:
        candidate = (excerpt + " " + sentence).strip()
        if len(candidate.split()) > 48 and excerpt:
            break
        excerpt = candidate
        if len(excerpt.split()) >= 25:
            break
    if not excerpt:
        excerpt = sentences[0].strip()
else:
    # Respaldo conservador si la página no trae puntuación reconocible.
    excerpt = passage.strip()

normalized_reference = normalize(reference)
theme = next(
    (item for passage_ref, item in PASSAGE_REFLECTIONS.items()
     if normalized_reference.startswith(normalize(passage_ref))),
    None
)

if theme is None:
    # No se fuerza una interpretación cuando no existe una ficha revisada
    # para esta lectura concreta.
    theme = {
        "reflection": f"Hoy escuchamos {reference}. Lee el pasaje completo y fíjate en tres cosas: qué sucede, qué hace o dice Jesús y cómo reaccionan las personas. Antes de buscar una moraleja, deja que el propio texto te sorprenda.",
        "question": "¿Qué sucede exactamente en este Evangelio? ¿Qué palabra, gesto o decisión de Jesús te llama la atención y por qué?",
        "commitment_title": "Responde a lo que has leído.",
        "commitment": "Elige una acción o actitud que aparezca claramente en el pasaje. Busca hoy una situación real en la que puedas vivirla, aunque sea con un gesto pequeño."
    }

# The weekly challenge is selected from Monday's Gospel and then kept
# unchanged for the rest of the ISO week, so every visitor sees the same one.
week_id = TODAY.strftime("%G-W%V")
previous = {}
if OUT.exists():
    try:
        previous = json.loads(OUT.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        previous = {}

if previous.get("weekly_challenge_week") == week_id:
    weekly_challenge = {
        "weekly_challenge_week": previous.get("weekly_challenge_week"),
        "weekly_challenge_title": previous.get("weekly_challenge_title"),
        "weekly_challenge": previous.get("weekly_challenge"),
        "weekly_challenge_reference": previous.get("weekly_challenge_reference"),
        "weekly_challenge_date": previous.get("weekly_challenge_date")
    }
else:
    weekly_text = theme["commitment"].replace("hoy", "esta semana").replace("Hoy", "Esta semana")
    weekly_challenge = {
        "weekly_challenge_week": week_id,
        "weekly_challenge_title": theme["commitment_title"],
        "weekly_challenge": weekly_text,
        "weekly_challenge_reference": reference,
        "weekly_challenge_date": TODAY.isoformat()
    }

payload = {
    "date": TODAY.isoformat(),
    "reference": reference,
    "excerpt": excerpt,
    "reflection": theme["reflection"],
    "question": theme["question"],
    "commitment_title": theme["commitment_title"],
    "commitment": theme["commitment"],
    **weekly_challenge,
    "source": SOURCE_URL,
    "provider": "Vatican News"
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Evangelio y reflexión actualizados: {TODAY.isoformat()} · {reference}")
