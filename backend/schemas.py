from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field


# ---------- Auth ----------
class UsuarioCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120)
    email: EmailStr
    telefono: Optional[str] = None
    password: str = Field(..., min_length=6)


class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str


class UsuarioOut(BaseModel):
    id: int
    nombre: str
    email: EmailStr
    telefono: Optional[str] = None
    rol: str
    identidad_verificada: bool = False
    documento_numero: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioOut


# ---------- Citas ----------
class CitaCreate(BaseModel):
    tipo: str
    fecha: str
    hora: str
    motivo: str
    origen: str = "formulario"


class CitaOut(BaseModel):
    id: int
    tipo: str
    fecha: str
    hora: str
    motivo: str
    origen: str
    estado: str
    creado_en: datetime
    usuario_id: int

    class Config:
        from_attributes = True


class CitaEstadoUpdate(BaseModel):
    estado: str


# ---------- Bot ----------
class BotMessage(BaseModel):
    message: str
    session_id: Optional[str] = None


class BotReply(BaseModel):
    reply: str
    session_id: str
    cita_creada: Optional[CitaOut] = None
    datos_parciales: Optional[dict] = None


# ---------- Visión ----------
class VisionResult(BaseModel):
    documento_id: int
    estado: str
    confianza: float
    nombre_extraido: Optional[str] = None
    documento_extraido: Optional[str] = None
    motivos: List[str] = []
    motor: Optional[str] = None
    detalle_motor: Optional[str] = None
    identidad_verificada: bool = False


class DocumentoOut(BaseModel):
    id: int
    nombre_extraido: Optional[str] = None
    documento_extraido: Optional[str] = None
    confianza: Optional[float] = None
    estado: str
    creado_en: datetime

    class Config:
        from_attributes = True


# ---------- Logs ----------
class AutomationLogOut(BaseModel):
    id: int
    flujo: str
    exito: bool
    error: Optional[str] = None
    intentos: int
    creado_en: datetime

    class Config:
        from_attributes = True
