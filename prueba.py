import sqlite3

# Conectar a la base de datos
conn = sqlite3.connect('database.db')
c = conn.cursor()

# Crear tabla si no existe
c.execute('''
CREATE TABLE IF NOT EXISTS solicitud_registro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL,
    numero_documento TEXT NOT NULL UNIQUE,
    direccion TEXT,
    tipo_usuario TEXT,
    contrasena TEXT NOT NULL
)
''')

# Insertar usuarios de prueba
usuarios = [
    
    ("Luna Ruiz", "luna@example.com", "1004", "Calle 13", "vendedor", "asdf")
]

for u in usuarios:
    try:
        c.execute('''
        INSERT INTO solicitud_registro (nombre, correo, numero_documento, direccion, tipo_usuario, contrasena)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', u)
    except sqlite3.IntegrityError:
        pass  # Si ya existe el usuario, ignorar

conn.commit()
conn.close()

print("Usuarios de prueba insertados correctamente.")
