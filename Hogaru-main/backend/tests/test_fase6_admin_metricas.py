"""Tests de la Fase 6: Administración, Métricas Globales y Control de Acceso."""
from .conftest import registrar


def test_metricas_plataforma_acceso_admin_y_estructura(client, admin):
    # Consulta de métricas por administrador
    r_metricas = client.get("/api/v1/admin/metricas", headers=admin["h"])
    assert r_metricas.status_code == 200, r_metricas.text
    datos = r_metricas.json()

    # Verificar bloques requeridos
    assert "solicitudes_por_estado" in datos
    assert "finanzas" in datos
    assert "usuarios" in datos
    assert "prestadores_verificacion" in datos

    # Verificar estados de solicitudes
    solicitudes = datos["solicitudes_por_estado"]
    for estado in ("pendiente", "aceptada", "en_curso", "finalizada", "cancelada"):
        assert estado in solicitudes
        assert isinstance(solicitudes[estado], int)

    # Verificar finanzas
    finanzas = datos["finanzas"]
    assert "ingresos_comision" in finanzas
    assert "volumen_total_procesado" in finanzas
    assert "transacciones_completadas" in finanzas
    assert isinstance(finanzas["ingresos_comision"], (int, float))

    # Verificar prestadores
    prestadores = datos["prestadores_verificacion"]
    assert isinstance(prestadores, dict)


def test_cliente_y_prestador_bloqueados_en_metricas(client):
    cliente = registrar(client, "cliente")
    prestador = registrar(client, "prestador")

    # Cliente no puede ver métricas
    r_cli = client.get("/api/v1/admin/metricas", headers=cliente["h"])
    assert r_cli.status_code == 403
    assert r_cli.json()["error"]["codigo"] == "ACCESO_DENEGADO"

    # Prestador no puede ver métricas
    r_pre = client.get("/api/v1/admin/metricas", headers=prestador["h"])
    assert r_pre.status_code == 403
    assert r_pre.json()["error"]["codigo"] == "ACCESO_DENEGADO"


def test_suspension_reactivacion_y_prohibicion_auto_suspension(client, admin):
    usuario = registrar(client, "cliente")
    id_u = usuario["id"]

    # Suspender cuenta
    r_susp = client.patch(
        f"/api/v1/admin/usuarios/{id_u}/estado",
        headers=admin["h"],
        json={"estado": "suspendido"},
    )
    assert r_susp.status_code == 200
    assert r_susp.json()["estado"] == "suspendido"

    # Reactivar cuenta
    r_act = client.patch(
        f"/api/v1/admin/usuarios/{id_u}/estado",
        headers=admin["h"],
        json={"estado": "activo"},
    )
    assert r_act.status_code == 200
    assert r_act.json()["estado"] == "activo"

    # Admin intenta auto-suspenderse -> 400 REGLA_NEGOCIO
    # Obtener id de admin a través de /auth/me
    id_admin = client.get("/api/v1/auth/me", headers=admin["h"]).json()["id_usuario"]
    r_auto = client.patch(
        f"/api/v1/admin/usuarios/{id_admin}/estado",
        headers=admin["h"],
        json={"estado": "suspendido"},
    )
    assert r_auto.status_code == 400
    assert r_auto.json()["error"]["codigo"] == "REGLA_NEGOCIO"
