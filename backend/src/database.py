import os
import re
import sqlite3
from pathlib import Path

from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except Exception:
    psycopg2 = None
    RealDictCursor = None

# Cargamos la ruta desde el .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()

def _resolve_db_path() -> str:
    env_path = os.getenv("DB_PATH")
    if env_path:
        return env_path
    return (DATA_DIR / "deuna_negocios.db").as_posix()

def _pg_conn_kwargs() -> dict:
    return {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": int(os.getenv("PG_PORT", "5432")),
        "dbname": os.getenv("PG_DB", "deuna_negocios"),
        "user": os.getenv("PG_USER", "postgres"),
        "password": os.getenv("PG_PASSWORD", ""),
    }

def _connect_postgres():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 is required for postgres connections")
    return psycopg2.connect(**_pg_conn_kwargs())

def get_db_path() -> str:
    return _resolve_db_path()

def execute_read_query(sql_query: str):
    """
    Ejecuta una consulta SQL de lectura en la base de datos SQLite local.
    Retorna los resultados como una lista de diccionarios para facilitar
    el procesamiento de gráficas y la humanización.
    """
    conn = None
    try:
        if not _is_safe_select(sql_query):
            print("⚠️ SQL bloqueado por seguridad")
            return None
        if DB_ENGINE == "postgres":
            conn = _connect_postgres()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(sql_query)
            rows = cursor.fetchall()
            return list(rows)

        # 1. Conexión a la base de datos (SQLite)
        conn = sqlite3.connect(_resolve_db_path())

        # 2. Configuramos row_factory para obtener resultados como diccionarios
        # Esto permite acceder a los datos como result['monto_total'] en lugar de result[3]
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 3. Ejecución del SQL generado por la IA
        cursor.execute(sql_query)
        rows = cursor.fetchall()

        # 4. Transformación a lista de diccionarios estándar
        results = [dict(row) for row in rows]

        return results

    except sqlite3.Error as e:
        print(f"⚠️ Error de SQLite al ejecutar: {sql_query}")
        print(f"Detalle del error: {e}")
        return None
    except Exception as e:
        print("⚠️ Error ejecutando consulta en la base de datos")
        print(f"Detalle del error: {e}")
        return None
    
    finally:
        if conn:
            conn.close()

def has_base_tables() -> bool:
    """
    Verifica si existen las tablas base requeridas.
    """
    conn = None
    try:
        if DB_ENGINE == "postgres":
            conn = _connect_postgres()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name IN ('transacciones', 'clientes', 'comercios');"
            )
            rows = cursor.fetchall()
            return len(rows) == 3

        conn = sqlite3.connect(_resolve_db_path())
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('transacciones', 'clientes', 'comercios');"
        )
        rows = cursor.fetchall()
        return len(rows) == 3
    except Exception as e:
        print(f"⚠️ Error verificando tablas base: {e}")
        return False
    finally:
        if conn:
            conn.close()

def _is_safe_select(sql_query: str) -> bool:
    if not sql_query:
        return False
    stripped = sql_query.strip()
    # Allow a single trailing semicolon, but block multiple statements.
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    if ";" in stripped:
        return False
    lowered = stripped.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False
    if re.search(r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum)\b", lowered):
        return False
    return True

def execute_write_query(sql_query: str):
    """
    Ejecuta una consulta SQL de escritura (DDL/DML) en la base de datos.
    """
    conn = None
    try:
        if DB_ENGINE == "postgres":
            conn = _connect_postgres()
            cursor = conn.cursor()
            for statement in [s.strip() for s in sql_query.split(";") if s.strip()]:
                cursor.execute(statement)
            conn.commit()
            return True

        conn = sqlite3.connect(_resolve_db_path())
        cursor = conn.cursor()
        cursor.executescript(sql_query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("⚠️ Error de SQLite al escribir en la base de datos")
        print(f"Detalle del error: {e}")
        return False
    except Exception as e:
        print("⚠️ Error escribiendo en base de datos")
        print(f"Detalle del error: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_db_schema():
    """
    Función de utilidad para extraer el esquema real de las tablas.
    Útil para verificar que el prompt coincide con la base de datos física.
    """
    if DB_ENGINE == "postgres":
        query = (
            "SELECT table_name, column_name, data_type "
            "FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "ORDER BY table_name, ordinal_position;"
        )
        return execute_read_query(query)

    query = "SELECT name, sql FROM sqlite_master WHERE type='table';"
    return execute_read_query(query)