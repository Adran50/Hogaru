"""Tests de la Fase 5: Pagos Mock, Calificaciones, Disputas y Notificaciones."""
from .conftest import pedir, registrar


def test_pagos_mock_comision_y_rechazo(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # 1. Pago rechazado si está pendiente (requiere estar aceptada/finalizada)
    assert client.post(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta"}).status_code == 409

    # Aceptar solicitud
    client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"])

    # 2. Simulación de fallo en pasarela -> HTTP 402
    r_fallo = client.post(
        f"/api/v1/solicitudes/{id_sol}/pago",
        headers=c["h"],
        json={"metodo_pago": "tarjeta", "simular_fallo": True},
    )
    assert r_fallo.status_code == 402
    assert r_fallo.json()["error"]["codigo"] == "PAGO_RECHAZADO"

    # 3. Pago aprobado exitoso con comisión 10%
    r_pago = client.post(
        f"/api/v1/solicitudes/{id_sol}/pago",
        headers=c["h"],
        json={"metodo_pago": "mercado_pago"},
    )
    assert r_pago.status_code == 201
    data_pago = r_pago.json()
    assert float(data_pago["monto"]) == 10000.0  # $5000 x 2 horas
    assert float(data_pago["comision_plataforma"]) == 1000.0  # 10%
    assert float(data_pago["neto_prestador"]) == 9000.0
    assert data_pago["estado"] == "completado"
    assert data_pago["referencia"].startswith("SIM-")

    # 4. Intento de pago duplicado -> 409
    r_dup = client.post(
        f"/api/v1/solicitudes/{id_sol}/pago",
        headers=c["h"],
        json={"metodo_pago": "tarjeta"},
    )
    assert r_dup.status_code == 409
    assert r_dup.json()["error"]["codigo"] == "CONFLICTO"

    # 5. Consulta de pago
    r_ver = client.get(f"/api/v1/solicitudes/{id_sol}/pago", headers=p["h"])
    assert r_ver.status_code == 200
    assert float(r_ver.json()["monto"]) == 10000.0


def test_calificaciones_recalculo_promedio_y_duplicado(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # No se puede calificar en estado pendiente o sin pago
    assert client.post(
        f"/api/v1/solicitudes/{id_sol}/calificacion",
        headers=c["h"],
        json={"puntuacion_puntualidad": 5, "puntuacion_prolijidad": 5, "puntuacion_trato": 5},
    ).status_code == 409

    # Completar ciclo: aceptar, pagar, iniciar, finalizar
    client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"])
    client.post(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta"})
    client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"])
    client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"])

    # Calificar con notas 5, 4, 3 -> promedio 4.0
    r_cal = client.post(
        f"/api/v1/solicitudes/{id_sol}/calificacion",
        headers=c["h"],
        json={
            "puntuacion_puntualidad": 5,
            "puntuacion_prolijidad": 4,
            "puntuacion_trato": 3,
            "comentario": "Buen servicio",
        },
    )
    assert r_cal.status_code == 201
    assert float(r_cal.json()["puntuacion_promedio_prestador"]) == 4.0

    # Segundo intento de calificar la misma solicitud -> 409
    r_cal_dup = client.post(
        f"/api/v1/solicitudes/{id_sol}/calificacion",
        headers=c["h"],
        json={"puntuacion_puntualidad": 5, "puntuacion_prolijidad": 5, "puntuacion_trato": 5},
    )
    assert r_cal_dup.status_code == 409
    assert r_cal_dup.json()["error"]["codigo"] == "CONFLICTO"

    # Prestador no puede auto-calificarse -> 403
    assert client.post(
        f"/api/v1/solicitudes/{id_sol}/calificacion",
        headers=p["h"],
        json={"puntuacion_puntualidad": 5, "puntuacion_prolijidad": 5, "puntuacion_trato": 5},
    ).status_code == 403

    # Consulta de reputación pública
    rep = client.get(f"/api/v1/prestadores/{p['id']}/calificaciones").json()
    assert rep["promedios"]["total"] == 1
    assert float(rep["promedios"]["puntualidad"]) == 5.0
    assert float(rep["promedios"]["prolijidad"]) == 4.0
    assert float(rep["promedios"]["trato"]) == 3.0


def test_disputas_apertura_y_resolucion_con_reembolso(client, admin, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # En pendiente no se abre disputa -> 409
    assert client.post(
        f"/api/v1/solicitudes/{id_sol}/disputas",
        headers=c["h"],
        json={"motivo": "Reclamo temprano en pendiente"},
    ).status_code == 409

    # Aceptar, pagar y finalizar
    client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"])
    client.post(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "transferencia"})
    client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"])
    client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"])

    # Abrir disputa formal
    r_disp = client.post(
        f"/api/v1/solicitudes/{id_sol}/disputas",
        headers=c["h"],
        json={"motivo": "Rotura de artefacto de iluminación durante la limpieza"},
    )
    assert r_disp.status_code == 201
    id_disp = r_disp.json()["id_disputa"]

    # Admin pasa a en_revision
    r_rev = client.patch(
        f"/api/v1/admin/disputas/{id_disp}",
        headers=admin["h"],
        json={"estado": "en_revision"},
    )
    assert r_rev.status_code == 200

    # Admin resuelve con reembolso
    r_res = client.patch(
        f"/api/v1/admin/disputas/{id_disp}",
        headers=admin["h"],
        json={
            "estado": "resuelta",
            "resolucion": "Se verifica el daño y se procede con el reembolso total",
            "reembolsar": True,
        },
    )
    assert r_res.status_code == 200
    assert r_res.json()["pago_reembolsado"] is True

    # Verificar que el pago pasó a reembolsado
    pago = client.get(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"]).json()
    assert pago["estado"] == "reembolsado"

    # Disputa resuelta no se reabre -> 409
    r_reabrir = client.patch(
        f"/api/v1/admin/disputas/{id_disp}",
        headers=admin["h"],
        json={"estado": "en_revision"},
    )
    assert r_reabrir.status_code == 409


def test_notificaciones_y_chat_de_trabajo(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # 1. Chat entre cliente y prestador
    r_msj = client.post(
        f"/api/v1/solicitudes/{id_sol}/mensajes",
        headers=c["h"],
        json={"contenido": "¿Podrías traer escalera para limpiar arriba de los muebles?"},
    )
    assert r_msj.status_code == 201

    client.post(
        f"/api/v1/solicitudes/{id_sol}/mensajes",
        headers=p["h"],
        json={"contenido": "Hola, sí, llevo una de dos peldaños sin problema."},
    )

    # Historial de mensajes
    chat = client.get(f"/api/v1/solicitudes/{id_sol}/mensajes", headers=c["h"]).json()
    assert len(chat) == 2

    # 2. Bandeja de notificaciones del prestador
    notifs = client.get("/api/v1/notificaciones", headers=p["h"]).json()
    assert notifs["no_leidas"] > 0
    id_notif = notifs["notificaciones"][0]["id_notificacion"]

    # Marcar una leída
    r_leer = client.post(f"/api/v1/notificaciones/{id_notif}/leer", headers=p["h"])
    assert r_leer.status_code == 200

    # Marcar todas leídas
    r_todas = client.post("/api/v1/notificaciones/leer-todas", headers=p["h"])
    assert r_todas.status_code == 200

    # Verificar que el contador quedó en 0
    assert client.get("/api/v1/notificaciones", headers=p["h"]).json()["no_leidas"] == 0
