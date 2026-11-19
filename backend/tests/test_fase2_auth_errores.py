"""Tests de la Fase 2: Auth, Roles y Manejo Centralizado de Errores con prefijo /api/v1."""
from .conftest import PASSWORD, email_unico, registrar


def test_registro_exitoso_cliente_y_prestador(client):
    email_c = email_unico("cliente")
    r_cli = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Ana",
            "apellido": "López",
            "email": email_c,
            "password": PASSWORD,
            "telefono": "1144556677",
            "tipo_cuenta": "cliente",
            "direccion": "San Martín 120, Ramos Mejía",
            "latitud": -34.6401,
            "longitud": -58.5620,
        },
    )
    assert r_cli.status_code == 201, r_cli.text
    data_cli = r_cli.json()
    assert data_cli["email"] == email_c
    assert data_cli["tipo_cuenta"] == "cliente"
    assert "password" not in data_cli and "contrasena" not in data_cli

    email_p = email_unico("prestador")
    r_pre = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Carlos",
            "apellido": "Díaz",
            "email": email_p,
            "password": PASSWORD,
            "telefono": "1122334455",
            "tipo_cuenta": "prestador",
            "descripcion": "Especialista en tapizados y alfombras",
            "latitud": -34.6450,
            "longitud": -58.5700,
        },
    )
    assert r_pre.status_code == 201, r_pre.text
    assert r_pre.json()["tipo_cuenta"] == "prestador"


def test_formato_error_validacion_422(client):
    r = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Pedro",
            "apellido": "Gómez",
            "email": "correo-invalido",
            "password": "123",  # muy corta
            "tipo_cuenta": "cliente",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert "error" in body
    assert body["error"]["codigo"] == "VALIDACION_ERROR"
    assert len(body["error"]["detalles"]) > 0


def test_formato_error_duplicado_409(client):
    u = registrar(client, "cliente")
    r = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Duplicado",
            "apellido": "Test",
            "email": u["email"],
            "password": PASSWORD,
            "tipo_cuenta": "cliente",
        },
    )
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["codigo"] == "CONFLICTO"


def test_login_y_token_jwt(client):
    u = registrar(client, "cliente")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": u["email"], "password": PASSWORD},
    )
    assert r.status_code == 200
    res = r.json()
    assert "access_token" in res
    assert res["token_type"] == "bearer"
    assert res["usuario"]["email"] == u["email"]
    assert "contrasena" not in res["usuario"]


def test_login_password_incorrecta_devuelve_401(client):
    u = registrar(client, "cliente")
    r = client.post(
        "/api/v1/auth/login",
        json={"email": u["email"], "password": "clave-erronea-xyz"},
    )
    assert r.status_code == 401
    body = r.json()
    assert body["error"]["codigo"] == "NO_AUTORIZADO"


def test_ver_y_actualizar_perfil(client):
    email = email_unico("cliente")
    r_reg = client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Valeria",
            "apellido": "Roca",
            "email": email,
            "password": PASSWORD,
            "tipo_cuenta": "cliente",
            "direccion": "Mitre 500",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET /me
    r_me = client.get("/api/v1/auth/me", headers=headers)
    assert r_me.status_code == 200
    assert r_me.json()["nombre"] == "Valeria"
    assert r_me.json()["perfil"]["direccion"] == "Mitre 500"
    assert "contrasena" not in r_me.json()

    # PUT /me
    r_put = client.put(
        "/api/v1/auth/me",
        headers=headers,
        json={
            "telefono": "1199887766",
            "direccion": "Av. de Mayo 1000, Ramos Mejía",
            "latitud": -34.6433,
            "longitud": -58.5644,
        },
    )
    assert r_put.status_code == 200
    data_up = r_put.json()
    assert data_up["telefono"] == "1199887766"
    assert data_up["perfil"]["direccion"] == "Av. de Mayo 1000, Ramos Mejía"
    assert float(data_up["perfil"]["latitud"]) == -34.6433


def test_cambiar_password(client):
    email = email_unico("prestador")
    client.post(
        "/api/v1/auth/registro",
        json={
            "nombre": "Tomás",
            "apellido": "Sosa",
            "email": email,
            "password": PASSWORD,
            "tipo_cuenta": "prestador",
        },
    )
    token = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Error: clave actual incorrecta
    r_err = client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers,
        json={"password_actual": "clave-falsa", "password_nueva": "nueva-clave-segura-123"},
    )
    assert r_err.status_code == 400
    assert r_err.json()["error"]["codigo"] == "REGLA_NEGOCIO"

    # Error: nueva clave igual a la actual
    r_misma = client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers,
        json={"password_actual": PASSWORD, "password_nueva": PASSWORD},
    )
    assert r_misma.status_code == 400

    # Cambio exitoso
    r_ok = client.post(
        "/api/v1/auth/cambiar-password",
        headers=headers,
        json={"password_actual": PASSWORD, "password_nueva": "nueva-clave-segura-123"},
    )
    assert r_ok.status_code == 200

    # Login con clave vieja debe fallar
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": PASSWORD},
    ).status_code == 401

    # Login con nueva clave debe tener éxito
    assert client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "nueva-clave-segura-123"},
    ).status_code == 200


def test_cuenta_suspendida_no_opera(client, admin):
    u = registrar(client, "cliente")
    # Admin suspende la cuenta
    r_susp = client.patch(
        f"/api/v1/admin/usuarios/{u['id']}/estado",
        headers=admin["h"],
        json={"estado": "suspendido"},
    )
    assert r_susp.status_code == 200

    # Intento de login da 403
    r_log = client.post(
        "/api/v1/auth/login",
        json={"email": u["email"], "password": PASSWORD},
    )
    assert r_log.status_code == 403
    assert r_log.json()["error"]["codigo"] == "ACCESO_DENEGADO"

    # Intento de acceder con token previo da 403
    r_op = client.get("/api/v1/auth/me", headers=u["h"])
    assert r_op.status_code == 403
    assert r_op.json()["error"]["codigo"] == "ACCESO_DENEGADO"
