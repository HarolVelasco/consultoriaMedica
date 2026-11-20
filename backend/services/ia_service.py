"""
Servicio de IA para el bot de agendamiento.
Usa OpenAI si hay OPENAI_API_KEY; si no, usa un modo simulado (sin API).
"""
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SYSTEM_PROMPT = """Eres un asistente de una consultoría médica.
Tu único objetivo es ayudar al paciente a agendar una cita.

Debes recopilar estos datos:
- tipo: Primera consulta | Seguimiento | Segunda opinión | Consulta online | Consulta presencial
- fecha: en formato YYYY-MM-DD (solo fechas futuras)
- hora: Mañana (9:00 - 13:00) | Tarde (16:00 - 20:00) | Cualquier horario
- motivo: texto breve del motivo de la consulta

Reglas:
1. Sé amable, breve y profesional.
2. Pregunta solo lo que falte.
3. Cuando tengas TODOS los datos, responde ÚNICAMENTE con un JSON válido en este formato (sin markdown):
{"listo": true, "tipo": "...", "fecha": "YYYY-MM-DD", "hora": "...", "motivo": "...", "resumen": "texto corto para confirmar"}
4. Si aún faltan datos, responde en texto normal (no JSON) preguntando lo que falta.
5. No inventes datos médicos ni des diagnósticos.
"""


def _parse_json_from_text(text: str) -> Optional[dict]:
    text = text.strip()
    # Intentar parseo directo
    try:
        data = json.loads(text)
        if isinstance(data, dict) and data.get("listo"):
            return data
    except json.JSONDecodeError:
        pass
    # Buscar bloque JSON dentro del texto
    match = re.search(r"\{[^{}]*\"listo\"\s*:\s*true[^{}]*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _simulated_reply(history: List[dict], user_message: str) -> Tuple[str, Optional[dict]]:
    """Modo sin API: extrae datos con reglas simples."""
    # Acumular texto del usuario
    all_user = " ".join(m["content"] for m in history if m["role"] == "user") + " " + user_message
    all_user_lower = all_user.lower()

    datos: Dict[str, Any] = {}

    # tipo
    tipos = {
        "primera": "Primera consulta",
        "seguimiento": "Seguimiento",
        "segunda opinión": "Segunda opinión",
        "segunda opinion": "Segunda opinión",
        "online": "Consulta online",
        "presencial": "Consulta presencial",
    }
    for k, v in tipos.items():
        if k in all_user_lower:
            datos["tipo"] = v
            break

    # fecha YYYY-MM-DD
    fecha_match = re.search(r"(20\d{2}-\d{2}-\d{2})", all_user)
    if fecha_match:
        datos["fecha"] = fecha_match.group(1)

    # hora
    if "mañana" in all_user_lower or "manana" in all_user_lower:
        datos["hora"] = "Mañana (9:00 - 13:00)"
    elif "tarde" in all_user_lower:
        datos["hora"] = "Tarde (16:00 - 20:00)"
    elif "cualquier" in all_user_lower:
        datos["hora"] = "Cualquier horario"

    # motivo: última frase larga del usuario si no es solo fecha/tipo
    if len(user_message) > 15 and not re.match(r"^20\d{2}-\d{2}-\d{2}$", user_message.strip()):
        if "motivo" not in datos:
            # Heurística simple
            skip = any(x in user_message.lower() for x in ["cita", "agendar", "quiero", "necesito", "mañana", "tarde"])
            if not skip or len(user_message) > 40:
                datos["motivo"] = user_message.strip()[:500]

    faltan = [c for c in ("tipo", "fecha", "hora", "motivo") if c not in datos]

    if not faltan:
        return (
            f"Perfecto. Resumen de tu cita:\n"
            f"- Tipo: {datos['tipo']}\n"
            f"- Fecha: {datos['fecha']}\n"
            f"- Franja: {datos['hora']}\n"
            f"- Motivo: {datos['motivo']}\n\n"
            f"¿Confirmas para agendarla? Responde sí para confirmar.",
            {**datos, "listo": True, "resumen": "Cita lista para confirmar"},
        )

    preguntas = {
        "tipo": "¿Qué tipo de consulta necesitas? (Primera consulta, Seguimiento, Segunda opinión, Online o Presencial)",
        "fecha": "¿Qué fecha prefieres? (formato AAAA-MM-DD, por ejemplo 2026-11-20)",
        "hora": "¿Prefieres mañana (9:00-13:00), tarde (16:00-20:00) o cualquier horario?",
        "motivo": "¿Cuál es el motivo de la consulta? (brevemente)",
    }
    return preguntas[faltan[0]], None


def chat_with_bot(history: List[dict], user_message: str) -> Tuple[str, Optional[dict]]:
    """
    history: lista de {"role": "user"|"assistant", "content": "..."}
    Retorna: (respuesta_texto, datos_cita_o_None)
    """
    if not OPENAI_API_KEY:
        return _simulated_reply(history, user_message)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=OPENAI_API_KEY)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in history[-12:]:  # últimos mensajes
            messages.append({"role": m["role"], "content": m["content"]})
        messages.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            messages=messages,
            temperature=0.3,
        )
        text = resp.choices[0].message.content or ""
        data = _parse_json_from_text(text)
        if data:
            # Mensaje amigable además del JSON
            resumen = data.get("resumen") or "Ya tengo todos los datos."
            return (
                f"{resumen}\n\n"
                f"- Tipo: {data.get('tipo')}\n"
                f"- Fecha: {data.get('fecha')}\n"
                f"- Franja: {data.get('hora')}\n"
                f"- Motivo: {data.get('motivo')}\n\n"
                f"Responde **sí** para confirmar y agendar la cita.",
                data,
            )
        return text, None
    except Exception as e:
        # Fallback al modo simulado
        print(f"[IA] Error OpenAI: {e}. Usando modo simulado.")
        return _simulated_reply(history, user_message)
