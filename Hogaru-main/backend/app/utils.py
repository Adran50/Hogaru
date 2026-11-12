"""Funciones compartidas entre los módulos de Hogaru API."""
from .db import insertar, uno
from .errores import AccesoDenegadoError, NoEncontradoError
from .integraciones import notification_sender

# Consulta base de una solicitud con todos los datos requeridos por los clientes
SQL_SOLICITUD_BASE = """
SELECT sc.id_solicitud, sc.id_cliente, sc.id_servicio, sc.fecha_hora_programada,
       sc.duracion_horas, sc.direccion_trabajo, sc.estado, sc.fecha_creacion,
       so.id_prestador, so.tarifa,
       cs.nombre AS servicio,
       ROUND(so.tarifa * sc.duracion_horas, 2) AS monto_estimado,
       pa.estado AS pago_estado,
       CONCAT(uc.nombre, ' ', LEFT(uc.apellido, 1), '.') AS cliente,
       CONCAT(up.nombre, ' ', LEFT(up.apellido, 1), '.') AS prestador
FROM solicitud_contratacion sc
JOIN servicio_ofrecido so ON so.id_servicio  = sc.id_servicio
JOIN categoria_servicio cs ON cs.id_categoria = so.id_categoria
JOIN usuario uc ON uc.id_usuario = sc.id_cliente
JOIN usuario up ON up.id_usuario = so.id_prestador
LEFT JOIN pago pa ON pa.id_solicitud = sc.id_solicitud
"""


def nombre_publico(nombre: str, apellido: str) -> str:
    """'Marisa Gómez' -> 'Marisa G.' (resguardo de privacidad)."""
    return f"{nombre} {apellido[:1]}."


def notificar(db, id_usuario: int, tipo: str, texto: str, id_solicitud: int | None = None):
    """Crea un registro de notificación persistente en la BD y despacha
    la notificación simulada mediante NotificationSender (consola/push/email).
    """
    insertar(
        db,
        "INSERT INTO notificacion (id_usuario, tipo, id_solicitud, texto) "
        "VALUES (%s, %s, %s, %s)",
        (id_usuario, tipo, id_solicitud, texto[:255]),
    )
    # Envío externo simulado
    notification_sender.enviar(
        destinatario=f"usuario_{id_usuario}",
        asunto=f"Hogaru - {tipo.upper()}",
        mensaje=texto,
    )


def cargar_solicitud(db, id_solicitud: int) -> dict:
    """Carga una solicitud por ID o lanza 404 NoEncontradoError."""
    solicitud = uno(db, SQL_SOLICITUD_BASE + " WHERE sc.id_solicitud = %s", (id_solicitud,))
    if not solicitud:
        raise NoEncontradoError("La solicitud no existe")
    return solicitud


def cargar_solicitud_de(db, id_solicitud: int, usuario: dict, permitir_admin: bool = False) -> dict:
    """Carga la solicitud y valida que el usuario sea el cliente, el prestador o un administrador."""
    solicitud = cargar_solicitud(db, id_solicitud)
    es_participante = usuario["id_usuario"] in (solicitud["id_cliente"], solicitud["id_prestador"])
    es_admin = permitir_admin and usuario["tipo_cuenta"] == "administrador"
    if not (es_participante or es_admin):
        raise AccesoDenegadoError("No tenés permiso para acceder o modificar esta solicitud")
    return solicitud


def contraparte(solicitud: dict, id_usuario: int) -> int:
    """Devuelve el ID del otro participante de la solicitud."""
    if id_usuario == solicitud["id_cliente"]:
        return solicitud["id_prestador"]
    return solicitud["id_cliente"]
