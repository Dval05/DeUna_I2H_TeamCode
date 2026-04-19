from src.question_router import route_question, _normalize

q1 = "cuantos clientes tengo en riesgo de abandono"
q2 = "¿cuántos clientes en riesgo de abandono tengo?"

print("Q1 en_riesgo:", "riesgo de abandono" in _normalize(q1), "=>", route_question(q1, "COM-001"))
print("Q2 en_riesgo:", "riesgo de abandono" in _normalize(q2), "=>", route_question(q2, "COM-001"))
