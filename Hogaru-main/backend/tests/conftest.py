"""Fixtures compartidos. Los tests corren contra la base configurada en .env
(usá una base de prueba, no la de producción): cada test crea sus propios
usuarios con emails únicos, así que no hace falta limpiar entre corridas."""
import uuid
from datetime import datetime, timedelta

import pytest  # type: ignore[import-not-found]
from fastapi.testclient import TestClient  # type: ignore[import-not-found]

from app.db import nueva_conexion
from app.main import app
from app.security import hash_password

PASSWORD = "clave-segura-123"


def email_unico(prefijo):
    return f"{prefijo}_{uuid.uuid4().hex[:10]}@hogaru.test"


def turno(dias=3, hora=10, minuto=0):
    """Fecha futura (ISO) a las `hora`:`minuto`, dentro de `dias` días."""
    f = (datetime.now() + timedelta(days=dias)).replace(hour=hora, minute=minuto, second=0, microsecond=0)
    return f.isoformat()


def autenticar(client, email):
    r = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def registrar(client, tipo, **extra):
    email = email_unico(tipo)
    cuerpo = {"nombre": tipo.capitalize(), "apellido": "Prueba", "email": email,
              "password": PASSWORD, "tipo_cuenta": tipo, **extra}
    r = client.post("/auth/registro", json=cuerpo)
    assert r.status_code == 201, r.text
    return {"id": r.json()["id_usuario"], "email": email, "h": autenticar(client, email)}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin(client):
    email = email_unico("admin")
    conn = nueva_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO usuario (nombre, apellido, email, contrasena, tipo_cuenta) "
                "VALUES ('Admin', 'Test', %s, %s, 'administrador')", (email, hash_password(PASSWORD)))
            cur.execute("INSERT INTO administrador (id_admin) VALUES (%s)", (cur.lastrowid,))
        conn.commit()
    finally:
        conn.close()
    return {"email": email, "h": autenticar(client, email)}


def verificar_prestador(client, admin, prestador):
    for tipo in ("dni", "antecedentes_penales"):
        r = client.post("/verificacion/documentos", headers=prestador["h"],
                        json={"tipo_documento": tipo, "archivo_url": f"/docs/{tipo}.pdf"})
        assert r.status_code == 201, r.text
        r = client.post(f"/admin/documentos/{r.json()['id_documento']}/resolver",
                        headers=admin["h"], json={"estado": "aprobado"})
        assert r.status_code == 200, r.text


@pytest.fixture
def escenario(client, admin):
    """Prestador verificado con un servicio disponible todos los días 08:00-20:00 + un cliente."""
    prestador = registrar(client, "prestador", descripcion="Prestador de prueba")
    verificar_prestador(client, admin, prestador)
    categoria = client.get("/categorias").json()[0]["id_categoria"]
    r = client.post("/servicios", headers=prestador["h"], json={
        "id_categoria": categoria, "descripcion": "Servicio de prueba", "tarifa": "5000.00",
        "disponibilidad": [{"dia_semana": d, "hora_inicio": "08:00", "hora_fin": "20:00"} for d in range(1, 8)],
    })
    assert r.status_code == 201, r.text
    cliente = registrar(client, "cliente", direccion="Calle Falsa 123, Morón")
    return {"prestador": prestador, "cliente": cliente, "id_servicio": r.json()["id_servicio"]}


def pedir(client, esc, **cambios):
    cuerpo = {"id_servicio": esc["id_servicio"], "fecha_hora_programada": turno(),
              "duracion_horas": 2, **cambios}
    return client.post("/solicitudes", headers=esc["cliente"]["h"], json=cuerpo)
