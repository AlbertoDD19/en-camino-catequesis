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

# Each theme is selected from words found in the Gospel text itself.
# Keep the language concrete, reflective and suitable for teenagers.
THEMES = [
    {
        "keys": ["sabado", "enfermo", "curacion", "curar", "sanar", "sanacion"],
        "reflection": "En este pasaje Jesús pone a la persona por delante de una norma entendida sin corazón. Ve a quien necesita ayuda y actúa con compasión. Nos recuerda que la fe no puede convertirse en una excusa para mirar hacia otro lado.",
        "question": "¿Alguna vez has preferido seguir con lo tuyo en vez de detenerte para ayudar a alguien? ¿Qué habría hecho Jesús en tu lugar?",
        "commitment_title": "Que la compasión se note.",
        "commitment": "Hoy, si ves que alguien necesita ayuda o se queda atrás, no pases de largo: acércate, pregunta cómo está y ofrece una ayuda concreta."
    },
    {
        "keys": ["perdon", "perdonar", "perdonad", "misericordia"],
        "reflection": "Jesús nos habla de un amor que no se queda atrapado en el error. Perdonar no significa justificar lo que hace daño ni olvidar de golpe; significa abrir, cuando sea posible y seguro, un camino hacia la reconciliación.",
        "question": "¿Hay alguna relación en la que puedas dar un primer paso hacia el diálogo, sin dejar de cuidar tus propios límites?",
        "commitment_title": "Abre una puerta al perdón.",
        "commitment": "Si has herido a alguien, reconoce tu parte y pide perdón con sinceridad. Si necesitas tiempo, empieza por decidir qué paso responsable puedes dar."
    },
    {
        "keys": ["orar", "oracion", "rezar", "padre nuestro", "pedid", "pedir"],
        "reflection": "Jesús enseña que podemos dirigirnos a Dios con confianza y sencillez. No hacen falta frases perfectas: la oración empieza cuando nos presentamos tal como estamos, también con nuestras dudas y preocupaciones.",
        "question": "Si hoy pudieras hablar con Dios con total sinceridad, ¿qué le contarías?",
        "commitment_title": "Regálate un momento de oración.",
        "commitment": "Busca hoy dos minutos de tranquilidad y habla con Dios con tus propias palabras. Cuéntale algo que agradeces y algo para lo que necesitas ayuda."
    },
    {
        "keys": ["pobre", "hambr", "sed", "necesitad", "limosna"],
        "reflection": "En este Evangelio, la atención se dirige a quienes necesitan apoyo. Jesús nos invita a no medir a las personas por lo que tienen y a reconocer que la dignidad de alguien no depende de su situación.",
        "question": "¿Quién puede estar necesitando hoy que alguien le tenga en cuenta en tu entorno?",
        "commitment_title": "Comparte lo que eres y tienes.",
        "commitment": "Haz hoy un gesto concreto de ayuda: comparte tu tiempo, escucha sin juzgar o colabora en algo que alivie la carga de otra persona."
    },
    {
        "keys": ["paz", "pacific", "enemigo", "amaros", "ama a tu", "amor"],
        "reflection": "Jesús propone una manera de relacionarnos que rompe la lógica de devolver mal por mal. Amar no es permitir que nos traten mal: es elegir el respeto, rechazar la venganza y buscar caminos que construyan paz.",
        "question": "¿En qué situación de hoy puedes evitar alimentar un conflicto y responder con respeto?",
        "commitment_title": "Sé una persona que construye paz.",
        "commitment": "No participes en una burla ni difundas un comentario que humille. Si surge un conflicto, intenta responder con respeto y busca ayuda si hace falta."
    },
    {
        "keys": ["miedo", "tempestad", "viento", "mar", "tormenta"],
        "reflection": "En medio de la dificultad, los discípulos descubren que no están solos. El pasaje no promete que nunca tendremos problemas; recuerda que podemos afrontarlos acompañados y pedir ayuda cuando algo nos supera.",
        "question": "¿Qué preocupación te gustaría no tener que afrontar en soledad? ¿A quién de confianza podrías acudir?",
        "commitment_title": "No camines solo.",
        "commitment": "Da hoy un paso para compartir una preocupación con alguien de confianza. Y estate atento por si otra persona necesita que la acompañes."
    },
    {
        "keys": ["sembrador", "semilla", "sembrar", "tierra", "fruto"],
        "reflection": "La imagen de la semilla nos recuerda que crecer lleva tiempo. No todo cambia de un día para otro: nuestras decisiones, la escucha y los pequeños gestos van preparando el terreno para que algo bueno dé fruto.",
        "question": "¿Qué actitud buena te gustaría cultivar poco a poco en tu vida?",
        "commitment_title": "Cuida lo que quieres hacer crecer.",
        "commitment": "Elige una actitud —paciencia, generosidad, sinceridad o constancia— y busca una ocasión concreta para practicarla hoy."
    },
    {
        "keys": ["perdida", "perdido", "oveja", "buscar", "encontrar"],
        "reflection": "Jesús muestra que nadie es insignificante ni queda olvidado. Para Él, cada persona importa. Este pasaje nos invita a mirar de nuevo a quienes quizá hemos dejado al margen.",
        "question": "¿Hay alguien de tu clase, familia o grupo que pueda sentirse olvidado o fuera de lugar?",
        "commitment_title": "Haz que alguien se sienta contado.",
        "commitment": "Acércate a alguien que suele quedarse al margen. Saluda, incluye en la conversación o pregunta de verdad cómo está."
    },
    {
        "keys": ["servir", "servidor", "ultimo", "pequeño", "lavar los pies"],
        "reflection": "Jesús presenta el servicio como una forma de amar. No se trata de ser menos que nadie, sino de no vivir pensando solo en uno mismo y descubrir que todos podemos hacer la vida un poco mejor a los demás.",
        "question": "¿Qué tarea o gesto podrías hacer hoy sin buscar reconocimiento?",
        "commitment_title": "Hazte útil con sencillez.",
        "commitment": "Ayuda hoy en casa, en clase o con tus amigos en algo concreto, sin esperar aplausos ni que tengan que pedírtelo."
    },
    {
        "keys": ["fe", "creer", "crees", "confianza"],
        "reflection": "La fe que aparece en este pasaje no consiste en tener todas las respuestas, sino en atreverse a confiar y seguir dando pasos. También podemos acercarnos a Jesús con preguntas y dudas sinceras.",
        "question": "¿Qué te cuesta confiar o poner en manos de Dios en este momento?",
        "commitment_title": "Da un paso desde la confianza.",
        "commitment": "Ante algo que te preocupe, haz hoy lo que esté en tu mano y pide acompañamiento para lo que no puedes resolver tú solo."
    },
    {
        "keys": ["riqueza", "dinero", "tesoro", "avaricia", "riquezas"],
        "reflection": "Jesús cuestiona la idea de que nuestro valor dependa de lo que acumulamos. Lo más valioso de una vida no se compra: son el amor, la amistad, la generosidad y el bien que compartimos.",
        "question": "¿Qué estás valorando mucho últimamente? ¿Te ayuda a querer mejor a las personas?",
        "commitment_title": "Invierte en lo que importa.",
        "commitment": "Dedica hoy tiempo y atención a una persona importante para ti, sin distracciones ni esperar nada a cambio."
    },
]

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

normalized_passage = normalize(passage)
theme = next(
    (item for item in THEMES if any(normalize(key) in normalized_passage for key in item["keys"])),
    None
)
if theme is None:
    # This fallback explicitly refers to the actual passage and its citation,
    # without pretending to have identified a theme it could not detect.
    theme = {
        "reflection": f"Hoy la Iglesia nos propone escuchar {reference}. Lee el pasaje completo con calma y fíjate en qué hace o dice Jesús, quién aparece en la escena y qué cambia a partir de ese encuentro. La Palabra se entiende mejor cuando la relacionamos con una situación real.",
        "question": "¿Qué palabra, gesto o decisión de este pasaje te ha llamado más la atención? ¿Por qué?",
        "commitment_title": "Pon en práctica una palabra.",
        "commitment": "Elige una enseñanza concreta del pasaje y conviértela hoy en un gesto pequeño y posible en casa, en clase o con tus amigos."
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
