"""Módulo de Pagos: cobro con PaymentGateway (simulada), comisión configurable y reembolsos."""
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from .. import config
from ..db import get_db, insertar, uno
from ..deps import solo_cliente, usuario_actual
from ..errores import AccesoDenegadoError, AppError, ConflictoError, NoEncontradoError
from ..integraciones import payment_service
from ..utils import cargar_solicitud_de, notificar

router = APIRouter(prefix="/solicitudes/{id_solicitud}/pago", tags=["Pagos"])

_CENTAVOS = Decimal("0.01")


class PagoIn(BaseModel):
    metodo_pago: Literal["tarjeta", "transferencia", "mercado_pago", "efectivo"]
    simular_fallo: bool = False  # bandera para testing del caso "pago rechazado"


@router.post("", status_code=201)
def registrar_pago(
    id_solicitud: int,
    datos: PagoIn,
    usuario=Depends(solo_cliente),
    db=Depends(get_db),
):
    """El cliente abona el servicio contratado a través de la pasarela de pagos.
    Calcula la comisión configurable de la plataforma e interactúa con PaymentGateway.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_cliente"]:
        raise AccesoDenegadoError("Solo el cliente que solicitó el servicio puede efectuar el pago")

    # Validación del momento del cobro según configuración
    momento = config.MOMENTO_PAGO
    estado = solicitud["estado"]

    if momento == "al_finalizar" and estado != "finalizada":
        raise ConflictoError("La plataforma está configurada para cobrar el servicio al finalizar el trabajo")
    elif momento == "al_aceptar" and estado != "aceptada":
        raise ConflictoError("La plataforma está configurada para cobrar el servicio una vez aceptada la solicitud")
    elif momento == "flexible" and estado not in ("aceptada", "en_curso", "finalizada"):
        raise ConflictoError(
            f"No es posible registrar el pago para una solicitud en estado '{estado}'"
        )

    # Evitar pagos duplicados para la misma solicitud
    pago_previo = uno(
        db,
        "SELECT id_pago, estado FROM pago WHERE id_solicitud = %s",
        (id_solicitud,),
    )
    if pago_previo and pago_previo["estado"] == "completado":
        raise ConflictoError("Esta solicitud ya cuenta con un pago completado registrado")

    monto = (solicitud["tarifa"] * solicitud["duracion_horas"]).quantize(_CENTAVOS)
    comision = (monto * config.COMISION_PLATAFORMA).quantize(_CENTAVOS)

    # Cobro a través de la pasarela desacoplada
    resultado = payment_service.cobrar(datos.metodo_pago, monto, datos.simular_fallo)
    if not resultado["aprobado"]:
        raise AppError(
            status_code=402,
            codigo="PAGO_RECHAZADO",
            mensaje=resultado["motivo"],
        )

    id_pago = insertar(
        db,
        "INSERT INTO pago (id_solicitud, monto, comision_plataforma, metodo_pago, estado) "
        "VALUES (%s, %s, %s, %s, 'completado')",
        (id_solicitud, monto, comision, datos.metodo_pago),
    )

    notificar(
        db,
        solicitud["id_prestador"],
        "pago",
        f"Se acreditó un pago de ${monto} por el servicio de {solicitud['servicio']}",
        id_solicitud,
    )
    db.commit()

    return {
        "id_pago": id_pago,
        "id_solicitud": id_solicitud,
        "monto": monto,
        "comision_plataforma": comision,
        "neto_prestador": monto - comision,
        "metodo_pago": datos.metodo_pago,
        "referencia": resultado["referencia"],
        "estado": "completado",
    }


@router.get("")
def ver_pago(id_solicitud: int, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Consulta la información del pago registrado para una solicitud dada."""
    cargar_solicitud_de(db, id_solicitud, usuario, permitir_admin=True)
    pago = uno(
        db,
        "SELECT id_pago, id_solicitud, monto, comision_plataforma, metodo_pago, estado, fecha "
        "FROM pago WHERE id_solicitud = %s",
        (id_solicitud,),
    )
    if not pago:
        raise NoEncontradoError("Esta solicitud todavía no registra ningún pago")
    return pago
