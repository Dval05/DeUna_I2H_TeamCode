import os
import re
import time
from dotenv import load_dotenv
from .prompts import SQLITE_SYSTEM_PROMPT, POSTGRES_SYSTEM_PROMPT, HUMANIZER_PROMPT

try:
    import google.generativeai as genai
except Exception:
    genai = None

load_dotenv()

_GEMINI_MODEL_DEFAULT = "gemini-2.0-flash"

_gemini_key = os.getenv("GEMINI_API_KEY")
if _gemini_key and genai:
    genai.configure(api_key=_gemini_key)


def _get_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider and provider != "gemini":
        return "none"
    if _gemini_key and genai:
        return "gemini"
    return "none"


def _gemini_generate(
    system_prompt: str,
    user_content: str,
    model_name: str,
    temperature: float,
    max_retries: int = 3,
) -> str:
    """Genera contenido con Gemini, con reintentos para rate limits."""
    if not genai or not _gemini_key:
        raise RuntimeError("GEMINI_API_KEY no configurada")

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_prompt,
    )

    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                user_content,
                generation_config=genai.GenerationConfig(temperature=temperature),
            )
            return (response.text or "").strip()
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = any(
                kw in error_str
                for kw in ["429", "rate", "quota", "resource_exhausted"]
            )
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5
                print(f"⏳ Rate limit. Reintentando en {wait_time}s ({attempt+1}/{max_retries})...")
                time.sleep(wait_time)
                continue
            raise
    return ""


def get_sql_from_question(question: str, commerce_id: str | None = None):
    """
    Paso 1: Pregunta → SQL + Chart.
    """
    try:
        provider = _get_provider()
        if provider == "none":
            print("⚠️ Configura GEMINI_API_KEY")
            return {"sql": None, "chart": "NONE"}

        db_engine = os.getenv("DB_ENGINE", "sqlite").lower()
        system_prompt = (
            POSTGRES_SYSTEM_PROMPT if db_engine == "postgres" else SQLITE_SYSTEM_PROMPT
        )
        if commerce_id:
            system_prompt = system_prompt.replace("{id_comercio}", commerce_id)

        model_name = (
            os.getenv("GEMINI_MODEL_SQL")
            or os.getenv("GEMINI_MODEL")
            or _GEMINI_MODEL_DEFAULT
        )

        print(f"🤖 Gemini SQL para: '{question[:60]}' (comercio: {commerce_id})")
        raw_content = _gemini_generate(system_prompt, question, model_name, 0.1)
        print(f"📝 Gemini respondió: {raw_content[:200]}")

        if raw_content == "NO_DATA":
            return {"sql": None, "chart": "NONE"}

        # Limpiar markdown
        cleaned = raw_content.replace("```sql", "").replace("```", "").strip()
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if not lines:
            return {"sql": None, "chart": "NONE"}

        if lines[0] == "NO_SQL":
            message = " ".join(lines[1:]) if len(lines) > 1 else "No tengo esos datos disponibles."
            return {"sql": None, "chart": "NONE", "message": message}

        if lines[0] == "GENERAL_ANSWER":
            message = " ".join(lines[1:]) if len(lines) > 1 else "Aquí tienes un consejo general..."
            return {"sql": None, "chart": "NONE", "message": message, "is_general": True}

        # Reconstruir SQL (todo hasta CHART:)
        sql_lines = []
        chart_type = "NONE"
        for line in lines:
            if line.startswith("CHART:"):
                chart_type = line.split("CHART:", 1)[1].strip() or "NONE"
                break
            sql_lines.append(line)

        sql_query = " ".join(sql_lines).strip()
        if not sql_query:
            return {"sql": None, "chart": "NONE"}

        # Validar que el SQL filtre por comercio
        has_commerce = (
            "id_comercio" in sql_query.lower() or
            (commerce_id and commerce_id.lower() in sql_query.lower())
        )
        if commerce_id and not has_commerce:
            print(f"⚠️ SQL sin filtro de comercio: {sql_query[:100]}")
            return {
                "sql": None,
                "chart": "NONE",
                "message": "No pude identificar el comercio para filtrar la consulta.",
            }

        # Compatibilidad formato antiguo [CHART:XXXX]
        chart_match = re.search(r"\[CHART:(.*?)\]", sql_query)
        if chart_match:
            chart_type = chart_match.group(1)
            sql_query = re.sub(r"\[CHART:.*?\]", "", sql_query).strip()

        print(f"✅ SQL final: {sql_query[:120]}")
        return {"sql": sql_query, "chart": chart_type}

    except Exception as e:
        error_msg = str(e).lower()
        print(f"❌ Error Gemini SQL: {e}")
        if "429" in error_msg or "quota" in error_msg or "resource_exhausted" in error_msg:
            return {
                "sql": None, 
                "chart": "NONE", 
                "message": "El servicio está procesando demasiadas solicitudes en este momento. Por favor, vuelve a intentarlo en unos segundos."
            }
        return {"sql": None, "chart": "NONE"}


def humanize_results(question: str, data_results: list):
    """
    Paso 2: Datos crudos → Respuesta humana con recomendaciones.
    """
    try:
        provider = _get_provider()
        if provider == "none":
            return "He obtenido los datos, pero falta configurar la IA para explicar el resultado."

        data_str = str(data_results[:20])  # Limitar datos para velocidad
        user_content = f"Pregunta del usuario: {question}\nDatos de la BD: {data_str}"

        model_name = (
            os.getenv("GEMINI_MODEL_HUMAN")
            or os.getenv("GEMINI_MODEL")
            or _GEMINI_MODEL_DEFAULT
        )
        return _gemini_generate(HUMANIZER_PROMPT, user_content, model_name, 0.5)

    except Exception as e:
        print(f"❌ Error Gemini Humanizer: {e}")
        return "He obtenido los datos, pero tuve un problema al redactar la explicación."


def generate_business_insights(commerce_id: str, summary_data: dict) -> str:
    """
    Genera insights proactivos y recomendaciones basadas en datos del negocio.
    """
    try:
        provider = _get_provider()
        if provider == "none":
            return None

        insights_prompt = """
Eres Deu, el asesor financiero inteligente de Deuna.
Con los datos que te doy, genera UN insight breve y accionable para el comerciante.

REGLAS:
- Máximo 2 oraciones.
- Español neutro y sencillo.
- Incluye un dato concreto del resumen.
- Sugiere UNA acción específica.
- Usa un emoji relevante.
- NO inventes datos.

EJEMPLOS:
Datos: ventas_semana=500, ventas_semana_anterior=700
→ Tus ventas bajaron un 28% esta semana comparado con la anterior. Podrías lanzar una promo de medio día para recuperar el ritmo 💡

Datos: clientes_riesgo=8, clientes_total=50
→ Tienes 8 clientes en riesgo de no volver (16% del total). Considera enviarles un mensaje o descuento especial para recuperarlos 📱
"""

        data_str = str(summary_data)
        model_name = os.getenv("GEMINI_MODEL") or _GEMINI_MODEL_DEFAULT
        return _gemini_generate(insights_prompt, data_str, model_name, 0.6)

    except Exception:
        return None