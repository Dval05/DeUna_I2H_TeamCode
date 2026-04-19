from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

q1 = "cuantos clientes tengo en riesgo de abandono"
q2 = "¿cuántos clientes en riesgo de abandono tengo?"

r1 = client.post("/ask", json={"question": q1}, headers={"Authorization": "Bearer COM-001"})
print("Q1:", r1.json())

r2 = client.post("/ask", json={"question": q2}, headers={"Authorization": "Bearer COM-001"})
print("Q2:", r2.json())
