"""Sistema de migraciones versionadas y carga de datos de prueba (Seed)."""
from pathlib import Path
import pymysql
from pymysql.cursors import DictCursor
from . import config
from .db import nueva_conexion

CARPETA_BASE = Path(__file__).resolve().parent.parent.parent / "base_de_datos"
CARPETA_MIGRACIONES = CARPETA_BASE / "migraciones"


def asegurar_base_de_datos():
    """Crea la base de datos si no existe conectando al servidor MySQL sin base."""
    conn = pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
    finally:
        conn.close()


def inicializar_tabla_migraciones(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS _migraciones (
                id_migracion INT AUTO_INCREMENT PRIMARY KEY,
                version      VARCHAR(50) NOT NULL UNIQUE,
                nombre       VARCHAR(100) NOT NULL,
                aplicada_en  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
            """
        )
    conn.commit()


def ejecutar_script_sql(conn, contenido_sql: str):
    """Ejecuta un script SQL dividiendo sentencias por delimitadores comunes (;)."""
    with conn.cursor() as cur:
        # Manejo simple de sentencias separadas por punto y coma
        sentencias = []
        actual = []
        en_delimiter = False
        delimiter = ";"

        for linea in contenido_sql.splitlines():
            linea_limpia = linea.strip()
            if not linea_limpia or linea_limpia.startswith("--"):
                continue

            if linea_limpia.upper().startswith("DELIMITER"):
                partes = linea_limpia.split()
                if len(partes) > 1:
                    delimiter = partes[1]
                continue

            actual.append(linea)
            if linea_limpia.endswith(delimiter):
                stmt = "\n".join(actual)
                if delimiter != ";":
                    stmt = stmt.rstrip()
                    if stmt.endswith(delimiter):
                        stmt = stmt[:-len(delimiter)]
                sentencias.append(stmt.strip())
                actual = []

        if actual:
            stmt = "\n".join(actual).strip()
            if stmt:
                sentencias.append(stmt)

        for stmt in sentencias:
            stmt_limpio = stmt.strip().rstrip(";")
            if stmt_limpio:
                cur.execute(stmt_limpio)
    conn.commit()


def aplicar_migraciones():
    """Busca y ejecuta las migraciones pendientes en base_de_datos/migraciones/."""
    asegurar_base_de_datos()
    conn = nueva_conexion()
    try:
        inicializar_tabla_migraciones(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT version FROM _migraciones")
            aplicadas = {fila["version"] for fila in cur.fetchall()}

        archivos = sorted(CARPETA_MIGRACIONES.glob("*.sql"))
        if not archivos:
            print("No se encontraron archivos de migración.")
            return

        nuevas = 0
        for archivo in archivos:
            version = archivo.name.split("_")[0]
            if version in aplicadas:
                continue

            print(f"Aplicando migración {archivo.name}...")
            contenido = archivo.read_text(encoding="utf-8")
            ejecutar_script_sql(conn, contenido)

            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO _migraciones (version, nombre) VALUES (%s, %s)",
                    (version, archivo.name),
                )
            conn.commit()
            print(f"Migración {archivo.name} aplicada exitosamente.")
            nuevas += 1

        if nuevas == 0:
            print("La base de datos ya está al día. No hay migraciones pendientes.")
        else:
            print(f"Se aplicaron {nuevas} migración(es) correctamente.")
    finally:
        conn.close()


def cargar_seed():
    """Carga los datos iniciales y de prueba desde hogaru_datos_prueba.sql."""
    asegurar_base_de_datos()
    conn = nueva_conexion()
    try:
        archivo_seed = CARPETA_BASE / "hogaru_datos_prueba.sql"
        if not archivo_seed.exists():
            print(f"No se encontró el archivo de seed en {archivo_seed}")
            return

        print("Cargando datos de prueba (seed)...")
        contenido = archivo_seed.read_text(encoding="utf-8")
        ejecutar_script_sql(conn, contenido)
        print("Datos de prueba cargados exitosamente.")
    finally:
        conn.close()
