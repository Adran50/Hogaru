"""Módulo de Verificación: carga de documentación del prestador e integración de antecedentes."""
from pathlib import Path
from typing import Literal
import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from ..db import actualizar, get_db, insertar, todos, uno
from ..deps import solo_prestador
from ..errores import ReglaNegocioError
from ..integraciones import background_check_service

router = APIRouter(prefix="/verificacion", tags=["Verificación de Prestadores"])

CARPETA_UPLOADS = Path(__file__).resolve().parent.parent.parent / "uploads" / "documentos"
CARPETA_UPLOADS.mkdir(parents=True, exist_ok=True)
EXTENSIONES_PERMITIDAS = {".pdf", ".jpg", ".jpeg", ".png"}
TAMANIO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB

TipoDoc = Literal["dni", "dni_frente", "dni_dorso", "antecedentes_penales", "otro"]


class DocumentoIn(BaseModel):
    tipo_documento: TipoDoc
    archivo_url: str = Field(min_length=1, max_length=255)


def recalcular_verificacion(db, id_prestador: int) -> str:
    """Recalcula `prestador.estado_verificacion` según el ÚLTIMO documento de cada tipo.

    Reglas de negocio:
    - Antecedentes penales es obligatorio.
    - DNI es obligatorio: se satisface con 'dni' (unificado/PDF) O con ambos ('dni_frente' Y 'dni_dorso').
    - Si algún documento presentado está 'rechazado' -> 'rechazado'.
    - Si se cumplen los requisitos y están todos 'aprobado' -> 'aprobado'.
    - De lo contrario -> 'pendiente'.
    """
    docs = todos(
        db,
        "SELECT tipo_documento, estado FROM documentacion_verificacion "
        "WHERE id_prestador = %s ORDER BY id_documento",
        (id_prestador,),
    )
    ultimo = {d["tipo_documento"]: d["estado"] for d in docs}

    # 1. Si algún documento presentado está rechazado, el prestador queda rechazado
    if "rechazado" in ultimo.values():
        nuevo = "rechazado"
    else:
        # 2. Verificar antecedentes penales
        ant_ok = (ultimo.get("antecedentes_penales") == "aprobado")

        # 3. Verificar DNI (unificado O frente + dorso)
        dni_unificado_ok = (ultimo.get("dni") == "aprobado")
        dni_partes_ok = (ultimo.get("dni_frente") == "aprobado" and ultimo.get("dni_dorso") == "aprobado")
        dni_ok = dni_unificado_ok or dni_partes_ok

        if ant_ok and dni_ok:
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
    """El prestador carga un documento (URL) para validación."""
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


@router.post("/subir", status_code=201)
async def subir_archivo_documento(
    tipo_documento: TipoDoc = Form(...),
    archivo: UploadFile = File(...),
    usuario=Depends(solo_prestador),
    db=Depends(get_db),
):
    """Sube un archivo físico (PDF o imagen) para verificación del prestador."""
    nombre_original = archivo.filename or "archivo"
    ext = Path(nombre_original).suffix.lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise ReglaNegocioError(
            f"Formato no permitido ({ext}). Solo se aceptan archivos PDF (.pdf) e imágenes (.jpg, .jpeg, .png)."
        )

    contenido = await archivo.read()
    if len(contenido) > TAMANIO_MAXIMO_BYTES:
        raise ReglaNegocioError("El archivo excede el tamaño máximo permitido de 10 MB.")

    if len(contenido) == 0:
        raise ReglaNegocioError("El archivo enviado está vacío.")

    nombre_seguro = f"{uuid.uuid4().hex}{ext}"
    ruta_destino = CARPETA_UPLOADS / nombre_seguro
    with open(ruta_destino, "wb") as f:
        f.write(contenido)

    archivo_url = f"/uploads/documentos/{nombre_seguro}"
    id_prestador = usuario["id_usuario"]

    id_documento = insertar(
        db,
        "INSERT INTO documentacion_verificacion (id_prestador, tipo_documento, archivo_url, estado) "
        "VALUES (%s, %s, %s, 'pendiente')",
        (id_prestador, tipo_documento, archivo_url),
    )

    resultado_antecedentes = None
    if tipo_documento == "antecedentes_penales":
        resultado_antecedentes = background_check_service.verificar_antecedentes(archivo_url)

    estado_actual = recalcular_verificacion(db, id_prestador)
    db.commit()

    respuesta = {
        "id_documento": id_documento,
        "tipo_documento": tipo_documento,
        "archivo_url": archivo_url,
        "nombre_original": nombre_original,
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
    for d in docs:
        if d["tipo_documento"] == "antecedentes_penales":
            d["prechequeo"] = background_check_service.verificar_antecedentes(d["archivo_url"])
    return docs
