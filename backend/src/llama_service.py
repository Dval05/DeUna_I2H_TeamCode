import os
import re
from groq import Groq
from dotenv import load_dotenv
from .prompts import SYSTEM_PROMPT, HUMANIZER_PROMPT

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente de Groq
# Recuerda que en el .env debe estar: GROQ_API_KEY=gsk_...
_groq_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=_groq_key) if _groq_key else None

def get_sql_from_question(question: str):
    """
    Paso 1: Transforma la pregunta en SQL + Etiqueta de Gráfica.
    Retorna un diccionario con {'sql': str, 'chart': str}
    """
    try:
        if client is None:
            print("⚠️ GROQ_API_KEY no configurada")
            return {"sql": None, "chart": "NONE"}
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # El más rápido para SQL
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ],
            temperature=0.1, # Precisión máxima
        )
        
        raw_content = response.choices[0].message.content.strip()
        
        if raw_content == "NO_DATA":
            return {"sql": None, "chart": "NONE"}

        # Extraer la etiqueta de la gráfica usando Regex [CHART:XXXX]
        chart_match = re.search(r"\[CHART:(.*?)\]", raw_content)
        chart_type = chart_match.group(1) if chart_match else "NONE"
        
        # Limpiar el SQL (quitar la etiqueta del string)
        sql_query = re.sub(r"\[CHART:.*?\]", "", raw_content).strip()
        
        # Quitar posibles bloques de código Markdown si la IA los pone
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        return {"sql": sql_query, "chart": chart_type}

    except Exception as e:
        print(f"Error en Llama Service (SQL): {e}")
        return {"sql": None, "chart": "NONE"}

def humanize_results(question: str, data_results: list):
    """
    Paso 2: Traduce los datos crudos a una respuesta amigable.
    """
    try:
        if client is None:
            return "He obtenido los datos, pero falta configurar la IA para explicar el resultado."
        # Convertimos la lista de resultados a string para el prompt
        data_str = str(data_results)
        
        user_content = f"Pregunta del usuario: {question}\nDatos de la BD: {data_str}"
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": HUMANIZER_PROMPT},
                {"role": "user", "content": user_content}
            ],
            temperature=0.5, # Un poco de fluidez natural
        )
        
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"Error en Llama Service (Humanizer): {e}")
        return "He obtenido los datos, pero tuve un problema al redactar la explicación. Revisa la tabla o gráfica."