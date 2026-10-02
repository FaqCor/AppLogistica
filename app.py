import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from PIL import Image
import io
import folium
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Choferes - Logística", page_icon="🚚", layout="centered")

# --- 2. ESTILOS CSS MODERNOS PARA PANTALLA TÁCTIL ---
st.markdown("""
    <style>
    .stApp {
        background-color: #07090e;
        color: #f3f4f6;
        font-family: 'Segoe UI', Roboto, sans-serif;
    }
    /* Tarjetas de módulos modernos */
    .menu-card {
        background: linear-gradient(145deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.4);
        margin-bottom: 15px;
        transition: transform 0.2s ease;
    }
    .menu-card:hover {
        transform: translateY(-3px);
        border-color: #3b82f6;
    }
    .orion-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.9) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        margin-bottom: 20px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 20px;
        font-weight: 600;
        width: 100%;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    .stButton>button:hover {
        opacity: 0.9;
        background: linear-gradient(135deg, #2563eb, #1e40af);
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    pk = creds_dict.get("private_key", "").replace("\\n", "\n")
    if "BEGIN PRIVATE KEY" in pk:
        lines = [l.strip() for l in pk.split("\n") if l.strip()]
        body = "".join([l for l in lines if "-----" not in l])
        formatted_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
        pk = f"-----BEGIN PRIVATE KEY-----\n{formatted_body}\n-----END PRIVATE KEY-----\n"
    creds_dict["private_key"] = pk
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

client = init_connection()

@st.cache_resource
def get_sheet():
    return client.open("sistema de control de flota")

sheet = get_sheet()

# --- 4. BASE DE DATOS DE PINES ---
PINES_CHOFERES = {
    "ADRIÁN ROLDÁN": "1234",
    "DIEGO MEDINA": "2345",
    "ROBERTO PEREZ": "3456",
    "GUILLERMO ALBERTO": "4567",
    "GERONIMO MOLINA": "5678",
    "GONZALO ONESTI": "6789",
    "GABRIEL LLULL": "1111",
    "NICOLÁS DÍAZ": "2222",
    "FELIX NICOLÁS": "3333"
}

# --- 5. COORDENADAS Y CORREDORES ---
COORDS_DESTINOS = {
    "salta": (-24.7821, -65.4232),
    "jujuy": (-24.1858, -65.2995),
    "san salvador de jujuy": (-24.1858, -65.2995),
    "tucuman": (-26.8083, -65.2176),
    "san miguel de tucuman": (-26.8083, -65.2176),
    "catamarca": (-28.4696, -65.7852),
    "santiago del estero": (-27.7951, -64.2615),
    "la rioja": (-29.4131, -66.8558),
    "chaco": (-27.4512, -58.9866),
    "resistencia": (-27.4512, -58.9866),
    "corrientes": (-27.4692, -58.8306),
    "formosa": (-26.1853, -58.1758)
}

ORDEN_CORREDOR = {
    "salta": 1, "jujuy": 2, "san salvador de jujuy": 2,
    "tucuman": 3, "san miguel de tucuman": 3, "catamarca": 4,
    "santiago del estero": 5, "la rioja": 6, "chaco": 7,
    "resistencia": 7, "corrientes": 8, "formosa": 9
}

def obtener_coordenada(destino_str):
    dest_clean = destino_str.strip().lower()
    for key, coords in COORDS_DESTINOS.items():
        if key in dest_clean:
            return coords
    return (-24.7821, -65.4232)

def obtener_peso_destino(destino_str):
    dest_clean = destino_str.strip().lower()
    for key, peso in ORDEN_CORREDOR.items():
        if key in dest_clean:
            return peso
    return 99

def obtener_asignaciones_chofer(chofer):
    envios_lista = []
    patente_asignada = "Sin Asignar"
    try:
        ws = sheet.worksheet("Asignación")
        registros = ws.get_all_records()
        for row in registros:
            row_lower = {str(k).strip().lower(): v for k, v in row.items()}
            chofer_fila = str(row_lower.get("chofer", "")).strip()
            if chofer_fila.lower() == chofer.strip().lower():
                envio = str(row_lower.get("envio n°", row_lower.get("envio", "ENV-000")))
                pedido = str(row_lower.get("pedido n°", row_lower.get("pedido", "PED-000")))
                dominio = str(row_lower.get("dominio", row_lower.get("patente", "Sin Asignar")))
                bultos_raw = row_lower.get("cantidad de bulto", row_lower.get("bultos", 1))
                bultos = int(bultos_raw) if str(bultos_raw).isdigit() else 1
                destino = str(row_lower.get("destino", "Sin Destino"))
                estado = str(row_lower.get("estado", "Pendiente"))
                
                if estado.strip().lower() != "entregado":
                    patente_asignada = dominio
                    envios_lista.append({
                        "envio": envio, "pedido": pedido, "bultos": bultos,
                        "destino": destino, "dominio": dominio
                    })
    except Exception as e:
        st.error(f"Error al leer la solapa Asignación: {e}")
    return patente_asignada, envios_lista

# --- 6. AUTENTICACIÓN ---
st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🚚 DM MAESTRO S.R.L. </h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 25px;'>Sistema de Flota y Logística</p>", unsafe_allow_html=True)

choferes_lista = list(PINES_CHOFERES.keys())
params = st.query_params
chofer_en_url = params.get("chofer", None)
es_encargado = params.get("admin", None) == "logadmin2026"

if es_encargado:
    with st.sidebar:
        st.header("Panel de Logística")
        chofer_sel_admin = st.selectbox("Crear enlace para chofer:", choferes_lista)
        link_wpp = f"applogistica-zcpbhxepee55agsgxq6rwd.streamlit.app/?chofer={chofer_sel_admin.replace(' ', '%20')}"
        st.code(link_wpp, language="markdown")
else:
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)

chofer_actual = chofer_en_url if chofer_en_url else st.selectbox("Seleccione su Nombre y Apellido:", choferes_lista)

if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chofer_auth" not in st.session_state:
    st.session_state.chofer_auth = None
if "checklist_realizado" not in st.session_state:
    st.session_state.checklist_realizado = False
if "menu_activo" not in st.session_state:
    st.session_state.menu_activo = "Home"

if st.session_state.chofer_auth != chofer_actual:
    st.session_state.autenticado = False
    st.session_state.chofer_auth = chofer_actual
    st.session_state.checklist_realizado = False
    st.session_state.menu_activo = "Home"

if not st.session_state.autenticado:
    st.info(f"🔒 Identidad detectada: **{chofer_actual}**")
    with st.form("form_pin"):
        pin_ingresado = st.text_input("Ingrese su PIN de 4 dígitos:", type="password")
        if st.form_submit_button("INGRESAR AL SISTEMA"):
            if pin_ingresado.strip() == PINES_CHOFERES.get(chofer_actual, ""):
                st.session_state.autenticado = True
                st.rerun()
            else:
                st.error("❌ PIN incorrecto.")
    st.stop()

# Barra superior de sesión
col_ses1, col_ses2 = st.columns([3, 1])
with col_ses1:
    st.success(f"🔓 Chofer activo: **{chofer_actual}**")
with col_ses2:
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.checklist_realizado = False
        st.session_state.menu_activo = "Home"
        st.query_params.clear()
        st.rerun()

patente_asignada, envios_disponibles = obtener_asignaciones_chofer(chofer_actual)

if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

# --- 7. CONTROL DE FLUJO Y PANTALLA PRINCIPAL (ESTILO TÁCTIL / TABLET) ---

if not st.session_state.checklist_realizado:
    st.warning("⚠️ **CHECKLIST OBLIGATORIO:** Para habilitar la salida del camión y desbloquear el menú principal, debe completar la inspección.")
    
    st.markdown("<div class='orion-card'><h3>📋 1. Checklist Pre-operacional</h3><p style='color:#94a3b8;'>Verificación obligatoria de la unidad asignada.</p></div>", unsafe_allow_html=True)
    
    with st.form("form_checklist_obligatorio"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Chofer", value=chofer_actual, disabled=True)
            patente_in = st.text_input("Patente / Dominio Asignado (Bloqueado)", value=patente_asignada, disabled=True)
            neumaticos = st.checkbox("Presión y estado de neumáticos OK")
            luces = st.checkbox("Luces altas, bajas y guiños OK")
        with col2:
            kilometraje = st.number_input("Kilometraje Actual (Km)", min_value=0, step=100)
            frenos = st.checkbox("Sistema de frenos y estacionamiento OK")
            fluidos = st.checkbox("Niveles de agua y aceite OK")
            documentacion = st.checkbox("Documentación y seguros vigentes OK")
        
        if st.form_submit_button("APROBAR Y DESBLOQUEAR SISTEMA"):
            if neumaticos and luces and frenos and fluidos and documentacion:
                try:
                    ws_check = sheet.worksheet("Checklist")
                except:
                    ws_check = sheet.add_worksheet(title="Checklist", rows=100, cols=10)
                    ws_check.append_row(["Fecha", "Chofer", "Patente", "Km", "Estado"])
                
                ws_check.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, patente_asignada, kilometraje, "Aprobado"])
                st.session_state.checklist_realizado = True
                st.success("✅ ¡Checklist aprobado con éxito! Desbloqueando menú principal...")
                st.rerun()
            else:
                st.error("❌ Debe tildar todos los puntos de control obligatorios para salir.")

else:
    # --- MENÚ TÁCTIL PRINCIPAL (6 MÓDULOS DE ACCESO RÁPIDO) ---
    if st.session_state.menu_activo == "Home":
        st.markdown("### 🎛️ Panel de Operaciones")
        st.markdown("Seleccione el módulo en el que desea trabajar:")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='menu-card'><h3>⛽</h3><h4>Viáticos</h4><p style='font-size:12px; color:#94a3b8;'>Gastos y rendiciones</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Viáticos"):
                st.session_state.menu_activo = "Viáticos"
                st.rerun()
        with c2:
            st.markdown("<div class='menu-card'><h3>🛠️</h3><h4>Mecánica</h4><p style='font-size:12px; color:#94a3b8;'>Estado técnico unidad</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Mecánica"):
                st.session_state.menu_activo = "Mecánica"
                st.rerun()
        with c3:
            st.markdown("<div class='menu-card'><h3>⚙</h3><h4>Cierre de Viaje</h4><p style='font-size:12px; color:#94a3b8;'>Odómetro y cierre</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Cierre"):
                st.session_state.menu_activo = "Cierre"
                st.rerun()

        c4, c5, c6 = st.columns(3)
        with c4:
            st.markdown("<div class='menu-card'><h3>🧳</h3><h4>Entregas</h4><p style='font-size:12px; color:#94a3b8;'>Remitos y cobros</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Entregas"):
                st.session_state.menu_activo = "Entregas"
                st.rerun()
        with c5:
            st.markdown("<div class='menu-card'><h3>🚦</h3><h4>Incidentes</h4><p style='font-size:12px; color:#94a3b8;'>Reportar novedades</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Incidentes"):
                st.session_state.menu_activo = "Incidentes"
                st.rerun()
        with c6:
            st.markdown("<div class='menu-card'><h3>🗺️</h3><h4>Hoja de Ruta</h4><p style='font-size:12px; color:#94a3b8;'>Mapa y corredores</p></div>", unsafe_allow_html=True)
            if st.button("Abrir Ruta"):
                st.session_state.menu_activo = "Ruta"
                st.rerun()

    else:
        if st.button("⬅️ VOLVER AL MENÚ PRINCIPAL"):
            st.session_state.menu_activo = "Home"
            st.rerun()
        st.markdown("---")

        # --- MÓDULO 1: ENTREGAS ---
        if st.session_state.menu_activo == "Entregas":
            st.subheader("📦 Registro de Entregas")
            if not envios_disponibles:
                st.success("🎉 No tienes envíos pendientes asignados en este momento.")
            else:
                envio_actual_dict = envios_disponibles[st.session_state.envio_index]
                if len(envios_disponibles) > 1:
                    opciones = [f"{e['envio']} - Pedido: {e['pedido']} ({e['destino']})" for e in envios_disponibles]
                    sel = st.selectbox("Seleccione envío:", opciones, index=st.session_state.envio_index)
                    st.session_state.envio_index = opciones.index(sel)
                    envio_actual_dict = envios_disponibles[st.session_state.envio_index]

                with st.form("form_entregas_mod"):
                    envio_n = st.text_input("Envío N°", value=envio_actual_dict["envio"], disabled=True)
                    pedido_n = st.text_input("Pedido N°", value=envio_actual_dict["pedido"], disabled=True)
                    patente_s1 = st.text_input("Dominio", value=envio_actual_dict["dominio"], disabled=True)
                    destino_s1 = st.text_input("Destino", value=envio_actual_dict["destino"], disabled=True)
                    cant_bultos = st.number_input("Cantidad de bultos", value=envio_actual_dict["bultos"], disabled=True)
                    
                    estado_entrega = st.selectbox("Estado", ["ENTREGADO", "NO ENTREGADO"])
                    forma_cobro = st.selectbox("Forma de cobro", ["Efectivo", "Transferencia", "Cheque", "Sin Cobro"])
                    monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                    
                    if st.form_submit_button("REGISTRAR ENTREGA"):
                        try:
                            ws_ent = sheet.worksheet("Entregas")
                        except:
                            ws_ent = sheet.add_worksheet(title="Entregas", rows=100, cols=10)
                            ws_ent.append_row(["Fecha", "Envio N°", "Pedido N°", "Cantidad de bultos", "Estado", "Forma de cobro", "Monto"])
                        
                        ws_ent.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), envio_n, pedido_n, cant_bultos, estado_entrega, forma_cobro, monto])
                        
                        try:
                            ws_asig = sheet.worksheet("Asignación")
                            cell = ws_asig.find(envio_n)
                            if cell:
                                ws_asig.update_cell(cell.row, 8, estado_entrega)
                        except:
                            pass

                        st.success("¡Entrega registrada con éxito!")
                        if st.session_state.envio_index < len(envios_disponibles) - 1:
                            st.session_state.envio_index += 1
                        else:
                            st.session_state.envio_index = 0
                        st.rerun()

        # --- MÓDULO 2: CIERRE DE VIAJE ---
        elif st.session_state.menu_activo == "Cierre":
            st.subheader("⚙️ Cierre de Viaje y Rendición")
            with st.form("form_cierre_mod"):
                vehiculo_id = st.text_input("Dominio", value=patente_asignada, disabled=True)
                envio_cierre = st.text_input("Envío Actual", value=envios_disponibles[st.session_state.envio_index]["envio"] if envios_disponibles else "ENV-000", disabled=True)
                finalizo_viaje = st.selectbox("¿Finalizó el viaje?", ["Sí", "No"])
                km_actual = st.number_input("Kilometraje Actual", min_value=0.0, step=1.0)
                foto_odometro = st.file_uploader("Foto del Odómetro", type=["jpg", "jpeg", "png"])
                
                if st.form_submit_button("FINALIZAR Y ENVIAR CIERRE"):
                    link_foto = "Sin foto"
                    try:
                        ws_cierres = sheet.worksheet("Cierres")
                    except:
                        ws_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                        ws_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones", "Acceso Foto Odómetro"])

                    ws_cierres.append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, vehiculo_id, envio_cierre, 
                        finalizo_viaje, km_actual, "Sin observaciones", link_foto
                    ], value_input_option='USER_ENTERED')
                    st.success("¡Cierre de viaje registrado con éxito!")

        # --- MÓDULO 3: HOJA DE RUTA Y MAPA ---
        elif st.session_state.menu_activo == "Ruta":
            st.subheader("🗺️ Hoja de Ruta Óptima")
            if not envios_disponibles:
                st.info("No hay rutas activas.")
            else:
                envios_ordenados = sorted(envios_disponibles, key=lambda x: obtener_peso_destino(x["destino"]))
                punto_partida = (-24.7821, -65.4232)
                
                puntos_mapa = []
                for idx, envio in enumerate(envios_ordenados, start=1):
                    coords = obtener_coordenada(envio["destino"])
                    puntos_mapa.append({"parada": idx, "envio": envio["envio"], "pedido": envio["pedido"], "destino": envio["destino"], "bultos": envio["bultos"], "coords": coords})

                for p in puntos_mapa:
                    st.markdown(f"**Parada #{p['parada']}** ➔ Envío: `{p['envio']}` | Destino: **{p['destino']}** (Bultos: {p['bultos']})")
                
                st.markdown("---")
                mapa_ruta = folium.Map(location=punto_partida, zoom_start=7)
                folium.Marker(location=punto_partida, popup="Depósito Salta", icon=folium.Icon(color="orange", icon="home")).add_to(mapa_ruta)
                
                polyline_coords = [punto_partida]
                for p in puntos_mapa:
                    polyline_coords.append(p["coords"])
                    folium.Marker(location=p["coords"], popup=f"Parada #{p['parada']}: {p['destino']}", icon=folium.Icon(color="green", icon="shopping-cart")).add_to(mapa_ruta)
                
                if len(polyline_coords) > 1:
                    folium.PolyLine(polyline_coords, color="green", weight=5, opacity=0.85).add_to(mapa_ruta)
                
                st_folium(mapa_ruta, width=700, height=450)

        # --- MÓDULO 4: INCIDENTES ---
        elif st.session_state.menu_activo == "Incidentes":
            st.subheader("⚠ Reporte de Novedades e Incidentes")
            with st.form("form_inc_mod"):
                id_viaje = st.text_input("Número de Viaje / ID")
                tipo_incidente = st.selectbox("Tipo de Incidente", ["Falla mecánica", "Demora por tráfico", "Incidente climático", "Otro"])
                ubicacion = st.text_input("Ubicación aproximada (Km / Zona)")
                descripcion = st.text_area("Descripción detallada del problema")
                
                if st.form_submit_button("ENVIAR ALERTA DE INCIDENTE"):
                    if id_viaje and descripcion:
                        try:
                            ws_inc = sheet.worksheet("Incidentes")
                        except:
                            ws_inc = sheet.add_worksheet(title="Incidentes", rows=100, cols=10)
                            ws_inc.append_row(["Fecha", "Chofer", "Patente", "Viaje", "Tipo", "Ubicacion", "Descripcion"])
                        
                        ws_inc.append_row([
                            datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, patente_asignada, 
                            id_viaje, tipo_incidente, ubicacion, descripcion
                        ])
                        st.success("⚠️ Incidente reportado exitosamente al área de operaciones.")
                    else:
                        st.warning("Complete el número de viaje y la descripción.")

        # --- MÓDULO 5: VIÁTICOS ---
        elif st.session_state.menu_activo == "Viáticos":
            st.subheader("💳 Rendición de Viáticos y Gastos")
            with st.form("form_viat_mod"):
                viaje_v = st.text_input("Número de Viaje asociado")
                categoria_gasto = st.selectbox("Concepto", ["Peaje", "Combustible extra", "Estacionamiento", "Reparación", "Comida / Viático"])
                monto_gasto = st.number_input("Monto total ($)", min_value=0.0, format="%.2f")
                fecha_gasto = st.date_input("Fecha del gasto")
                
                if st.form_submit_button("GUARDAR COMPROBANTE"):
                    if viaje_v and monto_gasto > 0:
                        try:
                            ws_viat = sheet.worksheet("Viaticos")
                        except:
                            ws_viat = sheet.add_worksheet(title="Viaticos", rows=100, cols=10)
                            ws_viat.append_row(["Fecha Registro", "Chofer", "Patente", "Viaje", "Concepto", "Monto", "Fecha Gasto"])
                        
                        ws_viat.append_row([
                            datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, patente_asignada, 
                            viaje_v, categoria_gasto, monto_gasto, str(fecha_gasto)
                        ])
                        st.success(f"¡Gasto de ${monto_gasto:.2f} registrado correctamente!")
                    else:
                        st.warning("Ingrese un viaje válido y un monto mayor a cero.")

        # --- MÓDULO 6: MECÁNICA (ESTADO TÉCNICO) ---
        elif st.session_state.menu_activo == "Mecánica":
            st.subheader("🛠️ Estado Técnico y Mantenimiento")
            st.markdown(f"""
                <div class='orion-card'>
                    <h4>Unidad Asignada: <b>{patente_asignada}</b></h4>
                    <p style='color:#94a3b8;'>Estado general del vehículo registrado en el último checklist diario.</p>
                    <hr style='border-color: rgba(255,255,255,0.1);'>
                    <p>✅ <b>Neumáticos:</b> OK</p>
                    <p>✅ <b>Sistema eléctrico y luces:</b> OK</p>
                    <p>✅ <b>Frenos y fluidos:</b> OK</p>
                </div>
            """, unsafe_allow_html=True)
            st.info("Si detecta alguna anomalía mecánica nueva durante su recorrido, repórtela inmediatamente desde el módulo de **Incidentes**.")
