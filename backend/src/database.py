import sqlite3
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargamos la ruta desde el .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _resolve_db_path() -> str:
    env_path = os.getenv("DB_PATH")
    if env_path:
        return env_path
    return (DATA_DIR / "deuna_negocios.db").as_posix()

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
        # 1. Conexión a la base de datos
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
    
    finally:
        if conn:
            conn.close()

def execute_write_query(sql_query: str):
    """
    Ejecuta una consulta SQL de escritura (DDL/DML) en la base de datos.
    """
    conn = None
    try:
        conn = sqlite3.connect(_resolve_db_path())
        cursor = conn.cursor()
        cursor.executescript(sql_query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("⚠️ Error de SQLite al escribir en la base de datos")
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
    query = "SELECT name, sql FROM sqlite_master WHERE type='table';"
    return execute_read_query(query)