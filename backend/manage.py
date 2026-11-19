"""Utilidades de administración y base de datos para Hogaru.

Comandos disponibles:
    python manage.py servidor                       # Inicia el servidor de desarrollo con auto-recarga
    python manage.py migrar                         # Aplica migraciones versionadas pendientes
    python manage.py seed                           # Carga los datos de prueba iniciales
    python manage.py crear-admin EMAIL PASSWORD [NOMBRE] [APELLIDO]
    python manage.py passwords-demo [PASSWORD]     # Asigna clave demo a usuarios @hogaru.test
"""
import sys
from pathlib import Path

from app.db import nueva_conexion
from app.migraciones import aplicar_migraciones, cargar_seed
from app.security import hash_password


def iniciar_servidor():
    import uvicorn
    backend_dir = Path(__file__).resolve().parent
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, app_dir=str(backend_dir))


def crear_admin(email, password, nombre="Admin", apellido="Hogaru"):
    conn = nueva_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO usuario (nombre, apellido, email, contrasena, tipo_cuenta) "
                "VALUES (%s, %s, %s, %s, 'administrador')",
                (nombre, apellido, email.lower(), hash_password(password)),
            )
            cur.execute(
                "INSERT INTO administrador (id_admin, nivel_permiso) VALUES (%s, 'superadmin')",
                (cur.lastrowid,),
            )
        conn.commit()
        print(f"Administrador creado: {email}")
    finally:
        conn.close()


def passwords_demo(password="hogaru123"):
    conn = nueva_conexion()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE usuario SET contrasena = %s WHERE email LIKE %s",
                (hash_password(password), "%@hogaru.test"),
            )
            print(f"Contraseña '{password}' asignada a {cur.rowcount} usuarios @hogaru.test")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    comando, *args = sys.argv[1:] or ["ayuda"]
    if comando in ("servidor", "start", "run"):
        iniciar_servidor()
    elif comando == "migrar":
        aplicar_migraciones()
    elif comando == "seed":
        cargar_seed()
    elif comando == "crear-admin" and len(args) >= 2:
        crear_admin(*args)
    elif comando == "passwords-demo":
        passwords_demo(*args)
    else:
        print(__doc__)
