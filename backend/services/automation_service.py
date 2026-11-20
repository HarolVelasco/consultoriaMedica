"""
Motor de automatización propio (reemplazo de n8n).
Cada flujo se registra en automation_logs con entrada, resultado y errores.
"""
import json
import time
from typing import Any, Callable, Optional

from sqlalchemy.orm import Session

from ..models import AutomationLog


def log_ejecucion(
    db: Session,
    flujo: str,
    entrada: Any,
    resultado: Any = None,
    exito: bool = True,
    error: Optional[str] = None,
    usuario_id: Optional[int] = None,
    intentos: int = 1,
) -> AutomationLog:
    entry = AutomationLog(
        flujo=flujo,
        usuario_id=usuario_id,
        entrada=json.dumps(entrada, ensure_ascii=False, default=str) if entrada is not None else None,
        resultado=json.dumps(resultado, ensure_ascii=False, default=str) if resultado is not None else None,
        exito=exito,
        error=error,
        intentos=intentos,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def ejecutar_con_reintentos(
    db: Session,
    flujo: str,
    fn: Callable,
    entrada: Any,
    usuario_id: Optional[int] = None,
    max_intentos: int = 3,
    delay_seg: float = 0.5,
) -> Any:
    """
    Ejecuta una función con reintentos y deja log de la ejecución.
    Si falla todos los intentos, registra error y relanza la excepción.
    """
    last_err: Optional[Exception] = None
    for intento in range(1, max_intentos + 1):
        try:
            resultado = fn()
            log_ejecucion(
                db,
                flujo=flujo,
                entrada=entrada,
                resultado=resultado if not callable(resultado) else str(resultado)[:500],
                exito=True,
                usuario_id=usuario_id,
                intentos=intento,
            )
            return resultado
        except Exception as e:
            last_err = e
            if intento < max_intentos:
                time.sleep(delay_seg * intento)
            else:
                log_ejecucion(
                    db,
                    flujo=flujo,
                    entrada=entrada,
                    resultado=None,
                    exito=False,
                    error=str(e),
                    usuario_id=usuario_id,
                    intentos=intento,
                )
    raise last_err  # type: ignore
