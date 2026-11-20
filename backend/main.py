from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .database import Base, engine
from .routers import auth_router, bot_router, citas_router, vision_router

# Crear tablas (incluye automation_logs y documentos_verificacion)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Consultoría Médica API",
    description="Automatización en código + bot IA + módulo de visión (cédula)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(citas_router.router)
app.include_router(bot_router.router)
app.include_router(vision_router.router)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)

if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
    app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")

    @app.get("/")
    def index():
        return FileResponse(FRONTEND_DIR / "index.html")

    @app.get("/login")
    def login_page():
        return FileResponse(FRONTEND_DIR / "login.html")

    @app.get("/registro")
    def registro_page():
        return FileResponse(FRONTEND_DIR / "registro.html")

    @app.get("/panel")
    def panel_page():
        return FileResponse(FRONTEND_DIR / "panel.html")

    @app.get("/reserva")
    def reserva_page():
        return FileResponse(FRONTEND_DIR / "reserva.html")

    @app.get("/bot")
    def bot_page():
        return FileResponse(FRONTEND_DIR / "bot.html")

    @app.get("/verificar")
    def verificar_page():
        return FileResponse(FRONTEND_DIR / "verificar.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "message": "Consultoría Médica API",
        "modulos": ["auth", "citas", "bot", "vision", "automation_logs"],
    }
