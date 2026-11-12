"""Configuración de Hogaru. Se lee de variables de entorno (o del archivo .env)."""
import os
from decimal import Decimal
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "hogaru")

JWT_SECRET = os.getenv("JWT_SECRET", "cambiar-esto-antes-de-entregar")
JWT_HORAS = int(os.getenv("JWT_HORAS", "12"))

# Porcentaje de comisión que retiene la plataforma de cada pago (0.10 = 10%)
COMISION_PLATAFORMA = Decimal(os.getenv("COMISION_PLATAFORMA", "0.10"))

# Momento configurable del cobro: "flexible" (por defecto), "al_finalizar" o "al_aceptar"
MOMENTO_PAGO = os.getenv("MOMENTO_PAGO", "flexible").lower()

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]
