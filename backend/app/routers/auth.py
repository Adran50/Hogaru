"""Módulo de Usuarios y Autenticación: registro, login, perfil y cambio de contraseña."""
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, uno
from ..deps import usuario_actual
from ..errores import AccesoDenegadoError, ConflictoError, NoAutorizadoError, ReglaNegocioError
from ..security import crear_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Usuarios / Autenticación"])

_EMAIL_REGEX = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class RegistroIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=60)
    apellido: str = Field(min_length=1, max_length=60)
    email: str = Field(pattern=_EMAIL_REGEX, max_length=120)
    password: str = Field(min_length=8, max_length=72)
    telefono: str | None = Field(None, max_length=30)
    tipo_cuenta: Literal["cliente", "prestador"]
    # Campos específicos de cliente
    direccion: str | None = Field(None, max_length=200)
    # Coordenadas geográficas (cliente o prestador)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    # Campos específicos de prestador
    descripcion: str | None = Field(None, max_length=2000)


class LoginIn(BaseModel):
    email: str
    password: str


class PerfilUpdateIn(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=60)
    apellido: str | None = Field(None, min_length=1, max_length=60)
    telefono: str | None = Field(None, max_length=30)
    foto_perfil: str | None = Field(None, max_length=255)
    direccion: str | None = Field(None, max_length=200)
    descripcion: str | None = Field(None, max_length=2000)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)


class CambiarPasswordIn(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=72)


def _obtener_perfil_completo(db, usuario: dict) -> dict:
    """Devuelve los datos del usuario con los campos específicos de su rol."""
    id_usuario = usuario["id_usuario"]
    tipo = usuario["tipo_cuenta"]
    perfil_extra = None

    if tipo == "cliente":
        perfil_extra = uno(
            db,
            "SELECT direccion, latitud, longitud FROM cliente WHERE id_cliente = %s",
            (id_usuario,),
        )
    elif tipo == "prestador":
        perfil_extra = uno(
            db,
            "SELECT descripcion, estado_verificacion, puntuacion_promedio, latitud, longitud "
            "FROM prestador WHERE id_prestador = %s",
            (id_usuario,),
        )
    elif tipo == "administrador":
        perfil_extra = uno(
            db,
            "SELECT nivel_permiso FROM administrador WHERE id_admin = %s",
            (id_usuario,),
        )

    # Asegurar que nunca se filtre contraseña
    usuario_salida = {
        "id_usuario": usuario["id_usuario"],
        "nombre": usuario["nombre"],
        "apellido": usuario["apellido"],
        "email": usuario["email"],
        "tipo_cuenta": usuario["tipo_cuenta"],
        "estado": usuario.get("estado", "activo"),
        "foto_perfil": usuario.get("foto_perfil"),
        "perfil": perfil_extra,
    }
    if "telefono" in usuario:
        usuario_salida["telefono"] = usuario["telefono"]
    return usuario_salida


@router.post("/registro", status_code=201)
def registro(datos: RegistroIn, db=Depends(get_db)):
    """Registra una nueva cuenta de cliente o prestador con contraseña hasheada."""
    email = datos.email.lower()
    if uno(db, "SELECT 1 FROM usuario WHERE email = %s", (email,)):
        raise ConflictoError("Ya existe una cuenta con ese email")

    id_usuario = insertar(
        db,
        "INSERT INTO usuario (nombre, apellido, email, contrasena, telefono, tipo_cuenta) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (datos.nombre, datos.apellido, email, hash_password(datos.password),
         datos.telefono, datos.tipo_cuenta),
    )

    if datos.tipo_cuenta == "cliente":
        insertar(
            db,
            "INSERT INTO cliente (id_cliente, direccion, latitud, longitud) VALUES (%s, %s, %s, %s)",
            (id_usuario, datos.direccion, datos.latitud, datos.longitud),
        )
    else:
        insertar(
            db,
            "INSERT INTO prestador (id_prestador, descripcion, latitud, longitud) VALUES (%s, %s, %s, %s)",
            (id_usuario, datos.descripcion, datos.latitud, datos.longitud),
        )

    db.commit()
    return {
        "id_usuario": id_usuario,
        "nombre": datos.nombre,
        "apellido": datos.apellido,
        "email": email,
        "tipo_cuenta": datos.tipo_cuenta,
    }


@router.post("/login")
def login(datos: LoginIn, db=Depends(get_db)):
    """Autentica con email y contraseña, devolviendo token JWT y datos de sesión."""
    usuario = uno(
        db,
        "SELECT id_usuario, nombre, apellido, email, contrasena, tipo_cuenta, estado, foto_perfil "
        "FROM usuario WHERE email = %s",
        (datos.email.lower(),),
    )
    if not usuario or not verify_password(datos.password, usuario["contrasena"]):
        raise NoAutorizadoError("Email o contraseña incorrectos")
    if usuario["estado"] != "activo":
        raise AccesoDenegadoError("La cuenta está suspendida")

    return {
        "access_token": crear_token(usuario["id_usuario"], usuario["tipo_cuenta"]),
        "token_type": "bearer",
        "usuario": {
            "id_usuario": usuario["id_usuario"],
            "nombre": usuario["nombre"],
            "apellido": usuario["apellido"],
            "email": usuario["email"],
            "tipo_cuenta": usuario["tipo_cuenta"],
            "foto_perfil": usuario.get("foto_perfil"),
        },
    }


@router.get("/me")
@router.get("/perfil")
def ver_perfil(usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Devuelve los datos del perfil del usuario actualmente autenticado."""
    # Obtenemos los campos completos del usuario actual
    u_completo = uno(
        db,
        "SELECT id_usuario, nombre, apellido, email, telefono, tipo_cuenta, estado, foto_perfil "
        "FROM usuario WHERE id_usuario = %s",
        (usuario["id_usuario"],),
    )
    return _obtener_perfil_completo(db, u_completo or usuario)


@router.put("/me")
@router.put("/perfil")
def actualizar_perfil(datos: PerfilUpdateIn, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Actualiza datos personales, de contacto y perfil de cliente/prestador."""
    id_usuario = usuario["id_usuario"]
    tipo = usuario["tipo_cuenta"]

    # 1. Actualizar tabla base 'usuario' si corresponde
    cambios_usuario = {}
    if datos.nombre is not None:
        cambios_usuario["nombre"] = datos.nombre
    if datos.apellido is not None:
        cambios_usuario["apellido"] = datos.apellido
    if datos.telefono is not None:
        cambios_usuario["telefono"] = datos.telefono
    if datos.foto_perfil is not None:
        cambios_usuario["foto_perfil"] = datos.foto_perfil

    if cambios_usuario:
        set_clause = ", ".join(f"{col} = %s" for col in cambios_usuario)
        actualizar(
            db,
            f"UPDATE usuario SET {set_clause} WHERE id_usuario = %s",
            list(cambios_usuario.values()) + [id_usuario],
        )

    # 2. Actualizar tabla según rol
    if tipo == "cliente":
        cambios_cliente = {}
        if datos.direccion is not None:
            cambios_cliente["direccion"] = datos.direccion
        if datos.latitud is not None:
            cambios_cliente["latitud"] = datos.latitud
        if datos.longitud is not None:
            cambios_cliente["longitud"] = datos.longitud

        if cambios_cliente:
            set_clause = ", ".join(f"{col} = %s" for col in cambios_cliente)
            actualizar(
                db,
                f"UPDATE cliente SET {set_clause} WHERE id_cliente = %s",
                list(cambios_cliente.values()) + [id_usuario],
            )

    elif tipo == "prestador":
        cambios_prestador = {}
        if datos.descripcion is not None:
            cambios_prestador["descripcion"] = datos.descripcion
        if datos.latitud is not None:
            cambios_prestador["latitud"] = datos.latitud
        if datos.longitud is not None:
            cambios_prestador["longitud"] = datos.longitud

        if cambios_prestador:
            set_clause = ", ".join(f"{col} = %s" for col in cambios_prestador)
            actualizar(
                db,
                f"UPDATE prestador SET {set_clause} WHERE id_prestador = %s",
                list(cambios_prestador.values()) + [id_usuario],
            )

    db.commit()

    u_actualizado = uno(
        db,
        "SELECT id_usuario, nombre, apellido, email, telefono, tipo_cuenta, estado, foto_perfil "
        "FROM usuario WHERE id_usuario = %s",
        (id_usuario,),
    )
    return _obtener_perfil_completo(db, u_actualizado)


@router.post("/foto-perfil", status_code=200)
@router.post("/perfil/foto", status_code=200)
@router.post("/me/foto", status_code=200)
async def subir_foto_perfil(
    archivo: UploadFile = File(...),
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Sube una nueva fotografía de perfil y la asigna al usuario actual."""
    if not archivo.filename:
        raise ReglaNegocioError("No se seleccionó ningún archivo de imagen")

    ext = Path(archivo.filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ReglaNegocioError("Formato de imagen inválido. Solo se admiten archivos JPG, PNG y WebP.")

    contenido = await archivo.read()
    if len(contenido) > 10 * 1024 * 1024:
        raise ReglaNegocioError("La imagen no debe superar los 10 MB de tamaño.")

    carpeta_perfiles = Path(__file__).resolve().parent.parent.parent / "uploads" / "perfiles"
    carpeta_perfiles.mkdir(parents=True, exist_ok=True)

    nombre_archivo = f"perfil_{usuario['id_usuario']}_{uuid.uuid4().hex[:8]}{ext}"
    destino = carpeta_perfiles / nombre_archivo
    with open(destino, "wb") as f:
        f.write(contenido)

    foto_url = f"/uploads/perfiles/{nombre_archivo}"
    actualizar(db, "UPDATE usuario SET foto_perfil = %s WHERE id_usuario = %s", (foto_url, usuario["id_usuario"]))
    db.commit()

    return {
        "mensaje": "Foto de perfil actualizada exitosamente",
        "foto_perfil": foto_url,
    }


@router.delete("/foto-perfil", status_code=200)
@router.delete("/perfil/foto", status_code=200)
@router.delete("/me/foto", status_code=200)
def eliminar_foto_perfil(usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Quita la foto de perfil del usuario dejándola en null."""
    actualizar(db, "UPDATE usuario SET foto_perfil = NULL WHERE id_usuario = %s", (usuario["id_usuario"],))
    db.commit()
    return {
        "mensaje": "Foto de perfil eliminada exitosamente",
        "foto_perfil": None,
    }


@router.post("/cambiar-password")
def cambiar_password(datos: CambiarPasswordIn, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Permite al usuario cambiar su contraseña validando la clave actual."""
    id_usuario = usuario["id_usuario"]
    fila = uno(db, "SELECT contrasena FROM usuario WHERE id_usuario = %s", (id_usuario,))
    if not fila or not verify_password(datos.password_actual, fila["contrasena"]):
        raise ReglaNegocioError("La contraseña actual es incorrecta")

    if datos.password_actual == datos.password_nueva:
        raise ReglaNegocioError("La nueva contraseña no puede ser idéntica a la actual")

    nuevo_hash = hash_password(datos.password_nueva)
    actualizar(db, "UPDATE usuario SET contrasena = %s WHERE id_usuario = %s", (nuevo_hash, id_usuario))
    db.commit()

    return {"mensaje": "Contraseña actualizada exitosamente"}
