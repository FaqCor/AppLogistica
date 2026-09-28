import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="App Logística", page_icon="🚚", layout="centered")

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
@st.cache_resource
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # --- REPARADOR BLINDADO DE LA CLAVE PRIVADA ---
    pk = creds_dict.get("private_key", "")
    pk = pk.replace("\\n", "\n")
    
    if "BEGIN PRIVATE KEY" in pk:
        lines = [l.strip() for l in pk.split("\n") if l.strip()]
        body_lines = [l for l in lines if "-----" not in l]
        body = "".join(body_lines)
        formatted_body = "\n".join(body[i:i+64] for i in range(0, len(body), 64))
        pk = f"-----BEGIN PRIVATE KEY-----\n{formatted_body}\n-----END PRIVATE KEY-----\n"
    
    creds_dict["private_key"] = pk
    # ----------------------------------------------

    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client

client = init_connection()

@st.cache_resource
def get_sheet():
    return client.open("sistema de control de flota")

sheet = get_sheet()

# --- 3. OBTENER ASIGNACIONES DESDE LA PLANILLA ---
def obtener_asignaciones_chofer(chofer):
    """
    Retorna la patente y una lista de diccionarios con los envíos y pedidos 
    asignados al chofer desde la solapa 'Asignación' de Google Sheets.
    """
    patente_asignada = "Sin Asignar"
    envios_lista = []
    try:
        ws = sheet.worksheet("Asignación")
        registros = ws.get_all_records()
        for row in registros:
            if str(row.get("Chofer", "")).strip().lower() == chofer.strip().lower():
                patente_asignada = str(row.get("Patente", row.get("Dominio", "Sin Asignar")))
                envio_id = str(row.get("Envio", row.get("N° envio", "ENV-000")))
                pedido_id = str(row.get("Pedido", row.get("Pedido N°", "PED-9988")))
                bultos_sugeridos = int(row.get("Bultos", 1)) if str(row.get("Bultos", "")).isdigit() else 1
                
                envios_lista.append({
                    "envio": envio_id,
                    "pedido": pedido_id,
                    "bultos": bultos_sugeridos
                })
    except Exception as e:
        pass
    
    if not envios_lista:
        envios_lista = [{"envio": "ENV-000", "pedido": "PED-9988", "bultos": 1}]
        
    return patente_asignada, envios_lista

# --- 4. INTERFAZ GENERAL DE LA APP ---
st.title("🚚 Gestión de Logística - Choferes")

# Puedes ajustar la lista de choferes o cargarla también dinámicamente si prefieres
choferes_lista = ["Juan Pérez", "Carlos Gómez", "Mario Ruiz", "Matias", "Carlos", "Miguel"]
chofer_actual = st.selectbox("Seleccione su Usuario / Chofer:", choferes_lista)

patente_asignada, envios_disponibles = obtener_asignaciones_chofer(chofer_actual)

# Control de estado para manejar el envío actual seleccionado y avanzar automáticamente
if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

if st.session_state.envio_index >= len(envios_disponibles):
    st.session_state.envio_index = 0

tab1, tab2 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje"])

# --- SOLAPA 1: ENTREGAS ---
with tab1:
    st.subheader("Registro de Entrega")
    
    # Obtener el envío actual según el índice de la sesión
    envio_actual_dict = envios_disponibles[st.session_state.envio_index]
    envio_asignado = envio_actual_dict["envio"]
    pedido_asignado = envio_actual_dict["pedido"]
    bultos_asignados = envio_actual_dict["bultos"]

    # Selector visual si hay múltiples envíos asignados por logística
    if len(envios_disponibles) > 1:
        opciones_envios = [e["envio"] for e in envios_disponibles]
        envio_seleccionado = st.selectbox(
            "Seleccione el Envío a procesar (Asignado por Logística):", 
            opciones_envios, 
            index=st.session_state.envio_index
        )
        st.session_state.envio_index = opciones_envios.index(envio_seleccionado)
        envio_actual_dict = envios_disponibles[st.session_state.envio_index]
        envio_asignado = envio_actual_dict["envio"]
        pedido_asignado = envio_actual_dict["pedido"]
        bultos_asignados = envio_actual_dict["bultos"]

    with st.form("form_entregas"):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        # --- CAMPOS GRISEADOS Y BLOQUEADOS ---
        envio_n = st.text_input("Envío N° (Asignado por Logística)", value=envio_asignado, disabled=True)
        patente_s1 = st.text_input("Patente Asignada", value=patente_asignada, disabled=True)
        pedido_n = st.text_input("Pedido N°", value=pedido_asignado, disabled=True)
        cant_bultos = st.number_input("Cantidad de bultos", min_value=1, value=bultos_asignados, disabled=True)
        # ------------------------------------
        
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
                worksheet_entregas.append_row(["Fecha", "Chofer", "Patente", "Envio", "Pedido", "Bultos", "Estado", "Forma Cobro", "Monto"])

            worksheet_entregas.append_row([
                fecha_actual, chofer_actual, patente_s1, envio_n, pedido_n, cant_bultos, 
                estado_entrega, forma_cobro, monto
            ])
            st.success(f"¡Entrega del envío {envio_n} registrada y enviada a Google Sheets con éxito!")
            
            # Avanzar automáticamente al siguiente envío disponible en la lista
            if st.session_state.envio_index < len(envios_disponibles) - 1:
                st.session_state.envio_index += 1
            else:
                st.info("¡Has completado todos los envíos asignados en esta lista!")
            
            st.rerun()

# --- SOLAPA 2: CIERRE DE VIAJE ---
with tab2:
    st.subheader("Cierre de Viaje y Rendición")
    
    with st.form("form_cierre"):
        fecha_cierre = datetime.now().strftime("%Y-%m-%d")
        
        vehiculo_id = st.text_input("Patente del Vehículo (Asignada)", value=patente_asignada, disabled=True)
        envio_cierre = st.text_input("Envío N° (Asignado)", value=envio_asignado, disabled=True)
        
        finalizo_viaje = st.selectbox("¿Finalizó viaje?", ["Sí", "No"])
        km_actual = st.number_input("Km Actual del Odómetro", min_value=0.0, value=15250.0, step=1.0)
        
        foto_odometro = st.file_uploader("Subir foto del odómetro", type=["jpg", "jpeg", "png"])
        
        st.markdown("---")
        st.markdown("### Novedades del Viaje")
        observaciones = st.text_area("Observaciones", placeholder="Ej: Tránsito demorado, novedades...")
        
        btn_enviar_2 = st.form_submit_button("FINALIZAR Y ENVIAR CIERRE DE VIAJE")
        
        if btn_enviar_2:
            link_foto = "Sin foto"
            if foto_odometro is not None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"Odometro_{chofer_actual}_{patente_asignada}_{timestamp}.jpg"
                folder_id = "1THxT45-t-VFWU0JmWD2kR2WDCwmA9vdW"
                link_foto = f'=HYPERLINK("https://drive.google.com/drive/folders/{folder_id}", "Abrir Carpeta Drive")'

            try:
                worksheet_cierres = sheet.worksheet("Cierres")
            except:
                worksheet_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                worksheet_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones", "Acceso Foto Odómetro"])

            fila_datos = [
                fecha_cierre, chofer_actual, vehiculo_id, envio_cierre, finalizo_viaje, 
                km_actual, observaciones, link_foto
            ]
            
            worksheet_cierres.append_row(fila_datos, value_input_option='USER_ENTERED')
            st.success("¡Cierre de viaje registrado con éxito! El enlace interactivo ya está disponible en Google Sheets.")
