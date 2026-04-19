import os
import sqlite3
from .database import get_db_path

DEFAULT_REFRESH_WINDOW_DAYS = 90

def _get_refresh_window_days() -> int:
    raw_value = os.getenv("MATERIALIZED_REFRESH_WINDOW_DAYS", str(DEFAULT_REFRESH_WINDOW_DAYS))
    try:
        return int(raw_value)
    except ValueError:
        return DEFAULT_REFRESH_WINDOW_DAYS

def _build_refresh_sql(window_days: int) -> str:
    txn_where = ""
    registration_where = ""
    if window_days > 0:
        txn_where = f"WHERE fecha_hora >= datetime('now', '-{window_days} days')"
        registration_where = f"WHERE fecha_registro >= date('now', '-{window_days} days')"

    return f"""
BEGIN;

CREATE INDEX IF NOT EXISTS idx_txn_estado ON transacciones(estado);
CREATE INDEX IF NOT EXISTS idx_txn_fecha_hora ON transacciones(fecha_hora);
CREATE INDEX IF NOT EXISTS idx_txn_estado_fecha ON transacciones(estado, fecha_hora);
CREATE INDEX IF NOT EXISTS idx_txn_id_cliente ON transacciones(id_cliente);
CREATE INDEX IF NOT EXISTS idx_txn_categoria ON transacciones(categoria_compra);
CREATE INDEX IF NOT EXISTS idx_txn_metodo ON transacciones(metodo_pago);
CREATE INDEX IF NOT EXISTS idx_txn_id_comercio ON transacciones(id_comercio);
CREATE INDEX IF NOT EXISTS idx_clientes_segmento ON clientes(segmento);
CREATE INDEX IF NOT EXISTS idx_clientes_fecha_registro ON clientes(fecha_registro);

CREATE TABLE IF NOT EXISTS mv_refresh_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_refresh TEXT
);
INSERT OR IGNORE INTO mv_refresh_state (id, last_refresh) VALUES (1, NULL);

CREATE TABLE IF NOT EXISTS mv_sales_daily (
    day TEXT PRIMARY KEY,
    total_sales REAL,
    total_profit REAL,
    txn_count INTEGER
);

CREATE TABLE IF NOT EXISTS mv_category_stats (
    categoria_compra TEXT PRIMARY KEY,
    txn_count INTEGER,
    total_sales REAL,
    total_profit REAL
);

CREATE TABLE IF NOT EXISTS mv_payment_monthly (
    month TEXT,
    metodo_pago TEXT,
    total_sales REAL,
    PRIMARY KEY (month, metodo_pago)
);

CREATE TABLE IF NOT EXISTS mv_payment_stats (
    metodo_pago TEXT PRIMARY KEY,
    txn_count INTEGER,
    total_sales REAL
);

CREATE TABLE IF NOT EXISTS mv_hourly_txn (
    hour INTEGER PRIMARY KEY,
    txn_count INTEGER
);

CREATE TABLE IF NOT EXISTS mv_customers_segment (
    segmento TEXT PRIMARY KEY,
    customer_count INTEGER
);

CREATE TABLE IF NOT EXISTS mv_customer_last_txn (
    id_cliente TEXT PRIMARY KEY,
    last_txn_date TEXT
);

CREATE TABLE IF NOT EXISTS mv_customer_profit (
    id_cliente TEXT PRIMARY KEY,
    total_profit REAL
);

CREATE TABLE IF NOT EXISTS mv_customer_sales (
    id_cliente TEXT PRIMARY KEY,
    total_sales REAL
);

CREATE TABLE IF NOT EXISTS mv_customer_first_txn (
    id_cliente TEXT PRIMARY KEY,
    first_txn_date TEXT,
    txn_count INTEGER
);

CREATE TABLE IF NOT EXISTS mv_customer_monthly_txn (
    month TEXT,
    id_cliente TEXT,
    txn_count INTEGER,
    PRIMARY KEY (month, id_cliente)
);

CREATE TABLE IF NOT EXISTS mv_customers_registration_daily (
    day TEXT PRIMARY KEY,
    new_customers INTEGER
);

CREATE TABLE IF NOT EXISTS mv_category_monthly (
    month TEXT,
    categoria_compra TEXT,
    txn_count INTEGER,
    total_sales REAL,
    total_profit REAL,
    PRIMARY KEY (month, categoria_compra)
);

CREATE TABLE IF NOT EXISTS mv_city_sales (
    ciudad TEXT PRIMARY KEY,
    total_sales REAL,
    total_profit REAL,
    txn_count INTEGER
);

CREATE TABLE IF NOT EXISTS mv_txn_status_daily (
    day TEXT,
    estado TEXT,
    txn_count INTEGER,
    total_sales REAL,
    PRIMARY KEY (day, estado)
);

CREATE INDEX IF NOT EXISTS idx_mv_customer_last_txn_date ON mv_customer_last_txn(last_txn_date);
CREATE INDEX IF NOT EXISTS idx_mv_customer_monthly_month ON mv_customer_monthly_txn(month);
CREATE INDEX IF NOT EXISTS idx_mv_category_monthly_month ON mv_category_monthly(month);
CREATE INDEX IF NOT EXISTS idx_mv_payment_monthly_month ON mv_payment_monthly(month);
CREATE INDEX IF NOT EXISTS idx_mv_txn_status_day ON mv_txn_status_daily(day);

DROP TABLE IF EXISTS temp_base_txn;
CREATE TEMP TABLE temp_base_txn AS
SELECT
    id_cliente,
    id_comercio,
    categoria_compra,
    metodo_pago,
    estado,
    monto_total,
    ganancia_neta,
    fecha_hora,
    date(fecha_hora) AS day,
    strftime('%Y-%m', fecha_hora) AS month,
    CAST(strftime('%H', fecha_hora) AS INTEGER) AS hour
FROM transacciones
{txn_where};

DROP TABLE IF EXISTS temp_base_clients;
CREATE TEMP TABLE temp_base_clients AS
SELECT DISTINCT id_cliente FROM temp_base_txn;

DROP TABLE IF EXISTS temp_base_days;
CREATE TEMP TABLE temp_base_days AS
SELECT DISTINCT day FROM temp_base_txn;

DROP TABLE IF EXISTS temp_base_months;
CREATE TEMP TABLE temp_base_months AS
SELECT DISTINCT month FROM temp_base_txn;

DROP TABLE IF EXISTS temp_base_cities;
CREATE TEMP TABLE temp_base_cities AS
SELECT DISTINCT c.ciudad
FROM temp_base_txn t
JOIN comercios c ON c.id = t.id_comercio;

DELETE FROM mv_sales_daily WHERE day IN (SELECT day FROM temp_base_days);
INSERT INTO mv_sales_daily (day, total_sales, total_profit, txn_count)
SELECT
    day,
    SUM(CASE WHEN estado = 'Exitosa' THEN monto_total END) AS total_sales,
    SUM(CASE WHEN estado = 'Exitosa' THEN ganancia_neta END) AS total_profit,
    SUM(CASE WHEN estado = 'Exitosa' THEN 1 END) AS txn_count
FROM temp_base_txn
GROUP BY day;

DELETE FROM mv_txn_status_daily WHERE day IN (SELECT day FROM temp_base_days);
INSERT INTO mv_txn_status_daily (day, estado, txn_count, total_sales)
SELECT
    day,
    estado,
    COUNT(*) AS txn_count,
    SUM(monto_total) AS total_sales
FROM temp_base_txn
GROUP BY day, estado;

DELETE FROM mv_payment_monthly WHERE month IN (SELECT month FROM temp_base_months);
INSERT INTO mv_payment_monthly (month, metodo_pago, total_sales)
SELECT
    month,
    metodo_pago,
    SUM(monto_total) AS total_sales
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY month, metodo_pago;

DELETE FROM mv_payment_stats;
INSERT INTO mv_payment_stats (metodo_pago, txn_count, total_sales)
SELECT
    metodo_pago,
    COUNT(*) AS txn_count,
    SUM(monto_total) AS total_sales
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY metodo_pago;

DELETE FROM mv_category_monthly WHERE month IN (SELECT month FROM temp_base_months);
INSERT INTO mv_category_monthly (month, categoria_compra, txn_count, total_sales, total_profit)
SELECT
    month,
    categoria_compra,
    COUNT(*) AS txn_count,
    SUM(monto_total) AS total_sales,
    SUM(ganancia_neta) AS total_profit
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY month, categoria_compra;

DELETE FROM mv_category_stats;
INSERT INTO mv_category_stats (categoria_compra, txn_count, total_sales, total_profit)
SELECT
    categoria_compra,
    COUNT(*) AS txn_count,
    SUM(monto_total) AS total_sales,
    SUM(ganancia_neta) AS total_profit
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY categoria_compra;

DELETE FROM mv_hourly_txn;
INSERT INTO mv_hourly_txn (hour, txn_count)
SELECT
    hour,
    COUNT(*) AS txn_count
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY hour;

DELETE FROM mv_customers_segment;
INSERT INTO mv_customers_segment (segmento, customer_count)
SELECT
    segmento,
    COUNT(*) AS customer_count
FROM clientes
GROUP BY segmento;

DELETE FROM mv_customer_last_txn WHERE id_cliente IN (SELECT id_cliente FROM temp_base_clients);
INSERT INTO mv_customer_last_txn (id_cliente, last_txn_date)
SELECT
    id_cliente,
    MAX(date(fecha_hora)) AS last_txn_date
FROM transacciones
WHERE estado = 'Exitosa'
  AND id_cliente IN (SELECT id_cliente FROM temp_base_clients)
GROUP BY id_cliente;

DELETE FROM mv_customer_profit WHERE id_cliente IN (SELECT id_cliente FROM temp_base_clients);
INSERT INTO mv_customer_profit (id_cliente, total_profit)
SELECT
    id_cliente,
    SUM(ganancia_neta) AS total_profit
FROM transacciones
WHERE estado = 'Exitosa'
  AND id_cliente IN (SELECT id_cliente FROM temp_base_clients)
GROUP BY id_cliente;

DELETE FROM mv_customer_sales WHERE id_cliente IN (SELECT id_cliente FROM temp_base_clients);
INSERT INTO mv_customer_sales (id_cliente, total_sales)
SELECT
    id_cliente,
    SUM(monto_total) AS total_sales
FROM transacciones
WHERE estado = 'Exitosa'
  AND id_cliente IN (SELECT id_cliente FROM temp_base_clients)
GROUP BY id_cliente;

DELETE FROM mv_customer_first_txn WHERE id_cliente IN (SELECT id_cliente FROM temp_base_clients);
INSERT INTO mv_customer_first_txn (id_cliente, first_txn_date, txn_count)
SELECT
    id_cliente,
    MIN(date(fecha_hora)) AS first_txn_date,
    COUNT(*) AS txn_count
FROM transacciones
WHERE estado = 'Exitosa'
  AND id_cliente IN (SELECT id_cliente FROM temp_base_clients)
GROUP BY id_cliente;

DELETE FROM mv_customer_monthly_txn
WHERE month IN (SELECT month FROM temp_base_months)
  AND id_cliente IN (SELECT id_cliente FROM temp_base_clients);
INSERT INTO mv_customer_monthly_txn (month, id_cliente, txn_count)
SELECT
        month,
        id_cliente,
        COUNT(*) AS txn_count
FROM temp_base_txn
WHERE estado = 'Exitosa'
GROUP BY month, id_cliente;

DELETE FROM mv_customers_registration_daily
WHERE day IN (
    SELECT DISTINCT date(fecha_registro)
    FROM clientes
    {registration_where}
);
INSERT INTO mv_customers_registration_daily (day, new_customers)
SELECT
    date(fecha_registro) AS day,
    COUNT(*) AS new_customers
FROM clientes
{registration_where}
GROUP BY date(fecha_registro);

DELETE FROM mv_city_sales WHERE ciudad IN (SELECT ciudad FROM temp_base_cities);
INSERT INTO mv_city_sales (ciudad, total_sales, total_profit, txn_count)
SELECT
    c.ciudad,
    SUM(t.monto_total) AS total_sales,
    SUM(t.ganancia_neta) AS total_profit,
    COUNT(*) AS txn_count
FROM transacciones t
JOIN comercios c ON c.id = t.id_comercio
WHERE t.estado = 'Exitosa'
  AND c.ciudad IN (SELECT ciudad FROM temp_base_cities)
GROUP BY c.ciudad;

UPDATE mv_refresh_state SET last_refresh = datetime('now') WHERE id = 1;

COMMIT;
"""


def refresh_materialized_views(full_refresh: bool = False) -> bool:
    conn = None
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        window_days = 0 if full_refresh else _get_refresh_window_days()
        cursor.executescript(_build_refresh_sql(window_days))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print("⚠️ Error al refrescar vistas materializadas")
        print(f"Detalle del error: {e}")
        return False
    finally:
        if conn:
            conn.close()
