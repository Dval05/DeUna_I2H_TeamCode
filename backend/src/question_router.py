"""
Question Router Inteligente con Fuzzy Matching.
Intenta resolver preguntas comunes SIN llamar a Gemini = respuesta instantánea.
"""
import os
import re
import unicodedata
from typing import Optional, Dict


def _normalize(text: str) -> str:
    """Normaliza texto: minúsculas, sin acentos, sin puntuación."""
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[\?\!\¿\¡\.,;:]", "", text)
    return " ".join(text.split())


DB_ENGINE = os.getenv("DB_ENGINE", "sqlite").lower()


# ── Helpers SQL multi-engine ─────────────────────────────────────────────────

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
    if DB_ENGINE == "postgres":
        return "TO_CHAR(CURRENT_DATE, 'YYYY-MM')"
    return "strftime('%Y-%m', 'now')"


def _sql_last_sunday() -> str:
    if DB_ENGINE == "postgres":
        return "(DATE_TRUNC('week', CURRENT_DATE) - INTERVAL '1 day')::date"
    return "date('now', 'weekday 0', '-7 days')"


def _sql_hour_expr() -> str:
    if DB_ENGINE == "postgres":
        return "EXTRACT(HOUR FROM fecha_hora)::int"
    return "CAST(strftime('%H', fecha_hora) AS INTEGER)"


def _sql_month_label_expr() -> str:
    if DB_ENGINE == "postgres":
        return "TO_CHAR(fecha_hora, 'YYYY-MM')"
    return "strftime('%Y-%m', fecha_hora)"


def _sql_dow_expr() -> str:
    """Día de la semana (0=Domingo para SQLite, 0=Domingo para PostgreSQL)."""
    if DB_ENGINE == "postgres":
        return "EXTRACT(DOW FROM fecha_hora)::int"
    return "CAST(strftime('%w', fecha_hora) AS INTEGER)"


def _sql_dow_name_expr() -> str:
    if DB_ENGINE == "postgres":
        return "TO_CHAR(fecha_hora, 'Day')"
    return (
        "CASE CAST(strftime('%w', fecha_hora) AS INTEGER) "
        "WHEN 0 THEN 'Domingo' WHEN 1 THEN 'Lunes' WHEN 2 THEN 'Martes' "
        "WHEN 3 THEN 'Miércoles' WHEN 4 THEN 'Jueves' WHEN 5 THEN 'Viernes' "
        "WHEN 6 THEN 'Sábado' END"
    )


# ── Fuzzy matching helpers ───────────────────────────────────────────────────

def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def _contains_all(text: str, keywords: list[str]) -> bool:
    return all(kw in text for kw in keywords)


# ── Router principal ─────────────────────────────────────────────────────────

def route_question(question: str, commerce_id: Optional[str]) -> Optional[Dict[str, str]]:
    """
    Intenta resolver la pregunta sin llamar al LLM.
    Retorna dict con {sql, chart, source} o None si no matchea.
    """
    if not commerce_id:
        return None

    q = _normalize(question)
    commerce_and = f"AND id_comercio = '{commerce_id}'"

    # ── 1. Ventas de hoy ───────────────────────────────────────────────────
    if _contains_any(q, ["vendi hoy", "ventas hoy", "vendi en total el dia de hoy",
                         "vendido hoy", "ingrese hoy"]):
        return {
            "sql": (
                "SELECT COALESCE(SUM(monto_total), 0) AS total_ventas_hoy "
                "FROM transacciones "
                f"WHERE DATE(fecha_hora) = {_sql_today()} "
                f"AND estado = 'Exitosa' {commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 2. Ganancia de la semana ───────────────────────────────────────────
    if (_contains_any(q, ["ganancia"]) and _contains_any(q, ["semana"])) or \
       q == "de lo que vendi esta semana cual fue mi ganancia real":
        return {
            "sql": (
                "SELECT COALESCE(SUM(ganancia_neta), 0) AS ganancia_semana "
                "FROM transacciones "
                f"WHERE DATE(fecha_hora) >= {_sql_days_ago(7)} "
                f"AND estado = 'Exitosa' {commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 3. Qué más compran / categoría más vendida ────────────────────────
    if _contains_any(q, ["que mas me compran", "mas compran", "categoria mas",
                         "producto mas vendido", "que se vende mas",
                         "lo que mas vendo"]):
        return {
            "sql": (
                "SELECT categoria_compra, COUNT(*) AS txn_count, "
                "SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                "GROUP BY categoria_compra "
                "ORDER BY txn_count DESC LIMIT 5;"
            ),
            "chart": '{"type":"bar","x":"categoria_compra","y":"txn_count","title":"Top categorías"}',
            "source": "router",
        }

    # ── 4. Clientes frecuentes ─────────────────────────────────────────────
    if _contains_any(q, ["clientes frecuentes", "clientes fieles"]):
        return {
            "sql": (
                "SELECT COUNT(*) AS clientes_frecuentes "
                "FROM clientes "
                f"WHERE segmento = 'Frecuente' {commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 5. Hora pico ──────────────────────────────────────────────────────
    if _contains_any(q, ["hora se llena", "hora pico", "hora mas", "horario"]):
        return {
            "sql": (
                f"SELECT {_sql_hour_expr()} AS hora, COUNT(*) AS txn_count "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                "GROUP BY hora "
                "ORDER BY txn_count DESC LIMIT 5;"
            ),
            "chart": '{"type":"bar","x":"hora","y":"txn_count","title":"Horas más activas"}',
            "source": "router",
        }

    # ── 6. Métodos de pago ────────────────────────────────────────────────
    if _contains_any(q, ["metodo de pago", "metodos de pago", "transferencia",
                         "qr deuna", "pago mas usado", "como me pagan"]):
        month_filter = ""
        if _contains_any(q, ["este mes", "mes actual"]):
            month_filter = f"AND {_sql_month_label_expr()} = {_sql_current_month_label()} "
        return {
            "sql": (
                "SELECT metodo_pago, COUNT(*) AS cantidad, "
                "SUM(monto_total) AS total_sales "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {month_filter}{commerce_and} "
                "GROUP BY metodo_pago ORDER BY total_sales DESC;"
            ),
            "chart": '{"type":"pie","x":"metodo_pago","y":"total_sales","title":"Métodos de pago"}',
            "source": "router",
        }

    # ── 7. Ventas del domingo pasado ──────────────────────────────────────
    if _contains_any(q, ["domingo pasado", "ultimo domingo"]):
        return {
            "sql": (
                "SELECT COALESCE(SUM(monto_total), 0) AS ventas_domingo "
                "FROM transacciones "
                f"WHERE DATE(fecha_hora) = {_sql_last_sunday()} "
                f"AND estado = 'Exitosa' {commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 8. Comparación mes actual vs mes pasado / Estado de ventas ───────
    if (_contains_any(q, ["este mes"]) and _contains_any(q, ["mes pasado"])) or \
       _contains_any(q, ["gane mas", "vendido mas"]) or \
       _contains_any(q, ["como estan mis ventas", "han subido", "han bajado", "subido o bajado", "subieron o bajaron"]):

        # Si el usuario especifica otro tiempo (ej. año, trimestre, 3 meses, etc), saltamos el router y pasamos a Gemini
        dynamic_timeframes = ["año", "ano", "semana", "trimestre", "estos", "ultimos", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        # Solo lo saltamos si NO pregunta por "este mes" vs "mes pasado" literalmente.
        if (not (_contains_any(q, ["este mes"]) and _contains_any(q, ["mes pasado"]))) and _contains_any(q, dynamic_timeframes):
            pass # Saltamos al LLM
        else:
            return {
                "sql": (
                    "SELECT 'Este mes' AS periodo, "
                    "COALESCE(SUM(ganancia_neta), 0) AS ganancia "
                    "FROM transacciones "
                    f"WHERE DATE(fecha_hora) >= {_sql_month_start(0)} "
                    f"AND estado = 'Exitosa' {commerce_and} "
                    "UNION ALL "
                    "SELECT 'Mes pasado' AS periodo, "
                    "COALESCE(SUM(ganancia_neta), 0) AS ganancia "
                    "FROM transacciones "
                    f"WHERE DATE(fecha_hora) >= {_sql_month_start(-1)} "
                    f"AND DATE(fecha_hora) < {_sql_month_start(0)} "
                    f"AND estado = 'Exitosa' {commerce_and};"
                ),
                "chart": '{"type":"bar","x":"periodo","y":"ganancia","title":"Ganancia mensual"}',
                "source": "router",
            }

    # ── 9. Meses específicos (ej. "diciembre", "noviembre") ──────────────
    meses_map = {
        "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
        "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12
    }
    mes_encontrado = None
    for mes, num in meses_map.items():
        if _contains_any(q, [mes]):
            mes_encontrado = num
            break

    # Si encontramos un mes y preguntan por ventas/como están (sin decir "este mes")
    if mes_encontrado and not _contains_any(q, ["este mes", "mes pasado"]):
        # Asumimos el año actual (o el año de los datos), agrupar por semana
        if DB_ENGINE == "postgres":
            mes_sql = f"EXTRACT(MONTH FROM fecha_hora) = {mes_encontrado}"
            semana_col = "DATE_TRUNC('week', fecha_hora)::date"
        else:
            mes_sql = f"CAST(strftime('%m', fecha_hora) AS INTEGER) = {mes_encontrado}"
            semana_col = "strftime('%W', fecha_hora)"
            
        mes_str = list(meses_map.keys())[mes_encontrado-1].capitalize()
        return {
            "sql": (
                f"SELECT {semana_col} AS semana, SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"AND {mes_sql} "
                "GROUP BY semana ORDER BY semana;"
            ),
            "chart": f'{{"type":"bar","x":"semana","y":"total","title":"Ventas semanales de {mes_str}"}}',
            "source": "router",
        }

    # ── 10. Esta semana o semana pasada (Agrupado por día de la semana) ──
    # Para tener Lunes, Martes, Miercoles... evitamos LLM
    semana_kw = ["esta semana", "semana pasada", "informe semanal", "estadistica semanal", "ventas semanales", "la semana", "ultimos 7 dias", "de la semana"]
    if _contains_any(q, semana_kw) and not _contains_any(q, ["mes", "año", "ano", "varias semanas", "algunas semanas", "tres semanas", "dos semanas"]):
        # Determinar el inicio y fin
        if _contains_any(q, ["semana pasada"]):
            filtro_fecha = "fecha_hora >= date_trunc('week', CURRENT_DATE - INTERVAL '1 week') AND fecha_hora < date_trunc('week', CURRENT_DATE)"
            titulo = "Ventas de la semana pasada"
        elif _contains_any(q, ["ultimos 7 dias"]):
            filtro_fecha = "fecha_hora >= CURRENT_DATE - INTERVAL '7 days' AND fecha_hora <= CURRENT_DATE"
            titulo = "Ventas de los últimos 7 días"
        else:
            filtro_fecha = "fecha_hora >= date_trunc('week', CURRENT_DATE) AND fecha_hora < date_trunc('week', CURRENT_DATE) + INTERVAL '1 week'"
            titulo = "Ventas de esta semana"

        if DB_ENGINE == "postgres":
            dia_literal = "to_char(fecha_hora, 'Day')"
        else:
            dia_literal = "strftime('%w', fecha_hora)"

        return {
            "sql": (
                f"SELECT {dia_literal} AS dia_semana, SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"AND {filtro_fecha} "
                "GROUP BY dia_semana, DATE(fecha_hora) ORDER BY DATE(fecha_hora);"
            ),
            "chart": f'{{"type":"bar","x":"dia_semana","y":"total","title":"{titulo}"}}',
            "source": "router",
        }

    # ── 11. Clientes que dejaron de venir ────────────────────────────────
    if _contains_any(q, ["dejaron de venir", "no han vuelto", "perdidos",
                         "clientes que no vienen", "no volvieron"]):
        return {
            "sql": (
                "SELECT id_cliente, MAX(DATE(fecha_hora)) AS ultima_compra "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                "GROUP BY id_cliente "
                f"HAVING MAX(DATE(fecha_hora)) < {_sql_days_ago(30)} "
                "ORDER BY ultima_compra DESC LIMIT 10;"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 10. Categoría más rentable ────────────────────────────────────────
    if _contains_any(q, ["mas plata limpia", "mas rentable", "mas ganancia",
                         "mas utilidad", "mejor margen"]):
        return {
            "sql": (
                "SELECT categoria_compra, "
                "SUM(ganancia_neta) AS ganancia_total, "
                "ROUND(SUM(ganancia_neta)*100.0/SUM(monto_total), 1) AS margen_pct "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                "GROUP BY categoria_compra "
                "ORDER BY ganancia_total DESC LIMIT 5;"
            ),
            "chart": '{"type":"bar","x":"categoria_compra","y":"ganancia_total","title":"Categorías más rentables"}',
            "source": "router",
        }

    # ── 11. Ticket promedio ──────────────────────────────────────────────
    if _contains_any(q, ["promedio", "ticket promedio", "gasta la gente en promedio"]):
        return {
            "sql": (
                "SELECT ROUND(SUM(monto_total)*1.0/COUNT(*), 2) AS ticket_promedio "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 12. Clientes nuevos esta semana ──────────────────────────────────
    if _contains_any(q, ["clientes nuevos", "nuevos clientes"]):
        return {
            "sql": (
                "SELECT COUNT(*) AS nuevos "
                "FROM clientes "
                f"WHERE fecha_registro >= {_sql_days_ago(7)} "
                f"{commerce_and};"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 13. Clientes que recompraron ─────────────────────────────────────
    if _contains_any(q, ["volvio a comprar", "recompra", "volvieron a comprar",
                         "me volvio"]):
        return {
            "sql": (
                "SELECT COUNT(*) AS clientes_recompra "
                "FROM ("
                "  SELECT id_cliente, MIN(DATE(fecha_hora)) AS first_txn, COUNT(*) AS txn_count "
                "  FROM transacciones "
                f"  WHERE estado = 'Exitosa' {commerce_and} "
                "  GROUP BY id_cliente"
                ") t "
                f"WHERE first_txn >= {_sql_days_ago(7)} "
                "AND txn_count > 1;"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 14. Mejor cliente ────────────────────────────────────────────────
    if _contains_any(q, ["mejor cliente", "cliente mas importante",
                         "cliente que mas"]):
        return {
            "sql": (
                "SELECT id_cliente, SUM(monto_total) AS total_compras, "
                "SUM(ganancia_neta) AS ganancia_total, COUNT(*) AS visitas "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                "GROUP BY id_cliente "
                "ORDER BY ganancia_total DESC LIMIT 5;"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 15. Peor día de la semana ────────────────────────────────────────
    if _contains_any(q, ["peor dia", "dia mas flojo", "dia menos", "dia malo"]):
        return {
            "sql": (
                f"SELECT {_sql_dow_name_expr()} AS dia_semana, "
                "SUM(monto_total) AS total, COUNT(*) AS transacciones "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"GROUP BY {_sql_dow_expr()}, dia_semana "
                "ORDER BY total ASC LIMIT 1;"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 16. Mejor día de la semana ───────────────────────────────────────
    if _contains_any(q, ["mejor dia", "dia mas fuerte", "dia que mas vendo"]):
        return {
            "sql": (
                f"SELECT {_sql_dow_name_expr()} AS dia_semana, "
                "SUM(monto_total) AS total, COUNT(*) AS transacciones "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"GROUP BY {_sql_dow_expr()}, dia_semana "
                "ORDER BY total DESC LIMIT 1;"
            ),
            "chart": "NONE",
            "source": "router",
        }

    # ── 17. Ventas por día de la semana ──────────────────────────────────
    if _contains_any(q, ["ventas por dia", "cada dia de la semana", "dias de la semana"]):
        return {
            "sql": (
                f"SELECT {_sql_dow_name_expr()} AS dia_semana, "
                f"{_sql_dow_expr()} AS dow, "
                "SUM(monto_total) AS total, COUNT(*) AS transacciones "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"GROUP BY {_sql_dow_expr()}, dia_semana "
                "ORDER BY dow;"
            ),
            "chart": '{"type":"bar","x":"dia_semana","y":"total","title":"Ventas por día de la semana"}',
            "source": "router",
        }

    # ── 18. Segmentos de clientes ────────────────────────────────────────
    if _contains_any(q, ["segmentos", "tipos de clientes", "clientes en riesgo",
                         "riesgo de abandono"]):
        return {
            "sql": (
                "SELECT segmento, COUNT(*) AS cantidad "
                "FROM clientes "
                f"WHERE id_comercio = '{commerce_id}' "
                "GROUP BY segmento ORDER BY cantidad DESC;"
            ),
            "chart": '{"type":"pie","x":"segmento","y":"cantidad","title":"Segmentos de clientes"}',
            "source": "router",
        }

    # ── 19. Ventas del mes actual ────────────────────────────────────────
    # Agrupadas por semana para que el gráfico no sea tan grande
    if (_contains_any(q, ["vendi", "ventas", "ingrese", "datos", "estadisticas", "informe"]) and
        _contains_any(q, ["este mes", "mes actual", "del mes"]) and
        not _contains_any(q, ["mes pasado", "anterior"])):
        
        if DB_ENGINE == "postgres":
            semana_col = "DATE_TRUNC('week', fecha_hora)::date"
        else:
            semana_col = "strftime('%W', fecha_hora)"

        return {
            "sql": (
                f"SELECT {semana_col} AS semana, SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"AND DATE(fecha_hora) >= {_sql_month_start(0)} AND fecha_hora <= CURRENT_DATE "
                "GROUP BY semana ORDER BY semana;"
            ),
            "chart": '{"type":"bar","x":"semana","y":"total","title":"Ventas de este mes"}',
            "source": "router",
        }

    # ── 19.5 Ventas de este año (Nuevo para evitar LLM) ──────────────────
    if _contains_any(q, ["datos", "estadistica", "informe", "ventas", "resumen"]) and _contains_any(q, ["este ano", "este año", "del año", "del ano"]):
        if DB_ENGINE == "postgres":
            mes_col = "DATE_TRUNC('month', fecha_hora)::date"
        else:
            mes_col = "DATE(fecha_hora, 'start of month')"

        return {
            "sql": (
                f"SELECT {mes_col} AS mes, SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"AND DATE(fecha_hora) >= date_trunc('year', CURRENT_DATE) AND fecha_hora <= CURRENT_DATE "
                "GROUP BY mes ORDER BY mes;"
            ),
            "chart": '{"type":"bar","x":"mes","y":"total","title":"Resumen de este año"}',
            "source": "router",
        }

    # ── 20. Tendencia de ventas diarias ──────────────────────────────────
    if _contains_any(q, ["tendencia", "evolucion", "historial de ventas"]):
        return {
            "sql": (
                "SELECT DATE(fecha_hora) AS dia, SUM(monto_total) AS total "
                "FROM transacciones "
                f"WHERE estado = 'Exitosa' {commerce_and} "
                f"AND DATE(fecha_hora) >= {_sql_days_ago(30)} "
                "GROUP BY dia ORDER BY dia;"
            ),
            "chart": '{"type":"line","x":"dia","y":"total","title":"Tendencia de ventas (30 días)"}',
            "source": "router",
        }

    # ── 21. Pregunta fuera de alcance (arriendo, luz, etc) ───────────────
    if _contains_any(q, ["arriendo", "alquiler", "luz", "agua", "internet",
                         "sueldo", "empleados", "nomina"]):
        return {
            "sql": None,
            "chart": "NONE",
            "source": "router",
        }

    # ── 22. Estadísticas generales / resumen / gráficas ──────────────────
    if _contains_any(q, ["estadisticas", "estadistica", "graficas", "graficos",
                         "resumen", "como va mi negocio", "como me va"]):
        
        # Si la pregunta tiene un mes, "semana", "año" o categoría específica, PASAMOS al LLM
        specific_terms = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio", 
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
            "mes", "semana", "pasado", "año", "ano", "categoria", "producto", "cliente"
        ]
        
        if not _contains_any(q, specific_terms):
            return {
                "sql": (
                    "SELECT DATE(fecha_hora) AS dia, SUM(monto_total) AS total "
                    "FROM transacciones "
                    f"WHERE estado = 'Exitosa' {commerce_and} "
                    f"AND DATE(fecha_hora) >= {_sql_days_ago(7)} "
                    "GROUP BY dia ORDER BY dia;"
                ),
                "chart": '{"type":"bar","x":"dia","y":"total","title":"Ventas de la última semana"}',
                "source": "router",
            }

    # No se encontró match → se irá al LLM
    return None
