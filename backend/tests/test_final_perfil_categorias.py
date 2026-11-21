"""Tests para la actualización final:
- Perfil: Biografía (máx 200 caracteres), hasta 5 redes sociales y restricción de 2 semanas para cambio de nombre/apellido.
- Categorías: Creación y confirmación inmediata desde 'Otros', y gestión por parte de administradores.
"""
from datetime import datetime, timedelta
import pytest
from tests.conftest import PASSWORD, admin, email_unico, registrar


def test_perfil_biografia_y_redes_sociales(client):
    cli = registrar(client, "cliente")

    # 1. Asignar biografía y 3 redes sociales válidas
    redes = [
        {"titulo": "Instagram", "url": "https://instagram.com/usuario_hogaru"},
        {"titulo": "LinkedIn", "url": "https://linkedin.com/in/usuario-hogaru"},
        {"titulo": "Sitio Web", "url": "https://mihogar.com"},
    ]
    r = client.put(
        "/auth/me",
        headers=cli["h"],
        json={"biografia": "Soy cliente frecuente y busco servicios de limpieza prolijos.", "redes_sociales": redes},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["biografia"] == "Soy cliente frecuente y busco servicios de limpieza prolijos."
    assert len(data["redes_sociales"]) == 3
    assert data["redes_sociales"][0]["titulo"] == "Instagram"

    # 2. Verificar que se refleje al consultar /auth/me
    r_get = client.get("/auth/me", headers=cli["h"])
    assert r_get.status_code == 200
    assert r_get.json()["biografia"] == "Soy cliente frecuente y busco servicios de limpieza prolijos."
    assert len(r_get.json()["redes_sociales"]) == 3

    # 3. Rechazar más de 5 redes sociales
    seis_redes = redes + [
        {"titulo": "Twitter", "url": "https://twitter.com/hogaru"},
        {"titulo": "Facebook", "url": "https://facebook.com/hogaru"},
        {"titulo": "TikTok", "url": "https://tiktok.com/@hogaru"},
    ]
    r_exceso = client.put("/auth/me", headers=cli["h"], json={"redes_sociales": seis_redes})
    assert r_exceso.status_code == 422 or r_exceso.status_code == 400


def test_restriccion_dos_semanas_cambio_nombre(client):
    cli = registrar(client, "cliente")

    # 1. Primer cambio de nombre y apellido -> debe permitirse
    r_primer_cambio = client.put(
        "/auth/me",
        headers=cli["h"],
        json={"nombre": "NuevoNombre", "apellido": "NuevoApellido"},
    )
    assert r_primer_cambio.status_code == 200, r_primer_cambio.text
    assert r_primer_cambio.json()["nombre"] == "NuevoNombre"
    assert r_primer_cambio.json()["apellido"] == "NuevoApellido"
    assert r_primer_cambio.json()["puede_cambiar_nombre"] is False
    assert r_primer_cambio.json()["dias_para_cambio_nombre"] > 0

    # 2. Segundo intento inmediato de cambio de nombre -> debe bloquearse por 2 semanas (400)
    r_intento_bloqueado = client.put(
        "/auth/me",
        headers=cli["h"],
        json={"nombre": "OtroNombre"},
    )
    assert r_intento_bloqueado.status_code == 400
    assert "2 semanas" in r_intento_bloqueado.json()["detail"]

    # 3. Modificar biografía o redes SIN cambiar nombre -> sí debe permitirse
    r_cambio_bio = client.put(
        "/auth/me",
        headers=cli["h"],
        json={"biografia": "Nueva biografía actualizada sin alterar el nombre."},
    )
    assert r_cambio_bio.status_code == 200
    assert r_cambio_bio.json()["biografia"] == "Nueva biografía actualizada sin alterar el nombre."


def test_categoria_desde_otros_inmediatamente_disponible(client):
    prestador = registrar(client, "prestador", descripcion="Prestador independiente")

    cat_nombre = f"Pulido de Parquet {email_unico('cat')}"
    # 1. Crear categoría directamente (como al usar la opción 'Otros' y confirmar)
    r = client.post(
        "/categorias",
        headers=prestador["h"],
        json={"nombre": cat_nombre, "descripcion": "Restauración y pulido de pisos de madera", "icono": "🪵"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["estado"] == "activa"
    id_cat = data["id_categoria"]

    # 2. Verificar que cualquier otro usuario (incluso anónimo o cliente) ya la vea disponible en /categorias
    r_list = client.get("/categorias")
    assert r_list.status_code == 200
    categorias_activas = r_list.json()
    assert any(c["id_categoria"] == id_cat for c in categorias_activas)


def test_admin_gestion_y_eliminacion_categorias(client, admin):
    # 1. Crear categoría redundante
    cat_redundante = f"Limpieza Duplicada {email_unico('cat')}"
    r_cat = client.post(
        "/admin/categorias",
        headers=admin["h"],
        json={"nombre": cat_redundante, "descripcion": "Categoría para prueba de borrado", "icono": "🗑️"},
    )
    assert r_cat.status_code == 201
    id_cat = r_cat.json()["id_categoria"]

    # 2. Admin la elimina
    r_del = client.delete(f"/admin/categorias/{id_cat}", headers=admin["h"])
    assert r_del.status_code == 200

    # 3. Ya no debe estar en /categorias
    r_list = client.get("/categorias")
    assert not any(c["id_categoria"] == id_cat for c in r_list.json())
