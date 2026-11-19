"""Tests de la Fase 3: Verificación con BackgroundCheckProvider y Servicios con Haversine y filtros."""
from .conftest import registrar, verificar_prestador


def test_verificacion_con_chequeo_de_antecedentes_mock(client, admin):
    prestador = registrar(client, "prestador", descripcion="Prestador antecedentes par")

    # DNI
    r_dni = client.post(
        "/api/v1/verificacion/documentos",
        headers=prestador["h"],
        json={"tipo_documento": "dni", "archivo_url": "/docs/dni_40000000.pdf"},
    )
    assert r_dni.status_code == 201

    # Antecedentes con terminación par -> apto simulado
    r_ant_par = client.post(
        "/api/v1/verificacion/documentos",
        headers=prestador["h"],
        json={"tipo_documento": "antecedentes_penales", "archivo_url": "/docs/antecedentes_40000002.pdf"},
    )
    assert r_ant_par.status_code == 201
    data_par = r_ant_par.json()
    assert "prechequeo_antecedentes" in data_par
    assert data_par["prechequeo_antecedentes"]["apto"] is True
    assert data_par["prechequeo_antecedentes"]["codigo"] == "SIN_ANTECEDENTES"

    # Admin aprueba ambos documentos
    docs = client.get("/api/v1/admin/documentos", headers=admin["h"]).json()
    ids_prestador = [d["id_documento"] for d in docs if d["id_prestador"] == prestador["id"]]
    for id_doc in ids_prestador:
        r_res = client.post(
            f"/api/v1/admin/documentos/{id_doc}/resolver",
            headers=admin["h"],
            json={"estado": "aprobado", "motivo": "Documentación validada"},
        )
        assert r_res.status_code == 200

    # Estado final del prestador: aprobado
    me = client.get("/api/v1/auth/me", headers=prestador["h"]).json()
    assert me["perfil"]["estado_verificacion"] == "aprobado"


def test_antecedentes_impar_observado_y_rechazo_admin(client, admin):
    prestador = registrar(client, "prestador", descripcion="Prestador antecedentes impar")

    # DNI aprobado
    r_dni = client.post(
        "/api/v1/verificacion/documentos",
        headers=prestador["h"],
        json={"tipo_documento": "dni", "archivo_url": "/docs/dni_35000000.pdf"},
    )
    client.post(
        f"/api/v1/admin/documentos/{r_dni.json()['id_documento']}/resolver",
        headers=admin["h"],
        json={"estado": "aprobado"},
    )

    # Antecedentes con terminación impar -> observado
    r_ant = client.post(
        "/api/v1/verificacion/documentos",
        headers=prestador["h"],
        json={"tipo_documento": "antecedentes_penales", "archivo_url": "/docs/antecedentes_35000001.pdf"},
    )
    assert r_ant.status_code == 201
    assert r_ant.json()["prechequeo_antecedentes"]["apto"] is False

    # Admin rechaza
    r_rech = client.post(
        f"/api/v1/admin/documentos/{r_ant.json()['id_documento']}/resolver",
        headers=admin["h"],
        json={"estado": "rechazado", "motivo": "Registros de antecedentes detectados"},
    )
    assert r_rech.status_code == 200
    assert r_rech.json()["estado_verificacion_prestador"] == "rechazado"


def test_prestador_no_aprobado_no_puede_publicar(client):
    p_pendiente = registrar(client, "prestador", descripcion="Pendiente")
    r = client.post(
        "/api/v1/servicios",
        headers=p_pendiente["h"],
        json={"id_categoria": 1, "tarifa": "4000.00"},
    )
    assert r.status_code == 403
    assert r.json()["error"]["codigo"] == "ACCESO_DENEGADO"


def test_busqueda_filtros_tarifa_puntuacion_y_haversine(client, admin):
    # Crear prestador aprobado con coordenadas en Morón (-34.653, -58.621)
    p_moron = registrar(client, "prestador", descripcion="Prestador Moron")
    verificar_prestador(client, admin, p_moron)
    # Asignar coordenadas
    client.put(
        "/api/v1/auth/me",
        headers=p_moron["h"],
        json={"latitud": -34.6530, "longitud": -58.6210},
    )

    cat = client.get("/api/v1/categorias").json()[0]["id_categoria"]

    # Publicar servicio en Morón a $4500 con disponibilidad
    r_s = client.post(
        "/api/v1/servicios",
        headers=p_moron["h"],
        json={
            "id_categoria": cat,
            "descripcion": "Servicio Morón Centro",
            "tarifa": "4500.00",
            "disponibilidad": [
                {"dia_semana": 1, "hora_inicio": "08:00", "hora_fin": "16:00"},
                {"dia_semana": 3, "hora_inicio": "08:00", "hora_fin": "16:00"},
            ],
        },
    )
    assert r_s.status_code == 201
    id_serv = r_s.json()["id_servicio"]

    # 1. Filtro por rango de tarifa
    r_tarifa_ok = client.get("/api/v1/servicios", params={"tarifa_min": 4000, "tarifa_max": 5000})
    ids_ok = [s["id_servicio"] for s in r_tarifa_ok.json()]
    assert id_serv in ids_ok

    r_tarifa_fuera = client.get("/api/v1/servicios", params={"tarifa_min": 5000})
    ids_fuera = [s["id_servicio"] for s in r_tarifa_fuera.json()]
    assert id_serv not in ids_fuera

    # 2. Filtro por día y horario
    r_dia_lunes = client.get("/api/v1/servicios", params={"dia_semana": 1, "hora": "10:00"})
    assert id_serv in [s["id_servicio"] for s in r_dia_lunes.json()]

    r_dia_domingo = client.get("/api/v1/servicios", params={"dia_semana": 7})
    assert id_serv not in [s["id_servicio"] for s in r_dia_domingo.json()]

    # 3. Filtro geográfico Haversine desde Morón (distancia ~0.2 km dentro de radio de 2 km)
    r_geo_cerca = client.get(
        "/api/v1/servicios",
        params={"lat": -34.6510, "lng": -58.6190, "radio_km": 5, "orden": "cercania"},
    )
    assert r_geo_cerca.status_code == 200
    res_cerca = r_geo_cerca.json()
    item_moron = next((s for s in res_cerca if s["id_servicio"] == id_serv), None)
    assert item_moron is not None
    assert item_moron["distancia_km"] is not None
    assert item_moron["distancia_km"] <= 5.0

    # 4. Filtro Haversine fuera de radio (radio 0.05 km)
    r_geo_lejos = client.get(
        "/api/v1/servicios",
        params={"lat": -34.6510, "lng": -58.6190, "radio_km": 0.05},
    )
    assert id_serv not in [s["id_servicio"] for s in r_geo_lejos.json()]


def test_edicion_y_reemplazo_disponibilidad(client, admin):
    p = registrar(client, "prestador", descripcion="Prestador Edicion")
    verificar_prestador(client, admin, p)
    cat = client.get("/api/v1/categorias").json()[0]["id_categoria"]

    r_s = client.post(
        "/api/v1/servicios",
        headers=p["h"],
        json={
            "id_categoria": cat,
            "descripcion": "Original",
            "tarifa": "3000.00",
            "disponibilidad": [{"dia_semana": 2, "hora_inicio": "09:00", "hora_fin": "12:00"}],
        },
    )
    id_s = r_s.json()["id_servicio"]

    # Editar tarifa
    r_patch = client.patch(
        f"/api/v1/servicios/{id_s}",
        headers=p["h"],
        json={"tarifa": "3800.00", "activo": True},
    )
    assert r_patch.status_code == 200

    # Reemplazar disponibilidad
    r_disp = client.put(
        f"/api/v1/servicios/{id_s}/disponibilidad",
        headers=p["h"],
        json=[
            {"dia_semana": 4, "hora_inicio": "10:00", "hora_fin": "18:00"},
            {"dia_semana": 5, "hora_inicio": "10:00", "hora_fin": "18:00"},
        ],
    )
    assert r_disp.status_code == 200
    assert r_disp.json()["franjas_configuradas"] == 2

    # Verificar detalle
    detalle = client.get(f"/api/v1/servicios/{id_s}").json()
    assert float(detalle["tarifa"]) == 3800.00
    assert len(detalle["disponibilidad"]) == 2
    assert detalle["disponibilidad"][0]["hora_inicio"] == "10:00"
