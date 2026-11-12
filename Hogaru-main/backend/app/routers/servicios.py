"""Módulo de Servicios: catálogo, búsqueda con Haversine, filtros avanzados y gestión de disponibilidad."""
from datetime import time, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import solo_prestador
from ..errores import AccesoDenegadoError, NoEncontradoError, ReglaNegocioError

router = APIRouter(tags=["Servicios"])


class FranjaIn(BaseModel):
    dia_semana: int = Field(ge=1, le=7, description="1 = lunes ... 7 = domingo")
    hora_inicio: time
    hora_fin: time

    @model_validator(mode="after")
    def _fin_despues_de_inicio(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser posterior a hora_inicio")
        return self


class ServicioIn(BaseModel):
    id_categoria: int
    descripcion: str | None = Field(None, max_length=2000)
    tarifa: Decimal = Field(gt=0, max_digits=10, decimal_places=2, description="Precio por hora")
    disponibilidad: list[FranjaIn] = Field(default_factory=list)


class ServicioPatch(BaseModel):
    descripcion: str | None = Field(None, max_length=2000)
    tarifa: Decimal | None = Field(None, gt=0, max_digits=10, decimal_places=2)
    activo: bool | None = None


def _guardar_franjas(db, id_servicio: int, franjas: list[FranjaIn]):
    for f in franjas:
        insertar(
            db,
            "INSERT INTO disponibilidad (id_servicio, dia_semana, hora_inicio, hora_fin) "
            "VALUES (%s, %s, %s, %s)",
            (id_servicio, f.dia_semana, f.hora_inicio, f.hora_fin),
        )


def _hhmm(td) -> str:
    """Convierte timedelta (formato devuelto por PyMySQL para TIME) a texto 'HH:MM'."""
    if isinstance(td, str):
        return td[:5]
    if isinstance(td, time):
        return f"{td.hour:02d}:{td.minute:02d}"
    minutos = int(td.total_seconds() // 60)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def _servicio_propio(db, id_servicio: int, id_prestador: int) -> dict:
    servicio = uno(db, "SELECT * FROM servicio_ofrecido WHERE id_servicio = %s", (id_servicio,))
    if not servicio:
        raise NoEncontradoError("El servicio no existe")
    if servicio["id_prestador"] != id_prestador:
        raise AccesoDenegadoError("Ese servicio no pertenece a tu cuenta")
    return servicio


@router.get("/categorias")
def listar_categorias(db=Depends(get_db)):
    """Listado de categorías disponibles (limpieza doméstica, oficinas, jardinería, etc.)."""
    return todos(db, "SELECT id_categoria, nombre, descripcion FROM categoria_servicio ORDER BY nombre")


@router.get("/servicios")
def buscar_servicios(
    categoria: int | None = Query(None, description="Filtrar por id_categoria"),
    q: str | None = Query(None, description="Búsqueda por texto en nombre, categoría o descripción"),
    tarifa_min: Decimal | None = Query(None, ge=0, description="Tarifa mínima por hora"),
    tarifa_max: Decimal | None = Query(None, gt=0, description="Tarifa máxima por hora"),
    puntuacion_min: Decimal | None = Query(None, ge=1, le=5, description="Puntuación promedio mínima"),
    dia_semana: int | None = Query(None, ge=1, le=7, description="Día disponible (1=Lunes a 7=Domingo)"),
    hora: time | None = Query(None, description="Horario disponible (HH:MM)"),
    lat: float | None = Query(None, ge=-90, le=90, description="Latitud del cliente para Haversine"),
    lng: float | None = Query(None, ge=-180, le=180, description="Longitud del cliente para Haversine"),
    radio_km: float | None = Query(None, gt=0, description="Radio de cobertura máximo en kilómetros"),
    orden: Literal["puntuacion", "tarifa_asc", "tarifa_desc", "cercania"] = "puntuacion",
    limite: int = Query(20, ge=1, le=100),
    pagina: int = Query(1, ge=1),
    db=Depends(get_db),
):
    """Búsqueda y filtrado multicriterio de servicios disponibles.
    Soporta radio en kilómetros con la fórmula de Haversine sobre prestadores activos y verificados.
    """
    condiciones = ["1 = 1"]
    params = []

    # 1. Filtro por categoría
    if categoria is not None:
        condiciones.append("so.id_categoria = %s")
        params.append(categoria)

    # 2. Búsqueda textual
    if q:
        condiciones.append("(v.nombre_publico LIKE %s OR v.categoria LIKE %s OR so.descripcion LIKE %s)")
        params += [f"%{q}%"] * 3

    # 3. Rango de tarifas
    if tarifa_min is not None:
        condiciones.append("v.tarifa >= %s")
        params.append(tarifa_min)
    if tarifa_max is not None:
        condiciones.append("v.tarifa <= %s")
        params.append(tarifa_max)

    # 4. Puntuación mínima
    if puntuacion_min is not None:
        condiciones.append("v.puntuacion_promedio >= %s")
        params.append(puntuacion_min)

    # 5. Disponibilidad por día y hora
    if dia_semana is not None:
        if hora is not None:
            condiciones.append(
                "EXISTS (SELECT 1 FROM disponibilidad d "
                "WHERE d.id_servicio = v.id_servicio AND d.dia_semana = %s "
                "  AND d.hora_inicio <= %s AND d.hora_fin >= %s)"
            )
            params.extend([dia_semana, hora, hora])
        else:
            condiciones.append(
                "EXISTS (SELECT 1 FROM disponibilidad d "
                "WHERE d.id_servicio = v.id_servicio AND d.dia_semana = %s)"
            )
            params.append(dia_semana)

    # 6. Cálculo geoespacial con fórmula de Haversine
    # R_Tierra = 6371 km
    select_distancia = "NULL AS distancia_km"
    formula_haversine = None
    if lat is not None and lng is not None:
        formula_haversine = (
            "(6371 * ACOS(LEAST(1.0, GREATEST(-1.0, "
            "COS(RADIANS(%s)) * COS(RADIANS(v.latitud)) * "
            "COS(RADIANS(v.longitud) - RADIANS(%s)) + "
            "SIN(RADIANS(%s)) * SIN(RADIANS(v.latitud))"
            "))))"
        )
        select_distancia = f"ROUND({formula_haversine}, 2) AS distancia_km"
        # Coordenadas prestador no nulas
        condiciones.append("v.latitud IS NOT NULL AND v.longitud IS NOT NULL")

    if radio_km is not None and formula_haversine:
        condiciones.append(f"{formula_haversine} <= %s")

    # 7. Criterio de ordenamiento
    if orden == "tarifa_asc":
        orden_sql = "v.tarifa ASC, v.puntuacion_promedio DESC"
    elif orden == "tarifa_desc":
        orden_sql = "v.tarifa DESC, v.puntuacion_promedio DESC"
    elif orden == "cercania" and formula_haversine:
        orden_sql = "distancia_km ASC, v.puntuacion_promedio DESC"
    else:
        orden_sql = "v.puntuacion_promedio DESC, v.servicios_realizados DESC"

    # Construcción de la consulta final
    # Parámetros para select_distancia si aplica
    params_select = [lat, lng, lat] if formula_haversine else []
    # Parámetros para condición de radio si aplica
    params_radio = [lat, lng, lat, radio_km] if (radio_km is not None and formula_haversine) else []

    sql = (
        f"SELECT v.*, so.id_categoria, so.descripcion, {select_distancia} "
        "FROM v_prestadores_disponibles v "
        "JOIN servicio_ofrecido so ON so.id_servicio = v.id_servicio "
        f"WHERE {' AND '.join(condiciones)} "
        f"ORDER BY {orden_sql} LIMIT %s OFFSET %s"
    )

    offset = (pagina - 1) * limite
    todos_params = params_select + params + params_radio + [limite, offset]
    return todos(db, sql, todos_params)


@router.get("/servicios/{id_servicio}")
def detalle_servicio(id_servicio: int, db=Depends(get_db)):
    """Detalle completo de un servicio con su disponibilidad semanal configurada."""
    servicio = uno(
        db,
        "SELECT v.*, so.id_categoria, so.descripcion "
        "FROM v_prestadores_disponibles v "
        "JOIN servicio_ofrecido so ON so.id_servicio = v.id_servicio "
        "WHERE v.id_servicio = %s",
        (id_servicio,),
    )
    if not servicio:
        raise NoEncontradoError("El servicio no existe o no está disponible públicamente")

    franjas = todos(
        db,
        "SELECT dia_semana, hora_inicio, hora_fin FROM disponibilidad "
        "WHERE id_servicio = %s ORDER BY dia_semana, hora_inicio",
        (id_servicio,),
    )
    for f in franjas:
        f["hora_inicio"] = _hhmm(f["hora_inicio"])
        f["hora_fin"] = _hhmm(f["hora_fin"])

    servicio["disponibilidad"] = franjas
    return servicio


@router.post("/servicios", status_code=201)
def publicar_servicio(datos: ServicioIn, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Publica un nuevo servicio. Requiere que el prestador tenga verificación 'aprobado'."""
    prestador = uno(
        db,
        "SELECT estado_verificacion FROM prestador WHERE id_prestador = %s",
        (usuario["id_usuario"],),
    )
    if not prestador or prestador["estado_verificacion"] != "aprobado":
        raise AccesoDenegadoError("Tu cuenta de prestador todavía no está verificada y aprobada")

    if not uno(db, "SELECT 1 FROM categoria_servicio WHERE id_categoria = %s", (datos.id_categoria,)):
        raise NoEncontradoError("La categoría de servicio seleccionada no existe")

    id_servicio = insertar(
        db,
        "INSERT INTO servicio_ofrecido (id_prestador, id_categoria, descripcion, tarifa, activo) "
        "VALUES (%s, %s, %s, %s, TRUE)",
        (usuario["id_usuario"], datos.id_categoria, datos.descripcion, datos.tarifa),
    )
    _guardar_franjas(db, id_servicio, datos.disponibilidad)
    db.commit()

    return {
        "id_servicio": id_servicio,
        "id_categoria": datos.id_categoria,
        "tarifa": datos.tarifa,
        "franjas_configuradas": len(datos.disponibilidad),
    }


@router.get("/mis-servicios")
def mis_servicios(usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Lista todos los servicios del prestador logueado (incluye activos y pausados)."""
    return todos(
        db,
        "SELECT so.id_servicio, so.id_categoria, cs.nombre AS categoria, so.descripcion, "
        "       so.tarifa, so.activo "
        "FROM servicio_ofrecido so "
        "JOIN categoria_servicio cs ON cs.id_categoria = so.id_categoria "
        "WHERE so.id_prestador = %s ORDER BY so.id_servicio",
        (usuario["id_usuario"],),
    )


@router.patch("/servicios/{id_servicio}")
def editar_servicio(
    id_servicio: int,
    datos: ServicioPatch,
    usuario=Depends(solo_prestador),
    db=Depends(get_db),
):
    """Modifica tarifa, descripción o pausa/reactiva un servicio propio."""
    _servicio_propio(db, id_servicio, usuario["id_usuario"])
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise ReglaNegocioError("No enviaste ningún campo para modificar")

    set_cols = ", ".join(f"{col} = %s" for col in cambios)
    actualizar(
        db,
        f"UPDATE servicio_ofrecido SET {set_cols} WHERE id_servicio = %s",
        list(cambios.values()) + [id_servicio],
    )
    db.commit()
    return {"id_servicio": id_servicio, **cambios}


@router.put("/servicios/{id_servicio}/disponibilidad")
def reemplazar_disponibilidad(
    id_servicio: int,
    franjas: list[FranjaIn],
    usuario=Depends(solo_prestador),
    db=Depends(get_db),
):
    """Reemplaza íntegramente las franjas horarias de disponibilidad semanal de un servicio."""
    _servicio_propio(db, id_servicio, usuario["id_usuario"])
    actualizar(db, "DELETE FROM disponibilidad WHERE id_servicio = %s", (id_servicio,))
    _guardar_franjas(db, id_servicio, franjas)
    db.commit()
    return {"id_servicio": id_servicio, "franjas_configuradas": len(franjas)}
