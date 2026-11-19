"""Servicios externos SIMULADOS (mocks e interfaces desacopladas).

Define interfaces abstractas y sus implementaciones simuladas para:
1. Pasarela de pagos (PaymentGateway / MockPaymentGateway)
2. Verificación de antecedentes penales (BackgroundCheckProvider / MockBackgroundCheckProvider)
3. Notificaciones push/email (NotificationSender / ConsoleNotificationSender)
"""
from abc import ABC, abstractmethod
from decimal import Decimal
import uuid


# =====================================================
# 1. VERIFICACION DE ANTECEDENTES
# =====================================================
class BackgroundCheckProvider(ABC):
    """Interfaz abstracta para el proveedor de verificación de antecedentes penales."""

    @abstractmethod
    def verificar_antecedentes(self, identificador: str) -> dict:
        """Consulta antecedentes penales a partir de un identificador (DNI, CUIT o nombre de archivo).
        Retorna:
            {
                "apto": bool,
                "codigo": str,
                "detalle": str,
                "identificador": str
            }
        """
        pass


class MockBackgroundCheckProvider(BackgroundCheckProvider):
    """Implementación simulada determinística:
    - Extrae los dígitos numéricos del identificador.
    - Si el último dígito es par -> Apto / Sin antecedentes registrados.
    - Si el último dígito es impar -> Observado / Antecedentes registrados.
    - La aprobación final siempre es confirmada por un administrador.
    """

    def verificar_antecedentes(self, identificador: str) -> dict:
        digitos = [c for c in identificador if c.isdigit()]
        if not digitos:
            # Si no hay dígitos (ej. /docs/archivo.pdf), tomamos el largo de la cadena
            ultimo = len(identificador)
        else:
            ultimo = int(digitos[-1])

        if ultimo % 2 == 0:
            return {
                "apto": True,
                "codigo": "SIN_ANTECEDENTES",
                "detalle": "Chequeo automático favorable: sin antecedentes penales registrados (regla par)",
                "identificador": identificador,
            }
        return {
            "apto": False,
            "codigo": "ANTECEDENTES_OBSERVADOS",
            "detalle": "Chequeo automático observado: se detectaron posibles registros de antecedentes (regla impar)",
            "identificador": identificador,
        }


# Instancia por defecto
background_check_service: BackgroundCheckProvider = MockBackgroundCheckProvider()


# =====================================================
# 2. PASARELA DE PAGOS
# =====================================================
class PaymentGateway(ABC):
    """Interfaz abstracta para pasarelas de pago (Mercado Pago, Stripe, etc.)."""

    @abstractmethod
    def cobrar(self, metodo: str, monto: Decimal, simular_fallo: bool = False) -> dict:
        pass

    @abstractmethod
    def reembolsar(self, referencia: str, monto: Decimal) -> dict:
        pass


class MockPaymentGateway(PaymentGateway):
    """Implementación simulada de pasarela de pagos."""

    def cobrar(self, metodo: str, monto: Decimal, simular_fallo: bool = False) -> dict:
        if simular_fallo:
            return {
                "aprobado": False,
                "motivo": "Pago rechazado por la pasarela de pagos (simulación de fallo)",
                "referencia": None,
            }
        referencia = f"SIM-{uuid.uuid4().hex[:12].upper()}"
        return {
            "aprobado": True,
            "referencia": referencia,
            "motivo": "Pago aprobado exitosamente",
            "metodo": metodo,
            "monto": float(monto),
        }

    def reembolsar(self, referencia: str, monto: Decimal) -> dict:
        return {
            "reembolsado": True,
            "referencia_reembolso": f"REEMB-{uuid.uuid4().hex[:10].upper()}",
            "referencia_original": referencia,
            "monto": float(monto),
        }


payment_service: PaymentGateway = MockPaymentGateway()


def procesar_pago(metodo: str, monto: Decimal, simular_fallo: bool = False) -> dict:
    """Función de compatibilidad con código existente."""
    return payment_service.cobrar(metodo, monto, simular_fallo)


# =====================================================
# 3. NOTIFICACIONES EXTERNAS
# =====================================================
class NotificationSender(ABC):
    """Interfaz abstracta para envío de notificaciones push o email."""

    @abstractmethod
    def enviar(self, destinatario: str, asunto: str, mensaje: str) -> bool:
        pass


class ConsoleNotificationSender(NotificationSender):
    """Implementación simulada que imprime en consola / log."""

    def enviar(self, destinatario: str, asunto: str, mensaje: str) -> bool:
        print(f"[NOTIFICACION SIMULADA] Para: {destinatario} | Asunto: {asunto} | Mensaje: {mensaje}")
        return True


notification_sender: NotificationSender = ConsoleNotificationSender()
