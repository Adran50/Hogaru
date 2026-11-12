"""Módulo de Calificaciones: reputación, puntuación multidimensional y recálculo de promedio."""
from decimal import Decimal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import solo_cliente
from ..errores import AccesoDenegadoError, ConflictoError, NoEncontradoError
from ..utils import cargar_solicitud_de, notificar

router = APIRouter(tags=["Calificaciones"])


class CalificacionIn(BaseModel):
    puntuacion_puntualidad: int = Field(ge=1, le=5, description="Puntualidad del prestador (1 a 5)")
    puntuacion_prolijidad: int = Field(ge=1, le=5, description="Prolijidad del trabajo realizado (1 a 5)")
    puntuacion_trato: int = Field(ge=1, le=5, description="Trato y comunicación (1 a 5)")
    comentario: str | None = Field(None, max_length=1000, description="Comentario o reseña del cliente")


def recalcular_promedio_prestador(db, id_prestador: int) -> Decimal:
    """Calcula y persiste el nuevo promedio general del prestador en la capa de servicio."""
    fila = uno(
        db,
        "SELECT ROUND(AVG((c.puntuacion_puntualidad + c.puntuacion_prolijidad + c.puntuacion_trato) / 3.0), 2) AS promedio "
        "FROM calificacion c "
        "JOIN solicitud_contratacion sc ON sc.id_solicitud = c.id_solicitud "
        "JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio "
        "WHERE so.id_prestador = %s",
        (id_prestador,),
    )
    nuevo_promedio = fila["promedio"] if fila and fila["promedio"] is not None else Decimal("0.00")
    actualizar(
        db,
        "UPDATE prestador SET puntuacion_promedio = %s WHERE id_prestador = %s",
        (nuevo_promedio, id_prestador),
    )
    return nuevo_promedio


@router.post("/solicitudes/{id_solicitud}/calificacion", status_code=201)
def calificar_servicio(
    id_solicitud: int,
    datos: CalificacionIn,
    usuario=Depends(solo_cliente),
    db=Depends(get_db),
):
    """El cliente califica un servicio finalizado y pagado (una única vez).
    Recalcula la puntuación promedio del prestador en la capa de servicio.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_cliente"]:
        raise AccesoDenegadoError("Solo el cliente de la solicitud puede registrar la calificación")

    # Regla: solo solicitudes finalizadas
    if solicitud["estado"] != "finalizada":
        raise ConflictoError("Solo es posible calificar servicios que se encuentren en estado 'finalizada'")

    # Regla: solicitud debe contar con pago completado
    pago = uno(
        db,
        "SELECT estado FROM pago WHERE id_solicitud = %s",
        (id_solicitud,),
    )
    if not pago or pago["estado"] != "completado":
        raise ConflictoError("La solicitud debe estar debidamente pagada para poder calificarla")

    # Regla: calificar solo una vez por solicitud
    if uno(db, "SELECT 1 FROM calificacion WHERE id_solicitud = %s", (id_solicitud,)):
        raise ConflictoError("Esta solicitud ya ha sido calificada previamente")

    id_calificacion = insertar(
        db,
        "INSERT INTO calificacion (id_solicitud, puntuacion_puntualidad, puntuacion_prolijidad, "
        "puntuacion_trato, comentario) VALUES (%s, %s, %s, %s, %s)",
        (id_solicitud, datos.puntuacion_puntualidad, datos.puntuacion_prolijidad,
         datos.puntuacion_trato, datos.comentario),
    )

    # Recálculo explícito de la reputación del prestador en la capa de servicio
    nuevo_promedio = recalcular_promedio_prestador(db, solicitud["id_prestador"])

    notificar(
        db,
        solicitud["id_prestador"],
        "cambio_estado",
        f"Recibiste una nueva calificación por el servicio de {solicitud['servicio']}",
        id_solicitud,
    )
    db.commit()

    return {
        "id_calificacion": id_calificacion,
        "id_solicitud": id_solicitud,
        "puntuacion_promedio_prestador": float(nuevo_promedio),
    }


@router.get("/prestadores/{id_prestador}/calificaciones")
def ver_calificaciones_prestador(id_prestador: int, db=Depends(get_db)):
    """Reputación pública de un prestador: desglose por categoría y lista de reseñas."""
    prestador = uno(
        db,
        "SELECT p.id_prestador, CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS nombre_publico, "
        "       p.puntuacion_promedio "
        "FROM prestador p "
        "JOIN usuario u ON u.id_usuario = p.id_prestador "
        "WHERE p.id_prestador = %s",
        (id_prestador,),
    )
    if not prestador:
        raise NoEncontradoError("El prestador no existe")

    base_from = (
        "FROM calificacion c "
        "JOIN solicitud_contratacion sc ON sc.id_solicitud = c.id_solicitud "
        "JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio "
        "WHERE so.id_prestador = %s"
    )

    promedios = uno(
        db,
        "SELECT COUNT(*) AS total, "
        "ROUND(AVG(c.puntuacion_puntualidad), 2) AS puntualidad, "
        "ROUND(AVG(c.puntuacion_prolijidad), 2) AS prolijidad, "
        "ROUND(AVG(c.puntuacion_trato), 2) AS trato " + base_from,
        (id_prestador,),
    )

    resenas = todos(
        db,
        "SELECT c.puntuacion_puntualidad, c.puntuacion_prolijidad, c.puntuacion_trato, "
        "       c.comentario, c.fecha, CONCAT(uc.nombre, ' ', LEFT(uc.apellido, 1), '.') AS cliente "
        + base_from.replace("WHERE", "JOIN usuario uc ON uc.id_usuario = sc.id_cliente WHERE")
        + " ORDER BY c.fecha DESC LIMIT 50",
        (id_prestador,),
    )

    return {
        "prestador": prestador,
        "promedios": promedios,
        "calificaciones": resenas,
    }
