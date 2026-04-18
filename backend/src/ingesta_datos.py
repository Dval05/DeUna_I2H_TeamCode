import pandas as pd
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"

# Asegurar que la carpeta data exista
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _resolve_csv_path(filename: str) -> Path:
    # Prefer backend/data; fall back to backend root for legacy layouts.
    candidate = DATA_DIR / filename
    if candidate.exists():
        return candidate
    return PROJECT_ROOT / filename

def cargar_datasets():
    db_path = DATA_DIR / "deuna_negocios.db"
    conn = sqlite3.connect(db_path.as_posix())
    
    print("⏳ Cargando transacciones...")
    df_tx = pd.read_csv(_resolve_csv_path("tabla_transacciones.csv"))
    df_tx.to_sql('transacciones', conn, if_exists='replace', index=False)
    
    print("⏳ Cargando comercios...")
    df_co = pd.read_csv(_resolve_csv_path("tabla_comercios.csv"))
    df_co.to_sql('comercios', conn, if_exists='replace', index=False)
    
    print("⏳ Cargando clientes...")
    df_cl = pd.read_csv(_resolve_csv_path("tabla_clientes.csv"))
    df_cl.to_sql('clientes', conn, if_exists='replace', index=False)
    
    conn.close()
    print("✅ ¡Base de datos 'deuna_negocios.db' creada con los datos para el reto!")

if __name__ == "__main__":
    cargar_datasets()