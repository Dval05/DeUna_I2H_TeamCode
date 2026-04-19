import os
import re
import unicodedata
from typing import Optional, Dict


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\?\!\¿\¡\.,;:]", "", text)
    return " ".join(text.split())


DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()


def _sql_today() -> str:
    return "CURRENT_DATE" if DB_ENGINE == "postgres" else "date('now')"


def _sql_days_ago(days: int) -> str:
    if DB_ENGINE == "postgres":
        return f"(CURRENT_DATE - INTERVAL '{days} days')"
    return f"date('now', '-{days} days')"


def _sql_month_start(offset_months: int = 0) -> str:
    if DB_ENGINE == "postgres":
        if offset_months == 0:
            return "DATE_TRUNC('month', CURRENT_DATE)::date"
        return f"DATE_TRUNC('month', CURRENT_DATE + INTERVAL '{offset_months} month')::date"
    if offset_months == 0:
        return "date('now', 'start of month')"
    return f"date('now', 'start of month', '{offset_months} month')"


def _sql_current_month_label() -> str:
    return "to_char(CURRENT_DATE, 'YYYY-MM')" if DB_ENGINE == "postgres" else "strftime('%Y-%m', 'now')"


def _sql_last_sunday() -> str:
    if DB_ENGINE == "postgres":
        return "(DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 day')::date"
    return "date('now', 'weekday 0', '-7 days')"


def route_question(question: str) -> Optional[Dict[str, str]]:
    q = _normalize(question)

    if q == "cuanto vendi en total el dia de hoy":
        return {
            "sql": (
                "SELECT COALESCE((SELECT total_sales "
                "FROM mv_sales_daily "
                f"WHERE day = {_sql_today()}), 0) AS total_ventas_hoy;"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "de lo que vendi esta semana cual fue mi ganancia real":
        return {
            "sql": (
                "SELECT COALESCE(SUM(total_profit), 0) AS ganancia_semana "
                "FROM mv_sales_daily "
                f"WHERE day >= {_sql_days_ago(7)};"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "que es lo que mas me compran mis clientes":
        return {
            "sql": (
                "SELECT categoria_compra, txn_count "
                "FROM mv_category_stats "
                "ORDER BY txn_count DESC LIMIT 1;"
            ),
            "chart": "BAR",
            "source": "materialized"
        }

    if q == "cuantos clientes frecuentes tengo registrados":
        return {
            "sql": (
                "SELECT COALESCE(customer_count, 0) AS clientes_frecuentes "
                "FROM mv_customers_segment "
                "WHERE segmento = 'Frecuente';"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "a que hora se llena mas mi local normalmente":
        return {
            "sql": (
                "SELECT hour, txn_count "
                "FROM mv_hourly_txn "
                "ORDER BY txn_count DESC LIMIT 1;"
            ),
            "chart": "BAR",
            "source": "materialized"
        }

    if q == "cuanto dinero me entro por transferencias vs qr deuna este mes":
        return {
            "sql": (
                "SELECT metodo_pago, total_sales "
                "FROM mv_payment_monthly "
                f"WHERE month = {_sql_current_month_label()};"
            ),
            "chart": "BAR",
            "source": "materialized"
        }

    if q == "cuanto vendi el domingo pasado":
        return {
            "sql": (
                "SELECT COALESCE((SELECT total_sales "
                "FROM mv_sales_daily "
                f"WHERE day = {_sql_last_sunday()}), 0) "
                "AS ventas_domingo_pasado;"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "cuanto pago de arriendo y luz por el local":
        return {
            "sql": None,
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "gane mas dinero este mes o el mes pasado":
        return {
            "sql": (
                "SELECT 'este_mes' AS periodo, "
                "COALESCE(SUM(total_profit), 0) AS ganancia "
                "FROM mv_sales_daily "
                f"WHERE day >= {_sql_month_start(0)} "
                "UNION ALL "
                "SELECT 'mes_pasado' AS periodo, "
                "COALESCE(SUM(total_profit), 0) AS ganancia "
                "FROM mv_sales_daily "
                f"WHERE day >= {_sql_month_start(-1)} "
                f"AND day < {_sql_month_start(0)};"
            ),
            "chart": "BAR",
            "source": "materialized"
        }

    if q == "que clientes dejaron de venir ultimamente":
        return {
            "sql": (
                "SELECT id_cliente "
                "FROM mv_customer_last_txn "
                f"WHERE last_txn_date < {_sql_days_ago(30)};"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "se que vendo mas bebidas pero que categoria me deja mas plata limpia":
        return {
            "sql": (
                "SELECT categoria_compra, total_profit "
                "FROM mv_category_stats "
                "ORDER BY total_profit DESC LIMIT 1;"
            ),
            "chart": "BAR",
            "source": "materialized"
        }

    if q == "cuanto gasta la gente en promedio cada vez que me compra":
        return {
            "sql": (
                "SELECT "
                "CASE WHEN SUM(txn_count) = 0 THEN 0 "
                "ELSE ROUND(SUM(total_sales) * 1.0 / SUM(txn_count), 2) END "
                "AS ticket_promedio "
                "FROM mv_sales_daily;"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "he conseguido clientes nuevos esta semana":
        return {
            "sql": (
                "SELECT COALESCE(SUM(new_customers), 0) AS nuevos_semana "
                "FROM mv_customers_registration_daily "
                f"WHERE day >= {_sql_days_ago(7)};"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "de esos clientes nuevos alguno ya me volvio a comprar":
        return {
            "sql": (
                "SELECT COUNT(*) AS clientes_recompra "
                "FROM mv_customer_first_txn "
                f"WHERE first_txn_date >= {_sql_days_ago(7)} "
                "AND txn_count > 1;"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    if q == "quien es mi mejor cliente y cuanto me ha hecho ganar":
        return {
            "sql": (
                "SELECT id_cliente, total_profit "
                "FROM mv_customer_profit "
                "ORDER BY total_profit DESC LIMIT 1;"
            ),
            "chart": "NONE",
            "source": "materialized"
        }

    return None
