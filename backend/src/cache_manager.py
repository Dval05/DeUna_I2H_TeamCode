import sqlite3
import hashlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Ruta para la base de datos de caché (independiente del dataset de negocios)
CACHE_DB_PATH = (DATA_DIR / "cache_repertorio.db").as_posix()

def init_cache_db():
    """Crea la tabla de caché si no existe."""
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            hash_pregunta TEXT PRIMARY KEY,
            pregunta_original TEXT,
            sql_generado TEXT,
            tipo_grafica TEXT,
            respuesta_humanizada TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generar_hash(texto):
    """Convierte la pregunta a un hash único para buscar rápido."""
    return hashlib.md5(texto.lower().strip().encode()).hexdigest()

def obtener_de_cache(pregunta):
    """Busca si la pregunta ya fue respondida antes."""
    init_cache_db()  # Asegura que la tabla existe
    h = generar_hash(pregunta)
    
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql_generado, tipo_grafica, respuesta_humanizada FROM cache WHERE hash_pregunta = ?", 
        (h,)
    )
    res = cursor.fetchone()
    conn.close()
    
    if res:
        return {
            "sql": res[0],
            "chart": res[1],
            "human_answer": res[2]
        }
    return None

def guardar_en_cache(pregunta, sql, chart, human_answer):
    """Guarda una nueva consulta en el repertorio."""
    init_cache_db()
    h = generar_hash(pregunta)
    
    conn = sqlite3.connect(CACHE_DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR REPLACE INTO cache VALUES (?, ?, ?, ?, ?)",
            (h, pregunta, sql, chart, human_answer)
        )
        conn.commit()
    except Exception as e:
        print(f"⚠️ Error guardando en caché: {e}")
    finally:
        conn.close()