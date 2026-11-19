"""Dependencias de autenticación y autorización para Hogaru API."""
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import get_db, uno
from .errores import AccesoDenegadoError, NoAutorizadoError
from .security import decodificar_token

_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db=Depends(get_db),
) -> dict:
    """Devuelve el usuario logueado validando JWT y estado en base de datos.
    Un usuario suspendido no puede operar (403).
    """
    if credenciales is None:
        raise NoAutorizadoError("Falta el token de autenticación")
    try:
        payload = decodificar_token(credenciales.credentials)
        id_usuario = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise NoAutorizadoError("Token inválido o vencido")

    usuario = uno(
        db,
        "SELECT id_usuario, nombre, apellido, email, tipo_cuenta, estado "
        "FROM usuario WHERE id_usuario = %s",
        (id_usuario,),
    )
    if not usuario:
        raise NoAutorizadoError("El usuario ya no existe")
    if usuario["estado"] != "activo":
        raise AccesoDenegadoError("La cuenta está suspendida")
    return usuario


def requiere(*tipos: str):
    """Dependencia de autorización por rol/tipo de cuenta (cliente, prestador, administrador)."""

    def _dep(usuario: dict = Depends(usuario_actual)) -> dict:
        if usuario["tipo_cuenta"] not in tipos:
            raise AccesoDenegadoError(
                f"Esta acción es solo para usuarios con rol: {', '.join(tipos)}"
            )
        return usuario

    return _dep


# Helpers comunes de conveniencia
solo_admin = requiere("administrador")
solo_cliente = requiere("cliente")
solo_prestador = requiere("prestador")
cliente_o_prestador = requiere("cliente", "prestador")
