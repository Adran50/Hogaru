"""Casos límite: validaciones, permisos, cancelaciones y errores."""
from .conftest import PASSWORD, email_unico, pedir, registrar, turno, verificar_prestador


# ---------- usuarios y permisos ----------
def test_email_duplicado_devuelve_409(client):
    u = registrar(client, "cliente")
    r = client.post("/auth/registro", json={"nombre": "A", "apellido": "B", "email": u["email"],
                                            "password": PASSWORD, "tipo_cuenta": "cliente"})
    assert r.status_code == 409


def test_login_con_password_incorrecta_devuelve_401(client):
    u = registrar(client, "cliente")
    r = client.post("/auth/login", json={"email": u["email"], "password": "otra-clave-xyz"})
    assert r.status_code == 401


def test_registro_valida_datos(client):
    base = {"nombre": "A", "apellido": "B", "tipo_cuenta": "cliente"}
    assert client.post("/auth/registro", json={**base, "email": "no-es-email", "password": PASSWORD}).status_code == 422
    assert client.post("/auth/registro", json={**base, "email": email_unico("x"), "password": "corta"}).status_code == 422
    assert client.post("/auth/registro", json={**base, "email": email_unico("x"), "password": PASSWORD,
                                               "tipo_cuenta": "administrador"}).status_code == 422


def test_sin_token_o_token_falso_devuelve_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer abc.def.ghi"}).status_code == 401


def test_cliente_no_puede_publicar_servicios_ni_entrar_a_admin(client):
    c = registrar(client, "cliente")
    assert client.post("/servicios", headers=c["h"], json={"id_categoria": 1, "tarifa": "100"}).status_code == 403
    assert client.get("/admin/usuarios", headers=c["h"]).status_code == 403


def test_prestador_sin_verificar_no_puede_publicar(client):
    p = registrar(client, "prestador")
    r = client.post("/servicios", headers=p["h"], json={"id_categoria": 1, "tarifa": "100"})
    assert r.status_code == 403


def test_documento_rechazado_bloquea_y_se_puede_recargar(client, admin):
    p = registrar(client, "prestador")
    r = client.post("/verificacion/documentos", headers=p["h"], json={"tipo_documento": "dni", "archivo_url": "/a.pdf"})
    res = client.post(f"/admin/documentos/{r.json()['id_documento']}/resolver", headers=admin["h"], json={"estado": "rechazado"})
    assert res.json()["estado_verificacion_prestador"] == "rechazado"
    assert client.get("/auth/me", headers=p["h"]).json()["perfil"]["estado_verificacion"] == "rechazado"
    # recarga el DNI -> vuelve a 'pendiente' y se puede aprobar
    verificar_prestador(client, admin, p)
    assert client.get("/auth/me", headers=p["h"]).json()["perfil"]["estado_verificacion"] == "aprobado"


def test_cuenta_suspendida_no_puede_operar(client, admin):
    c = registrar(client, "cliente")
    assert client.patch(f"/admin/usuarios/{c['id']}/estado", headers=admin["h"], json={"estado": "suspendido"}).status_code == 200
    assert client.get("/auth/me", headers=c["h"]).status_code == 403
    assert client.post("/auth/login", json={"email": c["email"], "password": PASSWORD}).status_code == 403


# ---------- solicitudes ----------
def test_turno_en_el_pasado_se_rechaza(client, escenario):
    assert pedir(client, escenario, fecha_hora_programada=turno(dias=-1)).status_code == 400


def test_turno_fuera_del_horario_del_prestador_se_rechaza(client, escenario):
    assert pedir(client, escenario, fecha_hora_programada=turno(hora=6)).status_code == 400          # antes de las 08:00
    assert pedir(client, escenario, fecha_hora_programada=turno(hora=19), duracion_horas=3).status_code == 400  # termina 22:00


def test_solicitud_sin_direccion_se_rechaza(client, admin, escenario):
    sin_direccion = registrar(client, "cliente")
    r = client.post("/solicitudes", headers=sin_direccion["h"],
                    json={"id_servicio": escenario["id_servicio"], "fecha_hora_programada": turno(), "duracion_horas": 1})
    assert r.status_code == 422


def test_duracion_invalida_se_rechaza(client, escenario):
    assert pedir(client, escenario, duracion_horas=0).status_code == 422
    assert pedir(client, escenario, duracion_horas=13).status_code == 422


def test_servicio_inexistente_devuelve_404(client, escenario):
    assert pedir(client, escenario, id_servicio=999999).status_code == 404


def test_dos_turnos_que_se_pisan_no_se_pueden_aceptar(client, escenario):
    p = escenario["prestador"]
    a = pedir(client, escenario, fecha_hora_programada=turno(hora=10), duracion_horas=2).json()["id_solicitud"]
    b = pedir(client, escenario, fecha_hora_programada=turno(hora=11), duracion_horas=2).json()["id_solicitud"]  # pisa 11-12
    assert client.post(f"/solicitudes/{a}/aceptar", headers=p["h"]).status_code == 200
    assert client.post(f"/solicitudes/{b}/aceptar", headers=p["h"]).status_code == 409
    # turnos consecutivos (12:00, justo cuando termina el primero) sí se pueden
    c = pedir(client, escenario, fecha_hora_programada=turno(hora=12), duracion_horas=1).json()["id_solicitud"]
    assert client.post(f"/solicitudes/{c}/aceptar", headers=p["h"]).status_code == 200


def test_estados_fuera_de_orden_devuelven_409(client, escenario):
    p = escenario["prestador"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    assert client.post(f"/solicitudes/{id_sol}/iniciar", headers=p["h"]).status_code == 409    # falta aceptar
    assert client.post(f"/solicitudes/{id_sol}/finalizar", headers=p["h"]).status_code == 409
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    assert client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"]).status_code == 409    # ya aceptada


def test_un_tercero_no_ve_ni_toca_la_solicitud(client, escenario):
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    intruso = registrar(client, "cliente")
    assert client.get(f"/solicitudes/{id_sol}", headers=intruso["h"]).status_code == 403
    assert client.post(f"/solicitudes/{id_sol}/cancelar", headers=intruso["h"]).status_code == 403
    assert client.get(f"/solicitudes/{id_sol}/mensajes", headers=intruso["h"]).status_code == 403
    otro_prestador = registrar(client, "prestador")
    assert client.post(f"/solicitudes/{id_sol}/aceptar", headers=otro_prestador["h"]).status_code == 403


def test_cancelar_con_pago_completado_reembolsa(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    client.post(f"/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "transferencia"})
    r = client.post(f"/solicitudes/{id_sol}/cancelar", headers=c["h"])
    assert r.status_code == 200 and r.json()["estado"] == "cancelada"
    assert client.get(f"/solicitudes/{id_sol}/pago", headers=c["h"]).json()["estado"] == "reembolsado"
    # y ya no se puede cancelar de nuevo
    assert client.post(f"/solicitudes/{id_sol}/cancelar", headers=c["h"]).status_code == 409


# ---------- pagos ----------
def test_pago_rechazado_por_pasarela_no_registra_pago(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    r = client.post(f"/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta", "simular_fallo": True})
    assert r.status_code == 402
    assert client.get(f"/solicitudes/{id_sol}/pago", headers=c["h"]).status_code == 404
    # reintento exitoso, y un segundo cobro se rechaza
    assert client.post(f"/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta"}).status_code == 201
    assert client.post(f"/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta"}).status_code == 409


def test_no_se_paga_una_solicitud_pendiente(client, escenario):
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    r = client.post(f"/solicitudes/{id_sol}/pago", headers=escenario["cliente"]["h"], json={"metodo_pago": "efectivo"})
    assert r.status_code == 409


# ---------- calificaciones y disputas ----------
def test_calificacion_solo_finalizada_una_vez_y_en_rango(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    nota = {"puntuacion_puntualidad": 5, "puntuacion_prolijidad": 5, "puntuacion_trato": 5}
    assert client.post(f"/solicitudes/{id_sol}/calificacion", headers=c["h"], json=nota).status_code == 409  # no finalizada
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    client.post(f"/solicitudes/{id_sol}/iniciar", headers=p["h"])
    client.post(f"/solicitudes/{id_sol}/finalizar", headers=p["h"])
    assert client.post(f"/solicitudes/{id_sol}/calificacion", headers=c["h"], json={**nota, "puntuacion_trato": 6}).status_code == 422
    assert client.post(f"/solicitudes/{id_sol}/calificacion", headers=c["h"], json=nota).status_code == 201
    assert client.post(f"/solicitudes/{id_sol}/calificacion", headers=c["h"], json=nota).status_code == 409  # duplicada
    assert client.post(f"/solicitudes/{id_sol}/calificacion", headers=p["h"], json=nota).status_code == 403  # el prestador no califica


def test_disputa_requiere_solicitud_aceptada_y_motivo_valido(client, escenario):
    c, p = escenario["cliente"], escenario["prestador"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    assert client.post(f"/solicitudes/{id_sol}/disputas", headers=c["h"], json={"motivo": "motivo suficientemente largo"}).status_code == 409
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    assert client.post(f"/solicitudes/{id_sol}/disputas", headers=c["h"], json={"motivo": "corto"}).status_code == 422
    assert client.post(f"/solicitudes/{id_sol}/disputas", headers=c["h"], json={"motivo": "motivo suficientemente largo"}).status_code == 201


def test_resolver_disputa_exige_resolucion(client, admin, escenario):
    c, p = escenario["cliente"], escenario["prestador"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    client.post(f"/solicitudes/{id_sol}/aceptar", headers=p["h"])
    id_disputa = client.post(f"/solicitudes/{id_sol}/disputas", headers=c["h"], json={"motivo": "motivo suficientemente largo"}).json()["id_disputa"]
    r = client.patch(f"/admin/disputas/{id_disputa}", headers=admin["h"], json={"estado": "resuelta"})
    assert r.status_code == 422


# ---------- mensajes y notificaciones ----------
def test_mensaje_vacio_y_leer_notificaciones(client, escenario):
    c, p = escenario["cliente"], escenario["prestador"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    assert client.post(f"/solicitudes/{id_sol}/mensajes", headers=c["h"], json={"contenido": ""}).status_code == 422
    client.post(f"/solicitudes/{id_sol}/mensajes", headers=c["h"], json={"contenido": "Hola"})
    antes = client.get("/notificaciones", headers=p["h"]).json()["no_leidas"]
    assert antes >= 2  # solicitud + mensaje
    una = client.get("/notificaciones", headers=p["h"]).json()["notificaciones"][0]["id_notificacion"]
    assert client.post(f"/notificaciones/{una}/leer", headers=p["h"]).status_code == 200
    assert client.post(f"/notificaciones/{una}/leer", headers=c["h"]).status_code == 404   # no es suya
    assert client.post("/notificaciones/leer-todas", headers=p["h"]).status_code == 200
    assert client.get("/notificaciones", headers=p["h"]).json()["no_leidas"] == 0


def test_busqueda_filtra_por_categoria_y_tarifa(client, escenario):
    id_servicio = escenario["id_servicio"]
    ids = lambda **p: [s["id_servicio"] for s in client.get("/servicios", params={"limite": 100, **p}).json()]
    assert id_servicio in ids(tarifa_max=5000)
    assert id_servicio not in ids(tarifa_max=4999)
    assert id_servicio not in ids(categoria=999999)


def test_horarios_del_detalle_salen_con_formato_hh_mm(client, escenario):
    d = client.get(f"/servicios/{escenario['id_servicio']}").json()
    assert d["disponibilidad"][0]["hora_inicio"] == "08:00"
    assert d["disponibilidad"][0]["hora_fin"] == "20:00"
