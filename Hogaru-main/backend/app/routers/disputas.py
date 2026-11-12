"""Módulo de Disputas: apertura de reclamos por clientes o prestadores y consulta de estado."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import get_db, insertar, todos
from ..deps import usuario_actual
from ..errores import AccesoDenegadoError, ConflictoError
from ..utils import cargar_solicitud_de, contraparte, notificar

router = APIRouter(prefix="/solicitudes/{id_solicitud}/disputas", tags=["Disputas y Mediación"])


class DisputaIn(BaseModel):
    motivo: str = Field(min_length=10, max_length=2000, description="Motivo detallado del reclamo")


@router.post("", status_code=201)
def abrir_disputa(
    id_solicitud: int,
    datos: DisputaIn,
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """El cliente o prestador involucrado abre un reclamo formal sobre la solicitud.
    No es posible reclamar sobre solicitudes que aún están en estado 'pendiente'.
    """
    if usuario["tipo_cuenta"] not in ("cliente", "prestador"):
        raise AccesoDenegadoError("Solo los clientes o prestadores participantes pueden abrir disputas")

    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if solicitud["estado"] == "pendiente":
        raise ConflictoError("No se puede iniciar un reclamo sobre una solicitud que aún no ha sido aceptada")

    id_disputa = insertar(
        db,
        "INSERT INTO disputa (id_solicitud, motivo, estado) VALUES (%s, %s, 'abierta')",
        (id_solicitud, datos.motivo),
    )

    otro_usuario = contraparte(solicitud, usuario["id_usuario"])
    notificar(
        db,
        otro_usuario,
        "disputa",
        f"Se abrió un reclamo sobre el servicio de {solicitud['servicio']}",
        id_solicitud,
    )
    db.commit()

    return {
        "id_disputa": id_disputa,
        "id_solicitud": id_solicitud,
        "motivo": datos.motivo,
        "estado": "abierta",
    }


@router.get("")
def ver_disputas(id_solicitud: int, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Lista las disputas asociadas a una solicitud (visible para las partes y el admin)."""
    cargar_solicitud_de(db, id_solicitud, usuario, permitir_admin=True)
    return todos(
        db,
        "SELECT id_disputa, id_solicitud, id_admin, motivo, estado, resolucion, fecha_apertura, fecha_cierre "
        "FROM disputa WHERE id_solicitud = %s ORDER BY id_disputa",
        (id_solicitud,),
    )
