"""Manejo centralizado de errores y excepciones para Hogaru API."""
from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import pymysql


def formato_error(codigo: str, mensaje: str, detalles: list | None = None) -> dict:
    """Estructura estandarizada de error requerida por la especificación:
    { "error": { "codigo": "...", "mensaje": "...", "detalles": [...] } }
    Se agrega 'detail' para garantizar compatibilidad retroactiva con frontend existente.
    """
    detalles_limpios = detalles or []
    return {
        "error": {
            "codigo": codigo,
            "mensaje": mensaje,
            "detalles": detalles_limpios,
        },
        "detail": mensaje,
    }


class AppError(Exception):
    """Excepción base de la aplicación con código HTTP y código simbólico."""
    def __init__(
        self,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        codigo: str = "ERROR_APLICACION",
        mensaje: str = "Ocurrió un error en la solicitud",
        detalles: list | None = None,
    ):
        super().__init__(mensaje)
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or []


class NoAutorizadoError(AppError):
    def __init__(self, mensaje: str = "Falta el token de autenticación o es inválido"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, "NO_AUTORIZADO", mensaje)


class AccesoDenegadoError(AppError):
    def __init__(self, mensaje: str = "No tenés permiso para realizar esta acción"):
        super().__init__(status.HTTP_403_FORBIDDEN, "ACCESO_DENEGADO", mensaje)


class NoEncontradoError(AppError):
    def __init__(self, mensaje: str = "El recurso solicitado no existe"):
        super().__init__(status.HTTP_404_NOT_FOUND, "NO_ENCONTRADO", mensaje)


class ConflictoError(AppError):
    def __init__(self, mensaje: str = "Existe un conflicto con el estado del recurso"):
        super().__init__(status.HTTP_409_CONFLICT, "CONFLICTO", mensaje)


class ReglaNegocioError(AppError):
    def __init__(self, mensaje: str = "La operación viola una regla de negocio"):
        super().__init__(status.HTTP_400_BAD_REQUEST, "REGLA_NEGOCIO", mensaje)


_MAPA_STATUS_CODIGO = {
    400: "SOLICITUD_INVALIDA",
    401: "NO_AUTORIZADO",
    402: "PAGO_REQUERIDO",
    403: "ACCESO_DENEGADO",
    404: "NO_ENCONTRADO",
    409: "CONFLICTO",
    422: "VALIDACION_ERROR",
    500: "ERROR_INTERNO",
    503: "SERVICIO_NO_DISPONIBLE",
}


def registrar_manejadores_error(app):
    """Registra todos los exception handlers centralizados en la aplicación FastAPI."""

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=formato_error(exc.codigo, exc.mensaje, exc.detalles),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        codigo = _MAPA_STATUS_CODIGO.get(exc.status_code, "ERROR_HTTP")
        mensaje = str(exc.detail) if exc.detail else "Error en la solicitud"
        return JSONResponse(
            status_code=exc.status_code,
            content=formato_error(codigo, mensaje),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        detalles = []
        for err in exc.errors():
            campo = ".".join(
                str(loc) for loc in err.get("loc", []) if loc not in ("body", "query", "path")
            )
            detalles.append({
                "campo": campo or "general",
                "mensaje": err.get("msg", "Dato inválido"),
                "tipo": err.get("type", "valor_invalido"),
            })
        mensaje = "Los datos enviados contienen errores de validación"
        if detalles:
            mensaje = f"Error de validación en: {', '.join(d['campo'] for d in detalles if d['campo'])}"
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=formato_error("VALIDACION_ERROR", mensaje, detalles),
        )

    @app.exception_handler(pymysql.err.OperationalError)
    async def error_operacional(request: Request, exc: pymysql.err.OperationalError):
        num_error = exc.args[0] if exc.args else 0
        if num_error == 1644:
            # SIGNAL generado por un trigger en MySQL
            msg = str(exc.args[1]) if len(exc.args) > 1 else "Regla de negocio infringida"
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=formato_error("REGLA_NEGOCIO", msg),
            )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=formato_error("BASE_DE_DATOS_NO_DISPONIBLE", "La base de datos no está disponible temporalmente"),
        )

    @app.exception_handler(pymysql.err.IntegrityError)
    async def error_integridad(request: Request, exc: pymysql.err.IntegrityError):
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=formato_error(
                "CONFLICTO_INTEGRIDAD",
                "El dato viola una restricción de integridad de la base (duplicado o foránea inexistente)",
            ),
        )

    @app.exception_handler(pymysql.err.DataError)
    async def error_datos(request: Request, exc: pymysql.err.DataError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=formato_error("FORMATO_DATO_INVALIDO", "Dato con formato, longitud o rango inválido"),
        )
