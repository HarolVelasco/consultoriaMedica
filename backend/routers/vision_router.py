import json
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import DocumentoVerificacion, Usuario
from ..schemas import DocumentoOut, VisionResult
from ..services.automation_service import ejecutar_con_reintentos, log_ejecucion
from ..services.vision_service import (
    comparar_con_usuario,
    guardar_imagen,
    procesar_cedula,
)

router = APIRouter(prefix="/api/vision", tags=["vision"])

UPLOADS = Path(__file__).resolve().parent.parent.parent / "uploads"
ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


@router.post("/verificar-cedula", response_model=VisionResult)
async def verificar_cedula(
    file: UploadFile = File(...),
    documento_manual: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    """
    Sube foto de cédula → visión IA → compara con el usuario → actualiza perfil.
    """
    if file.content_type not in ALLOWED:
        raise HTTPException(400, "Solo se permiten imágenes JPG, PNG o WEBP")

    content = await file.read()
    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(400, "La imagen no puede superar 8 MB")
    if len(content) < 1000:
        raise HTTPException(400, "Archivo demasiado pequeño o vacío")

    mime = file.content_type or "image/jpeg"

    def _pipeline():
        datos_ia = procesar_cedula(content, mime)
        path = guardar_imagen(UPLOADS, current.id, file.filename or "cedula.jpg", content)

        comparacion = comparar_con_usuario(
            datos_ia,
            current.nombre,
            current.documento_numero or documento_manual,
        )

        # Si el usuario envía documento manual y la IA no lo leyó, usarlo
        doc_final = datos_ia.get("numero_documento") or documento_manual
        nombre_ext = datos_ia.get("nombre_completo")

        estado = comparacion["estado"]
        conf = float(datos_ia.get("confianza") or 0)

        doc = DocumentoVerificacion(
            usuario_id=current.id,
            archivo_path=path,
            nombre_extraido=nombre_ext,
            documento_extraido=str(doc_final) if doc_final else None,
            confianza=conf,
            estado=estado,
            datos_json=json.dumps(
                {"ia": datos_ia, "comparacion": comparacion},
                ensure_ascii=False,
                default=str,
            ),
        )
        db.add(doc)

        if estado == "validado":
            current.identidad_verificada = True
            current.identidad_confianza = conf
            if doc_final:
                current.documento_numero = str(doc_final).strip()
        elif estado == "rechazado":
            current.identidad_verificada = False

        db.commit()
        db.refresh(doc)

        return {
            "documento_id": doc.id,
            "estado": estado,
            "confianza": conf,
            "nombre_extraido": nombre_ext,
            "documento_extraido": doc.documento_extraido,
            "motivos": comparacion.get("motivos", []),
            "motor": datos_ia.get("motor"),
            "detalle_motor": datos_ia.get("error_api") or (
                "GEMINI_API_KEY no configurada; se usó el modo demo."
                if datos_ia.get("motor") == "demo"
                else None
            ),
            "identidad_verificada": current.identidad_verificada,
        }

    try:
        resultado = ejecutar_con_reintentos(
            db,
            flujo="verificar_cedula",
            fn=_pipeline,
            entrada={"usuario_id": current.id, "filename": file.filename, "mime": mime},
            usuario_id=current.id,
            max_intentos=2,
        )
    except Exception as e:
        raise HTTPException(500, f"Error al procesar la imagen: {e}") from e

    return VisionResult(**resultado)


@router.get("/mis-documentos", response_model=List[DocumentoOut])
def mis_documentos(
    db: Session = Depends(get_db),
    current: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(DocumentoVerificacion)
        .filter(DocumentoVerificacion.usuario_id == current.id)
        .order_by(DocumentoVerificacion.creado_en.desc())
        .limit(20)
        .all()
    )
    return rows


@router.get("/estado-identidad")
def estado_identidad(current: Usuario = Depends(get_current_user)):
    return {
        "identidad_verificada": bool(current.identidad_verificada),
        "documento_numero": current.documento_numero,
        "confianza": current.identidad_confianza,
        "nombre": current.nombre,
    }
