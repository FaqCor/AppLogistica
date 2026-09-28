import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="App Logística", page_icon="🚚", layout="centered")

# --- 2. CONEXIÓN A GOOGLE SHEETS (CON REPARADOR AUTOMÁTICO DE LLAVE) ---
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

# --- 3. OBTENER ASIGNACIÓN DESDE LA PLANILLA ---
def obtener_asignacion(chofer):
    try:
        ws = sheet.worksheet("Asignaciones")
        registros = ws.get_all_records()
        for row in registros:
            if str(row.get("Chofer", "")).strip().lower() == chofer.strip().lower():
                return str(row.get("Patente", "Sin Asignar")), str(row.get("Envio", "ENV-000"))
    except Exception as e:
        pass
    return "Sin Asignar", "ENV-000"

# --- 4. INTERFAZ GENERAL DE LA APP ---
st.title("🚚 Gestión de Logística - Choferes")

choferes_lista = ["Juan Pérez", "Carlos Gómez", "Mario Ruiz"]
chofer_actual = st.selectbox("Seleccione su Usuario / Chofer:", choferes_lista)

patente_asignada, envio_asignado = obtener_asignacion(chofer_actual)

tab1, tab2 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje"])

# --- SOLAPA 1: ENTREGAS ---
with tab1:
    st.subheader("Registro de Entrega")
    
    with st.form("form_entregas"):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        envio_n = st.text_input("Envío N° (Asignado por Logística)", value=envio_asignado, disabled=True)
        patente_s1 = st.text_input("Patente Asignada", value=patente_asignada, disabled=True)
        
        pedido_n = st.text_input("Pedido N°", value="PED-9988")
        cant_bultos = st.number_input("Cantidad de bultos", min_value=1, value=4)
        
        estado_entrega = st.selectbox("Estado", ["ENTREGADO", "NO ENTREGADO"])
        
        st.markdown("---")
        st.markdown("### Información de Cobro")
        forma_cobro = st.selectbox("Forma de cobro", ["Efectivo", "Transferencia", "Cheque", "Sin Cobro"])
        monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
        
        btn_enviar_1 = st.form_submit_button("ENVIAR ENTREGA")
        
        if btn_enviar_1:
            worksheet_entregas = sheet.worksheet("Entregas")
            worksheet_entregas.append_row([
                fecha_actual, chofer_actual, patente_s1, envio_n, pedido_n, cant_bultos, 
                estado_entrega, forma_cobro, monto
            ])
            st.success("¡Entrega registrada y enviada a Google Sheets con éxito!")

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
            try:
                worksheet_cierres = sheet.worksheet("Cierres")
            except:
                worksheet_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                worksheet_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones", "Foto Odómetro"])

            nombre_foto = foto_odometro.name if foto_odometro is not None else "Sin foto"

            worksheet_cierres.append_row([
                fecha_cierre, chofer_actual, vehiculo_id, envio_cierre, finalizo_viaje, 
                km_actual, observaciones, nombre_foto
            ])
            st.success("¡Cierre de viaje registrado y guardado en Google Sheets con éxito!")
