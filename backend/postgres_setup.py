import io
import os
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2 import sql

DATA_DIR = Path(__file__).resolve().parent / "data"


def _env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _connect(dbname: str):
    return psycopg2.connect(
        host=_env("PG_HOST", "localhost"),
        port=int(_env("PG_PORT", "5432")),
        dbname=dbname,
        user=_env("PG_USER", "postgres"),
        password=_env("PG_PASSWORD", ""),
    )


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    try:
        df = pd.read_csv(path)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")
    if name == "tabla_comercios.csv":
        owner_col = next((c for c in df.columns if c.lower().startswith("due")), None)
        if owner_col and owner_col != "dueno":
            df = df.rename(columns={owner_col: "dueno"})
    return df


def _create_schema(conn):
    ddl = """
    CREATE TABLE IF NOT EXISTS comercios (
        id TEXT PRIMARY KEY,
        dueno TEXT,
        nombre TEXT,
        ciudad TEXT,
        rubro TEXT
    );

    CREATE TABLE IF NOT EXISTS clientes (
        id_cliente TEXT PRIMARY KEY,
        id_comercio TEXT,
        fecha_registro DATE,
        segmento TEXT
    );

    CREATE TABLE IF NOT EXISTS transacciones (
        id_txn TEXT PRIMARY KEY,
        id_comercio TEXT,
        id_cliente TEXT,
        fecha_hora TIMESTAMP,
        monto_total NUMERIC,
        costo_estimado NUMERIC,
        ganancia_neta NUMERIC,
        categoria_compra TEXT,
        estado TEXT,
        metodo_pago TEXT
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def _copy_dataframe(conn, df: pd.DataFrame, table: str):
    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=True)
    buffer.seek(0)
    with conn.cursor() as cur:
        cur.execute(sql.SQL("TRUNCATE TABLE {};").format(sql.Identifier(table)))
        cur.copy_expert(
            sql.SQL("COPY {} FROM STDIN WITH CSV HEADER").format(sql.Identifier(table)),
            buffer,
        )
    conn.commit()


def main():
    db_name = _env("PG_DB", "deuna_negocios", required=True)
    drop_db = _env("PG_DROP", "false").lower() == "true"

    admin_conn = _connect("postgres")
    admin_conn.autocommit = True
    with admin_conn.cursor() as cur:
        if drop_db:
            cur.execute(sql.SQL("DROP DATABASE IF EXISTS {};").format(sql.Identifier(db_name)))
        cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(db_name)))
    admin_conn.close()

    conn = _connect(db_name)
    _create_schema(conn)

    df_clientes = _read_csv("tabla_clientes.csv")
    df_comercios = _read_csv("tabla_comercios.csv")
    df_transacciones = _read_csv("tabla_transacciones.csv")

    if "fecha_registro" in df_clientes.columns:
        df_clientes["fecha_registro"] = pd.to_datetime(df_clientes["fecha_registro"], errors="coerce").dt.date
    if "fecha_hora" in df_transacciones.columns:
        df_transacciones["fecha_hora"] = pd.to_datetime(df_transacciones["fecha_hora"], errors="coerce")

    _copy_dataframe(conn, df_comercios, "comercios")
    _copy_dataframe(conn, df_clientes, "clientes")
    _copy_dataframe(conn, df_transacciones, "transacciones")

    conn.close()
    print("Postgres listo: esquema creado y datos cargados.")


if __name__ == "__main__":
    main()
