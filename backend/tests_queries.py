import requests
import time

# Configuración local de FastAPI
URL = "http://127.0.0.1:8000/ask"

# Las 15 preguntas de prueba (puedes añadir las que pide el reto)
TEST_QUESTIONS = [
    "¿Cuánto vendí en total el mes pasado?",
    "¿Cuál fue mi producto más vendido en diciembre?",
    "¿Quiénes son mis 5 mejores clientes por monto de compra?",
    "¿Qué categorías de productos me dan más ganancia?",
    "¿Cuántas transacciones fallidas hubo esta semana?",
    "¿Cuál es el ticket promedio de venta en mi local?",
    "¿Qué clientes no han comprado en los últimos 30 días?",
    "Compara las ventas de este lunes con el lunes anterior.",
    "¿Cuál es mi margen de ganancia neta total?",
    "Dime el horario en el que más vendo."
]

def run_tests():
    print("Iniciando validación del Agente de IA...\n")
    for i, q in enumerate(TEST_QUESTIONS, 1):
        start_time = time.time()
        try:
            response = requests.post(URL, json={"question": q})
            duration = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                status = "✅" if duration < 5 else "⚠️ LENTO"
                print(f"Test {i}: {q}")
                print(f"   ⏱️ Tiempo: {duration:.2f}s | {status}")
                print(f"   📊 Gráfico: {data['chart']}")
                print(f"   🤖 Respuesta: {data['answer'][:100]}...")
            else:
                print(f"Test {i}: ❌ Error {response.status_code}")
        except Exception as e:
            print(f"Test {i}: ❌ Fallo de conexión: {e}")
        print("-" * 50)

if __name__ == "__main__":
    run_tests()