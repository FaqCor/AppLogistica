import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA (DEBE IR PRIMERO) ---
st.set_page_config(page_title="App Logística", page_icon="🚚", layout="centered")

# --- 2. CONEXIÓN A GOOGLE SHEETS (MODO MODERNO Y SEGURO) ---
@st.cache_resource
def init_connection():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Cargamos directamente las credenciales usando el diccionario limpio de st.secrets
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # Aseguramos el reemplazo limpio de los saltos de línea escapados
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=scope
    )
    client = gspread.authorize(creds)
    return client

client = init_connection()

@st.cache_resource
def get_sheet():
    return client.open("sistema de control de flota")

sheet = get_sheet()

# --- 3. INTERFAZ GENERAL DE LA APP ---
st.title("🚚 Gestión de Logística - Choferes")

# Selector de Chofer (Identificación inicial)
choferes_lista = ["Juan Pérez", "Carlos Gómez", "Mario Ruiz"]
chofer_actual = st.selectbox("Seleccione su Usuario / Chofer:", choferes_lista)

# Pestañas de la aplicación
tab1, tab2 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje"])

# ==========================================
# SOLAPA 1: ENTREGAS
# ==========================================
with tab1:
    st.subheader("Registro de Entrega")
    
    with st.form("form_entregas"):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        envio_n = st.text_input("Envío N° (Automático)", value="ENV-001", disabled=True)
        pedido_n = st.text_input("Pedido N° (Automático)", value="PED-9988", disabled=True)
        cant_bultos = st.number_input("Cantidad de bultos", min_value=1, value=4, disabled=True)
        
        estado_entrega = st.selectbox("Estado", ["ENTREGADO", "NO ENTREGADO"])
        
        st.markdown("---")
        st.markdown("### Información de Cobro")
        forma_cobro = st.selectbox("Forma de cobro", ["Efectivo", "Transferencia", "Cheque", "Sin Cobro"])
        monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
        
        btn_enviar_1 = st.form_submit_button("ENVIAR ENTREGA")
        
        if btn_enviar_1:
            worksheet_entregas = sheet.worksheet("Entregas")
            worksheet_entregas.append_row([
                fecha_actual, envio_n, pedido_n, cant_bultos, 
                estado_entrega, forma_cobro, monto
            ])
            st.success("¡Entrega registrada y enviada a Google Sheets con éxito!")

# ==========================================
# SOLAPA 2: CIERRE DE VIAJE
# ==========================================
with tab2:
    st.subheader("Cierre de Viaje")
    st.write("Próximamente las opciones para el cierre de viaje.")
