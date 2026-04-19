import asyncio
import os
import re
import time
import unicodedata
from collections import OrderedDict
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from .llama_service import get_sql_from_question, humanize_results
from .database import execute_read_query, has_base_tables
from .materialized_views import refresh_materialized_views
from .question_router import route_question
from .template_humanizer import humanize_from_data

APP_VERSION = "1.0.0"

# ── Caché en memoria (LRU simple) ────────────────────────────────────────────
_CACHE_MAX = 200
_response_cache: OrderedDict = OrderedDict()

def _cache_key(question: str, commerce_id: str) -> str:
    return f"{commerce_id}:{question.strip().lower()}"

def _cache_get(key: str):
    if key in _response_cache:
        _response_cache.move_to_end(key)
        return _response_cache[key]
    return None

def _cache_set(key: str, value: dict):
    _response_cache[key] = value
    if len(_response_cache) > _CACHE_MAX:
        _response_cache.popitem(last=False)

app = FastAPI(title="Deuna Contador de Bolsillo API")

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Modelos ───────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str

class LoginRequest(BaseModel):
    username: str
    password: str

class AmbiguityRequest(BaseModel):
    question: str

_COMMERCE_ID_PATTERN = re.compile(r"^COM-\d{3}$")

def _is_valid_commerce_id(value: Optional[str]) -> bool:
    return bool(value and _COMMERCE_ID_PATTERN.match(value))

def _extract_username_from_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    if not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "", 1).strip()
    if not token.startswith("demo-token-"):
        return None
    return token.replace("demo-token-", "", 1).strip()

def _resolve_commerce_id_from_token(authorization: Optional[str]) -> Optional[str]:
    username = _extract_username_from_token(authorization)
    if not username:
        return None
    user_record = _DEMO_USERS.get(username)
    if not user_record:
        return None
    commerce_id = user_record.get("commerce_id")
    if not _is_valid_commerce_id(commerce_id):
        return None
    return commerce_id

def _normalize_short(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

def _get_refresh_minutes() -> int:
    raw_value = os.getenv("MATERIALIZED_REFRESH_MINUTES", "10")
    try:
        value = int(raw_value)
        return max(value, 0)
    except ValueError:
        return 10

def _sql_date_days_ago(days: int) -> str:
    if os.getenv("DB_ENGINE", "sqlite").lower() == "postgres":
        return f"(CURRENT_DATE - INTERVAL '{days} days')"
    return f"date('now', '-{days} days')"

def _fetch_single_value(sql_query: str) -> float:
    rows = execute_read_query(sql_query)
    if not rows:
        return 0.0
    value = next(iter(rows[0].values()), 0)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0

async def _materialized_refresh_loop(refresh_minutes: int):
    while True:
        await asyncio.sleep(refresh_minutes * 60)
        refresh_materialized_views()

@app.on_event("startup")
async def startup_refresh():
    if has_base_tables():
        refresh_materialized_views(full_refresh=True)
    else:
        print("⚠️ Tablas base no encontradas. Ejecuta la ingesta de datos primero.")
    refresh_minutes = _get_refresh_minutes()
    if refresh_minutes > 0:
        asyncio.create_task(_materialized_refresh_loop(refresh_minutes))

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Backend de IA para Deuna listo",
        "version": APP_VERSION,
    }

@app.post("/ask")
async def ask_ai(request: QuestionRequest, authorization: Optional[str] = Header(default=None)):
    t0 = time.time()
    user_query = request.question.strip()
    commerce_id = _resolve_commerce_id_from_token(authorization)
    if not commerce_id:
        raise HTTPException(status_code=401, detail="No autorizado. Inicia sesión de nuevo.")

    # 0. Saludos rápidos
    normalized = _normalize_short(user_query)
    if normalized in {"hola", "buenas", "buenos dias", "buenas tardes", "buenas noches", "hey", "ola", "como estas", "como esta", "quien eres", "que haces", "que puedes hacer", "saludos"}:
        return {
            "answer": "¡Hola! 👋 Soy tu Contador de Bolsillo con IA. Estoy diseñado para revisar tus ventas, analizar a tus clientes y darte los mejores consejos métricos para tu negocio. ¿En qué te ayudo hoy?",
            "chart": "NONE",
            "source": "rule",
        }

    # 1. Caché en memoria (respuesta instantánea)
    ck = _cache_key(user_query, commerce_id)
    cached = _cache_get(ck)
    if cached:
        cached["source"] = "cache"
        cached["response_time"] = f"{time.time() - t0:.2f}s"
        return cached

    # 2. Verificar datos
    if not has_base_tables():
        return {
            "answer": "No hay datos cargados. Ejecuta la ingesta de datos antes de consultar.",
            "chart": "NONE",
            "source": "no_data",
        }

    # 3. Router inteligente (SIN llamar a Gemini para SQL)
    routed = route_question(user_query, commerce_id)
    if routed:
        sql = routed["sql"]
        chart_type = routed["chart"]
        source = routed["source"]
        if sql is None:
            return {
                "answer": "No tengo esos datos disponibles. Solo puedo responder sobre ventas, clientes y transacciones de Deuna.",
                "chart": "NONE",
                "source": source,
            }
    else:
        # 4. Fallback: Gemini genera el SQL (solo preguntas no comunes)
        ai_response = get_sql_from_question(user_query, commerce_id)
        sql = ai_response.get("sql")
        chart_type = ai_response.get("chart", "NONE")
        source = "llm"

        if ai_response.get("is_general"):
            return {
                "answer": ai_response["message"],
                "chart": "NONE",
                "source": "general_chat",
            }

        if sql is None and ai_response.get("message"):
            return {
                "answer": ai_response["message"],
                "chart": "NONE",
                "source": "llm_no_sql",
            }

    if sql is None:
        return {
            "answer": "El sistema está un poco ocupado (límite de peticiones a la IA). Por favor, inténtalo de nuevo en unos segundos. ⏱️",
            "chart": "NONE",
            "source": "api_error",
        }
        
    if sql == "NO_DATA":
        return {
            "answer": "Lo siento, no tengo datos suficientes para responder esa pregunta.",
            "chart": "NONE",
            "source": "llm",
        }

    # 5. Ejecutar SQL en la base de datos
    data_results = execute_read_query(sql)

    if data_results is None:
        return {
            "answer": "No pude procesar tu consulta. Intenta con una pregunta más específica.",
            "chart": "NONE",
            "source": "db_error",
        }

    if not data_results:
        return {
            "answer": "No hay registros para esa consulta en tu negocio.",
            "chart": "NONE",
            "data": [],
            "sql": sql,
            "source": "no_data",
        }

    # 6. Humanizar: primero intenta TEMPLATES (instantáneo), luego Gemini
    final_answer = humanize_from_data(normalized, data_results, source)

    if final_answer is None:
        # Fallback a Gemini para humanizar
        final_answer = humanize_results(user_query, data_results)

    # 7. Guardar en caché
    response = {
        "answer": final_answer,
        "chart": chart_type,
        "data": data_results,
        "sql": sql,
        "source": source,
        "response_time": f"{time.time() - t0:.2f}s",
    }
    _cache_set(ck, response)

    return response


# ── Preguntas sugeridas ──────────────────────────────────────────────────────
SUGGESTED_QUESTIONS: List[str] = [
    "¿Cuánto vendí en total el día de hoy?",
    "De lo que vendí esta semana, ¿cuál fue mi ganancia real?",
    "¿Qué es lo que más me compran mis clientes?",
    "¿Cuántos clientes frecuentes tengo registrados?",
    "¿A qué hora se llena más mi local normalmente?",
    "¿Cuánto dinero me entró por transferencias vs QR Deuna este mes?",
    "¿Cuánto vendí el domingo pasado?",
    "¿Gané más dinero este mes o el mes pasado?",
    "¿Cuánto gasta la gente en promedio cada vez que me compra?",
    "¿He conseguido clientes nuevos esta semana?",
]

@app.get("/chat/suggested-questions")
def suggested_questions():
    return {"questions": SUGGESTED_QUESTIONS}


# ── Verificación de ambigüedad ───────────────────────────────────────────────
_AMBIGUOUS_RULES = {
    "ganancia": {
        "title": "Pregunta ambigua detectada",
        "message": '"Ganancia" puede significar utilidad neta o ingresos brutos. ¿Te refieres a lo que te quedó de ganancia o al total vendido?',
        "relatedQuestion": "¿Cuál fue mi ganancia real?",
    },
    "vendi": {
        "title": "Falta periodo de tiempo",
        "message": "Es súper útil saber de qué fecha hablamos. ¿Te refieres a las ventas de hoy, de esta semana o de este mes?",
        "relatedQuestion": "¿Cuánto vendí en total el día de hoy?",
    },
    "mejores clientes": {
        "title": "¿Mejores en compras o en visitas?",
        "message": "Un 'mejor cliente' puede ser el que más visita tu local o el que más dinero gasta en una sola compra.",
        "relatedQuestion": "¿Quién es mi cliente más importante en ganancias?",
    },
    "mejor producto": {
        "title": "¿Más vendido o más rentable?",
        "message": "Podemos ver qué categoría te trae más volumen o cuál te deja el mayor margen de ganancia limpia.",
        "relatedQuestion": "¿Qué categoría de compra me deja más ganancia?",
    },
    "clientes frecuentes": {
        "title": "Criterio de cliente frecuente",
        "message": '"Cliente frecuente" depende de cuántas veces consideras que deben regresar a la semana o al mes.',
        "relatedQuestion": "¿Cuántos clientes frecuentes tengo registrados?",
    },
    "perdidas": {
        "title": "Clarificando pérdidas",
        "message": "Con 'pérdidas' puedes referirte a clientes que no han vuelto, transacciones rechazadas o devoluciones. ¿Cuál te gustaría revisar?",
        "relatedQuestion": "¿Qué clientes no han vuelto en el último mes?",
    }
}

@app.post("/chat/ambiguity-check")
async def ambiguity_check(request: AmbiguityRequest):
    normalized = request.question.lower()
    for keyword, rule in _AMBIGUOUS_RULES.items():
        if keyword in normalized:
            return {
                "shouldWarn": True,
                "title": rule["title"],
                "message": rule["message"],
                "relatedQuestion": rule["relatedQuestion"],
            }
    return {"shouldWarn": False}


@app.get("/chat/proactive")
async def proactive_alert(authorization: Optional[str] = Header(default=None)):
    commerce_id = _resolve_commerce_id_from_token(authorization)
    if not commerce_id:
        raise HTTPException(status_code=401, detail="No autorizado. Inicia sesión de nuevo.")

    current_start = _sql_date_days_ago(7)
    previous_start = _sql_date_days_ago(14)

    sales_current_sql = (
        "SELECT COALESCE(SUM(monto_total), 0) AS total_sales "
        "FROM transacciones "
        f"WHERE DATE(fecha_hora) >= {current_start} "
        f"AND DATE(fecha_hora) < {_sql_date_days_ago(0)} "
        "AND estado = 'Exitosa' "
        f"AND id_comercio = '{commerce_id}';"
    )
    sales_previous_sql = (
        "SELECT COALESCE(SUM(monto_total), 0) AS total_sales "
        "FROM transacciones "
        f"WHERE DATE(fecha_hora) >= {previous_start} "
        f"AND DATE(fecha_hora) < {current_start} "
        "AND estado = 'Exitosa' "
        f"AND id_comercio = '{commerce_id}';"
    )
    new_customers_sql = (
        "SELECT COUNT(*) AS nuevos "
        "FROM clientes "
        f"WHERE fecha_registro >= {current_start} "
        f"AND id_comercio = '{commerce_id}';"
    )

    sales_current = _fetch_single_value(sales_current_sql)
    sales_previous = _fetch_single_value(sales_previous_sql)
    new_customers = _fetch_single_value(new_customers_sql)

    # Crear resumen de datos y pasarlo a Gemini para que genere un consejo experto
    from .llama_service import generate_business_insights
    summary_data = {
        "ventas_semana_actual": float(sales_current),
        "ventas_semana_pasada": float(sales_previous),
        "clientes_nuevos_semana": new_customers,
    }
    
    insight_message = generate_business_insights(commerce_id, summary_data)
    
    # Si la IA genera un consejo útil, lo usamos como alerta principal
    if insight_message:
        return {
            "shouldWarn": True,
            "title": "Tus datos al día 📈",
            "message": insight_message,
            "relatedQuestion": "¿Qué es lo que más me compran mis clientes?" if sales_previous > sales_current else "¿He conseguido clientes nuevos esta semana?",
        }

    # Fallback clásico si falla Gemini
    if sales_previous > 0:
        drop_pct = (sales_previous - sales_current) / sales_previous
        if drop_pct >= 0.2:
            return {
                "shouldWarn": True,
                "title": "Alerta de ventas",
                "message": "Tus ventas bajaron frente a la semana pasada. ¿Quieres revisar qué categoria se vendió menos?",
                "relatedQuestion": "¿Qué es lo que más me compran mis clientes?",
            }

    if new_customers == 0:
        return {
            "shouldWarn": True,
            "title": "Sin clientes nuevos",
            "message": "Esta semana no hay registros de nuevos clientes. Podrías lanzar una promoción para atraerlos.",
            "relatedQuestion": "¿He conseguido clientes nuevos esta semana?",
        }

    return {"shouldWarn": False}


# ── Login (autenticación simple para demo) ────────────────────────────────────
# En producción se usaría un sistema real de autenticación con hashing de
# contraseñas, JWT firmados, etc.  Esto es un placeholder funcional.
_DEMO_USERS = {
    "admin": {
        "password": "admin",
        "full_name": "Administrador DeUna",
        "role": "Admin",
        "commerce_id": "COM-001",
        "commerce_name": "Víveres Doña Rosa",
    },
    "comercio": {
        "password": "1234",
        "full_name": "Comercio Demo",
        "role": "Comercio",
        "commerce_id": "COM-002",
        "commerce_name": "Papelería Don Patricio",
    },
    "rosa": {
        "password": "1234",
        "full_name": "Doña Rosa",
        "role": "Comerciante",
        "commerce_id": "COM-001",
        "commerce_name": "Víveres Doña Rosa",
    },
    "patricio": {
        "password": "1234",
        "full_name": "Don Patricio",
        "role": "Comerciante",
        "commerce_id": "COM-002",
        "commerce_name": "Papelería Don Patricio",
    },
    "lorena": {
        "password": "1234",
        "full_name": "Dra. Lorena",
        "role": "Comerciante",
        "commerce_id": "COM-003",
        "commerce_name": "Farmacia Luz de Esperanza",
    },
    "lucho": {
        "password": "1234",
        "full_name": "Don Lucho",
        "role": "Comerciante",
        "commerce_id": "COM-004",
        "commerce_name": "Picantería El Sabor de la Abuela",
    },
}

@app.post("/auth/login")
async def login(request: LoginRequest):
    username = request.username.strip()
    user_record = _DEMO_USERS.get(username)
    if not user_record or user_record["password"] != request.password:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")
    return {
        "username": username,
        "full_name": user_record["full_name"],
        "role": user_record["role"],
        "commerce_id": user_record["commerce_id"],
        "commerce_name": user_record["commerce_name"],
        "token": f"demo-token-{username}",
    }