"""Módulo de Administración: verificación de prestadores, disputas y usuarios."""
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, todos, uno
from ..deps import solo_admin
from ..errores import ConflictoError, NoEncontradoError, ReglaNegocioError
from ..integraciones import background_check_service, payment_service
from ..utils import notificar
from .verificacion import recalcular_verificacion

router = APIRouter(prefix="/admin", tags=["Administración"])


# ---------- verificación de documentos ----------
class ResolverDocumentoIn(BaseModel):
    estado: Literal["aprobado", "rechazado"]
    motivo: str | None = Field(None, max_length=1000, description="Motivo del rechazo o nota de aprobación")


@router.get("/documentos")
def listar_documentos(
    estado: Literal["pendiente", "aprobado", "rechazado"] = "pendiente",
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    """Cola de documentos para revisión por parte de un administrador.
    Incluye prechequeo automatizado para antecedentes penales.
    """
    documentos = todos(
        db,
        "SELECT d.id_documento, d.id_prestador, CONCAT(u.nombre, ' ', u.apellido) AS prestador, "
        "       d.tipo_documento, d.archivo_url, d.estado, d.fecha_carga, d.fecha_revision "
        "FROM documentacion_verificacion d "
        "JOIN usuario u ON u.id_usuario = d.id_prestador "
        "WHERE d.estado = %s ORDER BY d.id_documento",
        (estado,),
    )
    for d in documentos:
        if d["tipo_documento"] == "antecedentes_penales":
            d["prechequeo"] = background_check_service.verificar_antecedentes(d["archivo_url"])
    return documentos


@router.post("/documentos/{id_documento}/resolver")
def resolver_documento(
    id_documento: int,
    datos: ResolverDocumentoIn,
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    """Aprueba o rechaza un documento y recalcula el estado general de verificación del prestador."""
    doc = uno(
        db,
        "SELECT id_prestador, estado, tipo_documento FROM documentacion_verificacion WHERE id_documento = %s",
        (id_documento,),
    )
    if not doc:
        raise NoEncontradoError("El documento no existe")
    if doc["estado"] != "pendiente":
        raise ConflictoError("Ese documento ya fue revisado con anterioridad")

    actualizar(
        db,
        "UPDATE documentacion_verificacion SET estado = %s, id_admin = %s, fecha_revision = NOW() "
        "WHERE id_documento = %s",
        (datos.estado, admin["id_usuario"], id_documento),
    )
    nuevo_estado = recalcular_verificacion(db, doc["id_prestador"])

    motivo_texto = f" (Motivo: {datos.motivo})" if datos.motivo else ""
    textos = {
        "aprobado": "¡Tu cuenta fue verificada y aprobada! Ya podés publicar servicios.",
        "rechazado": f"Uno de tus documentos fue rechazado{motivo_texto}. Por favor, volvé a cargarlo.",
        "pendiente": f"Revisamos tu documento '{doc['tipo_documento']}'. Aún quedan requisitos pendientes.",
    }
    texto_notif = textos.get(nuevo_estado, "Estado de documentación actualizado.")
    notificar(db, doc["id_prestador"], "cambio_estado", texto_notif)
    db.commit()

    return {
        "id_documento": id_documento,
        "estado": datos.estado,
        "motivo": datos.motivo,
        "estado_verificacion_prestador": nuevo_estado,
    }


# ---------- disputas ----------
class ResolverDisputaIn(BaseModel):
    estado: Literal["en_revision", "resuelta"]
    resolucion: str | None = Field(None, max_length=2000)
    reembolsar: bool = False


@router.get("/disputas")
def disputas(
    estado: Literal["abierta", "en_revision", "resuelta"] | None = None,
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    filtro, params = ("WHERE d.estado = %s", (estado,)) if estado else ("", ())
    return todos(
        db,
        "SELECT d.id_disputa, d.id_solicitud, d.motivo, d.estado, d.resolucion, d.fecha_apertura, d.fecha_cierre "
        f"FROM disputa d {filtro} ORDER BY d.id_disputa",
        params,
    )


@router.patch("/disputas/{id_disputa}")
def gestionar_disputa(
    id_disputa: int,
    datos: ResolverDisputaIn,
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    """Pasa una disputa a estado 'en_revision' o la cierra como 'resuelta' (con resolución obligatoria).
    Opcionalmente dispara el reembolso del pago asociado.
    """
    disputa = uno(
        db,
        "SELECT d.id_disputa, d.id_solicitud, d.estado, sc.id_cliente, so.id_prestador "
        "FROM disputa d "
        "JOIN solicitud_contratacion sc ON sc.id_solicitud = d.id_solicitud "
        "JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio "
        "WHERE d.id_disputa = %s",
        (id_disputa,),
    )
    if not disputa:
        raise NoEncontradoError("La disputa no existe")
    if disputa["estado"] == "resuelta":
        raise ConflictoError("La disputa ya se encuentra resuelta y cerrada")

    if datos.estado == "resuelta" and not datos.resolucion:
        raise ReglaNegocioError("Para resolver una disputa es obligatorio consignar la resolución")

    if datos.estado == "resuelta":
        actualizar(
            db,
            "UPDATE disputa SET estado = 'resuelta', resolucion = %s, id_admin = %s, fecha_cierre = NOW() "
            "WHERE id_disputa = %s",
            (datos.resolucion, admin["id_usuario"], id_disputa),
        )
    else:
        actualizar(
            db,
            "UPDATE disputa SET estado = 'en_revision', id_admin = %s WHERE id_disputa = %s",
            (admin["id_usuario"], id_disputa),
        )

    reembolsado = False
    if datos.reembolsar:
        pago_existente = uno(
            db,
            "SELECT id_pago, monto FROM pago WHERE id_solicitud = %s AND estado = 'completado'",
            (disputa["id_solicitud"],),
        )
        if pago_existente:
            # Invocar formalmente la pasarela de pagos desacoplada para el reembolso
            payment_service.reembolsar(f"PAGO-{pago_existente['id_pago']}", pago_existente["monto"])
            reembolsado = bool(
                actualizar(
                    db,
                    "UPDATE pago SET estado = 'reembolsado' WHERE id_pago = %s",
                    (pago_existente["id_pago"],),
                )
            )

    texto = "Tu reclamo fue resuelto" if datos.estado == "resuelta" else "Tu reclamo fue puesto en revisión"
    for dest in (disputa["id_cliente"], disputa["id_prestador"]):
        notificar(db, dest, "disputa", texto, disputa["id_solicitud"])

    db.commit()
    return {"id_disputa": id_disputa, "estado": datos.estado, "pago_reembolsado": reembolsado}


# ---------- gestión de usuarios ----------
class EstadoUsuarioIn(BaseModel):
    estado: Literal["activo", "suspendido"]


@router.get("/usuarios")
def usuarios(
    tipo_cuenta: Literal["cliente", "prestador", "administrador"] | None = None,
    limite: int = Query(100, ge=1, le=500),
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    filtro, params = ("WHERE tipo_cuenta = %s", [tipo_cuenta]) if tipo_cuenta else ("", [])
    return todos(
        db,
        f"SELECT id_usuario, nombre, apellido, email, tipo_cuenta, estado, fecha_registro "
        f"FROM usuario {filtro} ORDER BY id_usuario LIMIT %s",
        params + [limite],
    )


@router.patch("/usuarios/{id_usuario}/estado")
def cambiar_estado_usuario(
    id_usuario: int,
    datos: EstadoUsuarioIn,
    admin=Depends(solo_admin),
    db=Depends(get_db),
):
    """Suspende o reactiva la cuenta de un usuario."""
    if id_usuario == admin["id_usuario"]:
        raise ReglaNegocioError("No podés modificar el estado de tu propia cuenta de administrador")

    filas = actualizar(
        db,
        "UPDATE usuario SET estado = %s WHERE id_usuario = %s",
        (datos.estado, id_usuario),
    )
    if not filas and not uno(db, "SELECT 1 FROM usuario WHERE id_usuario = %s", (id_usuario,)):
        raise NoEncontradoError("El usuario no existe")

    db.commit()
    return {"id_usuario": id_usuario, "estado": datos.estado}


# ---------- métricas globales de la plataforma ----------
@router.get("/metricas")
def metricas_plataforma(admin=Depends(solo_admin), db=Depends(get_db)):
    """Métricas globales para el panel de administración:
    - Cantidad de solicitudes desglosadas por estado
    - Ingresos por comisión acumulados y volumen total facturado
    - Distribución de usuarios por rol y prestadores por estado de verificación
    """
    solicitudes_por_estado = todos(
        db,
        "SELECT estado, COUNT(*) AS cantidad FROM solicitud_contratacion GROUP BY estado",
    )
    resumen_solicitudes = {fila["estado"]: fila["cantidad"] for fila in solicitudes_por_estado}
    for est in ("pendiente", "aceptada", "en_curso", "finalizada", "cancelada"):
        resumen_solicitudes.setdefault(est, 0)

    finanzas = uno(
        db,
        "SELECT COALESCE(SUM(monto), 0) AS total_pagos, "
        "       COALESCE(SUM(comision_plataforma), 0) AS ingresos_comision, "
        "       COUNT(*) AS total_transacciones "
        "FROM pago WHERE estado = 'completado'",
    )

    reembolsos = uno(
        db,
        "SELECT COALESCE(SUM(monto), 0) AS total_reembolsado, "
        "       COUNT(*) AS transacciones_reembolsadas "
        "FROM pago WHERE estado = 'reembolsado'",
    )

    usuarios_por_tipo = todos(
        db,
        "SELECT tipo_cuenta, estado, COUNT(*) AS cantidad FROM usuario GROUP BY tipo_cuenta, estado",
    )

    prestadores_verif = todos(
        db,
        "SELECT estado_verificacion, COUNT(*) AS cantidad FROM prestador GROUP BY estado_verificacion",
    )

    return {
        "solicitudes_por_estado": resumen_solicitudes,
        "finanzas": {
            "ingresos_comision": float(finanzas["ingresos_comision"]),
            "volumen_total_procesado": float(finanzas["total_pagos"]),
            "transacciones_completadas": finanzas["total_transacciones"],
            "total_reembolsado": float(reembolsos["total_reembolsado"]),
            "transacciones_reembolsadas": reembolsos["transacciones_reembolsadas"],
        },
        "usuarios": usuarios_por_tipo,
        "prestadores_verificacion": {
            fila["estado_verificacion"]: fila["cantidad"] for fila in prestadores_verif
        },
    }
