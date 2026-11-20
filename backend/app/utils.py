"""Funciones compartidas entre los módulos de Hogaru API."""
from .db import insertar, uno
from .errores import AccesoDenegadoError, NoEncontradoError
from .integraciones import notification_sender

# Consulta base de una solicitud con todos los datos requeridos por los clientes
SQL_SOLICITUD_BASE = """
SELECT sc.id_solicitud, sc.id_cliente, sc.id_servicio, sc.fecha_hora_programada,
       sc.duracion_horas, sc.direccion_trabajo, sc.estado, sc.id_anuncio, sc.fecha_creacion,
       so.id_prestador, so.tarifa,
       cs.nombre AS servicio,
       ROUND(so.tarifa * sc.duracion_horas, 2) AS monto_estimado,
       pa.estado AS pago_estado,
       CONCAT(uc.nombre, ' ', LEFT(uc.apellido, 1), '.') AS cliente,
       CONCAT(up.nombre, ' ', LEFT(up.apellido, 1), '.') AS prestador,
       uc.telefono AS cliente_telefono,
       up.telefono AS prestador_telefono
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
        raise NoEncontradoError("La solicitud de contratación no existe")
    return solicitud


def cargar_solicitud_de(db, id_solicitud: int, usuario, permitir_admin: bool = False) -> dict:
    """Carga una solicitud asegurando que el usuario logueado sea el cliente o el prestador (o admin si permitir_admin=True)."""
    solicitud = cargar_solicitud(db, id_solicitud)
    id_usuario = usuario["id_usuario"] if isinstance(usuario, dict) else int(usuario)
    es_admin = isinstance(usuario, dict) and usuario.get("tipo_cuenta") == "administrador"
    if permitir_admin and es_admin:
        return solicitud
    if solicitud["id_cliente"] != id_usuario and solicitud["id_prestador"] != id_usuario:
        raise AccesoDenegadoError("No tenés acceso a esta solicitud")
    return solicitud


def contraparte(solicitud: dict, id_usuario: int) -> int:
    """Dado un usuario (cliente o prestador), devuelve el ID de la otra parte."""
    if solicitud["id_cliente"] == id_usuario:
        return solicitud["id_prestador"]
    if solicitud["id_prestador"] == id_usuario:
        return solicitud["id_cliente"]
    raise AccesoDenegadoError("No participás de esta solicitud")
