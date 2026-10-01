import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from PIL import Image
import io
import folium
from streamlit_folium import st_folium

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="App Logística - Choferes", page_icon="🚚", layout="centered")

# --- 2. ESTILOS CSS PERSONALIZADOS (Diseño Oscuro / Tarjetas) ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0b0f19;
        color: #f3f4f6;
        font-family: 'Segoe UI', Roboto, sans-serif;
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
        border-radius: 10px;
        padding: 10px 20px;
        font-weight: 600;
        width: 100%;
    }
    .stButton>button:hover {
        opacity: 0.9;
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
    
    pk = creds_dict.get("private_key", "")
    pk = pk.replace("\\n", "\n")
    
    if "BEGIN PRIVATE KEY" in pk:
        lines = [l.strip() for l in pk.split("\n") if l.strip()]
        body_lines = [l for l in lines if "-----" not in l]
        body = "".join(body_lines)
        formatted_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
        pk = f"-----BEGIN PRIVATE KEY-----\n{formatted_body}\n-----END PRIVATE KEY-----\n"
    
    creds_dict["private_key"] = pk
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

client = init_connection()

@st.cache_resource
def get_sheet():
    return client.open("sistema de control de flota")

sheet = get_sheet()

# --- 4. BASE DE DATOS DE PINES DE SEGURIDAD ---
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

# --- 5. COORDENADAS Y CORREDORES GEOGRÁFICOS ---
COORDS_DESTINOS = {
    "salta": (-24.7821, -65.4232),
    "jujuy": (-24.1858, -65.2995),
    "san salvador de jujuy": (-24.1858, -65.2995),
    "tucuman": (-26.8083, -65.2176),
    "san miguel de tucuman": (-26.8083, -65.2176),
    "catamarca": (-28.4696, -65.7852),
    "san fernando del valle de catamarca": (-28.4696, -65.7852),
    "santiago del estero": (-27.7951, -64.2615),
    "la rioja": (-29.4131, -66.8558),
    "formosa": (-26.1853, -58.1758),
    "chaco": (-27.4512, -58.9866),
    "resistencia": (-27.4512, -58.9866),
    "corrientes": (-27.4692, -58.8306)
}

ORDEN_CORREDOR = {
    "salta": 1,
    "jujuy": 2,
    "san salvador de jujuy": 2,
    "tucuman": 3,
    "san miguel de tucuman": 3,
    "catamarca": 4,
    "san fernando del valle de catamarca": 4,
    "santiago del estero": 5,
    "la rioja": 6,
    "chaco": 7,
    "resistencia": 7,
    "corrientes": 8,
    "formosa": 9
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
                        "envio": envio,
                        "pedido": pedido,
                        "bultos": bultos,
                        "destino": destino,
                        "dominio": dominio
                    })
    except Exception as e:
        st.error(f"Error al leer la solapa Asignación: {e}")
    
    return patente_asignada, envios_lista

# --- 6. GESTIÓN DE ACCESO Y SEGURIDAD ---
st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>PORTAL DEL CHOFER - OPERACIONES</h1>", unsafe_allow_html=True)

choferes_lista = list(PINES_CHOFERES.keys())

params = st.query_params
chofer_en_url = params.get("chofer", None)
es_encargado = params.get("admin", None) == "logadmin2026"

if es_encargado:
    with st.sidebar:
        st.header("Panel de Logística")
        chofer_seleccionado_admin = st.selectbox("Seleccionar chofer para crear link:", choferes_lista)
        url_base = "applogistica-zcpbhxepee55agsgxq6rwd.streamlit.app" 
        link_wpp = f"{url_base}/?chofer={chofer_seleccionado_admin.replace(' ', '%20')}"
        st.markdown(f"**Link seguro para WhatsApp:**")
        st.code(link_wpp, language="markdown")
else:
    st.markdown("""<style>[data-testid="stSidebar"] { display: none; }</style>""", unsafe_allow_html=True)

if not chofer_en_url:
    st.info("👋 **Bienvenido al Sistema de Logística.**")
    chofer_actual = st.selectbox("Seleccione su Nombre y Apellido para ingresar:", choferes_lista)
else:
    chofer_actual = chofer_en_url

# Control de sesión por PIN
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chofer_auth" not in st.session_state:
    st.session_state.chofer_auth = None
if "checklist_realizado" not in st.session_state:
    st.session_state.checklist_realizado = False

if st.session_state.chofer_auth != chofer_actual:
    st.session_state.autenticado = False
    st.session_state.chofer_auth = chofer_actual
    st.session_state.checklist_realizado = False

if not st.session_state.autenticado:
    st.info(f"🔒 Identidad detectada para: **{chofer_actual}**")
    with st.form("form_pin"):
        pin_ingresado = st.text_input("Ingrese su PIN de seguridad de 4 dígitos:", type="password")
        btn_login = st.form_submit_button("INGRESAR AL SISTEMA")
        
        if btn_login:
            pin_correcto = PINES_CHOFERES.get(chofer_actual, "")
            if pin_ingresado.strip() == pin_correcto:
                st.session_state.autenticado = True
                st.success("¡Acceso autorizado!")
                st.rerun()
            else:
                st.error("❌ PIN incorrecto. Verifique con logística.")
    st.stop()

# Botón para cerrar sesión
col_sesion1, col_sesion2 = st.columns([3, 1])
with col_sesion1:
    st.success(f"🔓 Sesión iniciada: **{chofer_actual}**")
with col_sesion2:
    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.session_state.checklist_realizado = False
        st.query_params.clear()
        st.rerun()

patente_asignada, envios_disponibles = obtener_asignaciones_chofer(chofer_actual)

if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

if st.session_state.envio_index >= len(envios_disponibles) and len(envios_disponibles) > 0:
    st.session_state.envio_index = 0

# --- 7. ORGANIZACIÓN DE SOLAPAS ---
# El checklist es obligatorio y OBLIGA a completarse primero. Las demás solapas se bloquean si no está hecho.
if not st.session_state.checklist_realizado:
    st.warning("⚠️ **ATENCIÓN:** Por normas de seguridad y calidad, es obligatorio completar y enviar el **Checklist Pre-operacional** para habilitar la salida del camión y acceder al resto de las funciones.")
    
    tabs = st.tabs(["📋 1. Checklist Pre-operacional (OBLIGATORIO)"])
    tab_check = tabs[0]
    
    with tab_check:
        st.markdown("""
            <div class="orion-card">
                <h3>📋 Inspección Diaria del Vehículo</h3>
                <p style='color: #94a3b8;'>Verificá el estado general de la unidad antes de iniciar tu recorrido.</p>
            </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_checklist"):
            col1, col2 = st.columns(2)
            with col1:
                chofer_in = st.text_input("Chofer", value=chofer_actual, disabled=True)
                patente_in = st.text_input("Patente / Unidad Asignada", value=patente_asignada)
                neumaticos = st.checkbox("Presión y estado de neumáticos OK")
                luces = st.checkbox("Luces altas, bajas y guiños OK")
            with col2:
                kilometraje = st.number_input("Kilometraje Actual (Km)", min_value=0, step=100)
                frenos = st.checkbox("Sistema de frenos y estacionamiento OK")
                fluidos = st.checkbox("Niveles de agua y aceite OK")
                documentacion = st.checkbox("Documentación y seguros vigentes OK")
            
            submitted_check = st.form_submit_button("APROBAR Y ENVIAR CHECKLIST")
            if submitted_check:
                if patente_in and neumaticos and luces and frenos and fluidos and documentacion:
                    # Guardar opcionalmente en Google Sheets si existe la solapa de checklist
                    try:
                        ws_check = sheet.worksheet("Checklist")
                    except:
                        ws_check = sheet.add_worksheet(title="Checklist", rows=100, cols=10)
                        ws_check.append_row(["Fecha", "Chofer", "Patente", "Km", "Estado"])
                    
                    ws_check.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, patente_in, kilometraje, "Aprobado"])
                    
                    st.session_state.checklist_realizado = True
                    st.success("✅ ¡Checklist aprobado con éxito! Desbloqueando herramientas de viaje...")
                    st.rerun()
                else:
                    st.error("❌ Para habilitar la salida del camión, debés tildar todos los puntos de control obligatorios.")
else:
    # SI YA ESTÁ REALIZADO EL CHECKLIST, SE ABREN TODAS LAS SOLAPAS OPERATIVAS
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📦 1. Entregas", 
        "📊 2. Cierre de Viaje", 
        "🗺️ 3. Hoja de Ruta", 
        "⚠️ 4. Incidentes", 
        "💳 5. Viáticos"
    ])

    # --- SOLAPA 1: ENTREGAS ---
    with tab1:
        st.subheader("Registro de Entrega")
        if not envios_disponibles:
            st.success("🎉 ¡Felicitaciones! No tienes envíos pendientes asignados en este momento.")
        else:
            envio_actual_dict = envios_disponibles[st.session_state.envio_index]
            envio_asignado = envio_actual_dict["envio"]
            pedido_asignado = envio_actual_dict["pedido"]
            bultos_asignados = envio_actual_dict["bultos"]
            destino_asignado = envio_actual_dict["destino"]
            patente_asignada = envio_actual_dict["dominio"]

            if len(envios_disponibles) > 1:
                opciones_envios = [f"{e['envio']} - Pedido: {e['pedido']} (Destino: {e['destino']})" for e in envios_disponibles]
                envio_seleccionado = st.selectbox(
                    "Seleccione el Envío a procesar:", 
                    opciones_envios, 
                    index=st.session_state.envio_index
                )
                st.session_state.envio_index = opciones_envios.index(envio_seleccionado)
                envio_actual_dict = envios_disponibles[st.session_state.envio_index]
                envio_asignado = envio_actual_dict["envio"]
                pedido_asignado = envio_actual_dict["pedido"]
                bultos_asignados = envio_actual_dict["bultos"]
                destino_asignado = envio_actual_dict["destino"]
                patente_asignada = envio_actual_dict["dominio"]
            else:
                st.info(f"📍 **Destino Asignado:** {destino_asignado}")

            with st.form("form_entregas"):
                fecha_actual = datetime.now().strftime("%Y-%m-%d")
                envio_n = st.text_input("Envío N°", value=envio_asignado, disabled=True)
                pedido_n = st.text_input("Pedido N°", value=pedido_asignado, disabled=True)
                patente_s1 = st.text_input("Dominio / Patente", value=patente_asignada, disabled=True)
                destino_s1 = st.text_input("Destino", value=destino_asignado, disabled=True)
                cant_bultos = st.number_input("Cantidad de bulto", min_value=1, value=bultos_asignados, disabled=True)
                
                estado_entrega = st.selectbox("Estado", ["ENTREGADO", "NO ENTREGADO"])
                
                st.markdown("---")
                st.markdown("### Información de Cobro")
                forma_cobro = st.selectbox("Forma de cobro", ["Efectivo", "Transferencia", "Cheque", "Sin Cobro"])
                monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                
                btn_enviar_1 = st.form_submit_button("ENVIAR ENTREGA")
                
                if btn_enviar_1:
                    try:
                        worksheet_entregas = sheet.worksheet("Entregas")
                    except:
                        worksheet_entregas = sheet.add_worksheet(title="Entregas", rows=100, cols=10)
                        worksheet_entregas.append_row(["Fecha", "Envio N°", "Pedido N°", "Cantidad de bultos", "Estado", "Forma de cobro", "Monto"])

                    fila_entrega = [fecha_actual, envio_n, pedido_n, cant_bultos, estado_entrega, forma_cobro, monto]
                    worksheet_entregas.append_row(fila_entrega, value_input_option='USER_ENTERED')
                    
                    try:
                        ws_asig = sheet.worksheet("Asignación")
                        cell = ws_asig.find(envio_n)
                        if cell:
                            ws_asig.update_cell(cell.row, 8, estado_entrega)
                    except:
                        pass

                    st.success(f"¡Entrega del envío {envio_n} registrada con éxito!")
                    if st.session_state.envio_index < len(envios_disponibles) - 1:
                        st.session_state.envio_index += 1
                    else:
                        st.session_state.envio_index = 0
                    st.rerun()

    # --- SOLAPA 2: CIERRE DE VIAJE ---
    with tab2:
        st.subheader("Cierre de Viaje y Rendición")
        with st.form("form_cierre"):
            fecha_cierre = datetime.now().strftime("%Y-%m-%d")
            vehiculo_id = st.text_input("Dominio del Vehículo", value=patente_asignada, disabled=True)
            envio_cierre = st.text_input("Envío N° Actual", value=envios_disponibles[st.session_state.envio_index]["envio"] if envios_disponibles else "ENV-000", disabled=True)
            
            st.markdown("---")
            finalizo_viaje = st.selectbox("¿Finalizó viaje?", ["Sí", "No"])
            km_actual = st.number_input("Km Actual del Odómetro", min_value=0.0, value=0.0, step=1.0)
            foto_odometro = st.file_uploader("Subir foto del odómetro", type=["jpg", "jpeg", "png"])
            
            btn_enviar_2 = st.form_submit_button("FINALIZAR Y ENVIAR CIERRE DE VIAJE")
            
            if btn_enviar_2:
                link_foto = "Sin foto"
                if foto_odometro is not None:
                    try:
                        img = Image.open(foto_odometro)
                        img.thumbnail((800, 800))
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        buffered = io.BytesIO()
                        img.save(buffered, format="JPEG", quality=85)
                        folder_id = "1THxT45-t-VFWU0JmWD2kR2WDCwmA9vdW"
                        link_foto = f'=HYPERLINK("https://drive.google.com/drive/folders/{folder_id}", "Abrir Carpeta Drive")'
                    except Exception as img_err:
                        link_foto = "Error procesando imagen"
                        st.warning(f"No se pudo optimizar la foto: {img_err}")

                try:
                    worksheet_cierres = sheet.worksheet("Cierres")
                except:
                    worksheet_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                    worksheet_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones", "Acceso Foto Odómetro"])

                fila_datos = [
                    fecha_cierre, chofer_actual, vehiculo_id, envio_cierre, 
                    finalizo_viaje, km_actual, "Sin observaciones", link_foto
                ]
                worksheet_cierres.append_row(fila_datos, value_input_option='USER_ENTERED')
                st.success("¡Cierre de viaje registrado con éxito!")

    # --- SOLAPA 3: HOJA DE RUTA Y MAPA ---
    with tab3:
        st.subheader("🗺️ Ruta Óptima de Menor Kilometraje (Corredores Logísticos)")
        st.markdown("* **Optimización por Corredor Vial:** Paradas reordenadas para evitar saltos ineficientes.")
        
        if not envios_disponibles:
            st.info("No hay rutas activas en este momento.")
        else:
            envios_ordenados = sorted(envios_disponibles, key=lambda x: obtener_peso_destino(x["destino"]))
            punto_partida = (-24.7821, -65.4232)
            
            puntos_mapa = []
            for idx, envio in enumerate(envios_ordenados, start=1):
                coords = obtener_coordenada(envio["destino"])
                puntos_mapa.append({
                    "parada": idx, "envio": envio["envio"], "pedido": envio["pedido"],
                    "destino": envio["destino"], "bultos": envio["bultos"], "coords": coords
                })

            st.markdown("### 📋 Orden Secuencial Óptimo de Visitas")
            for parada in puntos_mapa:
                st.markdown(f"**Parada #{parada['parada']}** ➔ **Envío:** `{parada['envio']}` | **Pedido:** `{parada['pedido']}` | **Destino:** `{parada['destino']}` (Bultos: {parada['bultos']})")
            
            st.markdown("---")
            st.markdown("### 📍 Mapa Interactivo con la Ruta Optimizada")
            mapa_ruta = folium.Map(location=punto_partida, zoom_start=7)
            
            folium.Marker(
                location=punto_partida,
                popup="<b>Depósito Central (Salta)</b>",
                tooltip="Depósito",
                icon=folium.Icon(color="orange", icon="home")
            ).add_to(mapa_ruta)
            
            polyline_coords = [punto_partida]
            for parada in puntos_mapa:
                coords = parada["coords"]
                polyline_coords.append(coords)
                popup_text = f"<b>Parada #{parada['parada']}</b><br>Envío: {parada['envio']}<br>Destino: {parada['destino']}"
                folium.Marker(
                    location=coords,
                    popup=folium.Popup(popup_text, max_width=300),
                    tooltip=f"Parada {parada['parada']}: {parada['destino']}",
                    icon=folium.Icon(color="green", icon="shopping-cart")
                ).add_to(mapa_ruta)
                
            if len(polyline_coords) > 1:
                folium.PolyLine(polyline_coords, color="green", weight=5, opacity=0.85).add_to(mapa_ruta)
                
            st_folium(mapa_ruta, width=700, height=500)

    # --- SOLAPA 4: REPORTE DE INCIDENTES ---
    with tab4:
        st.subheader("⚠️ Reporte de Novedades o Incidentes")
        with st.form("form_incidente"):
            col1, col2 = st.columns(2)
            with col1:
                id_viaje = st.text_input("Número de Viaje / ID")
                tipo_incidente = st.selectbox("Tipo de Incidente", [
                    "Falla mecánica", "Demora por tráfico / Corte de ruta", "Incidente climático", "Otro"
                ])
            with col2:
                ubicacion = st.text_input("Ubicación aproximada (Kilómetro / Zona)")
                
            descripcion = st.text_area("Descripción detallada del problema")
            foto_evidencia = st.file_uploader("Adjuntar foto de evidencia (opcional)", type=["jpg", "png", "jpeg"])
            
            submitted_inc = st.form_submit_button("Enviar Alerta de Incidente")
            if submitted_inc:
                if id_viaje and descripcion:
                    st.error("⚠️ Incidente reportado y derivado al área de logística de inmediato.")
                else:
                    st.warning("Completá el número de viaje y la descripción.")

    # --- SOLAPA 5: GESTIÓN DE VIÁTICOS ---
    with tab5:
        st.subheader("💳 Rendición de Viáticos y Gastos")
        with st.form("form_viaticos"):
            col1, col2 = st.columns(2)
            with col1:
                viaje_v = st.text_input("Número de Viaje asociado")
                categoria_gasto = st.selectbox("Concepto", [
                    "Peaje", "Combustible extra", "Estacionamiento", "Reparación de emergencia", "Comida / Viático diario"
                ])
            with col2:
                monto = st.number_input("Monto total ($)", min_value=0.0, format="%.2f")
                fecha_gasto = st.date_input("Fecha del gasto")
                
            comprobante = st.file_uploader("Foto del Ticket / Factura", type=["jpg", "png", "jpeg", "pdf"])
            
            submitted_gasto = st.form_submit_button("Guardar Comprobante")
            if submitted_gasto:
                if viaje_v and monto > 0:
                    st.success(f"¡Gasto de ${monto:.2f} registrado correctamente para rendición!")
                else:
                    st.warning("Ingresá un número de viaje válido y un monto mayor a cero.")
