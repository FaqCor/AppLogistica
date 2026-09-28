import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import pandas as pd

# --- 1. CONFIGURACIÓN DE LA CONEXIÓN Y PLANILLA EN CACHÉ ---
@st.cache_resource
def init_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    ruta_credenciales = r"C:\Users\RoDriGo\OneDrive\Escritorio\AppLogistica\credentials.json"
    creds = ServiceAccountCredentials.from_json_keyfile_name(ruta_credenciales, scope)
    client = gspread.authorize(creds)
    return client

client = init_connection()

# Usamos caché para la hoja para evitar agotar el límite de la API de Google
@st.cache_resource
def get_sheet():
    # Si prefieres evitar fallos de nombre, puedes reemplazar "sistema de control de flota" 
    # por client.open_by_url("TU_URL_COMPLETA_DE_GOOGLE_SHEETS")
    return client.open("sistema de control de flota")

sheet = get_sheet()


client = init_connection()
sheet = client.open("sistema de control de flota")# Nombre de tu Google Sheet

# --- 2. INTERFAZ GENERAL DE LA APP ---
st.set_page_config(page_title="App Logística", page_icon="🚚", layout="centered")
st.title("🚚 Gestión de Logística - Choferes")

# Selector de Chofer (Identificación inicial)
choferes_lista = ["Juan Pérez", "Carlos Gómez", "Mario Ruiz"] # Ejemplo temporal
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
            # Columnas exactas: Fecha | Envio N° | Pedido N° | Cantidad de bultos | Estado | Forma de cobro | Monto
            worksheet_entregas.append_row([
                fecha_actual, envio_n, pedido_n, cant_bultos, 
                estado_entrega, forma_cobro, monto
            ])
            st.success("¡Entrega registrada y enviada a Google Sheets con éxito!")

import os
from datetime import datetime

# ==========================================
# SECCIÓN: CIERRE DE VIAJE
# ==========================================
st.subheader("Cierre de Viaje y Odómetro")

# Aquí van tus campos actuales de entrada (ejemplo)
# km_actual = st.number_input("Kilometraje actual", min_value=0)
# imagen_subida = st.file_uploader("Subir foto del odómetro", type=["jpg", "jpeg", "png"])

if st.button("Registrar Cierre de Viaje"):
    
    # 1. Asegurarnos de que la carpeta local exista
    carpeta_fotos = "fotos_odometro"
    os.makedirs(carpeta_fotos, exist_ok=True)
    
    url_o_enlace = ""
    
    # 2. Guardar la imagen si el usuario subió una
    if imagen_subida is not None:
        # Creamos un nombre único usando la fecha y hora actual
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_archivo = f"odometro_{timestamp_str}_{imagen_subida.name}"
        ruta_completa = os.path.join(carpeta_fotos, nombre_archivo)
        
        # Guardar el archivo físicamente en la carpeta local
        with open(ruta_completa, "wb") as f:
            f.write(imagen_subida.getbuffer())
            
        # 3. Crear la fórmula de Google Sheets para el enlace cliqueable
        ruta_absoluta = os.path.abspath(ruta_completa).replace("\\", "/")
        url_o_enlace = f'=HYPERLINK("file:///{ruta_absoluta}", "Ver foto")'
    else:
        url_o_enlace = "Sin foto"

    # 4. Preparar los datos y enviarlos a Google Sheets
    # Reemplaza 'hoja' por el objeto que uses para conectar con tu Google Sheet (ej: sheet.append_row(...))
    try:
        # Ejemplo de los datos que guardas en la fila:
        datos_fila = [
            str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), # Fecha y hora
            # vehiculo,       # <--- tu variable de vehículo
            # chofer,         # <--- tu variable de chofer
            # km_actual,      # <--- tu variable de km
            url_o_enlace      # El enlace a la foto o texto "Sin foto"
        ]
        
        # Ejecutas el comando para insertar en tu hoja (descomenta según tu librería, ej: gspread)
        # hoja.append_row(datos_fila, value_input_option='USER_ENTERED') 
        # ¡Ojo! Es MUY IMPORTANTE usar value_input_option='USER_ENTERED' para que 
        # Google Sheets interprete el '=HYPERLINK(...)' como una fórmula y no como texto plano.
        
        st.success("¡Cierre de viaje registrado con éxito y foto guardada localmente!")
        
    except Exception as e:
        st.error(f"Error al registrar los datos en Google Sheets: {e}")