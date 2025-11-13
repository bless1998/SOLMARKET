import sqlite3
import random

# Conexión a la base de datos
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Datos del vendedor
vendedor_id = '1004'
nombre_vendedor = 'Luna Ruiz'

# Crear 15 registros de ventas
for i in range(15):
    cantidad_horas = random.randint(10, 100)          # kWh disponibles
    precioxhora = random.randint(50, 100)             # precio por kWh
    preciototal = cantidad_horas * precioxhora

    cursor.execute('''
        INSERT INTO ventas (nombre_vendedor, numero_documento, cantidad_horas, precioxhora, preciototal)
        VALUES (?, ?, ?, ?, ?)
    ''', (nombre_vendedor, vendedor_id, cantidad_horas, precioxhora, preciototal))

conn.commit()
conn.close()

print("✅ Se han agregado 15 registros.")
