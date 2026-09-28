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
    Lee la solapa 'Asignación' y extrae todos los envíos correspondientes al chofer.
    Busca de manera flexible las columnas sin importar variaciones de nombres.
    """
    patente_asignada = "Sin Asignar"
    envios_lista = []
    try:
        ws = sheet.worksheet("Asignación")
        registros = ws.get_all_records()
        for row in registros:
            # Normalizar claves del diccionario a minúsculas para evitar errores
            row_lower = {str(k).strip().lower(): v for k, v in row.items()}
            
            chofer_fila = str(row_lower.get("chofer", "")).strip()
            if chofer_fila.lower() == chofer.strip().lower():
                # Buscar campos con distintas posibles variantes de nombres de columnas
                patente = str(row_lower.get("patente", row_lower.get("dominio", "Sin Asignar")))
                envio = str(row_lower.get("envio", row_lower.get("n° envio", row_lower.get("nro envio", "ENV-000"))))
                pedido = str(row_lower.get("pedido", row_lower.get("pedido n°", row_lower.get("n° ord pedido", "PED-9988"))))
                destino = str(row_lower.get("destino", "Sin Destino"))
                
                bultos_raw = row_lower.get("bultos", row_lower.get("peso (kg)", 1))
                bultos = int(bultos_raw) if str(bultos_raw).isdigit() else 1
                
                patente_asignada = patente
                envios_lista.append({
                    "envio": envio,
                    "pedido": pedido,
                    "bultos": bultos,
                    "destino": destino
                })
    except Exception as e:
        st.error(f"Error al leer la solapa Asignación: {e}")
    
    if not envios_lista:
        envios_lista = [{"envio": "ENV-000", "pedido": "PED-9988", "bultos": 1, "destino": "Salta"}]
        
    return patente_asignada, envios_lista

# --- 4. INTERFAZ GENERAL DE LA APP Y SOPORTE DE LINKS PERSONALIZADOS ---
st.title("🚚 Gestión de Logística - Choferes")

choferes_lista = ["Juan Pérez", "Carlos Gómez", "Mario Ruiz", "Matias", "Carlos", "Miguel", "Enrique", "Julio", "Rodrigo", "Wilson"]

# Leer si la URL trae un chofer por parámetro (Ej: tu-app.streamlit.app/?chofer=Juan%20Pérez)
params = st.query_params
chofer_en_url = params.get("chofer", None)

if chofer_en_url and chofer_en_url in choferes_lista:
    chofer_actual = chofer_en_url
    st.info(f"Sesión iniciada automáticamente para el chofer: **{chofer_actual}**")
    # Opción para cambiar de usuario si lo desea
    if st.button("🔄 Cambiar de usuario"):
        st.query_params.clear()
        st.rerun()
else:
    chofer_actual = st.selectbox("Seleccione su Usuario / Chofer:", choferes_lista)
    # Mostrar el link personalizado que el logístico puede copiar y enviar
    link_personalizado = f"https://tu-aplicacion.streamlit.app/?chofer={chofer_actual.replace(' ', '%20')}"
    st.caption(f"🔗 **Link para enviar por WhatsApp a {chofer_actual}:** `{link_personalizado}`")

patente_asignada, envios_disponibles = obtener_asignaciones_chofer(chofer_actual)

# Control de estado para avanzar automáticamente de envío
if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

if st.session_state.envio_index >= len(envios_disponibles):
    st.session_state.envio_index = 0

tab1, tab2 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje"])

# --- SOLAPA 1: ENTREGAS ---
with tab1:
    st.subheader("Registro de Entrega")
    
    # Filtrar envíos pendientes o mostrarlos todos en secuencia
    envio_actual_dict = envios_disponibles[st.session_state.envio_index]
    envio_asignado = envio_actual_dict["envio"]
    pedido_asignado = envio_actual_dict["pedido"]
    bultos_asignados = envio_actual_dict["bultos"]
    destino_asignado = envio_actual_dict["destino"]

    # Mostrar selector si tiene varios envíos asignados
    if len(envios_disponibles) > 1:
        opciones_envios = [f"{e['envio']} (Destino: {e['destino']})" for e in envios_disponibles]
        envio_seleccionado = st.selectbox(
            "Seleccione el Envío a procesar (Asignado por Logística):", 
            opciones_envios, 
            index=st.session_state.envio_index
        )
        # Sincronizar índice
        st.session_state.envio_index = opciones_envios.index(envio_seleccionado)
        envio_actual_dict = envios_disponibles[st.session_state.envio_index]
        envio_asignado = envio_actual_dict["envio"]
        pedido_asignado = envio_actual_dict["pedido"]
        bultos_asignados = envio_actual_dict["bultos"]
        destino_asignado = envio_actual_dict["destino"]
    else:
        st.info(f"📍 **Destino asignado:** {destino_asignado}")

    with st.form("form_entregas"):
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        
        # --- CAMPOS GRISEADOS Y BLOQUEADOS PARA EL CHOFER ---
        envio_n = st.text_input("Envío N° (Asignado)", value=envio_asignado, disabled=True)
        pedido_n = st.text_input("Pedido N° (Asignado)", value=pedido_asignado, disabled=True)
        patente_s1 = st.text_input("Patente Asignada", value=patente_asignada, disabled=True)
        destino_s1 = st.text_input("Destino", value=destino_asignado, disabled=True)
        cant_bultos = st.number_input("Cantidad de bultos", min_value=1, value=bultos_asignados, disabled=True)
        # ----------------------------------------------------
        
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

            # ORDEN EXACTO DE COLUMNAS COINCIDENTE CON TU PLANILLA
            fila_entrega = [
                fecha_actual,        # A: Fecha
                chofer_actual,       # B: Chofer
                patente_s1,          # C: Patente
                envio_n,             # D: Envios N°
                pedido_n,            # E: Pedido N°
                cant_bultos,         # F: Cantidad de bultos
                estado_entrega,      # G: Estado
                forma_cobro,         # H: Forma de cobro
                monto                # I: Monto
            ]
            
            worksheet_entregas.append_row(fila_entrega, value_input_option='USER_ENTERED')
            st.success(f"¡Entrega del envío {envio_n} registrada con éxito!")
            
            # Avanzar automáticamente al siguiente envío y limpiar formulario
            if st.session_state.envio_index < len(envios_disponibles) - 1:
                st.session_state.envio_index += 1
            else:
                st.info("¡Has completado todos los envíos asignados!")
            
            st.rerun()

# --- SOLAPA 2: CIERRE DE VIAJE ---
with tab2:
    st.subheader("Cierre de Viaje y Rendición")
    
    with st.form("form_cierre"):
        fecha_cierre = datetime.now().strftime("%Y-%m-%d")
        
        vehiculo_id = st.text_input("Patente del Vehículo", value=patente_asignada, disabled=True)
        envio_cierre = st.text_input("Envío N° Actual", value=envio_asignado, disabled=True)
        
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
            st.success("¡Cierre de viaje registrado con éxito!")
