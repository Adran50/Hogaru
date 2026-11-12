"""Hash de contraseñas (PBKDF2, solo biblioteca estándar) y tokens JWT."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from . import config

_ITERACIONES = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERACIONES)
    return f"pbkdf2_sha256${_ITERACIONES}${salt.hex()}${h.hex()}"


def verify_password(password: str, guardado: str) -> bool:
    try:
        algoritmo, iteraciones, salt, h = guardado.split("$")
        if algoritmo != "pbkdf2_sha256":
            return False
        nuevo = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iteraciones)
        )
        return hmac.compare_digest(nuevo.hex(), h)
    except (ValueError, TypeError):
        return False


def crear_token(id_usuario: int, tipo_cuenta: str) -> str:
    payload = {
        "sub": str(id_usuario),
        "tipo": tipo_cuenta,
        "exp": datetime.now(timezone.utc) + timedelta(hours=config.JWT_HORAS),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")


def decodificar_token(token: str) -> dict:
    """Lanza jwt.PyJWTError si el token es inválido o venció."""
    return jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
