"""Tests de la Fase 4: Máquina de estados de contratación, agenda y validaciones."""
from .conftest import pedir, registrar, turno


def test_transiciones_validas_flujo_completo(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]

    # 1. Crear solicitud -> pendiente
    r_sol = pedir(client, escenario)
    assert r_sol.status_code == 201
    id_sol = r_sol.json()["id_solicitud"]
    assert r_sol.json()["estado"] == "pendiente"

    # 2. Prestador acepta -> aceptada
    r_acep = client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"])
    assert r_acep.status_code == 200
    assert r_acep.json()["estado"] == "aceptada"

    # 3. Prestador inicia -> en_curso
    r_ini = client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"])
    assert r_ini.status_code == 200
    assert r_ini.json()["estado"] == "en_curso"

    # 4. Prestador finaliza -> finalizada
    r_fin = client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"])
    assert r_fin.status_code == 200
    assert r_fin.json()["estado"] == "finalizada"


def test_todas_las_transiciones_invalidas_devuelven_409(client, escenario):
    p = escenario["prestador"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # Desde pendiente: no se puede iniciar ni finalizar
    assert client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"]).status_code == 409

    # Pasar a aceptada
    assert client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"]).status_code == 200

    # Desde aceptada: no se puede aceptar de nuevo ni finalizar
    assert client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"]).status_code == 409

    # Pasar a en_curso
    assert client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"]).status_code == 200

    # Desde en_curso: no se puede aceptar, iniciar de nuevo ni cancelar
    assert client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/cancelar", headers=p["h"]).status_code == 409

    # Pasar a finalizada
    assert client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"]).status_code == 200

    # Desde finalizada: no se puede realizar ninguna transición posterior
    assert client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/iniciar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/finalizar", headers=p["h"]).status_code == 409
    assert client.post(f"/api/v1/solicitudes/{id_sol}/cancelar", headers=p["h"]).status_code == 409


def test_rechazo_fecha_pasada_y_horario_invalido(client, escenario):
    # Fecha pasada -> 400
    r_pasada = pedir(client, escenario, fecha_hora_programada=turno(dias=-2))
    assert r_pasada.status_code == 400
    assert r_pasada.json()["error"]["codigo"] == "REGLA_NEGOCIO"

    # Fuera de horario (ej. 05:00 hs de la mañana) -> 400
    r_fuera = pedir(client, escenario, fecha_hora_programada=turno(hora=5))
    assert r_fuera.status_code == 400
    assert r_fuera.json()["error"]["codigo"] == "REGLA_NEGOCIO"


def test_conflicto_de_superposicion_horaria(client, escenario):
    p = escenario["prestador"]
    t1 = turno(hora=10, minuto=0)
    t2 = turno(hora=11, minuto=0)  # Se solapa con t1 (de 10:00 a 12:00)

    sol_a = pedir(client, escenario, fecha_hora_programada=t1, duracion_horas=2).json()["id_solicitud"]
    sol_b = pedir(client, escenario, fecha_hora_programada=t2, duracion_horas=2).json()["id_solicitud"]

    # Se acepta la primera
    assert client.post(f"/api/v1/solicitudes/{sol_a}/aceptar", headers=p["h"]).status_code == 200

    # La segunda debe fallar con 409 por superposición en la agenda del prestador
    r_choque = client.post(f"/api/v1/solicitudes/{sol_b}/aceptar", headers=p["h"])
    assert r_choque.status_code == 409
    assert r_choque.json()["error"]["codigo"] == "CONFLICTO"


def test_autorizacion_y_privacidad_recurso(client, escenario):
    id_sol = pedir(client, escenario).json()["id_solicitud"]
    tercero_cliente = registrar(client, "cliente")
    tercero_prestador = registrar(client, "prestador")

    # Tercero no puede consultar detalle
    assert client.get(f"/api/v1/solicitudes/{id_sol}", headers=tercero_cliente["h"]).status_code == 403
    # Tercero no puede cancelar
    assert client.post(f"/api/v1/solicitudes/{id_sol}/cancelar", headers=tercero_cliente["h"]).status_code == 403
    # Prestador no asignado no puede aceptar
    assert client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=tercero_prestador["h"]).status_code == 403


def test_cancelacion_con_reembolso_automatico(client, escenario):
    p, c = escenario["prestador"], escenario["cliente"]
    id_sol = pedir(client, escenario).json()["id_solicitud"]

    # Aceptar y pagar
    client.post(f"/api/v1/solicitudes/{id_sol}/aceptar", headers=p["h"])
    client.post(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"], json={"metodo_pago": "tarjeta"})

    # Cancelación por el cliente mientras está aceptada
    r_canc = client.post(f"/api/v1/solicitudes/{id_sol}/cancelar", headers=c["h"])
    assert r_canc.status_code == 200
    assert r_canc.json()["estado"] == "cancelada"

    # Verificar que el pago pasó automáticamente a reembolsado
    pago = client.get(f"/api/v1/solicitudes/{id_sol}/pago", headers=c["h"]).json()
    assert pago["estado"] == "reembolsado"
