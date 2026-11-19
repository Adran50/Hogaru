"""Módulo de Contratación: solicitud, aceptación, agenda y máquina de estados estricta.

Transiciones válidas:
    - pendiente -> aceptada | cancelada
    - aceptada  -> en_curso | cancelada
    - en_curso  -> finalizada
Cualquier otra transición devuelve HTTP 409 CONFLICTO.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import requiere, solo_cliente, solo_prestador, usuario_actual
from ..errores import AccesoDenegadoError, ConflictoError, NoEncontradoError, ReglaNegocioError
from ..utils import (SQL_SOLICITUD_BASE, cargar_solicitud, cargar_solicitud_de,
                      contraparte, notificar)

router = APIRouter(prefix="/solicitudes", tags=["Contratación de Servicios"])


class SolicitudIn(BaseModel):
    id_servicio: int
    fecha_hora_programada: datetime
    duracion_horas: Decimal = Field(gt=0, le=12, max_digits=4, decimal_places=2)
    direccion_trabajo: str | None = Field(
        None, max_length=200, description="Dirección del trabajo (si se omite, usa la del perfil)"
    )


def validar_disponibilidad(db, id_servicio: int, inicio: datetime, horas: Decimal):
    """Verifica que el turno solicitado quepa dentro de una franja disponible del servicio."""
    inicio_td = timedelta(hours=inicio.hour, minutes=inicio.minute, seconds=inicio.second)
    fin_td = inicio_td + timedelta(hours=float(horas))
    dia_semana = inicio.isoweekday()  # 1 = lunes ... 7 = domingo

    franjas = todos(
        db,
        "SELECT hora_inicio, hora_fin FROM disponibilidad WHERE id_servicio = %s AND dia_semana = %s",
        (id_servicio, dia_semana),
    )
    if not franjas:
        raise ReglaNegocioError("El prestador no atiende en el día de la semana solicitado")

    # PyMySQL devuelve las columnas TIME como timedelta
    cabe = any(f["hora_inicio"] <= inicio_td and fin_td <= f["hora_fin"] for f in franjas)
    if not cabe:
        raise ReglaNegocioError("El turno solicitado queda fuera del horario de disponibilidad del servicio")


def validar_sin_conflictos(db, id_prestador: int, inicio: datetime, horas: Decimal, excluir: int = 0):
    """Verifica que el prestador no tenga otro turno confirmado (aceptada o en_curso) que se solape."""
    fin = inicio + timedelta(hours=float(horas))
    choque = uno(
        db,
        "SELECT sc.id_solicitud FROM solicitud_contratacion sc "
        "JOIN servicio_ofrecido so ON so.id_servicio = sc.id_servicio "
        "WHERE so.id_prestador = %s AND sc.estado IN ('aceptada', 'en_curso') "
        "  AND sc.id_solicitud <> %s "
        "  AND sc.fecha_hora_programada < %s "
        "  AND DATE_ADD(sc.fecha_hora_programada, INTERVAL ROUND(sc.duracion_horas * 60) MINUTE) > %s",
        (id_prestador, excluir, fin, inicio),
    )
    if choque:
        raise ConflictoError("El prestador ya tiene otro turno confirmado o en curso en esa franja horaria")


@router.post("", status_code=201)
def crear_solicitud(datos: SolicitudIn, usuario=Depends(solo_cliente), db=Depends(get_db)):
    """El cliente crea una solicitud de servicio en estado 'pendiente'."""
    servicio = uno(
        db,
        "SELECT so.id_servicio, so.id_prestador, p.estado_verificacion, u.estado AS estado_usuario "
        "FROM servicio_ofrecido so "
        "JOIN prestador p ON p.id_prestador = so.id_prestador "
        "JOIN usuario u   ON u.id_usuario   = so.id_prestador "
        "WHERE so.id_servicio = %s AND so.activo = TRUE",
        (datos.id_servicio,),
    )
    if not servicio or servicio["estado_usuario"] != "activo":
        raise NoEncontradoError("El servicio solicitado no existe o no se encuentra activo")

    # Validación de prestador aprobado
    if servicio["estado_verificacion"] != "aprobado":
        raise ReglaNegocioError("El prestador del servicio no cuenta con verificación aprobada")

    inicio = datos.fecha_hora_programada.replace(tzinfo=None)
    if inicio <= datetime.now():
        raise ReglaNegocioError("La fecha y hora del turno debe ser estrictamente futura")

    validar_disponibilidad(db, datos.id_servicio, inicio, datos.duracion_horas)

    direccion = datos.direccion_trabajo
    if not direccion:
        cliente_perfil = uno(
            db, "SELECT direccion FROM cliente WHERE id_cliente = %s", (usuario["id_usuario"],)
        )
        direccion = cliente_perfil["direccion"] if cliente_perfil else None

    if not direccion:
        raise ReglaNegocioError("Debe indicar la dirección de trabajo o registrar una en su perfil")

    id_solicitud = insertar(
        db,
        "INSERT INTO solicitud_contratacion "
        "(id_cliente, id_servicio, fecha_hora_programada, duracion_horas, direccion_trabajo, estado) "
        "VALUES (%s, %s, %s, %s, %s, 'pendiente')",
        (usuario["id_usuario"], datos.id_servicio, inicio, datos.duracion_horas, direccion),
    )
    db.commit()
    return cargar_solicitud(db, id_solicitud)


@router.get("")
def listar_solicitudes(
    estado: Literal["pendiente", "aceptada", "en_curso", "finalizada", "cancelada"] | None = None,
    limite: int = Query(50, ge=1, le=200),
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """Lista las solicitudes del usuario actual (o todas si es administrador)."""
    condiciones, params = ["1 = 1"], []
    if usuario["tipo_cuenta"] == "cliente":
        condiciones.append("sc.id_cliente = %s")
        params.append(usuario["id_usuario"])
    elif usuario["tipo_cuenta"] == "prestador":
        condiciones.append("so.id_prestador = %s")
        params.append(usuario["id_usuario"])

    if estado:
        condiciones.append("sc.estado = %s")
        params.append(estado)

    return todos(
        db,
        SQL_SOLICITUD_BASE + f" WHERE {' AND '.join(condiciones)} "
        "ORDER BY sc.fecha_hora_programada DESC LIMIT %s",
        params + [limite],
    )


@router.get("/{id_solicitud}")
def ver_solicitud(id_solicitud: int, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Detalle completo de la solicitud con calificación asociada si existe."""
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario, permitir_admin=True)
    solicitud["calificacion"] = uno(
        db,
        "SELECT puntuacion_puntualidad, puntuacion_prolijidad, puntuacion_trato, comentario, fecha "
        "FROM calificacion WHERE id_solicitud = %s",
        (id_solicitud,),
    )
    return solicitud


# =====================================================
# TRANSICIONES DE LA MAQUINA DE ESTADOS
# =====================================================
@router.post("/{id_solicitud}/aceptar")
def aceptar_solicitud(id_solicitud: int, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Transición: pendiente -> aceptada.
    Solo el prestador asignado puede aceptar.
    Exige que el prestador esté en estado 'aprobado' y valida que no se solape con otro turno.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_prestador"]:
        raise AccesoDenegadoError("Solo el prestador del servicio puede aceptar esta solicitud")

    if solicitud["estado"] != "pendiente":
        raise ConflictoError(
            f"Transición inválida: la solicitud está '{solicitud['estado']}' y para aceptar debe estar 'pendiente'"
        )

    # Verificar estado de verificación del prestador
    p_info = uno(
        db, "SELECT estado_verificacion FROM prestador WHERE id_prestador = %s", (usuario["id_usuario"],)
    )
    if not p_info or p_info["estado_verificacion"] != "aprobado":
        raise AccesoDenegadoError("Tu cuenta de prestador debe estar aprobada para aceptar contrataciones")

    # Validar ausencia de conflictos en la agenda
    validar_sin_conflictos(
        db,
        solicitud["id_prestador"],
        solicitud["fecha_hora_programada"],
        solicitud["duracion_horas"],
        excluir=id_solicitud,
    )

    actualizar(db, "UPDATE solicitud_contratacion SET estado = 'aceptada' WHERE id_solicitud = %s", (id_solicitud,))
    notificar(
        db,
        solicitud["id_cliente"],
        "cambio_estado",
        f"Tu solicitud de {solicitud['servicio']} fue aceptada",
        id_solicitud,
    )
    db.commit()
    return cargar_solicitud(db, id_solicitud)


@router.post("/{id_solicitud}/rechazar")
def rechazar_solicitud(id_solicitud: int, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Transición: pendiente -> cancelada (por rechazo del prestador)."""
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_prestador"]:
        raise AccesoDenegadoError("Solo el prestador del servicio puede rechazar esta solicitud")

    if solicitud["estado"] != "pendiente":
        raise ConflictoError(
            f"Transición inválida: no se puede rechazar una solicitud en estado '{solicitud['estado']}'"
        )

    actualizar(db, "UPDATE solicitud_contratacion SET estado = 'cancelada' WHERE id_solicitud = %s", (id_solicitud,))
    notificar(
        db,
        solicitud["id_cliente"],
        "cambio_estado",
        f"El prestador no pudo aceptar tu solicitud de {solicitud['servicio']}",
        id_solicitud,
    )
    db.commit()
    return cargar_solicitud(db, id_solicitud)


@router.post("/{id_solicitud}/iniciar")
def iniciar_servicio(id_solicitud: int, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Transición: aceptada -> en_curso.
    Solo el prestador asignado puede iniciar el servicio.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_prestador"]:
        raise AccesoDenegadoError("Solo el prestador del servicio puede iniciar este trabajo")

    if solicitud["estado"] != "aceptada":
        raise ConflictoError(
            f"Transición inválida: la solicitud está '{solicitud['estado']}'; para iniciar debe estar 'aceptada'"
        )

    actualizar(db, "UPDATE solicitud_contratacion SET estado = 'en_curso' WHERE id_solicitud = %s", (id_solicitud,))
    notificar(
        db,
        solicitud["id_cliente"],
        "cambio_estado",
        f"El servicio de {solicitud['servicio']} ha comenzado",
        id_solicitud,
    )
    db.commit()
    return cargar_solicitud(db, id_solicitud)


@router.post("/{id_solicitud}/finalizar")
def finalizar_servicio(id_solicitud: int, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Transición: en_curso -> finalizada.
    Solo el prestador asignado puede marcar el servicio como finalizado.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario)
    if usuario["id_usuario"] != solicitud["id_prestador"]:
        raise AccesoDenegadoError("Solo el prestador del servicio puede finalizar este trabajo")

    if solicitud["estado"] != "en_curso":
        raise ConflictoError(
            f"Transición inválida: la solicitud está '{solicitud['estado']}'; para finalizar debe estar 'en_curso'"
        )

    actualizar(db, "UPDATE solicitud_contratacion SET estado = 'finalizada' WHERE id_solicitud = %s", (id_solicitud,))
    notificar(
        db,
        solicitud["id_cliente"],
        "cambio_estado",
        f"El servicio de {solicitud['servicio']} finalizó. ¡Ya podés calificarlo!",
        id_solicitud,
    )
    db.commit()
    return cargar_solicitud(db, id_solicitud)


@router.post("/{id_solicitud}/cancelar")
def cancelar_solicitud(
    id_solicitud: int,
    usuario=Depends(requiere("cliente", "prestador", "administrador")),
    db=Depends(get_db),
):
    """Transición: (pendiente | aceptada) -> cancelada.
    Puede cancelar el cliente o el prestador asignado (o el administrador).
    Si existía un pago completado, se reembolsa automáticamente.
    """
    solicitud = cargar_solicitud_de(db, id_solicitud, usuario, permitir_admin=True)
    if solicitud["estado"] not in ("pendiente", "aceptada"):
        raise ConflictoError(
            f"Transición inválida: no es posible cancelar una solicitud con estado '{solicitud['estado']}'"
        )

    actualizar(db, "UPDATE solicitud_contratacion SET estado = 'cancelada' WHERE id_solicitud = %s", (id_solicitud,))

    # Notificar a la contraparte si quien cancela no es admin
    if usuario["tipo_cuenta"] != "administrador":
        otro_usuario = contraparte(solicitud, usuario["id_usuario"])
        notificar(
            db,
            otro_usuario,
            "cambio_estado",
            f"La solicitud de {solicitud['servicio']} fue cancelada",
            id_solicitud,
        )

    # Reembolso automático si el pago ya estaba completado
    reembolsados = actualizar(
        db,
        "UPDATE pago SET estado = 'reembolsado' WHERE id_solicitud = %s AND estado = 'completado'",
        (id_solicitud,),
    )
    if reembolsados:
        notificar(
            db,
            solicitud["id_cliente"],
            "pago",
            "Tu pago fue reembolsado automáticamente debido a la cancelación",
            id_solicitud,
        )

    db.commit()
    return cargar_solicitud(db, id_solicitud)
