"""Módulo de Verificación: carga de documentación del prestador e integración de antecedentes."""
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import solo_prestador
from ..integraciones import background_check_service

router = APIRouter(prefix="/verificacion", tags=["Verificación de Prestadores"])

# Documentos que un prestador necesita tener aprobados para poder publicar servicios
DOCUMENTOS_OBLIGATORIOS = {"dni", "antecedentes_penales"}


class DocumentoIn(BaseModel):
    tipo_documento: Literal["dni", "antecedentes_penales", "otro"]
    archivo_url: str = Field(min_length=1, max_length=255)


def recalcular_verificacion(db, id_prestador: int) -> str:
    """Recalcula `prestador.estado_verificacion` según el ÚLTIMO documento de cada tipo.

    Reglas de negocio:
    - Si algún documento obligatorio está rechazado        -> 'rechazado'
    - Si todos los obligatorios están aprobados            -> 'aprobado'
    - Cualquier otro caso (faltantes o en revisión)        -> 'pendiente'
    """
    docs = todos(
        db,
        "SELECT tipo_documento, estado FROM documentacion_verificacion "
        "WHERE id_prestador = %s ORDER BY id_documento",
        (id_prestador,),
    )
    ultimo = {d["tipo_documento"]: d["estado"] for d in docs}
    estados_obligatorios = {ultimo.get(t) for t in DOCUMENTOS_OBLIGATORIOS}

    if "rechazado" in estados_obligatorios:
        nuevo = "rechazado"
    elif estados_obligatorios == {"aprobado"}:
        nuevo = "aprobado"
    else:
        nuevo = "pendiente"

    actualizar(
        db,
        "UPDATE prestador SET estado_verificacion = %s WHERE id_prestador = %s",
        (nuevo, id_prestador),
    )
    return nuevo


@router.post("/documentos", status_code=201)
def subir_documento(datos: DocumentoIn, usuario=Depends(solo_prestador), db=Depends(get_db)):
    """El prestador carga un documento para validación.
    Si es de antecedentes penales, se corre la verificación previa simulada
    con BackgroundCheckProvider (la confirmación final siempre es del administrador).
    """
    id_prestador = usuario["id_usuario"]

    id_documento = insertar(
        db,
        "INSERT INTO documentacion_verificacion (id_prestador, tipo_documento, archivo_url, estado) "
        "VALUES (%s, %s, %s, 'pendiente')",
        (id_prestador, datos.tipo_documento, datos.archivo_url),
    )

    resultado_antecedentes = None
    if datos.tipo_documento == "antecedentes_penales":
        resultado_antecedentes = background_check_service.verificar_antecedentes(datos.archivo_url)

    estado_actual = recalcular_verificacion(db, id_prestador)
    db.commit()

    respuesta = {
        "id_documento": id_documento,
        "tipo_documento": datos.tipo_documento,
        "archivo_url": datos.archivo_url,
        "estado_documento": "pendiente",
        "estado_verificacion_prestador": estado_actual,
    }
    if resultado_antecedentes:
        respuesta["prechequeo_antecedentes"] = resultado_antecedentes

    return respuesta


@router.get("/documentos")
def mis_documentos(usuario=Depends(solo_prestador), db=Depends(get_db)):
    """Lista todos los documentos presentados por el prestador con su estado de revisión."""
    docs = todos(
        db,
        "SELECT id_documento, tipo_documento, archivo_url, estado, fecha_carga, fecha_revision "
        "FROM documentacion_verificacion WHERE id_prestador = %s ORDER BY id_documento DESC",
        (usuario["id_usuario"],),
    )
    # Agregar evaluación previa para documentos de antecedentes
    for d in docs:
        if d["tipo_documento"] == "antecedentes_penales":
            d["prechequeo"] = background_check_service.verificar_antecedentes(d["archivo_url"])
    return docs
