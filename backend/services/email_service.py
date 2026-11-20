"""
Emails + invitación de calendario (.ics).

Modo desarrollo (sin SMTP): imprime en consola.
Modo producción: configura variables de entorno SMTP_*.

El archivo .ics se abre en Gmail/Outlook/Apple Calendar y se puede
guardar en el calendario del paciente.
"""
import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders


SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@consultoria-medica.local")
EMAIL_MEDICO = os.getenv("EMAIL_MEDICO", "medico@consultoria-medica.local")


def _hora_inicio_fin(hora_franja: str) -> tuple[str, str]:
    """Devuelve (HHMMSS inicio, HHMMSS fin) según la franja."""
    h = (hora_franja or "").lower()
    if "tarde" in h:
        return "160000", "164500"
    if "cualquier" in h:
        return "100000", "104500"
    # Mañana por defecto
    return "100000", "104500"


def generar_ics(
    nombre: str,
    email: str,
    tipo: str,
    fecha: str,
    hora: str,
    motivo: str,
) -> str:
    """Genera contenido de archivo .ics (iCalendar)."""
    start_h, end_h = _hora_inicio_fin(hora)
    # fecha viene YYYY-MM-DD
    dt_start = fecha.replace("-", "") + "T" + start_h
    dt_end = fecha.replace("-", "") + "T" + end_h
    now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    uid = str(uuid.uuid4())

    summary = f"Cita médica – {tipo}"
    description = (
        f"Tipo: {tipo}\\n"
        f"Franja: {hora}\\n"
        f"Motivo: {motivo}\\n"
        f"Paciente: {nombre}"
    )

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Consultoria Medica//ES
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:{uid}
DTSTAMP:{now}
DTSTART:{dt_start}
DTEND:{dt_end}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:Consultoría Médica
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT24H
ACTION:DISPLAY
DESCRIPTION:Recordatorio: cita médica mañana
END:VALARM
END:VEVENT
END:VCALENDAR
"""
    return ics


def _send(
    to: str,
    subject: str,
    html: str,
    ics_content: str | None = None,
    ics_filename: str = "cita.ics",
) -> None:
    if not SMTP_HOST or not SMTP_USER:
        print("=" * 60)
        print(f"[EMAIL DEV] Para: {to}")
        print(f"[EMAIL DEV] Asunto: {subject}")
        print(html[:400])
        if ics_content:
            print("[EMAIL DEV] Adjunto: cita.ics (invitación de calendario)")
            print(ics_content[:300])
        print("=" * 60)
        return

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    if ics_content:
        part = MIMEBase("text", "calendar", method="REQUEST", name=ics_filename)
        part.set_payload(ics_content.encode("utf-8"))
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{ics_filename}"')
        part.add_header("Content-Class", "urn:content-classes:calendarmessage")
        msg.attach(part)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, to, msg.as_string())
        print(f"[EMAIL] Enviado a {to}: {subject}")


def enviar_confirmacion_paciente(
    nombre: str,
    email: str,
    tipo: str,
    fecha: str,
    hora: str,
    motivo: str = "",
) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <div style="background:#0d6efd;color:white;padding:20px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="margin:0;">Consultoría Médica</h2>
        <p style="margin:6px 0 0;opacity:.9;">Confirmación de cita</p>
      </div>
      <div style="background:#fff;padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
        <p>Hola <strong>{nombre}</strong>,</p>
        <p>Hemos recibido tu solicitud de cita:</p>
        <ul>
          <li><strong>Tipo:</strong> {tipo}</li>
          <li><strong>Fecha:</strong> {fecha}</li>
          <li><strong>Franja:</strong> {hora}</li>
        </ul>
        <p><strong>Adjunto encontrarás un archivo de calendario (.ics).</strong>
        Ábrelo para guardar la cita en Google Calendar, Outlook o Apple Calendar.</p>
        <p>Saludos,<br><strong>Equipo de Consultoría Médica</strong></p>
      </div>
    </div>
    """
    ics = generar_ics(nombre, email, tipo, fecha, hora, motivo or tipo)
    _send(
        email,
        "Confirmación de tu cita – Consultoría Médica",
        html,
        ics_content=ics,
        ics_filename="cita-medica.ics",
    )


def enviar_aviso_medico(
    nombre: str,
    email: str,
    telefono: str,
    tipo: str,
    fecha: str,
    hora: str,
    motivo: str,
) -> None:
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;">
      <div style="background:#1e293b;color:white;padding:18px;border-radius:12px 12px 0 0;text-align:center;">
        <h2 style="margin:0;font-size:18px;">Nueva solicitud de cita</h2>
      </div>
      <div style="background:#fff;padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
        <p><strong>Nombre:</strong> {nombre}</p>
        <p><strong>Email:</strong> {email}</p>
        <p><strong>Teléfono:</strong> {telefono or '—'}</p>
        <p><strong>Tipo:</strong> {tipo}</p>
        <p><strong>Fecha:</strong> {fecha}</p>
        <p><strong>Franja:</strong> {hora}</p>
        <p><strong>Motivo:</strong><br>{motivo}</p>
      </div>
    </div>
    """
    _send(EMAIL_MEDICO, f"Nueva cita – {nombre}", html)
