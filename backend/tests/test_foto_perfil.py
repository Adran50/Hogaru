"""Tests para el módulo de Foto de Perfil en Hogaru API."""
import io
from pathlib import Path
from tests.conftest import registrar


def test_ver_perfil_incluye_campo_foto(client):
    """Verifica que el endpoint /auth/me incluya el campo foto_perfil."""
    cli = registrar(client, "cliente")
    r = client.get("/auth/me", headers=cli["h"])
    assert r.status_code == 200
    data = r.json()
    assert "foto_perfil" in data
    # Al inicio no tiene foto asignada
    assert data["foto_perfil"] is None


def test_subir_foto_perfil_formato_invalido(client):
    """Rechaza archivos que no sean imágenes (ej. texto o scripts)."""
    cli = registrar(client, "cliente")
    archivo_falso = io.BytesIO(b"console.log('malicioso');")
    r = client.post(
        "/auth/foto-perfil",
        headers=cli["h"],
        files={"archivo": ("script.js", archivo_falso, "application/javascript")},
    )
    assert r.status_code == 400
    assert "Formato de imagen inválido" in r.json()["detail"]


def test_subir_y_eliminar_foto_perfil(client):
    """Flujo completo: subida de imagen JPG/PNG, persistencia en BD y eliminación."""
    cli = registrar(client, "cliente")

    # 1. Subir imagen válida simulada
    img_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 100
    archivo = io.BytesIO(img_bytes)

    r_subida = client.post(
        "/auth/foto-perfil",
        headers=cli["h"],
        files={"archivo": ("avatar.jpg", archivo, "image/jpeg")},
    )
    assert r_subida.status_code == 200
    res_data = r_subida.json()
    assert "foto_perfil" in res_data
    foto_url = res_data["foto_perfil"]
    assert foto_url.startswith("/uploads/perfiles/perfil_")
    assert foto_url.endswith(".jpg")

    # 2. Verificar que /auth/me ahora retorne la foto
    r_me = client.get("/auth/me", headers=cli["h"])
    assert r_me.status_code == 200
    assert r_me.json()["foto_perfil"] == foto_url

    # 3. Verificar que el archivo físico realmente exista en disco
    ruta_archivo = Path(__file__).resolve().parent.parent / foto_url.lstrip("/")
    assert ruta_archivo.exists()

    # 4. Eliminar la foto de perfil
    r_del = client.delete("/auth/foto-perfil", headers=cli["h"])
    assert r_del.status_code == 200
    assert r_del.json()["foto_perfil"] is None

    # 5. Comprobar que en /auth/me volvió a quedar en null
    r_me_post = client.get("/auth/me", headers=cli["h"])
    assert r_me_post.status_code == 200
    assert r_me_post.json()["foto_perfil"] is None


def test_actualizar_perfil_con_foto_url(client):
    """PUT /auth/me permite actualizar directamente la URL de la foto."""
    cli = registrar(client, "cliente")
    nueva_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400"
    r_put = client.put("/auth/me", headers=cli["h"], json={"foto_perfil": nueva_url})
    assert r_put.status_code == 200
    assert r_put.json()["foto_perfil"] == nueva_url

    # Limpiar a None
    r_clear = client.delete("/auth/foto-perfil", headers=cli["h"])
    assert r_clear.status_code == 200
    assert r_clear.json()["foto_perfil"] is None


def test_prestador_con_foto_en_vista_servicios(client):
    """Verifica que v_prestadores_disponibles y /servicios expongan foto_perfil del prestador."""
    # El prestador predefinido Marisa (id=2) tiene foto configurada en la migración 008
    r_servicios = client.get("/servicios?limite=10")
    assert r_servicios.status_code == 200
    servicios = r_servicios.json()
    assert len(servicios) > 0
    # Al menos un servicio debe tener el campo foto_perfil
    assert any("foto_perfil" in s for s in servicios)
