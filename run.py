"""Hogaru — Script de inicio rápido del servidor (Backend + Frontend).

Uso:
    python run.py
"""
import os
from pathlib import Path
import sys

# Asegurar que la carpeta 'backend' esté en el sys.path
BASE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = BASE_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Cargar variables de entorno desde backend/.env si existe
env_path = BACKEND_DIR / ".env"
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass


def aplicar_migraciones_si_es_posible():
    try:
        from app.migraciones import aplicar_migraciones
        aplicar_migraciones()
    except Exception as e:
        print(f"[*] Aviso al conectar a base de datos: {e}")
        print("[*] Asegurate de tener MySQL iniciado (puerto 3306) con la base 'hogaru'.\n")


def iniciar():
    print("=" * 65)
    print("           HOGARU — SERVIDOR DE DESARROLLO")
    print("=" * 65)
    
    # 1. Asegurar directorios de uploads
    uploads_dir = BACKEND_DIR / "uploads" / "documentos"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # 2. Aplicar migraciones automáticas si MySQL está corriendo
    print("[1/2] Verificando base de datos y migraciones...")
    aplicar_migraciones_si_es_posible()

    # 3. Informar accesos
    print("[2/2] Iniciando servidor con auto-recarga (Uvicorn)...")
    print(f"      -> Aplicación web:      http://127.0.0.1:8000")
    print(f"      -> Documentación API:   http://127.0.0.1:8000/docs")
    print(f"      -> ReDoc interactivo:   http://127.0.0.1:8000/redoc")
    print("\n[+] Servidor activo. Cualquier cambio en el código se recargará solo.")
    print("[+] Presioná Ctrl + C para detener el servidor.\n")
    print("=" * 65 + "\n")

    try:
        import uvicorn
        uvicorn.run(
            "app.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            app_dir=str(BACKEND_DIR),
        )
    except KeyboardInterrupt:
        print("\n[*] Servidor detenido por el usuario.")


if __name__ == "__main__":
    iniciar()
