"""
Generador de respuestas humanas SIN LLM.
Para preguntas del router, genera respuestas directas desde los datos SQL.
Esto elimina la segunda llamada a Gemini = respuesta en < 1 segundo.
"""
from typing import Optional


def _fmt_money(value) -> str:
    """Formatea un valor numérico como dinero."""
    try:
        v = float(value or 0)
        return f"${v:,.2f}"
    except (TypeError, ValueError):
        return str(value)


def _fmt_int(value) -> str:
    try:
        return str(int(float(value or 0)))
    except (TypeError, ValueError):
        return str(value)


def _fmt_pct(current, previous) -> str:
    """Calcula porcentaje de cambio."""
    try:
        c = float(current or 0)
        p = float(previous or 0)
        if p == 0:
            return ""
        change = ((c - p) / p) * 100
        if change >= 0:
            return f"un aumento del {change:.1f}%"
        else:
            return f"una baja del {abs(change):.1f}%"
    except (TypeError, ValueError):
        return ""


def humanize_from_data(question_normalized: str, data_results: list, source: str) -> Optional[str]:
    """
    Genera respuesta humana SIN llamar al LLM.
    Retorna None si no puede generar (se usará Gemini como fallback).
    """
    if not data_results:
        return "No encontré registros para esa consulta en tu negocio. Intenta con otro periodo o categoría 🔍"

    row = data_results[0]

    # ── Ventas de hoy ─────────────────────────────────────────────────────
    if "total_ventas_hoy" in row:
        total = float(row["total_ventas_hoy"] or 0)
        if total == 0:
            return "Aún no tienes ventas registradas para hoy. ¡El día recién empieza! ☀️"
        return f"Hoy llevas {_fmt_money(total)} en ventas 💰. ¡Sigue así!"

    # ── Ganancia semanal ──────────────────────────────────────────────────
    if "ganancia_semana" in row:
        g = float(row["ganancia_semana"] or 0)
        if g == 0:
            return "No se registró ganancia esta semana. Puede que aún no haya suficientes ventas procesadas."
        return f"Tu ganancia neta esta semana es de {_fmt_money(g)} 💪. Cada dólar cuenta para tu negocio."

    # ── Top categorías ────────────────────────────────────────────────────
    if "categoria_compra" in row and "txn_count" in row:
        if len(data_results) == 1:
            cat = row["categoria_compra"]
            count = _fmt_int(row["txn_count"])
            total = _fmt_money(row.get("total", row.get("total_sales", 0)))
            return f"Lo que más te compran es **{cat}** con {count} transacciones por un total de {total} 🏆"
        else:
            lines = []
            for i, r in enumerate(data_results[:5], 1):
                cat = r["categoria_compra"]
                count = _fmt_int(r["txn_count"])
                lines.append(f"{i}. **{cat}** — {count} ventas")
            top = "\n".join(lines)
            return f"Tus categorías más vendidas son:\n{top}\n\n¡Asegúrate de tener buen inventario de las primeras! 📦"

    # ── Clientes frecuentes ───────────────────────────────────────────────
    if "clientes_frecuentes" in row:
        n = _fmt_int(row["clientes_frecuentes"])
        return f"Tienes **{n} clientes frecuentes** registrados. Son la base de tu negocio 🌟. ¡Cuídalos!"

    # ── Hora pico ─────────────────────────────────────────────────────────
    if "hora" in row and "txn_count" in row:
        if len(data_results) == 1:
            h = int(float(row["hora"]))
            return f"Tu hora más activa es las **{h}:00** ⏰. Asegúrate de tener todo listo para ese momento."
        else:
            lines = []
            for r in data_results[:3]:
                h = int(float(r["hora"]))
                c = _fmt_int(r["txn_count"])
                lines.append(f"• {h}:00 — {c} transacciones")
            return "Tus horas más activas son:\n" + "\n".join(lines) + "\n\n⏰ Prepárate bien para esos horarios."

    # ── Métodos de pago ───────────────────────────────────────────────────
    if "metodo_pago" in row and ("total_sales" in row or "cantidad" in row):
        lines = []
        for r in data_results:
            mp = r["metodo_pago"]
            total = _fmt_money(r.get("total_sales", 0))
            cant = _fmt_int(r.get("cantidad", 0))
            lines.append(f"• **{mp}**: {total} ({cant} transacciones)")
        return "Así se distribuyen tus cobros:\n" + "\n".join(lines) + "\n\n💳 Revisa cuál te conviene más."

    # ── Ventas domingo ────────────────────────────────────────────────────
    if "ventas_domingo" in row or "ventas_domingo_pasado" in row:
        v = float(row.get("ventas_domingo", row.get("ventas_domingo_pasado", 0)))
        if v == 0:
            return "El domingo pasado no se registraron ventas. Es normal si ese día tu negocio cierra 😊"
        return f"El domingo pasado vendiste {_fmt_money(v)} 📊."

    # ── Comparación temporal ──────────────────────────────────────────────
    if "periodo" in row and ("ganancia" in row or "total" in row or "ventas" in row) and len(data_results) >= 2:
        val_key = "ganancia" if "ganancia" in row else ("total" if "total" in row else "ventas")
        this_period = float(data_results[0].get(val_key, 0) or 0)
        last_period = float(data_results[1].get(val_key, 0) or 0)
        
        change = _fmt_pct(this_period, last_period)
        if this_period >= last_period:
            return (
                f"¡Buenas noticias! 🎉 Para este periodo llevas {_fmt_money(this_period)} "
                f"vs {_fmt_money(last_period)} del periodo anterior ({change})."
            )
        else:
            return (
                f"En este periodo llevas {_fmt_money(this_period)} vs {_fmt_money(last_period)} "
                f"del periodo anterior ({change}). Revisa tus ventas recientes para ajustar tu estrategia 💡"
            )

    # ── Clientes perdidos ─────────────────────────────────────────────────
    if "ultima_compra" in row and "id_cliente" in row:
        n = len(data_results)
        sample = ", ".join(r["id_cliente"] for r in data_results[:3])
        if n == 1:
            return f"El cliente **{row['id_cliente']}** no ha vuelto desde {row['ultima_compra']}. ¿Podrías contactarlo? 📞"
        return (
            f"Hay **{n} clientes** que no han vuelto en el último mes. "
            f"Algunos: {sample}. Considera enviarles una promoción para que regresen 💡"
        )

    # ── Categoría más rentable ────────────────────────────────────────────
    if "ganancia_total" in row and "categoria_compra" in row:
        if len(data_results) == 1:
            return (
                f"La categoría que te deja más ganancia es **{row['categoria_compra']}** "
                f"con {_fmt_money(row['ganancia_total'])} de utilidad 💰"
            )
        lines = []
        for i, r in enumerate(data_results[:5], 1):
            lines.append(f"{i}. **{r['categoria_compra']}** — {_fmt_money(r['ganancia_total'])}")
        return "Las categorías que más ganancia te dejan son:\n" + "\n".join(lines)

    # ── Ticket promedio ───────────────────────────────────────────────────
    if "ticket_promedio" in row:
        return f"En promedio, cada cliente gasta {_fmt_money(row['ticket_promedio'])} por compra 🛒"

    # ── Clientes nuevos ───────────────────────────────────────────────────
    if "nuevos" in row or "nuevos_semana" in row:
        n = _fmt_int(row.get("nuevos", row.get("nuevos_semana", 0)))
        if n == "0":
            return "Esta semana no se registraron clientes nuevos. Podrías lanzar una promoción para atraer más personas 💡"
        return f"¡Genial! Esta semana llegaron **{n} clientes nuevos** a tu negocio 🎉"

    # ── Recompra ──────────────────────────────────────────────────────────
    if "clientes_recompra" in row:
        n = _fmt_int(row["clientes_recompra"])
        if n == "0":
            return "Aún ninguno de los clientes nuevos ha vuelto a comprar. Dale tiempo, ¡o incentívalos con algo especial! 💡"
        return f"**{n} clientes nuevos** ya volvieron a comprarte. ¡Eso es muy buena señal! 🎉"

    # ── Mejor cliente ─────────────────────────────────────────────────────
    if "total_compras" in row and "id_cliente" in row:
        return (
            f"Tu mejor cliente es **{row['id_cliente']}** con {_fmt_money(row.get('ganancia_total', row['total_compras']))} "
            f"de ganancia en {_fmt_int(row.get('visitas', 0))} visitas 🌟"
        )

    # ── Día de la semana ──────────────────────────────────────────────────
    if "dia_semana" in row and "total" in row:
        lines = []
        for r in data_results:
            dia = str(r["dia_semana"]).strip()
            # Traducción básica de inglés a español por si la BD está en inglés
            dia_es = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                      "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}.get(dia, dia)
            total = _fmt_money(r["total"])
            txn_str = f" en {_fmt_int(r.get('transacciones', 0))} transacciones" if "transacciones" in r else ""
            lines.append(f"• **{dia_es}**: {total}{txn_str}")
        total_sum = sum(float(r.get("total", 0) or 0) for r in data_results)
        return f"El total del periodo fue {_fmt_money(total_sum)} 💰 divididos así:\n" + "\n".join(lines)

    # ── Segmentos ─────────────────────────────────────────────────────────
    if "segmento" in row and "cantidad" in row:
        lines = []
        for r in data_results:
            lines.append(f"• **{r['segmento']}**: {_fmt_int(r['cantidad'])} clientes")
        return "Así se distribuyen tus clientes:\n" + "\n".join(lines)

    # ── Ventas del mes ────────────────────────────────────────────────────
    if "ventas_mes" in row:
        v = _fmt_money(row["ventas_mes"])
        g = _fmt_money(row.get("ganancia_mes", 0))
        n = _fmt_int(row.get("num_transacciones", 0))
        return f"Este mes llevas {v} en ventas ({g} de ganancia) con {n} transacciones 📈"

    # ── Clientes en riesgo (Generado por LLM) ─────────────────────────────
    if "en_riesgo" in row:
        n = _fmt_int(row["en_riesgo"])
        return f"Tienes **{n} clientes** identificados 'En riesgo de abandono'. Es un excelente momento para enviarles una promoción 🎯"

    # ── Rechazadas (Generado por LLM) ─────────────────────────────────────
    if "rechazadas" in row:
        n = _fmt_int(row["rechazadas"])
        total = _fmt_money(row.get("monto_total", 0))
        return f"Se registraron **{n} transacciones rechazadas** sumando {total} este mes ⚠️"

    # ── Clientes recurrentes (Generado por LLM) ───────────────────────────
    if "clientes_recurrentes" in row:
        n = _fmt_int(row["clientes_recurrentes"])
        return f"Tuviste **{n} clientes que te compraron más de una vez** este mes. ¡Tu negocio genera lealtad! 🏆"

    # ── Total general de ventas (Generado por LLM) ────────────────────────
    if "total_ventas" in row:
        v = _fmt_money(row["total_ventas"])
        return f"Tus ventas en el periodo consultado suman **{v}** 💰"

    # ── Comparación Semanal (Generado por LLM) ────────────────────────────
    if "semana" in row and "total" in row:
        lines = []
        for r in data_results:
            lines.append(f"• Semana {r['semana']}: {_fmt_money(r['total'])}")
        return "Aquí tienes tus ventas por semana:\n" + "\n".join(lines)

    # ── Resumen Mensual (Generado por LLM para años) ──────────────────────
    if "mes" in row and "total" in row:
        lines = []
        for r in data_results:
            lines.append(f"• Mes {r['mes']}: {_fmt_money(r['total'])}")
        total_sum = sum(float(r.get("total", 0) or 0) for r in data_results)
        return f"Tus ventas sumaron {_fmt_money(total_sum)} 💰 en {len(data_results)} meses activos. Aquí está el desglose mensual:\n" + "\n".join(lines)

    # ── Tendencia (Varios días) ──────────────────────────────────────────
    if "dia" in row and "total" in row:
        if len(data_results) > 3:
            totals = [float(r.get("total", 0) or 0) for r in data_results]
            best_day = max(data_results, key=lambda r: float(r.get("total", 0) or 0))
            worst_day = min(data_results, key=lambda r: float(r.get("total", 0) or 0))
            avg = sum(totals) / len(totals)
            return (
                f"En los últimos {len(data_results)} días, tu mejor día fue **{best_day['dia']}** "
                f"con {_fmt_money(best_day['total'])} y el más flojo **{worst_day['dia']}** "
                f"con {_fmt_money(worst_day['total'])}. Tu promedio diario es {_fmt_money(avg)} 📊"
            )
        else:
            total_sum = sum(float(r.get("total", 0) or 0) for r in data_results)
            return f"Durante este lapso vendiste {_fmt_money(total_sum)} 💰 en {len(data_results)} días operativos."

    # No pudimos generar respuesta template → usará Gemini
    return None
