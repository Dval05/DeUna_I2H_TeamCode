from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .llama_service import get_sql_from_question, humanize_results
from .database import execute_read_query
##from .cache_manager import obtener_de_cache, guardar_en_cache

app = FastAPI(title="Deuna Contador de Bolsillo API")

class QuestionRequest(BaseModel):
    question: str

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

    # 2. Generar SQL con LLAMA 3.1 (Groq)
    ai_response = get_sql_from_question(user_query)
    sql = ai_response["sql"]
    chart_type = ai_response["chart"]

    if not sql or sql == "NO_DATA":
        return {
            "answer": "Lo siento, no tengo datos suficientes para responder esa pregunta.",
            "chart": "NONE",
            "source": "llm"
        }

    # 3. Ejecutar en la Base de Datos Local
    data_results = execute_read_query(sql)
    
    if data_results is None:
        raise HTTPException(status_code=500, detail="Error ejecutando la consulta en la base de datos")

    # 4. Humanizar el resultado
    final_answer = humanize_results(user_query, data_results)

    # 5. Guardar en el REPERTORIO para la próxima vez
##   guardar_en_cache(user_query, sql, chart_type, final_answer)

    return {
        "answer": final_answer,
        "chart": chart_type,
        "data": data_results,
        "sql": sql,
        "source": "llm"
    }