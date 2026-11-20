"""
Módulo de visión por computador: verificación de documento de identidad (cédula).

Opciones (gratuitas):
1. GEMINI_API_KEY → Gemini multimodal (nivel gratuito)
2. Sin clave → modo demo: extrae con heurística mínima y pide confirmación manual

Plan B si falla la API: respuesta clara + estado "pendiente_revision".
"""
import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_VISION_MODEL", "gemini-3.5-flash-lite").strip()
if not GEMINI_MODEL:
    GEMINI_MODEL = "gemini-3.5-flash-lite"

PROMPT_CEDULA = """Eres un sistema de verificación de documentos de identidad colombianos (cédula).
Analiza la imagen y extrae SOLO estos campos en JSON válido, sin markdown:

{
  "nombre_completo": "string o null",
  "numero_documento": "string solo dígitos o null",
  "tipo_documento": "CC|TI|CE|otro|null",
  "confianza": 0.0 a 1.0,
  "observaciones": "texto breve"
}

Reglas:
- Si no puedes leer un campo, pon null.
- confianza alta (>0.8) solo si el texto es legible.
- No inventes datos.
- Responde ÚNICAMENTE el JSON.
"""


def _parse_json_respuesta(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    # Quitar fences markdown si vienen
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {
        "nombre_completo": None,
        "numero_documento": None,
        "tipo_documento": None,
        "confianza": 0.0,
        "observaciones": "No se pudo interpretar la respuesta del modelo",
        "raw": text[:500],
    }


def extraer_con_gemini(image_bytes: bytes, mime: str = "image/jpeg") -> Dict[str, Any]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no configurada")

    b64 = base64.b64encode(image_bytes).decode("utf-8")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT_CEDULA},
                    {"inline_data": {"mime_type": mime, "data": b64}},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 512},
    }

    with httpx.Client(timeout=60.0) as client:
        r = client.post(
            url,
            json=payload,
            headers={"x-goog-api-key": GEMINI_API_KEY},
        )
        r.raise_for_status()
        data = r.json()

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Respuesta Gemini inesperada: {e}") from e

    parsed = _parse_json_respuesta(text)
    parsed["motor"] = "gemini"
    return parsed


def extraer_modo_demo(image_bytes: bytes) -> Dict[str, Any]:
    """
    Plan B / demo sin API: no inventa datos de cédula.
    Marca confianza baja para revisión manual.
    """
    size_kb = len(image_bytes) / 1024
    return {
        "nombre_completo": None,
        "numero_documento": None,
        "tipo_documento": None,
        "confianza": 0.15,
        "observaciones": (
            f"Modo demo (sin GEMINI_API_KEY). Imagen recibida ({size_kb:.0f} KB). "
            "Configura GEMINI_API_KEY para extracción automática, "
            "o completa los datos manualmente tras revisar la foto."
        ),
        "motor": "demo",
    }


def _resumir_error_gemini(error: Exception) -> str:
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        if status == 404:
            return "Modelo de Gemini no disponible (HTTP 404); revisa GEMINI_VISION_MODEL"
        if status in (401, 403):
            return f"Gemini rechazó la clave o sus permisos (HTTP {status})"
        if status == 429:
            return "Se alcanzó el límite de solicitudes de Gemini (HTTP 429)"
        return f"Gemini respondió con HTTP {status}"
    if isinstance(error, httpx.TimeoutException):
        return "Tiempo de espera agotado al consultar Gemini"
    if isinstance(error, httpx.RequestError):
        return f"No se pudo conectar con Gemini ({type(error).__name__})"
    return f"Error al consultar Gemini ({type(error).__name__})"


def procesar_cedula(image_bytes: bytes, mime: str = "image/jpeg") -> Dict[str, Any]:
    """
    Punto de entrada del módulo de visión.
    Intenta Gemini; si falla o no hay clave, usa plan B.
    """
    if GEMINI_API_KEY:
        try:
            return extraer_con_gemini(image_bytes, mime)
        except Exception as e:
            # Plan B ante fallo de cuota o red
            error_api = _resumir_error_gemini(e)
            fallback = extraer_modo_demo(image_bytes)
            fallback["observaciones"] = (
                f"Fallo de Gemini: {error_api}. "
                + fallback["observaciones"]
            )
            fallback["motor"] = "demo_fallback"
            fallback["error_api"] = error_api
            return fallback
    return extraer_modo_demo(image_bytes)


def comparar_con_usuario(
    datos_ia: Dict[str, Any],
    nombre_usuario: str,
    documento_registrado: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compara datos extraídos con el perfil del usuario.
    Devuelve estado validado/rechazado/pendiente y motivos.
    """
    conf = float(datos_ia.get("confianza") or 0)
    nombre_ext = (datos_ia.get("nombre_completo") or "").strip()
    doc_ext = re.sub(r"\D", "", str(datos_ia.get("numero_documento") or ""))

    motivos = []
    coincide_nombre = False
    coincide_doc = False

    if nombre_ext and nombre_usuario:
        # Comparación simple por tokens
        tokens_u = set(nombre_usuario.lower().split())
        tokens_e = set(nombre_ext.lower().split())
        if tokens_u and tokens_e:
            inter = tokens_u & tokens_e
            coincide_nombre = len(inter) >= min(2, len(tokens_u))
        if not coincide_nombre:
            motivos.append("El nombre extraído no coincide con el de la cuenta")

    if documento_registrado and doc_ext:
        coincide_doc = re.sub(r"\D", "", documento_registrado) == doc_ext
        if not coincide_doc:
            motivos.append("El número de documento no coincide con el registrado")
    elif not doc_ext:
        motivos.append("No se pudo leer el número de documento")

    if conf < 0.5:
        estado = "pendiente"
        motivos.append("Confianza baja: se requiere revisión")
    elif coincide_nombre and (coincide_doc or not documento_registrado) and conf >= 0.6:
        estado = "validado"
        motivos = ["Datos coherentes con el perfil"]
    elif conf >= 0.6 and nombre_ext and doc_ext and not documento_registrado:
        # Primera vez: aceptamos si hay datos legibles y nombre similar
        if coincide_nombre or conf >= 0.75:
            estado = "validado"
            motivos = ["Documento legible; número guardado en el perfil"]
        else:
            estado = "pendiente"
    else:
        estado = "rechazado" if conf >= 0.5 else "pendiente"

    return {
        "estado": estado,
        "coincide_nombre": coincide_nombre,
        "coincide_documento": coincide_doc,
        "motivos": motivos,
        "confianza": conf,
    }


def guardar_imagen(uploads_dir: Path, usuario_id: int, filename: str, content: bytes) -> str:
    uploads_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]", "_", filename)[:80]
    path = uploads_dir / f"user{usuario_id}_{safe}"
    path.write_bytes(content)
    return str(path)
