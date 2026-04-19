import requests
import time
import json

# Configuración local de FastAPI
URL = "http://127.0.0.1:8000/ask"
AUTH_TOKEN = "demo-token-admin"
PROACTIVE_URL = "http://127.0.0.1:8000/chat/proactive"

# Las 15 preguntas de prueba (puedes añadir las que pide el reto)
TEST_QUESTIONS = [
    "¿Cuánto vendí en total el día de hoy?",  #1
    "De lo que vendí esta semana, ¿cuál fue mi ganancia real?", #2
    "¿Qué es lo que más me compran mis clientes?",#3
    "¿Cuántos clientes frecuentes tengo registrados?", #4
    "¿A qué hora se llena más mi local normalmente?",#5
    "¿Cuánto dinero me entró por transferencias vs QR Deuna este mes?",#6
    "¿Cuánto vendí el domingo pasado?" ,#7
    "¿Cuánto pago de arriendo y luz por el local?",#9
    "¿Gané más dinero este mes o el mes pasado?",
    "¿Qué clientes dejaron de venir últimamente?",
    "Sé que vendo más bebidas, pero ¿qué categoría me deja más plata limpia?",
    "¿Cuánto gasta la gente en promedio cada vez que me compra?",
    "¿He conseguido clientes nuevos esta semana?",
    "De esos clientes nuevos, ¿alguno ya me volvió a comprar?",
    "¿Quién es mi mejor cliente y cuánto me ha hecho ganar?"
]

def run_tests():
    print("Iniciando validación del Agente de IA...\n")
    results = []
    for i, q in enumerate(TEST_QUESTIONS, 1):
        start_time = time.time()
        try:
            response = requests.post(
                URL,
                json={"question": q},
                headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
            )
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                status = "✅" if duration < 5 else "⚠️ LENTO"
                print(f"Test {i}: {q}")
                print(f"   ⏱️ Tiempo: {duration:.2f}s | {status}")
                print(f"   📊 Gráfico: {data['chart']}")
                print(f"   🤖 Respuesta: {data['answer'][:100]}...")
                results.append({
                    "question": q,
                    "status": status,
                    "seconds": round(duration, 2),
                    "chart": data.get("chart"),
                    "answer": data.get("answer"),
                })
            else:
                print(f"Test {i}: ❌ Error {response.status_code}")
        except Exception as e:
            print(f"Test {i}: ❌ Fallo de conexión: {e}")
        print("-" * 50)

    try:
        proactive = requests.get(
            PROACTIVE_URL,
            headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        )
        if proactive.status_code == 200:
            print("Alerta proactiva:", proactive.json())
    except Exception as e:
        print("No se pudo consultar alerta proactiva:", e)

    with open("test_results.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    run_tests()