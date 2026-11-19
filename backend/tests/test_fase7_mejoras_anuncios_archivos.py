"""Tests de las mejoras: Carga física de PDFs, Categorías dinámicas y Marketplace Inverso (Anuncios)."""
import io
from datetime import datetime, timedelta
import pytest
from .conftest import PASSWORD, admin, autenticar, email_unico, registrar, turno


def test_subida_archivo_pdf_verificacion(client):
    prestador = registrar(client, "prestador", descripcion="Prestador con PDF")
    
    contenido_pdf = b"%PDF-1.5 \n%Dummy PDF content for testing verification"
    archivos = {
        "archivo": ("mi_certificado.pdf", io.BytesIO(contenido_pdf), "application/pdf")
    }
    datos = {"tipo_documento": "antecedentes_penales"}
    
    r = client.post("/verificacion/subir", files=archivos, data=datos, headers=prestador["h"])
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["tipo_documento"] == "antecedentes_penales"
    assert data["archivo_url"].startswith("/uploads/documentos/")
    assert data["archivo_url"].endswith(".pdf")
    assert data["estado_documento"] == "pendiente"


def test_subida_archivo_formato_invalido(client):
    prestador = registrar(client, "prestador", descripcion="Prestador con ejecutable")
    
    archivos = {
        "archivo": ("virus.exe", io.BytesIO(b"malicious script"), "application/x-msdownload")
    }
    datos = {"tipo_documento": "dni"}
    
    r = client.post("/verificacion/subir", files=archivos, data=datos, headers=prestador["h"])
    assert r.status_code == 400, r.text
    assert "Formato no permitido" in r.json()["detail"]


def test_gestion_dinamica_categorias(client, admin):
    cliente = registrar(client, "cliente", direccion="Calle Falsa 123")
    
    # 1. Cliente sugiere una nueva categoría
    r = client.post(
        "/categorias/sugerir",
        json={"nombre": f"Tapizados {email_unico('cat')}", "descripcion": "Limpieza a vapor de sillones", "icono": "🛋️"},
        headers=cliente["h"],
    )
    assert r.status_code == 201, r.text
    id_cat = r.json()["id_categoria"]
    assert r.json()["estado"] == "propuesta"
    
    # 2. Las categorías públicas aún no la muestran porque está en propuesta
    r_publicas = client.get("/categorias")
    assert not any(c["id_categoria"] == id_cat for c in r_publicas.json())
    
    # 3. Administrador lista categorías y la ve
    r_admin = client.get("/admin/categorias", headers=admin["h"])
    assert r_admin.status_code == 200
    cat_admin = next((c for c in r_admin.json() if c["id_categoria"] == id_cat), None)
    assert cat_admin is not None
    assert cat_admin["estado"] == "propuesta"
    
    # 4. Administrador aprueba la categoría
    r_aprob = client.post(f"/admin/categorias/{id_cat}/aprobar", headers=admin["h"])
    assert r_aprob.status_code == 200
    assert r_aprob.json()["estado"] == "activa"
    
    # 5. Ahora aparece en el catálogo público
    r_publicas_despues = client.get("/categorias")
    assert any(c["id_categoria"] == id_cat for c in r_publicas_despues.json())


def test_flujo_marketplace_inverso_anuncios(client, admin):
    cliente = registrar(client, "cliente", direccion="Av. Libertador 4500")
    prestador = registrar(client, "prestador", descripcion="Experto en limpieza")
    
    # 1. Aprobar prestador para que pueda postularse
    # Cargar y aprobar DNI y Antecedentes
    r_doc1 = client.post(
        "/verificacion/documentos",
        json={"tipo_documento": "dni", "archivo_url": "https://hogaru.test/dni.pdf"},
        headers=prestador["h"],
    )
    r_doc2 = client.post(
        "/verificacion/documentos",
        json={"tipo_documento": "antecedentes_penales", "archivo_url": "https://hogaru.test/ant_limpios.pdf"},
        headers=prestador["h"],
    )
    client.post(f"/admin/documentos/{r_doc1.json()['id_documento']}/resolver", json={"estado": "aprobado"}, headers=admin["h"])
    client.post(f"/admin/documentos/{r_doc2.json()['id_documento']}/resolver", json={"estado": "aprobado"}, headers=admin["h"])
    
    # 2. Cliente publica un anuncio
    fecha_futura = (datetime.now() + timedelta(days=5)).replace(hour=14, minute=0, second=0).isoformat()
    anuncio_payload = {
        "id_categoria": 1,
        "titulo": "Limpieza integral departamento 3 ambientes",
        "descripcion": "Necesito limpieza profunda luego de una mudanza, incluye vidrios.",
        "presupuesto": 35000.0,
        "fecha_servicio": fecha_futura,
        "duracion_horas": 4.0,
        "direccion": "Av. Libertador 4500, CABA",
    }
    r_anuncio = client.post("/anuncios", json=anuncio_payload, headers=cliente["h"])
    assert r_anuncio.status_code == 201, r_anuncio.text
    id_anuncio = r_anuncio.json()["id_anuncio"]
    
    # 3. Listar anuncios públicos
    r_lista = client.get("/anuncios")
    assert r_lista.status_code == 200
    assert any(a["id_anuncio"] == id_anuncio for a in r_lista.json())
    
    # 4. Prestador verificado se postula con una cotización
    r_postulacion = client.post(
        f"/anuncios/{id_anuncio}/postular",
        json={"propuesta_precio": 32000.0, "mensaje": "Tengo disponibilidad y llevo mis propios productos."},
        headers=prestador["h"],
    )
    assert r_postulacion.status_code == 201, r_postulacion.text
    id_postulacion = r_postulacion.json()["id_postulacion"]
    
    # 5. Cliente visualiza las ofertas recibidas
    r_postulaciones = client.get(f"/anuncios/{id_anuncio}/postulaciones", headers=cliente["h"])
    assert r_postulaciones.status_code == 200
    assert len(r_postulaciones.json()) == 1
    assert float(r_postulaciones.json()[0]["propuesta_precio"]) == 32000.0
    
    # 6. Cliente adjudica el trabajo al prestador
    r_adjudicar = client.post(f"/anuncios/{id_anuncio}/adjudicar/{id_postulacion}", headers=cliente["h"])
    assert r_adjudicar.status_code == 200, r_adjudicar.text
    id_solicitud = r_adjudicar.json()["id_solicitud"]
    
    # 7. Verificar que la solicitud existe y está aceptada
    r_sol = client.get(f"/solicitudes/{id_solicitud}", headers=cliente["h"])
    assert r_sol.status_code == 200
    assert r_sol.json()["estado"] == "aceptada"
    assert r_sol.json()["id_anuncio"] == id_anuncio


def test_verificacion_con_dni_frente_y_dorso(client, admin):
    """Valida que un prestador pueda ser verificado con fotos separadas de DNI Frente y Dorso + Antecedentes."""
    prestador = registrar(client, "prestador", descripcion="Prestador con fotos de DNI")

    # 1. Subir DNI Frente
    archivos_frente = {"archivo": ("frente.jpg", io.BytesIO(b"dummy image frente"), "image/jpeg")}
    r_frente = client.post("/verificacion/subir", files=archivos_frente, data={"tipo_documento": "dni_frente"}, headers=prestador["h"])
    assert r_frente.status_code == 201
    id_frente = r_frente.json()["id_documento"]

    # 2. Subir DNI Dorso
    archivos_dorso = {"archivo": ("dorso.png", io.BytesIO(b"dummy image dorso"), "image/png")}
    r_dorso = client.post("/verificacion/subir", files=archivos_dorso, data={"tipo_documento": "dni_dorso"}, headers=prestador["h"])
    assert r_dorso.status_code == 201
    id_dorso = r_dorso.json()["id_documento"]

    # 3. Subir Antecedentes
    archivos_ant = {"archivo": ("antecedentes.pdf", io.BytesIO(b"%PDF dummy"), "application/pdf")}
    r_ant = client.post("/verificacion/subir", files=archivos_ant, data={"tipo_documento": "antecedentes_penales"}, headers=prestador["h"])
    assert r_ant.status_code == 201
    id_ant = r_ant.json()["id_documento"]

    # Verificar que el prestador sigue pendiente
    me_resp = client.get("/auth/me", headers=prestador["h"])
    assert me_resp.json()["perfil"]["estado_verificacion"] == "pendiente"

    # 4. Admin aprueba DNI Frente -> Sigue pendiente
    client.post(f"/admin/documentos/{id_frente}/resolver", json={"estado": "aprobado"}, headers=admin["h"])
    me_resp = client.get("/auth/me", headers=prestador["h"])
    assert me_resp.json()["perfil"]["estado_verificacion"] == "pendiente"

    # 5. Admin aprueba DNI Dorso -> Sigue pendiente (falta antecedentes)
    client.post(f"/admin/documentos/{id_dorso}/resolver", json={"estado": "aprobado"}, headers=admin["h"])
    me_resp = client.get("/auth/me", headers=prestador["h"])
    assert me_resp.json()["perfil"]["estado_verificacion"] == "pendiente"

    # 6. Admin aprueba Antecedentes -> Ahora sí pasa a aprobado!
    client.post(f"/admin/documentos/{id_ant}/resolver", json={"estado": "aprobado"}, headers=admin["h"])
    me_resp = client.get("/auth/me", headers=prestador["h"])
    assert me_resp.json()["perfil"]["estado_verificacion"] == "aprobado"

