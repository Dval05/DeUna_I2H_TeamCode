import asyncio
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .llama_service import get_sql_from_question, humanize_results
from .database import execute_read_query
from .materialized_views import refresh_materialized_views
from .question_router import route_question
##from .cache_manager import obtener_de_cache, guardar_en_cache

app = FastAPI(title="Deuna Contador de Bolsillo API")

class QuestionRequest(BaseModel):
    question: str

def _get_refresh_minutes() -> int:
    raw_value = os.getenv("MATERIALIZED_REFRESH_MINUTES", "10")
    try:
        value = int(raw_value)
        return max(value, 0)
    except ValueError:
        return 10

async def _materialized_refresh_loop(refresh_minutes: int):
    while True:
        await asyncio.sleep(refresh_minutes * 60)
        refresh_materialized_views()

@app.on_event("startup")
async def startup_refresh():
    refresh_materialized_views(full_refresh=True)
    refresh_minutes = _get_refresh_minutes()
    if refresh_minutes > 0:
        asyncio.create_task(_materialized_refresh_loop(refresh_minutes))

@app.get("/")
def read_root():
    return {"status": "online", "message": "Backend de IA para Deuna listo"}

@app.post("/ask")
async def ask_ai(request: QuestionRequest):
    user_query = request.question.strip()
    
    # 1. Intentar obtener del REPERTORIO (Caché)
    ## cached_response = obtener_de_cache(user_query)
    ##if cached_response:
       ## return {
        ##    "answer": cached_response["human_answer"],
        ##    "chart": cached_response["chart"],
        ##    "sql": cached_response["sql"],
        ##    "source": "cache"
      ##  }

    # 2. Intentar ruteo a vistas materializadas
    routed = route_question(user_query)
    if routed:
        sql = routed["sql"]
        chart_type = routed["chart"]
        source = routed["source"]
        if sql is None:
            return {
                "answer": "No tengo esos datos disponibles. Solo puedo responder sobre ventas, clientes y transacciones de Deuna.",
                "chart": "NONE",
                "source": source
            }
    else:
        # 3. Generar SQL con LLAMA 3.1 (Groq)
        ai_response = get_sql_from_question(user_query)
        sql = ai_response["sql"]
        chart_type = ai_response["chart"]
        source = "llm"

    if not sql or sql == "NO_DATA":
        return {
            "answer": "Lo siento, no tengo datos suficientes para responder esa pregunta.",
            "chart": "NONE",
            "source": "llm"
        }

    # 4. Ejecutar en la Base de Datos Local
    data_results = execute_read_query(sql)
    
    if data_results is None:
        raise HTTPException(status_code=500, detail="Error ejecutando la consulta en la base de datos")

    # 5. Humanizar el resultado
    final_answer = humanize_results(user_query, data_results)

    # 5. Guardar en el REPERTORIO para la próxima vez
##   guardar_en_cache(user_query, sql, chart_type, final_answer)

    return {
        "answer": final_answer,
        "chart": chart_type,
        "data": data_results,
        "sql": sql,
        "source": source
    }