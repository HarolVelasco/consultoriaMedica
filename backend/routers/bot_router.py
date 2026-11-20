import uuid
from typing import Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Cita, Usuario
from ..schemas import BotMessage, BotReply, CitaOut
from ..services.email_service import enviar_aviso_medico, enviar_confirmacion_paciente
from ..services.ia_service import chat_with_bot

router = APIRouter(prefix="/api/bot", tags=["bot"])

# Memoria en RAM por session_id (suficiente para demo / proyecto)
_sessions: Dict[str, List[dict]] = {}
_pending_citas: Dict[str, dict] = {}  # datos listos esperando "sí"


@router.post("/chat", response_model=BotReply)
def chat(
    body: BotMessage,
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    session_id = body.session_id or str(uuid.uuid4())
    history = _sessions.setdefault(session_id, [])

    user_msg = body.message.strip()
    user_lower = user_msg.lower()

    # Si hay cita pendiente de confirmación y el usuario dice sí
    if session_id in _pending_citas and user_lower in (
        "si",
        "sí",
        "confirmar",
        "confirmo",
        "ok",
        "dale",
        "acepto",
    ):
        datos = _pending_citas.pop(session_id)
        cita = Cita(
            usuario_id=current.id,
            tipo=datos["tipo"],
            fecha=datos["fecha"],
            hora=datos["hora"],
            motivo=datos["motivo"],
            origen="bot",
            estado="pendiente",
        )
        db.add(cita)
        db.commit()
        db.refresh(cita)

        try:
            enviar_confirmacion_paciente(
                current.nombre,
                current.email,
                cita.tipo,
                cita.fecha,
                cita.hora,
                cita.motivo,
            )
            enviar_aviso_medico(
                current.nombre,
                current.email,
                current.telefono or "",
                cita.tipo,
                cita.fecha,
                cita.hora,
                cita.motivo,
            )
        except Exception as e:
            print(f"[Email] Error: {e}")

        reply = (
            f"✅ ¡Cita agendada con éxito!\n\n"
            f"Tipo: {cita.tipo}\n"
            f"Fecha: {cita.fecha}\n"
            f"Franja: {cita.hora}\n\n"
            f"Te enviamos un email con invitación de calendario (.ics). "
            f"También puedes verla en tu panel."
        )
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": reply})
        _sessions[session_id] = history

        return BotReply(
            reply=reply,
            session_id=session_id,
            cita_creada=CitaOut.model_validate(cita),
        )

    # Conversación normal con IA
    reply_text, datos = chat_with_bot(history, user_msg)

    history.append({"role": "user", "content": user_msg})
    history.append({"role": "assistant", "content": reply_text})
    _sessions[session_id] = history[-20:]  # limitar memoria

    if datos and datos.get("listo"):
        _pending_citas[session_id] = {
            "tipo": datos["tipo"],
            "fecha": datos["fecha"],
            "hora": datos["hora"],
            "motivo": datos["motivo"],
        }

    return BotReply(
        reply=reply_text,
        session_id=session_id,
        datos_parciales=datos,
    )


@router.post("/reset")
def reset_session(session_id: str):
    _sessions.pop(session_id, None)
    _pending_citas.pop(session_id, None)
    return {"ok": True}
