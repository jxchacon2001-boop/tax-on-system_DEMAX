import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timezone, timedelta
from PIL import Image
import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# --- CONFIGURACIÓN DE LA BASE DE DATOS (DEMAX) ---
def inicializar_bd():
    conn = sqlite3.connect("demax_system.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)
    
    # Tabla de Productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT,
            codigo TEXT UNIQUE NOT NULL,
            descripcion TEXT,
            unidades TEXT,
            precio_venta REAL NOT NULL,
            precio_compra REAL NOT NULL
        )
    """)
    
    cursor.execute("PRAGMA table_info(productos)")
    cols_prod = [col[1] for col in cursor.fetchall()]
    if 'tipo' not in cols_prod:
        cursor.execute("ALTER TABLE productos ADD COLUMN tipo TEXT DEFAULT 'General'")

    # Tabla de Proformas (Encabezado con estado)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS proformas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_proforma TEXT UNIQUE,
            fecha TEXT,
            cliente TEXT,
            ruc_cliente TEXT,
            vendedor TEXT,
            subtotal REAL,
            descuento REAL,
            iva REAL,
            total REAL,
            ganancia_neta REAL,
            estado TEXT DEFAULT 'Pendiente'
        )
    """)
    
    cursor.execute("PRAGMA table_info(proformas)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'estado' not in columns:
        cursor.execute("ALTER TABLE proformas ADD COLUMN estado TEXT DEFAULT 'Pendiente'")
    
    # Tabla de Detalle de Proforma
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detalle_proforma (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nro_proforma TEXT,
            codigo TEXT,
            descripcion TEXT,
            unidades TEXT,
            cantidad REAL,
            precio_unitario REAL,
            subtotal REAL,
            FOREIGN KEY(nro_proforma) REFERENCES proformas(nro_proforma)
        )
    """)
    
    # Crear cuenta Administrador por defecto
    cursor.execute("SELECT * FROM usuarios WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                       ("admin", "1234", "Administrador"))
    
    conn.commit()
    conn.close()

inicializar_bd()

# --- CONFIGURACIÓN DE PÁGINA Y ESTILO ---
st.set_page_config(page_title="DEMAX | Sistema de Cotizaciones", layout="wide")

# --- ENCABEZADO CON LOGOTIPO ---
col_logo, col_texto = st.columns([1, 8])
with col_logo:
    try:
        img_logo = Image.open("logo_demax.jpg")
        st.image(img_logo, width=80)
    except Exception:
        st.warning("⚠️ Logo 'logo_demax.jpg' no encontrado")

with col_texto:
    st.markdown("### DEMAX — Sistema de Cotizaciones y Control Financiero")

st.markdown("---")

if 'autenticado' not in st.session_state:
    st.session_state.autenticado = False
    st.session_state.usuario = None
    st.session_state.rol = None
    st.session_state.menu_actual = "Crear Cotización"

# --- PANTALLA DE LOGIN ---
if not st.session_state.autenticado:
    st.subheader("Iniciar Sesión en la plataforma DEMAX")
    col1, col2 = st.columns([1, 2])
    with col1:
        username_input = st.text_input("Usuario")
        password_input = st.text_input("Contraseña", type="password")
        
        if st.button("Ingresar a DEMAX"):
            conn = sqlite3.connect("demax_system.db")
            cursor = conn.cursor()
            cursor.execute("SELECT rol FROM usuarios WHERE username = ? AND password = ?", (username_input, password_input))
            resultado = cursor.fetchone()
            conn.close()
            
            if resultado:
                st.session_state.autenticado = True
                st.session_state.usuario = username_input
                st.session_state.rol = resultado[0]
                st.session_state.menu_actual = "Crear Cotización"
                st.success(f"¡Bienvenido a DEMAX, {username_input}!")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
else:
    # --- MENÚ LATERAL FIJO ---
    st.sidebar.markdown("### 🏢 DEMAX Panel")
    st.sidebar.write(f"Conectado: **{st.session_state.usuario}**")
    st.sidebar.write(f"Rol: **{st.session_state.rol}**")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Menú Principal")
    
    if st.sidebar.button("📝 Crear Cotización", use_container_width=True):
        st.session_state.menu_actual = "Crear Cotización"
    if st.sidebar.button("📂 Historial y Edición", use_container_width=True):
        st.session_state.menu_actual = "Historial y Descargas"
        
    if st.session_state.rol == "Administrador":
        if st.sidebar.button("📋 Gestión de Cotizaciones", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Cotizaciones"
        if st.sidebar.button("📦 Gestión de Productos", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Productos"
        if st.sidebar.button("👥 Gestión de Usuarios", use_container_width=True):
            st.session_state.menu_actual = "Gestión de Usuarios"
        if st.sidebar.button("📊 Reportes de Ganancias", use_container_width=True):
            st.session_state.menu_actual = "Reportes de Ganancias"
            
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.session_state.rol = None
        st.rerun()
        
    menu = st.session_state.menu_actual
        
    # --- GESTIÓN DE USUARIOS ---
    if menu == "Gestión de Usuarios" and st.session_state.rol == "Administrador":
        st.header("DEMAX | Administración de Cuentas")
        with st.form("form_crear_usuario"):
            nuevo_user = st.text_input("Nombre de Usuario")
            nuevo_pass = st.text_input("Contraseña", type="password")
            nuevo_rol = st.selectbox("Rol del Usuario", ["Vendedor", "Administrador"])
            btn_crear = st.form_submit_button("Crear Cuenta en DEMAX")
            
            if btn_crear:
                if nuevo_user and nuevo_pass:
                    try:
                        conn = sqlite3.connect("demax_system.db")
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)", 
                                       (nuevo_user, nuevo_pass, nuevo_rol))
                        conn.commit()
                        conn.close()
                        st.success(f"¡Usuario '{nuevo_user}' registrado con éxito!")
                    except sqlite3.IntegrityError:
                        st.error("El nombre de usuario ya existe.")
                else:
                    st.warning("Completa todos los campos.")
                    
        st.subheader("Usuarios Registrados")
        conn = sqlite3.connect("demax_system.db")
        df_usuarios = pd.read_sql_query("SELECT id, username, rol FROM usuarios", conn)
        conn.close()
        st.dataframe(df_usuarios, use_container_width=True)

    # --- GESTIÓN DE PRODUCTOS Y CARGA MASIVA ---
    elif menu == "Gestión de Productos" and st.session_state.rol == "Administrador":
        st.header("DEMAX | Catálogo de Productos y Carga Masiva")
        
        st.subheader("📥 Carga Masiva desde Archivo Excel")
        archivo_excel = st.file_uploader("Sube tu archivo Excel con el catálogo", type=["xlsx", "xls"])
        if archivo_excel is not None:
            try:
                df_subido = pd.read_excel(archivo_excel)
                if len(df_subido.columns) >= 6:
                    if df_subido.iloc[0, 0] == "Tipo":
                        df_subido.columns = df_subido.iloc[0]
                        df_subido = df_subido.drop(0).reset_index(drop=True)
                    else:
                        df_subido.columns = ['Tipo', 'Código', 'Descripción', 'Unidades', 'Precio de compra', 'Precio de venta']
                    
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    contador = 0
                    for _, row in df_subido.iterrows():
                        tipo = str(row.iloc[0]) if pd.notna(row.iloc[0]) else "General"
                        codigo = str(row.iloc[1]) if pd.notna(row.iloc[1]) else ""
                        desc = str(row.iloc[2]) if pd.notna(row.iloc[2]) else ""
                        unidades = str(row.iloc[3]) if pd.notna(row.iloc[3]) else "Pcs"
                        try:
                            p_compra = float(row.iloc[4]) if pd.notna(row.iloc[4]) else 0.0
                            p_venta = float(row.iloc[5]) if pd.notna(row.iloc[5]) else 0.0
                        except:
                            p_compra, p_venta = 0.0, 0.0
                            
                        if codigo and codigo != "nan":
                            cursor.execute("""
                                INSERT OR REPLACE INTO productos (tipo, codigo, descripcion, unidades, precio_venta, precio_compra)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (tipo, codigo, desc, unidades, p_venta, p_compra))
                            contador += 1
                    conn.commit()
                    conn.close()
                    st.success(f"¡Se cargaron/actualizaron {contador} productos masivamente con éxito!")
                else:
                    st.error("El formato del Excel debe incluir las columnas: Tipo, Código, Descripción, Unidades, Compra, Venta.")
            except Exception as e:
                st.error(f"Error al procesar el archivo Excel: {e}")

        st.markdown("---")
        st.subheader("Registrar Producto Individual")
        with st.form("form_producto"):
            col1, col2 = st.columns(2)
            with col1:
                tipo_prod = st.text_input("Tipo / Categoría")
                codigo = st.text_input("Código de Producto")
                descripcion = st.text_area("Descripción / Diseño")
                unidades = st.selectbox("Unidades / Medida", ["Pcs", "Bundle", "Metros", "Unidades", "Rollos", "Cajas"])
            with col2:
                p_venta = st.number_input("Precio de Venta ($)", min_value=0.0, format="%.2f")
                p_compra = st.number_input("Precio de Compra / Costo ($)", min_value=0.0, format="%.2f")
                
            btn_guardar_prod = st.form_submit_button("Guardar Producto")
            
            if btn_guardar_prod:
                if codigo and descripcion:
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    try:
                        cursor.execute("""
                            INSERT OR REPLACE INTO productos (tipo, codigo, descripcion, unidades, precio_venta, precio_compra)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (tipo_prod, codigo, descripcion, unidades, p_venta, p_compra))
                        conn.commit()
                        conn.close()
                        st.success(f"Producto '{codigo}' guardado correctamente.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Código y descripción obligatorios.")
                    
        st.subheader("Inventario Actual")
        conn = sqlite3.connect("demax_system.db")
        df_productos = pd.read_sql_query("SELECT id, tipo, codigo, descripcion, unidades, precio_venta, precio_compra FROM productos", conn)
        conn.close()
        st.dataframe(df_productos, use_container_width=True)

    # --- GESTIÓN DE COTIZACIONES (ESTADOS) ---
    elif menu == "Gestión de Cotizaciones" and st.session_state.rol == "Administrador":
        st.header("DEMAX | Gestión de Estado de Cotizaciones")
        conn = sqlite3.connect("demax_system.db")
        df_proformas = pd.read_sql_query("SELECT nro_proforma, fecha, cliente, ruc_cliente, vendedor, total, estado FROM proformas", conn)
        conn.close()
        
        if not df_proformas.empty:
            st.dataframe(df_proformas, use_container_width=True)
            
            st.markdown("### Actualizar Estado de Cotización")
            with st.form("form_actualizar_estado"):
                lista_nros = df_proformas['nro_proforma'].tolist()
                proforma_elegida = st.selectbox("Seleccione Nro. de Proforma", lista_nros)
                
                estado_actual_row = df_proformas[df_proformas['nro_proforma'] == proforma_elegida]['estado'].values[0]
                nuevo_estado = st.selectbox("Nuevo Estado", ["Pendiente", "Aceptada", "Rechazada"], index=["Pendiente", "Aceptada", "Rechazada"].index(estado_actual_row) if estado_actual_row in ["Pendiente", "Aceptada", "Rechazada"] else 0)
                
                btn_actualizar = st.form_submit_button("Actualizar Estado")
                
                if btn_actualizar:
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE proformas SET estado = ? WHERE nro_proforma = ?", (nuevo_estado, proforma_elegida))
                    conn.commit()
                    conn.close()
                    st.success(f"¡Cotización {proforma_elegida} actualizada a estado: **{nuevo_estado}**!")
                    st.rerun()
        else:
            st.info("No hay cotizaciones registradas aún.")

    # --- HISTORIAL, EDICIÓN Y DESCARGAS DE COTIZACIONES ---
    elif menu == "Historial y Descargas":
        st.header("DEMAX | Historial, Edición y Descarga de Cotizaciones")
        conn = sqlite3.connect("demax_system.db")
        df_hist = pd.read_sql_query("SELECT nro_proforma, fecha, cliente, ruc_cliente, vendedor, total, estado FROM proformas", conn)
        conn.close()
        
        if not df_hist.empty:
            busqueda = st.text_input("🔍 Buscar por Nombre de Cliente o Nro. de Proforma")
            if busqueda:
                df_hist = df_hist[df_hist['cliente'].str.contains(busqueda, case=False, na=False) | df_hist['nro_proforma'].str.contains(busqueda, case=False, na=False)]
            
            st.dataframe(df_hist, use_container_width=True)
            
            st.markdown("---")
            nro_elegido_descarga = st.selectbox("Seleccionar Proforma para Gestionar", df_hist['nro_proforma'].tolist() if not df_hist.empty else [])
            
            col_acc1, col_acc2 = st.columns(2)
            
            with col_acc1:
                if st.button("📥 Descargar PDF Actual"):
                    if nro_elegido_descarga:
                        conn = sqlite3.connect("demax_system.db")
                        cursor = conn.cursor()
                        cursor.execute("SELECT cliente, ruc_cliente, vendedor, fecha, subtotal, descuento, iva, total FROM proformas WHERE nro_proforma = ?", (nro_elegido_descarga,))
                        prof_data = cursor.fetchone()
                        cursor.execute("SELECT codigo, descripcion, unidades, cantidad, precio_unitario, subtotal FROM detalle_proforma WHERE nro_proforma = ?", (nro_elegido_descarga,))
                        detalles_data = cursor.fetchall()
                        conn.close()
                        
                        if prof_data:
                            cli, ruc_c, vend, fec, subt, desc, iv, tot = prof_data
                            nombre_archivo_pdf = f"{cli.upper()} - {nro_elegido_descarga}.pdf"
                            doc = SimpleDocTemplate(nombre_archivo_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                            elementos = []
                            
                            if os.path.exists("logo_demax.jpg"):
                                img_pdf = RLImage("logo_demax.jpg", width=100, height=40)
                                img_pdf.hAlign = 'CENTER'
                                elementos.append(img_pdf)
                                elementos.append(Spacer(1, 10))
                                
                            styles = getSampleStyleSheet()
                            estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A2B4C"), spaceAfter=6, alignment=1)
                            estilo_sub = ParagraphStyle('SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#555555"))
                            
                            elementos.append(Paragraph("<b>DEMAX — COTIZACIÓN DE VENTAS</b>", estilo_titulo))
                            elementos.append(Paragraph(f"<b>Nro:</b> {nro_elegido_descarga}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Fecha:</b> {fec}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Cliente:</b> {cli} | <b>RUC/Cédula:</b> {ruc_c}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Vendedor:</b> {vend}", estilo_sub))
                            elementos.append(Spacer(1, 15))
                            
                            data_tabla = [["Nro", "Código", "Descripción", "Unid.", "Cant.", "P. Venta", "Subtotal"]]
                            for idx, det in enumerate(detalles_data, start=1):
                                cod, des, unid, cant, p_uni, subt_lin = det
                                data_tabla.append([str(idx), cod, des, unid, f"{cant:.2f}", f"${p_uni:.3f}", f"${subt_lin:.3f}"])
                                
                            t = Table(data_tabla, colWidths=[30, 55, 205, 45, 45, 60, 70])
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A2B4C")),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0,0), (-1,-1), 8),
                                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ]))
                            elementos.append(t)
                            elementos.append(Spacer(1, 15))
                            elementos.append(Paragraph(f"<b>Subtotal:</b> ${subt:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Descuentos:</b> ${desc:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>IVA (15%):</b> ${iv:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>TOTAL:</b> ${tot:.3f}", estilo_sub))
                            doc.build(elementos)
                            
                            with open(nombre_archivo_pdf, "rb") as archivo_pdf:
                                st.download_button(
                                    label=f"📥 Guardar Archivo: {nombre_archivo_pdf}",
                                    data=archivo_pdf,
                                    file_name=nombre_archivo_pdf,
                                    mime="application/pdf",
                                    key=f"dl_{nro_elegido_descarga}"
                                )
                                
            with col_acc2:
                if st.button("✏️ Cargar para Editar"):
                    st.session_state.editando_nro = nro_elegido_descarga
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    cursor.execute("SELECT cliente, ruc_cliente, vendedor, descuento FROM proformas WHERE nro_proforma = ?", (nro_elegido_descarga,))
                    p_info = cursor.fetchone()
                    cursor.execute("SELECT codigo, descripcion, unidades, cantidad, precio_unitario, subtotal FROM detalle_proforma WHERE nro_proforma = ?", (nro_elegido_descarga,))
                    d_info = cursor.fetchall()
                    conn.close()
                    
                    if p_info:
                        st.session_state.edit_cliente = p_info[0]
                        st.session_state.edit_ruc = p_info[1]
                        st.session_state.edit_vendedor = p_info[2]
                        st.session_state.edit_descuento = p_info[3]
                        st.session_state.edit_carrito = []
                        for row in d_info:
                            st.session_state.edit_carrito.append({
                                "codigo": row[0],
                                "descripcion": row[1],
                                "unidades": row[2],
                                "cantidad": row[3],
                                "precio_unitario": row[4],
                                "subtotal": row[5]
                            })
                    st.success(f"Proforma {nro_elegido_descarga} cargada para edición.")

            if 'editando_nro' in st.session_state and st.session_state.editando_nro:
                st.markdown("---")
                st.subheader(f"Editando Proforma: {st.session_state.editando_nro}")
                
                e_cli = st.text_input("Cliente (Editar)", value=st.session_state.get('edit_cliente', ''))
                e_ruc = st.text_input("RUC / Cédula (Editar)", value=st.session_state.get('edit_ruc', ''))
                e_vend = st.text_input("Vendedor (Editar)", value=st.session_state.get('edit_vendedor', ''))
                e_desc = st.number_input("Descuento Total ($) (Editar)", min_value=0.0, value=float(st.session_state.get('edit_descuento', 0.0)), format="%.2f")
                
                st.markdown("##### 🛒 Ítems en la Proforma (Modificar Cantidades, Precios o Añadir Nuevos):")
                
                if 'edit_carrito' not in st.session_state:
                    st.session_state.edit_carrito = []
                    
                nuevos_items_editados = []
                for idx, item in enumerate(st.session_state.edit_carrito):
                    col_e1, col_e2, col_e3, col_e4, col_e5 = st.columns([2, 1, 1, 1, 1])
                    with col_e1:
                        st.write(f"**[{item['codigo']}]** {item['descripcion']}")
                    with col_e2:
                        nueva_cant = st.number_input("Cant.", min_value=1.0, value=float(item['cantidad']), step=1.0, key=f"ecant_{idx}")
                    with col_e3:
                        nuevo_precio = st.number_input("P. Venta ($)", min_value=0.0, value=float(item['precio_unitario']), format="%.3f", key=f"eprec_{idx}")
                    with col_e4:
                        sub_l = nueva_cant * nuevo_precio
                        st.write(f"Sub: **${sub_l:.2f}**")
                    with col_e5:
                        quitar = st.button("🗑️ Quitar", key=f"edel_{idx}")
                        
                    if not quitar:
                        nuevos_items_editados.append({
                            "codigo": item['codigo'],
                            "descripcion": item['descripcion'],
                            "unidades": item['unidades'],
                            "cantidad": nueva_cant,
                            "precio_unitario": nuevo_precio,
                            "subtotal": nueva_cant * nuevo_precio
                        })
                st.session_state.edit_carrito = nuevos_items_editados
                
                st.markdown("##### ➕ Agregar Producto Adicional")
                conn_inv = sqlite3.connect("demax_system.db")
                df_inv_edit = pd.read_sql_query("SELECT tipo, codigo, descripcion, unidades, precio_venta FROM productos", conn_inv)
                conn_inv.close()
                
                if not df_inv_edit.empty:
                    prod_add = st.selectbox("Seleccionar producto para añadir", df_inv_edit['codigo'] + " - " + df_inv_edit['descripcion'], key="sel_add_edit")
                    col_add1, col_add2 = st.columns(2)
                    with col_add1:
                        cant_add = st.number_input("Cantidad Adicional", min_value=1.0, value=1.0, step=1.0, key="cant_add_edit")
                    with col_add2:
                        cod_add_sel = prod_add.split(" - ")[0]
                        row_add_prod = df_inv_edit[df_inv_edit['codigo'] == cod_add_sel].iloc[0]
                        precio_add_sug = float(row_add_prod['precio_venta'])
                        precio_add = st.number_input("Precio Unitario Adicional ($)", min_value=0.0, value=precio_add_sug, format="%.3f", key="prec_add_edit")
                        
                    if st.button("➕ Añadir este producto a la edición"):
                        st.session_state.edit_carrito.append({
                            "codigo": cod_add_sel,
                            "descripcion": row_add_prod['descripcion'],
                            "unidades": row_add_prod['unidades'],
                            "cantidad": cant_add,
                            "precio_unitario": precio_add,
                            "subtotal": cant_add * precio_add
                        })
                        st.success("¡Producto añadido a la proforma!")
                        st.rerun()

                st.markdown("---")
                if st.button("💾 Guardar Todos los Cambios y Regenerar PDF"):
                    nro_target = st.session_state.editando_nro
                    carrito_actual = st.session_state.edit_carrito
                    
                    subtotal_ac = sum([i['subtotal'] for i in carrito_actual])
                    sub_desc = subtotal_ac - e_desc
                    iva_val = sub_desc * 0.15
                    total_val = sub_desc + iva_val
                    
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    
                    ganancia_tot = 0
                    for i in carrito_actual:
                        cursor.execute("SELECT precio_compra FROM productos WHERE codigo = ?", (i['codigo'],))
                        rc = cursor.fetchone()
                        costo_u = rc[0] if rc else 0
                        ganancia_tot += (i['precio_unitario'] - costo_u) * i['cantidad']
                    ganancia_fin = ganancia_tot - e_desc
                    
                    cursor.execute("""
                        UPDATE proformas SET cliente = ?, ruc_cliente = ?, vendedor = ?, subtotal = ?, descuento = ?, iva = ?, total = ?, ganancia_neta = ?
                        WHERE nro_proforma = ?
                    """, (e_cli, e_ruc, e_vend, subtotal_ac, e_desc, iva_val, total_val, ganancia_fin, nro_target))
                    
                    cursor.execute("DELETE FROM detalle_proforma WHERE nro_proforma = ?", (nro_target,))
                    for i in carrito_actual:
                        cursor.execute("""
                            INSERT INTO detalle_proforma (nro_proforma, codigo, descripcion, unidades, cantidad, precio_unitario, subtotal)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (nro_target, i['codigo'], i['descripcion'], i['unidades'], i['cantidad'], i['precio_unitario'], i['subtotal']))
                        
                    conn.commit()
                    conn.close()
                    
                    nombre_archivo_pdf = f"{e_cli.upper()} - {nro_target}.pdf"
                    doc = SimpleDocTemplate(nombre_archivo_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                    elementos = []
                    
                    if os.path.exists("logo_demax.jpg"):
                        img_pdf = RLImage("logo_demax.jpg", width=100, height=40)
                        img_pdf.hAlign = 'CENTER'
                        elementos.append(img_pdf)
                        elementos.append(Spacer(1, 10))
                        
                    styles = getSampleStyleSheet()
                    estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A2B4C"), spaceAfter=6, alignment=1)
                    estilo_sub = ParagraphStyle('SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#555555"))
                    
                    elementos.append(Paragraph("<b>DEMAX — COTIZACIÓN DE VENTAS</b>", estilo_titulo))
                    elementos.append(Paragraph(f"<b>Nro:</b> {nro_target}", estilo_sub))
                    elementos.append(Paragraph(f"<b>Cliente:</b> {e_cli} | <b>RUC/Cédula:</b> {e_ruc}", estilo_sub))
                    elementos.append(Paragraph(f"<b>Vendedor:</b> {e_vend}", estilo_sub))
                    elementos.append(Spacer(1, 15))
                    
                    data_t = [["Nro", "Código", "Descripción", "Unid.", "Cant.", "P. Venta", "Subtotal"]]
                    for idx, item in enumerate(carrito_actual, start=1):
                        data_t.append([str(idx), item['codigo'], item['descripcion'], item['unidades'], f"{item['cantidad']:.2f}", f"${item['precio_unitario']:.3f}", f"${item['subtotal']:.3f}"])
                        
                    t = Table(data_t, colWidths=[30, 55, 205, 45, 45, 60, 70])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A2B4C")),
                        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0,0), (-1,-1), 8),
                        ('BOTTOMPADDING', (0,0), (-1,0), 6),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                    ]))
                    elementos.append(t)
                    elementos.append(Spacer(1, 15))
                    elementos.append(Paragraph(f"<b>Subtotal:</b> ${subtotal_ac:.3f}", estilo_sub))
                    elementos.append(Paragraph(f"<b>Descuentos:</b> ${e_desc:.3f}", estilo_sub))
                    elementos.append(Paragraph(f"<b>IVA (15%):</b> ${iva_val:.3f}", estilo_sub))
                    elementos.append(Paragraph(f"<b>TOTAL:</b> ${total_val:.3f}", estilo_sub))
                    doc.build(elementos)
                    
                    st.success(f"¡Proforma {nro_target} actualizada y PDF regenerado con éxito!")
                    with open(nombre_archivo_pdf, "rb") as archivo_pdf:
                        st.download_button(
                            label="📥 Descargar PDF Actualizado",
                            data=archivo_pdf,
                            file_name=nombre_archivo_pdf,
                            mime="application/pdf"
                        )
                    st.session_state.editando_nro = None
        else:
            st.info("No hay cotizaciones registradas en el historial.")

    # --- MÓDULO DE COTIZACIONES ---
    elif menu == "Crear Cotización":
        st.header("DEMAX | Generador de Cotizaciones y Proformas")
        
        conn = sqlite3.connect("demax_system.db")
        df_inv = pd.read_sql_query("SELECT tipo, codigo, descripcion, unidades, precio_venta FROM productos", conn)
        conn.close()
        
        if df_inv.empty:
            st.warning("⚠️ No hay productos registrados en el sistema.")
        else:
            conn = sqlite3.connect("demax_system.db")
            cursor = conn.cursor()
            meses_es = {"01":"ENE", "02":"FEB", "03":"MAR", "04":"ABR", "05":"MAY", "06":"JUN", "07":"JUL", "08":"AGO", "09":"SEP", "10":"OCT", "11":"NOV", "12":"DIC"}
            
            ecuador_tz = timezone(timedelta(hours=-5))
            now = datetime.now(ecuador_tz)
            
            anio_mes = f"{now.year}-{meses_es.get(now.strftime('%m'), 'OCT')}"
            
            cursor.execute("SELECT COUNT(*) FROM proformas WHERE nro_proforma LIKE ?", (f"{anio_mes}%",))
            count = cursor.fetchone()[0]
            nro_sugerido = f"{anio_mes}-{str(count + 1).zfill(3)}"
            conn.close()

            col_c1, col_c2, col_c3, col_c4 = st.columns(4)
            with col_c1:
                cliente = st.text_input("Nombre del Cliente", value="")
            with col_c2:
                ruc_cliente = st.text_input("RUC / Cédula del Cliente", value="")
            with col_c3:
                nro_cotizacion = st.text_input("Nro. de Proforma", value=nro_sugerido)
            with col_c4:
                vendedor = st.text_input("Vendedor", value=st.session_state.usuario)
                
            st.markdown(f"**Fecha de Emisión:** {now.strftime('%Y-%m-%d')} | **Tipo de Documento:** Cotización de ventas estándar")
            st.markdown("---")
            st.subheader("Agregar Ítems a la Proforma")
            
            if 'carrito' not in st.session_state:
                st.session_state.carrito = []
                
            tipos_disponibles = ["Todos"] + sorted(df_inv['tipo'].dropna().unique().tolist())
            tipo_seleccionado = st.selectbox("📂 Filtrar por Tipo / Categoría de Producto", tipos_disponibles)
            
            if tipo_seleccionado != "Todos":
                df_filtrado = df_inv[df_inv['tipo'] == tipo_seleccionado]
            else:
                df_filtrado = df_inv
                
            col_i1, col_i2, col_i3 = st.columns([3, 1, 1])
            with col_i1:
                prod_seleccionado = st.selectbox("Seleccionar Producto", df_filtrado['codigo'] + " - " + df_filtrado['descripcion'])
            
            codigo_sel = prod_seleccionado.split(" - ")[0]
            row_prod = df_inv[df_inv['codigo'] == codigo_sel].iloc[0]
            
            with col_i2:
                cantidad = st.number_input("Cantidad", min_value=1.0, value=1.0, step=1.0)
            with col_i3:
                precio_sugerido = float(row_prod['precio_venta'])
                unidades_prod = row_prod['unidades']
                precio_unitario = st.number_input("Precio Unitario ($)", min_value=0.0, value=precio_sugerido, format="%.2f")
                
            if st.button("➕ Añadir a la Cotización"):
                desc_sel = row_prod['descripcion']
                subtotal_linea = cantidad * precio_unitario
                st.session_state.carrito.append({
                    "codigo": codigo_sel,
                    "descripcion": desc_sel,
                    "unidades": unidades_prod,
                    "cantidad": cantidad,
                    "precio_unitario": precio_unitario,
                    "subtotal": subtotal_linea
                })
                st.success("Ítem añadido correctamente.")
                
            if st.session_state.carrito:
                st.markdown("### Detalle de la Proforma")
                
                items_a_mantener = []
                for idx, item in enumerate(st.session_state.carrito):
                    col_det1, col_det2 = st.columns([5, 1])
                    with col_det1:
                        st.write(f"**{idx+1}.** [{item['codigo']}] {item['descripcion']} | Cant: {item['cantidad']} | P.U: ${item['precio_unitario']:.2f} | Sub: ${item['subtotal']:.2f}")
                    with col_det2:
                        if st.button("🗑️", key=f"del_item_{idx}"):
                            continue
                    items_a_mantener.append(item)
                st.session_state.carrito = items_a_mantener
                
                if st.button("🗑️ Vaciar Cotización Completa"):
                    st.session_state.carrito = []
                    st.rerun()
                    
                st.markdown("---")
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    descuento = st.number_input("Descuento Total ($)", min_value=0.0, value=0.0, format="%.2f")
                
                subtotal_acumulado = sum([item['subtotal'] for item in st.session_state.carrito])
                subtotal_con_desc = subtotal_acumulado - descuento
                iva = subtotal_con_desc * 0.15
                total_final = subtotal_con_desc + iva
                
                with col_t2:
                    st.markdown(f"#### Subtotal: ${subtotal_acumulado:.2f}")
                    st.markdown(f"#### Descuento: ${descuento:.2f}")
                    st.markdown(f"#### IVA (15%): ${iva:.2f}")
                    st.markdown(f"### TOTAL A PAGAR: ${total_final:.2f}")
                    
                if st.session_state.rol == "Administrador":
                    ganancia_estimada_preview = 0
                    conn = sqlite3.connect("demax_system.db")
                    cursor = conn.cursor()
                    for item in st.session_state.carrito:
                        cursor.execute("SELECT precio_compra FROM productos WHERE codigo = ?", (item['codigo'],))
                        res_c = cursor.fetchone()
                        costo_u = res_c[0] if res_c else 0
                        ganancia_estimada_preview += (item['precio_unitario'] - costo_u) * item['cantidad']
                    conn.close()
                    ganancia_estimada_preview -= descuento
                    st.info(f"🔒 **[Vista Administrador] Ganancia Neta Estimada:** ${ganancia_estimada_preview:.2f}")
                    
                if st.button("💾 Guardar y Generar PDF de la Proforma"):
                    if cliente:
                        conn = sqlite3.connect("demax_system.db")
                        cursor = conn.cursor()
                        try:
                            ganancia_total_proforma = 0
                            for item in st.session_state.carrito:
                                cursor.execute("SELECT precio_compra FROM productos WHERE codigo = ?", (item['codigo'],))
                                res_compra = cursor.fetchone()
                                costo_unitario = res_compra[0] if res_compra else 0
                                ganancia_total_proforma += (item['precio_unitario'] - costo_unitario) * item['cantidad']
                            
                            ganancia_neta_final = ganancia_total_proforma - descuento
                            
                            cursor.execute("""
                                INSERT OR REPLACE INTO proformas (nro_proforma, fecha, cliente, ruc_cliente, vendedor, subtotal, descuento, iva, total, ganancia_neta, estado)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pendiente')
                            """, (nro_cotizacion, now.strftime("%Y-%m-%d"), cliente, ruc_cliente, vendedor, subtotal_acumulado, descuento, iva, total_final, ganancia_neta_final))
                            
                            cursor.execute("DELETE FROM detalle_proforma WHERE nro_proforma = ?", (nro_cotizacion,))
                            for item in st.session_state.carrito:
                                cursor.execute("""
                                    INSERT INTO detalle_proforma (nro_proforma, codigo, descripcion, unidades, cantidad, precio_unitario, subtotal)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (nro_cotizacion, item['codigo'], item['descripcion'], item['unidades'], item['cantidad'], item['precio_unitario'], item['subtotal']))
                                
                            conn.commit()
                            conn.close()
                            
                            nombre_archivo_pdf = f"{cliente.upper()} - {nro_cotizacion}.pdf"
                            doc = SimpleDocTemplate(nombre_archivo_pdf, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
                            elementos = []
                            
                            if os.path.exists("logo_demax.jpg"):
                                img_pdf = RLImage("logo_demax.jpg", width=100, height=40)
                                img_pdf.hAlign = 'CENTER'
                                elementos.append(img_pdf)
                                elementos.append(Spacer(1, 10))
                                
                            styles = getSampleStyleSheet()
                            estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1A2B4C"), spaceAfter=6, alignment=1)
                            estilo_sub = ParagraphStyle('SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor("#555555"))
                            
                            elementos.append(Paragraph("<b>DEMAX — COTIZACIÓN DE VENTAS</b>", estilo_titulo))
                            elementos.append(Paragraph(f"<b>Nro:</b> {nro_cotizacion}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Fecha:</b> {now.strftime('%Y-%m-%d')}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Cliente:</b> {cliente} | <b>RUC/Cédula:</b> {ruc_cliente}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Vendedor:</b> {vendedor}", estilo_sub))
                            elementos.append(Spacer(1, 15))
                            
                            data_tabla = [["Nro", "Código", "Descripción", "Unid.", "Cant.", "P. Venta", "Subtotal"]]
                            for idx, item in enumerate(st.session_state.carrito, start=1):
                                data_tabla.append([
                                    str(idx), item['codigo'], item['descripcion'], item['unidades'],
                                    f"{item['cantidad']:.2f}", f"${item['precio_unitario']:.3f}", f"${item['subtotal']:.3f}"
                                ])
                                
                            t = Table(data_tabla, colWidths=[30, 55, 205, 45, 45, 60, 70])
                            t.setStyle(TableStyle([
                                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A2B4C")),
                                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0,0), (-1,-1), 8),
                                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                            ]))
                            elementos.append(t)
                            elementos.append(Spacer(1, 15))
                            elementos.append(Paragraph(f"<b>Subtotal:</b> ${subtotal_acumulado:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>Descuentos:</b> ${descuento:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>IVA (15%):</b> ${iva:.3f}", estilo_sub))
                            elementos.append(Paragraph(f"<b>TOTAL:</b> ${total_final:.3f}", estilo_sub))
                            doc.build(elementos)
                            
                            st.success(f"¡Cotización guardada y PDF generado con éxito!")
                            with open(nombre_archivo_pdf, "rb") as archivo_pdf:
                                st.download_button(
                                    label="📥 Descargar PDF de la proforma",
                                    data=archivo_pdf,
                                    file_name=nombre_archivo_pdf,
                                    mime="application/pdf"
                                )
                            st.session_state.carrito = []
                        except Exception as e:
                            st.error(f"Error al generar la proforma o PDF: {e}")
                    else:
                        st.warning("Por favor ingresa el nombre del cliente.")

    # --- REPORTES DE GANANCIAS (CON FILTROS Y SOLO ADMIN) ---
    elif menu == "Reportes de Ganancias" and st.session_state.rol == "Administrador":
        st.header("DEMAX | Reportes Financieros de Ganancia Neta")
        conn = sqlite3.connect("demax_system.db")
        df_todas = pd.read_sql_query("SELECT nro_proforma, fecha, cliente, ruc_cliente, vendedor, total, ganancia_neta, estado FROM proformas", conn)
        conn.close()
        
        if not df_todas.empty:
            st.markdown("### 🔎 Filtros de Reporte")
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                filtro_estado = st.selectbox("Estado de Cotización", ["Todos", "Aceptada", "Pendiente", "Rechazada"], index=1)
            with col_f2:
                vendedores_disp = ["Todos"] + sorted(df_todas['vendedor'].dropna().unique().tolist())
                filtro_vendedor = st.selectbox("Vendedor", vendedores_disp)
            with col_f3:
                filtro_cliente = st.text_input("Filtrar por Cliente (Texto)")
                
            df_filtrado = df_todas.copy()
            if filtro_estado != "Todos":
                df_filtrado = df_filtrado[df_filtrado['estado'] == filtro_estado]
            if filtro_vendedor != "Todos":
                df_filtrado = df_filtrado[df_filtrado['vendedor'] == filtro_vendedor]
            if filtro_cliente:
                df_filtrado = df_filtrado[df_filtrado['cliente'].str.contains(filtro_cliente, case=False, na=False)]

            st.markdown("### Historial General de Proformas (Filtrado)")
            st.dataframe(df_filtrado, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 💰 Ganancia Neta de Cotizaciones (Según Filtros)")
            df_aceptadas_filt = df_filtrado[df_filtrado['estado'] == 'Aceptada']
            
            if not df_aceptadas_filt.empty:
                st.dataframe(df_aceptadas_filt[['nro_proforma', 'fecha', 'cliente', 'vendedor', 'total', 'ganancia_neta']], use_container_width=True)
                ganancia_neta_total = df_aceptadas_filt['ganancia_neta'].sum()
                st.metric(label="Ganancia Neta Total (Proformas Aceptadas Filtradas)", value=f"${ganancia_neta_total:.2f}")
            else:
                st.warning("⚠️ No hay cotizaciones con estado 'Aceptada' que coincidan con los filtros seleccionados.")
        else:
            st.info("Aún no hay cotizaciones registradas en el sistema.")