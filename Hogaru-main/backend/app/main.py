"""Hogaru API — Punto de entrada de la aplicación.

Levantar:  uvicorn app.main:app --reload
Docs interactivas:  http://localhost:8000/docs
Prefijo API principal: /api/v1
"""
from pathlib import Path
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import nueva_conexion
from .errores import registrar_manejadores_error
from .routers import (admin, auth, calificaciones, contratacion, disputas,
                      mensajes, notificaciones, pagos, servicios, verificacion)

app = FastAPI(
    title="Hogaru API",
    description="Marketplace de servicios de limpieza doméstica — Prácticas Profesionalizantes, E.E.S.T. N°6.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware de CORS permisivo para desarrollo y frontend estático
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registro de Exception Handlers centralizados
registrar_manejadores_error(app)

# Router principal versionado /api/v1
api_v1_router = APIRouter(prefix="/api/v1")

modulos_routers = (
    auth,
    verificacion,
    servicios,
    contratacion,
    pagos,
    calificaciones,
    disputas,
    mensajes,
    notificaciones,
    admin,
)

# 1. Registrar endpoints bajo /api/v1 (estándar REST de la especificación)
for modulo in modulos_routers:
    api_v1_router.include_router(modulo.router)

app.include_router(api_v1_router)

# 2. Registrar endpoints en la raíz (retrocompatibilidad para frontend existente y tests)
for modulo in modulos_routers:
    app.include_router(modulo.router)


# ---------- Archivos Estáticos del Frontend ----------
CARPETA_FRONTEND = Path(__file__).resolve().parent.parent.parent
if (CARPETA_FRONTEND / "index.html").exists():
    app.mount("/js", StaticFiles(directory=str(CARPETA_FRONTEND / "js")), name="js")
    app.mount("/paginas", StaticFiles(directory=str(CARPETA_FRONTEND / "paginas")), name="paginas")
    if (CARPETA_FRONTEND / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(CARPETA_FRONTEND / "assets")), name="assets")
    if (CARPETA_FRONTEND / "componentes").exists():
        app.mount("/componentes", StaticFiles(directory=str(CARPETA_FRONTEND / "componentes")), name="componentes")

    @app.get("/estilos.css", include_in_schema=False)
    def estilos_css():
        return FileResponse(CARPETA_FRONTEND / "estilos.css", media_type="text/css")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon():
        fav = CARPETA_FRONTEND / "favicon.ico"
        if not fav.exists():
            fav = CARPETA_FRONTEND / "assets" / "favicon.ico"
        return FileResponse(fav, media_type="image/x-icon")

    @app.get("/index.html", include_in_schema=False)
    @app.get("/", tags=["Frontend"])
    def index():
        return FileResponse(CARPETA_FRONTEND / "index.html")


# ---------- Estado y Salud ----------
@app.get("/api/v1", tags=["Estado"])
def api_v1_raiz():
    return {
        "app": "Hogaru API",
        "version": "1.0.0",
        "docs": "/docs",
        "api_v1": "/api/v1",
    }


@app.get("/salud", tags=["Estado"])
@app.get("/api/v1/salud", tags=["Estado"])
def salud():
    """Verifica que la API llegue a la base de datos."""
    conn = nueva_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
            return {
                "api": "ok",
                "base_de_datos": "ok" if cur.fetchone()["ok"] == 1 else "error",
            }
    finally:
        conn.close()
