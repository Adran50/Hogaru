"""Flujo completo (camino feliz) del documento: pasos 1 a 9."""
from .conftest import autenticar, pedir, registrar, turno


def test_flujo_completo_de_contratacion(client, admin, escenario):
    prestador, cliente, id_servicio = escenario["prestador"], escenario["cliente"], escenario["id_servicio"]

    # 3. el cliente busca y encuentra al prestador (ya verificado)
    r = client.get("/servicios", params={"limite": 100})
    assert id_servicio in [s["id_servicio"] for s in r.json()]

    # 4. solicitud -> el trigger notifica al prestador
    r = pedir(client, escenario)
    assert r.status_code == 201, r.text
    solicitud = r.json()
    id_sol = solicitud["id_solicitud"]
    assert solicitud["estado"] == "pendiente"
    assert float(solicitud["monto_estimado"]) == 10000.0  # 5000 x 2 hs
    notifs = client.get("/notificaciones", headers=prestador["h"]).json()
    assert any(n["tipo"] == "solicitud" and n["id_solicitud"] == id_sol for n in notifs["notificaciones"])

    # mensajes del cliente al prestador -> notificación de mensaje
    r = client.post(f"/solicitudes/{id_sol}/mensajes", headers=cliente["h"], json={"contenido": "¿Llevás los productos?"})
    assert r.status_code == 201
    notifs = client.get("/notificaciones", headers=prestador["h"], params={"solo_no_leidas": True}).json()
    assert any(n["tipo"] == "mensaje" for n in notifs["notificaciones"])
    client.post(f"/solicitudes/{id_sol}/mensajes", headers=prestador["h"], json={"contenido": "Sí, llevo todo"})
    chat = client.get(f"/solicitudes/{id_sol}/mensajes", headers=prestador["h"]).json()
    assert [m["contenido"] for m in chat] == ["¿Llevás los productos?", "Sí, llevo todo"]

    # 5. el prestador acepta
    r = client.post(f"/solicitudes/{id_sol}/aceptar", headers=prestador["h"])
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"

    # 7. pago (monto, comisión y neto)
    r = client.post(f"/solicitudes/{id_sol}/pago", headers=cliente["h"], json={"metodo_pago": "mercado_pago"})
    assert r.status_code == 201, r.text
    assert float(r.json()["monto"]) == 10000.0
    assert float(r.json()["comision_plataforma"]) == 1000.0
    assert float(r.json()["neto_prestador"]) == 9000.0

    # 6. se realiza el servicio
    assert client.post(f"/solicitudes/{id_sol}/iniciar", headers=prestador["h"]).json()["estado"] == "en_curso"
    assert client.post(f"/solicitudes/{id_sol}/finalizar", headers=prestador["h"]).json()["estado"] == "finalizada"

    # 8-9. calificación -> el trigger recalcula el promedio del prestador
    r = client.post(f"/solicitudes/{id_sol}/calificacion", headers=cliente["h"], json={
        "puntuacion_puntualidad": 5, "puntuacion_prolijidad": 4, "puntuacion_trato": 3, "comentario": "Bien"})
    assert r.status_code == 201, r.text
    assert float(r.json()["puntuacion_promedio_prestador"]) == 4.0
    rep = client.get(f"/prestadores/{prestador['id']}/calificaciones").json()
    assert rep["promedios"]["total"] == 1 and len(rep["calificaciones"]) == 1

    # historial del cliente
    hist = client.get("/solicitudes", headers=cliente["h"], params={"estado": "finalizada"}).json()
    assert [s["id_solicitud"] for s in hist] == [id_sol]


def test_disputa_y_reembolso_por_administrador(client, admin, escenario):
    prestador, cliente = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=prestador["h"])
    client.post(f"/solicitudes/{id_sol}/pago", headers=cliente["h"], json={"metodo_pago": "tarjeta"})
    client.post(f"/solicitudes/{id_sol}/iniciar", headers=prestador["h"])
    client.post(f"/solicitudes/{id_sol}/finalizar", headers=prestador["h"])

    # varias disputas sobre la misma solicitud
    for motivo in ("El servicio llegó 40 minutos tarde", "No limpiaron la cocina como se acordó"):
        r = client.post(f"/solicitudes/{id_sol}/disputas", headers=cliente["h"], json={"motivo": motivo})
        assert r.status_code == 201, r.text
    disputas = client.get(f"/solicitudes/{id_sol}/disputas", headers=prestador["h"]).json()
    assert len(disputas) == 2

    id_disputa = disputas[0]["id_disputa"]
    r = client.patch(f"/admin/disputas/{id_disputa}", headers=admin["h"], json={"estado": "en_revision"})
    assert r.status_code == 200
    r = client.patch(f"/admin/disputas/{id_disputa}", headers=admin["h"],
                     json={"estado": "resuelta", "resolucion": "Se reembolsa el total", "reembolsar": True})
    assert r.status_code == 200 and r.json()["pago_reembolsado"] is True
    assert client.get(f"/solicitudes/{id_sol}/pago", headers=cliente["h"]).json()["estado"] == "reembolsado"
    # una disputa resuelta no se reabre
    r = client.patch(f"/admin/disputas/{id_disputa}", headers=admin["h"], json={"estado": "en_revision"})
    assert r.status_code == 409


def test_detalle_de_solicitud_incluye_la_calificacion(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    assert client.get(f"/solicitudes/{id_sol}", headers=c["h"]).json()["calificacion"] is None
    for accion in ("aceptar", "iniciar", "finalizar"):
        client.post(f"/solicitudes/{id_sol}/{accion}", headers=p["h"])
    client.post(f"/solicitudes/{id_sol}/calificacion", headers=c["h"], json={
        "puntuacion_puntualidad": 5, "puntuacion_prolijidad": 4, "puntuacion_trato": 5, "comentario": "Todo bien"})
    detalle = client.get(f"/solicitudes/{id_sol}", headers=c["h"]).json()
    assert detalle["calificacion"]["puntuacion_prolijidad"] == 4
