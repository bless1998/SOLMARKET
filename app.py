from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'solmarket123'

# --- Credenciales del administrador ---
ADMIN_USER = "admin"
ADMIN_PASS = "solmarket123"

# --- Conexión a la base de datos ---
def get_db_connection():
    conn = sqlite3.connect('database.db', timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

# --- Crear tablas si no existen ---
def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()

        # Tabla de usuarios
        c.execute('''
            CREATE TABLE IF NOT EXISTS solicitud_registro (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                numero_documento TEXT NOT NULL UNIQUE,
                correo TEXT NOT NULL,
                direccion TEXT,
                tipo_usuario TEXT NOT NULL,
                contrasena TEXT NOT NULL
            )
        ''')

        # Tabla de solicitudes de compra
        c.execute('''
            CREATE TABLE IF NOT EXISTS solicitud_compra (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_comprador TEXT NOT NULL,
                numero_documento TEXT NOT NULL,
                energia_solicitada REAL NOT NULL,
                celular TEXT,
                fecha TEXT,
                metodo_pago TEXT,
                FOREIGN KEY (numero_documento) REFERENCES solicitud_registro(numero_documento)
            )
        ''')

        # Tabla de ventas
        c.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_vendedor TEXT NOT NULL,
                numero_documento TEXT NOT NULL,
                cantidad_horas REAL NOT NULL,
                precioxhora REAL NOT NULL,
                preciototal REAL NOT NULL DEFAULT 0
            )
        ''')

        # Tabla de ventas realizadas
        c.execute('''
            CREATE TABLE IF NOT EXISTS ventas_realizadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_vendedor INTEGER NOT NULL,
                nombre_vendedor TEXT NOT NULL,
                nombre_comprador TEXT NOT NULL,
                energia_vendida REAL NOT NULL,
                preciototal REAL NOT NULL
            )
        ''')

        conn.commit()

# Inicializar BD
init_db()

# --- Página principal ---
@app.route('/')
def index():
    return render_template('index.html')

# --- Registro ---
@app.route('/registro')
def registro():
    return render_template('registro.html')

@app.route('/registro_form', methods=['GET', 'POST'])
def registro_form():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        numero_documento = request.form.get('numero_documento')
        correo = request.form.get('correo')
        direccion = request.form.get('direccion')
        tipo_usuario = request.form.get('tipo_usuario')
        contrasena = request.form.get('contrasena')

        if not nombre or not numero_documento or not correo or not tipo_usuario or not contrasena:
            flash('⚠️ Faltan campos obligatorios.')
            return redirect(url_for('registro_form'))

        try:
            with get_db_connection() as conn:
                conn.execute('''
                    INSERT INTO solicitud_registro (nombre, numero_documento, correo, direccion, tipo_usuario, contrasena)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (nombre, numero_documento, correo, direccion, tipo_usuario, contrasena))
                conn.commit()
            flash('✅ Registro exitoso, ya puedes iniciar sesión.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('❌ El número de documento ya está registrado.')
        except Exception as e:
            flash(f'❌ Error al guardar el registro: {e}')

        return redirect(url_for('registro_form'))

    return render_template('registro.html')

# --- Login ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        numero_documento = request.form.get('numero_documento')
        clave = request.form.get('clave')

        if numero_documento == ADMIN_USER and clave == ADMIN_PASS:
            session['rol'] = 'admin'
            session['nombre'] = 'Administrador Sol-Market'
            flash("✅ Bienvenido, administrador.")
            return redirect(url_for('admin_ventas'))

        with get_db_connection() as conn:
            user = conn.execute(
                'SELECT * FROM solicitud_registro WHERE numero_documento = ? AND contrasena = ?',
                (numero_documento, clave)
            ).fetchone()

        if user:
            session['usuario_id'] = user['id']
            session['nombre'] = user['nombre']
            session['numero_documento'] = user['numero_documento']
            session['tipo_usuario'] = user['tipo_usuario']
            flash(f"Bienvenido {user['nombre']}!")

            if user['tipo_usuario'] == 'comprador':
                return redirect(url_for('reservas'))
            elif user['tipo_usuario'] == 'vendedor':
                return redirect(url_for('ventas_vendedor'))
            elif user['tipo_usuario'] == 'comprador-vendedor':
                return redirect(url_for('index'))
        else:
            flash('Número de documento o clave incorrectos.')

        return redirect(url_for('login'))

    return render_template('login.html')

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión.')
    return redirect(url_for('login'))

# --- Reservas ---
@app.route('/reservas')
def reservas():
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión para acceder.')
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        vendedores = conn.execute(
            'SELECT id, nombre FROM solicitud_registro WHERE tipo_usuario IN ("vendedor", "comprador-vendedor")'
        ).fetchall()

    return render_template('reservas.html', vendedores=vendedores)

# --- Guardar venta ---
@app.route('/guardar_venta', methods=['POST'])
def guardar_venta():
    is_json = request.is_json
    data = request.get_json() if is_json else request.form

    id_vendedor = data.get('id_vendedor') or data.get('numero_documento')
    nombre_comprador = session.get('nombre')
    cantidad_solicitada = float(data.get('energia_solicitada') or data.get('cantidad_horas', 0))

    with get_db_connection() as conn:
        vendedor = conn.execute('SELECT * FROM solicitud_registro WHERE id = ?', (id_vendedor,)).fetchone()
        if not vendedor:
            mensaje = 'Vendedor no encontrado.'
            return jsonify({"mensaje": mensaje}) if is_json else redirect(url_for('reservas'))

        venta_vendedor = conn.execute(
            'SELECT * FROM ventas WHERE numero_documento = ?',
            (vendedor['numero_documento'],)
        ).fetchone()

        if not venta_vendedor:
            mensaje = f'El vendedor {vendedor["nombre"]} no tiene energía disponible.'
            return jsonify({"mensaje": mensaje}) if is_json else redirect(url_for('reservas'))

        disponible = venta_vendedor['cantidad_horas']
        precio = venta_vendedor['precioxhora']

        if cantidad_solicitada > disponible:
            mensaje = f'⚠️ El vendedor {vendedor["nombre"]} no tiene suficiente energía disponible.'
            return jsonify({"mensaje": mensaje}) if is_json else redirect(url_for('reservas'))

        total_venta = cantidad_solicitada * precio

        conn.execute(
            'INSERT INTO ventas_realizadas (id_vendedor, nombre_vendedor, nombre_comprador, energia_vendida, preciototal) VALUES (?,?,?,?,?)',
            (vendedor['id'], vendedor['nombre'], nombre_comprador, cantidad_solicitada, total_venta)
        )

        nueva_cantidad = disponible - cantidad_solicitada
        conn.execute(
            'UPDATE ventas SET cantidad_horas = ?, preciototal = ? WHERE id = ?',
            (nueva_cantidad, nueva_cantidad * precio, venta_vendedor['id'])
        )

        conn.commit()

    mensaje = f'✅ Compra realizada correctamente! Total: ${total_venta:.2f}'
    return jsonify({"mensaje": mensaje}) if is_json else redirect(url_for('reservas'))

@app.route('/guardar_venta_v', methods=['POST'])
def guardar_venta_v():
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión antes de publicar tu oferta.')
        return redirect(url_for('login'))

    # Datos desde sesión y formulario
    nombre_vendedor = session['nombre']
    numero_documento = session['numero_documento']
    cantidad_horas = float(request.form.get('cantidad_horas', 0))
    precioxhora = float(request.form.get('precioxhora', 0))
    preciototal = cantidad_horas * precioxhora

    try:
        with get_db_connection() as conn:
            conn.execute(
                'INSERT INTO ventas (nombre_vendedor, numero_documento, cantidad_horas, precioxhora, preciototal) VALUES (?,?,?,?,?)',
                (nombre_vendedor, numero_documento, cantidad_horas, precioxhora, preciototal)
            )
            conn.commit()

        flash(f'✅ Oferta registrada correctamente. Total: ${preciototal:.2f}')
    except Exception as e:
        flash(f'❌ Error al registrar la oferta: {e}')

    return redirect(url_for('ventas_vendedor'))


# --- Ventas del vendedor ---
@app.route('/ventas')
def ventas_vendedor():
    if 'usuario_id' not in session:
        flash('Debes iniciar sesión.')
        return redirect(url_for('login'))

    if session['tipo_usuario'] not in ['vendedor', 'comprador-vendedor']:
        flash('No tienes permisos para acceder a este módulo.')
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        ventas_vendedor = conn.execute(
            'SELECT * FROM ventas WHERE numero_documento = ?',
            (session['numero_documento'],)
        ).fetchall()

    return render_template('ventas.html', ventas=ventas_vendedor)

# --- Panel administrador ---
@app.route('/admin/ventas')
def admin_ventas():
    if 'rol' not in session or session['rol'] != 'admin':
        flash('Acceso denegado.')
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        ventas = conn.execute('''
            SELECT 
                vr.id, 
                vr.id_vendedor, 
                vr.nombre_vendedor, 
                vr.nombre_comprador, 
                vr.energia_vendida, 
                vr.preciototal
            FROM ventas_realizadas vr
            ORDER BY vr.id DESC
        ''').fetchall()

    return render_template('admin_ventas.html', ventas=ventas)

# --- Panel de administrador: Solicitudes de registro ---
@app.route('/admin/solicitudes')
def admin_solicitudes():
    if 'rol' not in session or session['rol'] != 'admin':
        flash('Acceso denegado. Solo el administrador puede ver esta página.')
        return redirect(url_for('login'))

    with get_db_connection() as conn:
        solicitudes = conn.execute('SELECT * FROM solicitud_registro ORDER BY id DESC').fetchall()

    return render_template('admin_solicitudes.html', solicitudes=solicitudes)



if __name__ == '__main__':
    app.run()
