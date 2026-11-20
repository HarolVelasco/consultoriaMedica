from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    telefono = Column(String(40), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    rol = Column(String(20), default="paciente")  # paciente | medico
    # Verificación de identidad (módulo de visión)
    documento_numero = Column(String(40), nullable=True)
    identidad_verificada = Column(Boolean, default=False)
    identidad_confianza = Column(Float, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    citas = relationship("Cita", back_populates="usuario")
    documentos = relationship("DocumentoVerificacion", back_populates="usuario")


class Cita(Base):
    __tablename__ = "citas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    tipo = Column(String(80), nullable=False)
    fecha = Column(String(20), nullable=False)
    hora = Column(String(60), nullable=False)
    motivo = Column(Text, nullable=False)
    origen = Column(String(60), default="formulario")
    estado = Column(String(30), default="pendiente")
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="citas")


class ChatMensaje(Base):
    __tablename__ = "chat_mensajes"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    session_id = Column(String(80), index=True, nullable=False)
    rol = Column(String(20), nullable=False)
    contenido = Column(Text, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)


class AutomationLog(Base):
    """Registro de cada ejecución del motor de automatización (requisito guía)."""
    __tablename__ = "automation_logs"

    id = Column(Integer, primary_key=True, index=True)
    flujo = Column(String(80), nullable=False)  # crear_cita | verificar_documento | email | ...
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    entrada = Column(Text, nullable=True)  # JSON resumen
    resultado = Column(Text, nullable=True)
    exito = Column(Boolean, default=True)
    error = Column(Text, nullable=True)
    intentos = Column(Integer, default=1)
    creado_en = Column(DateTime, default=datetime.utcnow)


class DocumentoVerificacion(Base):
    """Imágenes de cédula / documentos procesados por visión."""
    __tablename__ = "documentos_verificacion"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    archivo_path = Column(String(255), nullable=False)
    nombre_extraido = Column(String(180), nullable=True)
    documento_extraido = Column(String(40), nullable=True)
    confianza = Column(Float, nullable=True)
    estado = Column(String(30), default="pendiente")  # pendiente | validado | rechazado
    datos_json = Column(Text, nullable=True)  # respuesta completa de la IA
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="documentos")
