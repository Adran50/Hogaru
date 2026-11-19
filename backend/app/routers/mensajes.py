"""Módulo de Mensajes: chat directo entre cliente y prestador para una solicitud de trabajo."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos
from ..deps import usuario_actual
from ..errores import AccesoDenegadoError
from ..utils import cargar_solicitud_de

router = APIRouter(prefix="/solicitudes/{id_solicitud}/mensajes", tags=["Mensajes / Chat de Trabajo"])


class MensajeIn(BaseModel):
    contenido: str = Field(min_length=1, max_length=2000, description="Texto del mensaje")


@router.post("", status_code=201)
def enviar_mensaje(
    id_solicitud: int,
    datos: MensajeIn,
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Envía un mensaje en el hilo de chat de la solicitud. Solo para cliente y prestador asignados."""
    if usuario["tipo_cuenta"] not in ("cliente", "prestador"):
        raise AccesoDenegadoError("Solo los clientes y prestadores participantes pueden intercambiar mensajes")

    cargar_solicitud_de(db, id_solicitud, usuario)

    id_mensaje = insertar(
        db,
        "INSERT INTO mensaje (id_solicitud, id_emisor, contenido) VALUES (%s, %s, %s)",
        (id_solicitud, usuario["id_usuario"], datos.contenido),
    )
    db.commit()
    return {
        "id_mensaje": id_mensaje,
        "id_solicitud": id_solicitud,
        "id_emisor": usuario["id_usuario"],
        "contenido": datos.contenido,
    }


@router.get("")
def leer_mensajes(
    id_solicitud: int,
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Obtiene el historial de chat de una solicitud y marca como leídas sus notificaciones."""
    cargar_solicitud_de(db, id_solicitud, usuario, permitir_admin=True)

    mensajes = todos(
        db,
        "SELECT m.id_mensaje, m.id_emisor, CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS emisor, "
        "       m.contenido, m.fecha_envio "
        "FROM mensaje m "
        "JOIN usuario u ON u.id_usuario = m.id_emisor "
        "WHERE m.id_solicitud = %s ORDER BY m.id_mensaje",
        (id_solicitud,),
    )

    actualizar(
        db,
        "UPDATE notificacion SET leida = TRUE "
        "WHERE id_usuario = %s AND id_solicitud = %s AND tipo = 'mensaje'",
        (usuario["id_usuario"], id_solicitud),
    )
    db.commit()
    return mensajes
