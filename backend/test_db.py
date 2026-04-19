import psycopg2

conn = psycopg2.connect(
    host='localhost', port=5432,
    dbname='deuna_negocios', user='postgres', password='root123'
)
cur = conn.cursor()

# 1. Verificar segmentos de clientes para COM-001
print("=== SEGMENTOS DE CLIENTES COM-001 ===")
cur.execute("SELECT segmento, COUNT(*) FROM clientes WHERE id_comercio = 'COM-001' GROUP BY segmento")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print()

# 2. Verificar datos en riesgo de abandono para todos los comercios
print("=== EN RIESGO DE ABANDONO (TODOS) ===")
cur.execute("SELECT id_comercio, COUNT(*) FROM clientes WHERE segmento = 'En riesgo de abandono' GROUP BY id_comercio")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

print()

# 3. Verificar valores únicos de segmento
print("=== VALORES ÚNICOS DE SEGMENTO ===")
cur.execute("SELECT DISTINCT segmento FROM clientes")
for row in cur.fetchall():
    print(f"  '{row[0]}'")

print()

# 4. Ver muestra de transacciones recientes
print("=== ÚLTIMAS 5 TRANSACCIONES COM-001 ===")
cur.execute("SELECT id_txn, fecha_hora::date, monto_total, estado FROM transacciones WHERE id_comercio = 'COM-001' ORDER BY fecha_hora DESC LIMIT 5")
for row in cur.fetchall():
    print(f"  {row}")

print()

# 5. Verificar conteo total
print("=== CONTEO GENERAL ===")
cur.execute("SELECT COUNT(*) FROM transacciones")
print(f"  Total transacciones: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM clientes")
print(f"  Total clientes: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM comercios")
print(f"  Total comercios: {cur.fetchone()[0]}")

conn.close()
