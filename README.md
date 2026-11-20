# Consultoría Médica – Backend propio + Bot IA

Proyecto con **Python (FastAPI)**, sin depender de n8n Cloud.

Incluye:
- Registro e inicio de sesión (JWT)
- Panel del paciente (listar / cancelar citas)
- Formulario de agendamiento
- **Bot con IA** (complementario) para agendar por chat
- Emails de confirmación (consola en desarrollo; SMTP en producción)

---

## Requisitos

- Python 3.10+
- (Opcional) API key de OpenAI para el bot “real”

---

## Instalación

```bash
cd consultoria-medica

# Entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

pip install -r requirements.txt
```

---

## Ejecutar

Desde la carpeta `consultoria-medica`:

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Abre en el navegador:

- http://127.0.0.1:8000/          → Inicio
- http://127.0.0.1:8000/registro → Crear cuenta
- http://127.0.0.1:8000/login    → Iniciar sesión
- http://127.0.0.1:8000/panel    → Mis citas
- http://127.0.0.1:8000/reserva  → Formulario
- http://127.0.0.1:8000/bot      → Chat con IA
- http://127.0.0.1:8000/docs     → Documentación API (Swagger)

---

## Bot con IA

### Sin API key (modo simulado)
El bot funciona con reglas simples: te pide tipo, fecha, hora y motivo, y al final confirmas con **sí**.

### Con OpenAI
```bash
# Linux / Mac
export OPENAI_API_KEY=sk-tu-clave
export OPENAI_MODEL=gpt-4o-mini

# Windows (CMD)
set OPENAI_API_KEY=sk-tu-clave
```

Luego reinicia uvicorn.

---

## Verificación de cédula con Gemini

1. Copia `.env.example` como `.env` en la carpeta del proyecto.
2. En `.env`, configura `GEMINI_API_KEY` con una clave creada en [Google AI Studio](https://aistudio.google.com/apikey). El modelo por defecto es `gemini-3.5-flash-lite`.
3. Reinicia Uvicorn para que cargue la configuración.

Si definiste `GEMINI_VISION_MODEL` como variable de entorno de Windows, actualízala también; esa variable prevalece sobre `.env`.
Sin una clave válida o si Gemini no acepta el modelo, la imagen queda guardada como pendiente y no se marca la identidad como verificada.

---

## Emails + calendario (.ics)

Por defecto los emails se **imprimen en la consola** (modo desarrollo).

Con SMTP configurado, el paciente recibe:
- Email HTML de confirmación
- Archivo **cita-medica.ics** → al abrirlo se guarda en Google Calendar, Outlook o Apple Calendar

### Configurar Gmail (Windows PowerShell)

1. Activa verificación en 2 pasos en Google.
2. Crea una **Contraseña de aplicación**: https://myaccount.google.com/apppasswords
3. Antes de arrancar el servidor:

```powershell
$env:SMTP_HOST="smtp.gmail.com"
$env:SMTP_PORT="587"
$env:SMTP_USER="tu@gmail.com"
$env:SMTP_PASS="xxxx xxxx xxxx xxxx"
$env:EMAIL_FROM="tu@gmail.com"
$env:EMAIL_MEDICO="medico@gmail.com"
```

Luego:

```powershell
uvicorn backend.main:app --reload --port 8000
```

Sin estas variables el sistema funciona igual; verás el email en la consola.

---

## Estructura

```
consultoria-medica/
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── auth_router.py
│   │   ├── citas_router.py
│   │   └── bot_router.py
│   └── services/
│       ├── email_service.py
│       └── ia_service.py
├── frontend/
│   ├── index.html, login.html, registro.html
│   ├── panel.html, reserva.html, bot.html
│   ├── css/styles.css
│   └── js/api.js, nav.js
├── requirements.txt
└── README.md
```

La base de datos SQLite se crea sola: `consultoria.db` en la carpeta desde donde ejecutes uvicorn.

---

## Flujo del bot

1. El paciente escribe en el chat.
2. La IA (o el modo simulado) pide los datos que faltan.
3. Cuando están completos, pide confirmación (**sí**).
4. Se crea la cita, se envían emails y aparece en el panel.

---

## Notas para el profesor

- Backend **nativo en Python** (FastAPI), sin n8n Cloud.
- Autenticación JWT.
- Automatizaciones (emails) en el propio backend.
- IA integrada en el endpoint `/api/bot/chat`.
- El formulario clásico y el bot conviven (bot complementario).
