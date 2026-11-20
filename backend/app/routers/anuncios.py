"""Módulo de Anuncios / Marketplace Inverso:
Permite a los clientes publicar avisos de trabajo con presupuesto y fecha requerida,
y a los prestadores verificados postularse con cotizaciones personalizadas.
"""
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import solo_cliente, solo_prestador, usuario_actual
from ..errores import AccesoDenegadoError, NoEncontradoError, ReglaNegocioError
from ..utils import notificar

router = APIRouter(prefix="/anuncios", tags=["Anuncios y Bolsa de Trabajos"])


class AnuncioIn(BaseModel):
    id_categoria: int
    titulo: str = Field(..., min_length=5, max_length=120)
    descripcion: str = Field(..., min_length=10, max_length=2000)
    presupuesto: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2, description="Presupuesto ofrecido")
    fecha_servicio: datetime = Field(..., description="Fecha y hora requerida para la realización")
    duracion_horas: Decimal = Field(Decimal("1.0"), gt=0, max_digits=4, decimal_places=2)
    direccion: str = Field(..., min_length=3, max_length=200)


class PostulacionIn(BaseModel):
    propuesta_precio: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2, description="Precio total propuesto por el prestador")
    mensaje: str | None = Field(None, max_length=1000, description="Mensaje de presentación o detalle de lo incluido")


@router.post("", status_code=201)
def crear_anuncio(datos: AnuncioIn, cliente=Depends(solo_cliente), db=Depends(get_db)):
    """El cliente publica un nuevo anuncio solicitando un servicio."""
    categoria = uno(db, "SELECT id_categoria, estado FROM categoria_servicio WHERE id_categoria = %s", (datos.id_categoria,))
    if not categoria or categoria["estado"] != "activa":
        raise ReglaNegocioError("La categoría seleccionada no existe o no está activa.")

    fecha_limpia = datos.fecha_servicio.replace(tzinfo=None)
    if fecha_limpia <= datetime.now():
        raise ReglaNegocioError("La fecha del servicio debe ser futura.")

    id_cliente = cliente["id_usuario"]
    id_anuncio = insertar(
        db,
        "INSERT INTO anuncio_trabajo (id_cliente, id_categoria, titulo, descripcion, presupuesto, fecha_servicio, duracion_horas, direccion, estado) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'abierto')",
        (
            id_cliente,
            datos.id_categoria,
            datos.titulo.strip(),
            datos.descripcion.strip(),
            datos.presupuesto,
            fecha_limpia,
            datos.duracion_horas,
            datos.direccion.strip(),
        ),
    )
    db.commit()
    return {
        "id_anuncio": id_anuncio,
        "titulo": datos.titulo,
        "estado": "abierto",
        "mensaje": "Anuncio publicado exitosamente en la Bolsa de Trabajos.",
    }


@router.get("")
def listar_anuncios(
    categoria: int | None = Query(None, description="Filtrar por id_categoria"),
    q: str | None = Query(None, description="Búsqueda por texto en título o descripción"),
    db=Depends(get_db),
):
    """Lista todos los anuncios abiertos disponibles para postulación."""
    condiciones = ["a.estado = 'abierto'"]
    params = []

    if categoria is not None:
        condiciones.append("a.id_categoria = %s")
        params.append(categoria)

    if q and q.strip():
        condiciones.append("(a.titulo LIKE %s OR a.descripcion LIKE %s)")
        termino = f"%{q.strip()}%"
        params.extend([termino, termino])

    sql = f"""
        SELECT a.id_anuncio, a.id_cliente, a.id_categoria, a.titulo, a.descripcion,
               a.presupuesto, a.fecha_servicio, a.duracion_horas, a.direccion, a.estado, a.fecha_creacion,
               c.nombre AS categoria, COALESCE(c.icono, '🧹') AS icono,
               CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS cliente_nombre,
               u.foto_perfil AS cliente_foto,
               (SELECT COUNT(*) FROM postulacion_anuncio p WHERE p.id_anuncio = a.id_anuncio) AS total_postulaciones
        FROM anuncio_trabajo a
        JOIN categoria_servicio c ON c.id_categoria = a.id_categoria
        JOIN usuario u ON u.id_usuario = a.id_cliente
        WHERE {' AND '.join(condiciones)}
        ORDER BY a.fecha_creacion DESC
    """
    return todos(db, sql, tuple(params))


@router.get("/mis-anuncios")
def mis_anuncios(cliente=Depends(solo_cliente), db=Depends(get_db)):
    """Lista todos los anuncios publicados por el cliente autenticado."""
    id_cliente = cliente["id_usuario"]
    sql = """
        SELECT a.id_anuncio, a.id_categoria, a.titulo, a.descripcion, a.presupuesto,
               a.fecha_servicio, a.duracion_horas, a.direccion, a.estado, a.fecha_creacion,
               c.nombre AS categoria, COALESCE(c.icono, '🧹') AS icono,
               u.foto_perfil AS cliente_foto,
               (SELECT COUNT(*) FROM postulacion_anuncio p WHERE p.id_anuncio = a.id_anuncio) AS total_postulaciones
        FROM anuncio_trabajo a
        JOIN categoria_servicio c ON c.id_categoria = a.id_categoria
        JOIN usuario u ON u.id_usuario = a.id_cliente
        WHERE a.id_cliente = %s
        ORDER BY a.fecha_creacion DESC
    """
    return todos(db, sql, (id_cliente,))


@router.get("/{id_anuncio}")
def detalle_anuncio(id_anuncio: int, usuario=Depends(usuario_actual), db=Depends(get_db)):
    """Obtiene el detalle completo de un anuncio y el estado de postulación del usuario actual."""
    anuncio = uno(
        db,
        """
        SELECT a.id_anuncio, a.id_cliente, a.id_categoria, a.titulo, a.descripcion,
               a.presupuesto, a.fecha_servicio, a.duracion_horas, a.direccion, a.estado, a.fecha_creacion,
               c.nombre AS categoria, COALESCE(c.icono, '🧹') AS icono,
               CONCAT(u.nombre, ' ', LEFT(u.apellido, 1), '.') AS cliente_nombre,
               u.foto_perfil AS cliente_foto,
               (SELECT COUNT(*) FROM postulacion_anuncio p WHERE p.id_anuncio = a.id_anuncio) AS total_postulaciones
        FROM anuncio_trabajo a
        JOIN categoria_servicio c ON c.id_categoria = a.id_categoria
        JOIN usuario u ON u.id_usuario = a.id_cliente
        WHERE a.id_anuncio = %s
        """,
        (id_anuncio,),
    )
    if not anuncio:
        raise NoEncontradoError("El anuncio no existe.")

    # Si es prestador, verificar si ya se postuló
    mi_postulacion = None
    if usuario["tipo_cuenta"] == "prestador":
        mi_postulacion = uno(
            db,
            "SELECT id_postulacion, propuesta_precio, mensaje, estado, fecha_postulacion "
            "FROM postulacion_anuncio WHERE id_anuncio = %s AND id_prestador = %s",
            (id_anuncio, usuario["id_usuario"]),
        )

    anuncio["mi_postulacion"] = mi_postulacion
    anuncio["es_mio"] = (anuncio["id_cliente"] == usuario["id_usuario"])
    return anuncio


@router.post("/{id_anuncio}/postular", status_code=201)
def postular_a_anuncio(
    id_anuncio: int,
    datos: PostulacionIn,
    prestador=Depends(solo_prestador),
    db=Depends(get_db),
):
    """Un prestador verificado se postula a un anuncio abierto enviando su cotización."""
    id_prestador = prestador["id_usuario"]

    # Verificar que el prestador esté aprobado
    perfil = uno(db, "SELECT estado_verificacion FROM prestador WHERE id_prestador = %s", (id_prestador,))
    if not perfil or perfil["estado_verificacion"] != "aprobado":
        raise AccesoDenegadoError(
            "Debés tener tu cuenta verificada (DNI y antecedentes aprobados) para poder postularte a avisos de trabajo."
        )

    anuncio = uno(db, "SELECT id_anuncio, id_cliente, titulo, estado FROM anuncio_trabajo WHERE id_anuncio = %s", (id_anuncio,))
    if not anuncio:
        raise NoEncontradoError("El anuncio no existe.")

    if anuncio["estado"] != "abierto":
        raise ReglaNegocioError("Este anuncio ya no está abierto para recibir postulaciones.")

    if anuncio["id_cliente"] == id_prestador:
        raise ReglaNegocioError("No podés postularte a tu propio anuncio.")

    ya_postulado = uno(
        db,
        "SELECT id_postulacion FROM postulacion_anuncio WHERE id_anuncio = %s AND id_prestador = %s",
        (id_anuncio, id_prestador),
    )
    if ya_postulado:
        raise ReglaNegocioError("Ya enviaste una propuesta para este aviso de trabajo.")

    id_postulacion = insertar(
        db,
        "INSERT INTO postulacion_anuncio (id_anuncio, id_prestador, propuesta_precio, mensaje, estado) "
        "VALUES (%s, %s, %s, %s, 'pendiente')",
        (id_anuncio, id_prestador, datos.propuesta_precio, datos.mensaje),
    )

    notificar(
        db,
        anuncio["id_cliente"],
        "solicitud",
        f"Nueva postulación para tu aviso '{anuncio['titulo']}': cotización ${datos.propuesta_precio:,.2f}.",
    )
    db.commit()

    return {
        "id_postulacion": id_postulacion,
        "id_anuncio": id_anuncio,
        "propuesta_precio": datos.propuesta_precio,
        "estado": "pendiente",
        "mensaje": "¡Propuesta enviada con éxito al cliente!",
    }


@router.get("/{id_anuncio}/postulaciones")
def listar_postulaciones(
    id_anuncio: int,
    usuario=Depends(usuario_actual),
    db=Depends(get_db),
):
    """El cliente dueño del anuncio visualiza todas las ofertas recibidas."""
    anuncio = uno(db, "SELECT id_anuncio, id_cliente, titulo, estado FROM anuncio_trabajo WHERE id_anuncio = %s", (id_anuncio,))
    if not anuncio:
        raise NoEncontradoError("El anuncio no existe.")

    if anuncio["id_cliente"] != usuario["id_usuario"] and usuario["tipo_cuenta"] != "administrador":
        raise AccesoDenegadoError("Solo el cliente que publicó el aviso puede ver las postulaciones recibidas.")

    sql = """
        SELECT p.id_postulacion, p.id_anuncio, p.id_prestador, p.propuesta_precio, p.mensaje,
               p.estado, p.fecha_postulacion,
               u.nombre, u.apellido, u.telefono, u.email, u.foto_perfil,
               pr.puntuacion_promedio, pr.descripcion AS prestador_descripcion
        FROM postulacion_anuncio p
        JOIN usuario u ON u.id_usuario = p.id_prestador
        JOIN prestador pr ON pr.id_prestador = p.id_prestador
        WHERE p.id_anuncio = %s
        ORDER BY p.propuesta_precio ASC, pr.puntuacion_promedio DESC
    """
    return todos(db, sql, (id_anuncio,))


@router.post("/{id_anuncio}/adjudicar/{id_postulacion}")
def adjudicar_anuncio(
    id_anuncio: int,
    id_postulacion: int,
    cliente=Depends(solo_cliente),
    db=Depends(get_db),
):
    """El cliente adjudica el trabajo al prestador de la postulación seleccionada.
    Genera automáticamente la contratación formal y notifica al prestador.
    """
    id_cliente = cliente["id_usuario"]
    anuncio = uno(
        db,
        "SELECT id_anuncio, id_cliente, id_categoria, titulo, descripcion, fecha_servicio, duracion_horas, direccion, estado "
        "FROM anuncio_trabajo WHERE id_anuncio = %s",
        (id_anuncio,),
    )
    if not anuncio:
        raise NoEncontradoError("El anuncio no existe.")

    if anuncio["id_cliente"] != id_cliente:
        raise AccesoDenegadoError("Solo podés adjudicar tus propios anuncios.")

    if anuncio["estado"] != "abierto":
        raise ReglaNegocioError("Este anuncio ya fue adjudicado o cancelado.")

    postulacion = uno(
        db,
        "SELECT id_postulacion, id_prestador, propuesta_precio, estado "
        "FROM postulacion_anuncio WHERE id_postulacion = %s AND id_anuncio = %s",
        (id_postulacion, id_anuncio),
    )
    if not postulacion:
        raise NoEncontradoError("La postulación no corresponde a este anuncio.")

    id_prestador = postulacion["id_prestador"]

    # 1. Obtener o crear servicio ofrecido del prestador para esa categoría
    servicio = uno(
        db,
        "SELECT id_servicio FROM servicio_ofrecido WHERE id_prestador = %s AND id_categoria = %s LIMIT 1",
        (id_prestador, anuncio["id_categoria"]),
    )
    if servicio:
        id_servicio = servicio["id_servicio"]
    else:
        # Calcular tarifa horaria basada en el precio total acordado
        tarifa_hora = Decimal(postulacion["propuesta_precio"]) / Decimal(anuncio["duracion_horas"])
        id_servicio = insertar(
            db,
            "INSERT INTO servicio_ofrecido (id_prestador, id_categoria, descripcion, tarifa, activo) "
            "VALUES (%s, %s, %s, %s, TRUE)",
            (id_prestador, anuncio["id_categoria"], f"Servicio asignado por aviso: {anuncio['titulo']}", tarifa_hora),
        )

    # 2. Crear solicitud de contratación formal
    id_solicitud = insertar(
        db,
        "INSERT INTO solicitud_contratacion (id_cliente, id_servicio, fecha_hora_programada, duracion_horas, direccion_trabajo, estado, id_anuncio) "
        "VALUES (%s, %s, %s, %s, %s, 'aceptada', %s)",
        (
            id_cliente,
            id_servicio,
            anuncio["fecha_servicio"],
            anuncio["duracion_horas"],
            anuncio["direccion"],
            id_anuncio,
        ),
    )

    # 3. Actualizar estados del anuncio y de las postulaciones
    actualizar(db, "UPDATE anuncio_trabajo SET estado = 'adjudicado' WHERE id_anuncio = %s", (id_anuncio,))
    actualizar(db, "UPDATE postulacion_anuncio SET estado = 'aceptada' WHERE id_postulacion = %s", (id_postulacion,))
    actualizar(
        db,
        "UPDATE postulacion_anuncio SET estado = 'rechazada' WHERE id_anuncio = %s AND id_postulacion != %s",
        (id_anuncio, id_postulacion),
    )

    # 4. Insertar mensaje inicial en el chat y notificar al prestador
    insertar(
        db,
        "INSERT INTO mensaje (id_solicitud, id_emisor, contenido) VALUES (%s, %s, %s)",
        (
            id_solicitud,
            id_cliente,
            f"¡Hola! Adjudiqué tu cotización (${postulacion['propuesta_precio']:,.2f}) para el aviso '{anuncio['titulo']}'. Ya podemos coordinar por acá.",
        ),
    )

    notificar(
        db,
        id_prestador,
        "solicitud",
        f"¡Tu propuesta para '{anuncio['titulo']}' fue aceptada! Ya tenés un trabajo agendado en tus solicitudes.",
        id_solicitud=id_solicitud,
    )

    db.commit()

    return {
        "id_anuncio": id_anuncio,
        "id_solicitud": id_solicitud,
        "id_prestador": id_prestador,
        "estado": "adjudicado",
        "mensaje": "¡Trabajo adjudicado con éxito! Se generó la contratación formal.",
    }


@router.delete("/{id_anuncio}")
def cancelar_anuncio(id_anuncio: int, cliente=Depends(solo_cliente), db=Depends(get_db)):
    """El cliente cancela un anuncio abierto."""
    anuncio = uno(db, "SELECT id_cliente, estado FROM anuncio_trabajo WHERE id_anuncio = %s", (id_anuncio,))
    if not anuncio:
        raise NoEncontradoError("El anuncio no existe.")
    if anuncio["id_cliente"] != cliente["id_usuario"]:
        raise AccesoDenegadoError("Solo podés cancelar tus propios anuncios.")
    if anuncio["estado"] != "abierto":
        raise ReglaNegocioError("Solo se pueden cancelar anuncios que estén abiertos.")

    actualizar(db, "UPDATE anuncio_trabajo SET estado = 'cancelado' WHERE id_anuncio = %s", (id_anuncio,))
    db.commit()
    return {"id_anuncio": id_anuncio, "estado": "cancelado", "mensaje": "Anuncio cancelado."}
