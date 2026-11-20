from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Cita, Usuario
from ..schemas import CitaCreate, CitaEstadoUpdate, CitaOut
from ..services.automation_service import ejecutar_con_reintentos, log_ejecucion
from ..services.email_service import enviar_aviso_medico, enviar_confirmacion_paciente

router = APIRouter(prefix="/api/citas", tags=["citas"])


@router.post("", response_model=CitaOut, status_code=201)
def crear_cita(
    datos: CitaCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    entrada = {
        "usuario_id": current.id,
        "tipo": datos.tipo,
        "fecha": datos.fecha,
        "hora": datos.hora,
        "origen": datos.origen,
    }

    def _crear():
        cita = Cita(
            usuario_id=current.id,
            tipo=datos.tipo,
            fecha=datos.fecha,
            hora=datos.hora,
            motivo=datos.motivo,
            origen=datos.origen or "formulario",
            estado="pendiente",
        )
        db.add(cita)
        db.commit()
        db.refresh(cita)

        # Automatización: emails (con reintento interno vía ejecutar_con_reintentos solo del bloque email)
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
            log_ejecucion(
                db,
                flujo="email_cita",
                entrada={"cita_id": cita.id, "email": current.email},
                resultado={"enviado": True},
                exito=True,
                usuario_id=current.id,
            )
        except Exception as e:
            log_ejecucion(
                db,
                flujo="email_cita",
                entrada={"cita_id": cita.id},
                resultado=None,
                exito=False,
                error=str(e),
                usuario_id=current.id,
            )
            print(f"[Email] Error: {e}")

        return {
            "id": cita.id,
            "tipo": cita.tipo,
            "fecha": cita.fecha,
            "hora": cita.hora,
            "motivo": cita.motivo,
            "origen": cita.origen,
            "estado": cita.estado,
            "creado_en": cita.creado_en,
            "usuario_id": cita.usuario_id,
        }

    resultado = ejecutar_con_reintentos(
        db,
        flujo="crear_cita",
        fn=_crear,
        entrada=entrada,
        usuario_id=current.id,
        max_intentos=2,
    )
    return resultado


@router.get("/mias", response_model=List[CitaOut])
def mis_citas(
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    return (
        db.query(Cita)
        .filter(Cita.usuario_id == current.id)
        .order_by(Cita.creado_en.desc())
        .all()
    )


@router.patch("/{cita_id}/estado", response_model=CitaOut)
def actualizar_estado(
    cita_id: int,
    body: CitaEstadoUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    if body.estado not in ("confirmada", "cancelada", "pendiente"):
        raise HTTPException(status_code=400, detail="Estado no válido")

    cita = db.query(Cita).filter(Cita.id == cita_id, Cita.usuario_id == current.id).first()
    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    cita.estado = body.estado
    db.commit()
    db.refresh(cita)

    log_ejecucion(
        db,
        flujo="actualizar_estado_cita",
        entrada={"cita_id": cita_id, "estado": body.estado},
        resultado={"ok": True},
        exito=True,
        usuario_id=current.id,
    )
    return cita
