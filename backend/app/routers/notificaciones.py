"""Módulo de Notificaciones: bandeja de alertas y gestión de lectura."""
from fastapi import APIRouter, Depends, Query

from ..db import actualizar, get_db, todos, uno
from ..deps import usuario_actual
from ..errores import NoEncontradoError

router = APIRouter(prefix="/notificaciones", tags=["Notificaciones"])


@router.get("")
def mis_notificaciones(
    solo_no_leidas: bool = False,
    limite: int = Query(50, ge=1, le=200),
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Consulta la bandeja de notificaciones del usuario autenticado."""
    filtro = " AND leida = FALSE" if solo_no_leidas else ""
    notificaciones = todos(
        db,
        "SELECT id_notificacion, tipo, id_solicitud, id_mensaje, texto, leida, fecha "
        f"FROM notificacion WHERE id_usuario = %s{filtro} ORDER BY id_notificacion DESC LIMIT %s",
        (usuario["id_usuario"], limite),
    )
    no_leidas = uno(
        db,
        "SELECT COUNT(*) AS total FROM notificacion WHERE id_usuario = %s AND leida = FALSE",
        (usuario["id_usuario"],),
    )["total"]

    return {
        "no_leidas": no_leidas,
        "total_obtenidas": len(notificaciones),
        "notificaciones": notificaciones,
    }


@router.post("/leer-todas")
def marcar_todas_leidas(usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Marca todas las notificaciones pendientes del usuario como leídas."""
    marcadas = actualizar(
        db,
        "UPDATE notificacion SET leida = TRUE WHERE id_usuario = %s AND leida = FALSE",
        (usuario["id_usuario"],),
    )
    db.commit()
    return {"marcadas": marcadas}


@router.post("/{id_notificacion}/leer")
def marcar_como_leida(
    id_notificacion: int,
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Marca una notificación específica como leída validando que pertenezca al usuario."""
    notif = uno(
        db,
        "SELECT id_notificacion FROM notificacion WHERE id_notificacion = %s AND id_usuario = %s",
        (id_notificacion, usuario["id_usuario"]),
    )
    if not notif:
        raise NoEncontradoError("La notificación no existe o no pertenece a tu cuenta")

    actualizar(
        db,
        "UPDATE notificacion SET leida = TRUE WHERE id_notificacion = %s",
        (id_notificacion,),
    )
    db.commit()
    return {"id_notificacion": id_notificacion, "leida": True}
