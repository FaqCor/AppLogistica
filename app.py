import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="App Logística - Choferes", page_icon="🚚", layout="centered")

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

# --- 3. BASE DE DATOS DE PINES DE SEGURIDAD ---
# Puedes modificar o ampliar estos PINs según tus choferes
PINES_CHOFERES = {
    "ADRIÁN ROLDÁN": "1234",
    "DIEGO MEDINA": "2345",
    "ROBERTO PEREZ": "3456",
    "GUILLERMO AL...": "4567",
    "GERONIMO M...": "5678",
    "GONZALO ONE...": "6789",
    "GABRIEL LLULL": "1111",
    "NICOLÁS DÍAZ": "2222",
    "FELIX NICOLÁS ...": "3333"
}

# --- 4. OBTENER ASIGNACIONES DESDE LA PLANILLA ---
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

# --- 5. GESTIÓN DE ACCESO Y SEGURIDAD ---
st.title("🚚 Gestión de Logística - Choferes")

choferes_lista = list(PINES_CHOFERES.keys())

# Leer parámetro de la URL
params = st.query_params
chofer_en_url = params.get("chofer", None)

# Panel de Logística (Oculto para los choferes si entran con su link seguro)
with st.sidebar:
    st.header("Panel de Logística")
    chofer_seleccionado_admin = st.selectbox("Seleccionar chofer para crear link:", choferes_lista)
    url_base = "https://applogistica.streamlit.app" # Reemplaza con tu URL real
    link_wpp = f"{url_base}/?chofer={chofer_seleccionado_admin.replace(' ', '%20')}"
    st.markdown(f"**Link seguro para WhatsApp:**")
    st.code(link_wpp, language="markdown")

if not chofer_en_url:
    st.warning("⚠️ Acceso restringido. Por favor, ingrese mediante el enlace personal enviado por el área de logística.")
    chofer_actual = st.selectbox("O seleccione su usuario para pruebas:", choferes_lista)
else:
    chofer_actual = chofer_en_url

# --- SISTEMA DE AUTENTICACIÓN POR PIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chofer_auth" not in st.session_state:
    st.session_state.chofer_auth = None

# Si cambia el chofer en la URL, requerir nuevo PIN
if st.session_state.chofer_auth != chofer_actual:
    st.session_state.autenticado = False
    st.session_state.chofer_auth = chofer_actual

if not st.session_state.autenticado:
    st.info(f"🔒 Identidad detectada para: **{chofer_actual}**")
    with st.form("form_pin"):
        pin_ingresado = st.text_input("Ingrese su PIN de seguridad de 4 dígitos:", type="password")
        btn_login = st.form_submit_button("INGRESAR A MIS PEDIDOS")
        
        if btn_login:
            pin_correcto = PINES_CHOFERES.get(chofer_actual, "")
            if pin_ingresado.strip() == pin_correcto:
                st.session_state.autenticado = True
                st.success("¡Acceso autorizado!")
                st.rerun()
            else:
                st.error("❌ PIN incorrecto. Verifique con logística.")
    st.stop() # Detiene la ejecución de la app hasta que ponga el PIN correcto

# --- A PARTIR DE ACÁ LA APP FUNCIONA CON TOTAL SEGURIDAD ---
st.success(f"🔓 Sesión segura iniciada para: **{chofer_actual}**")
if st.button("🔒 Cerrar Sesión / Salir"):
    st.session_state.autenticado = False
    st.query_params.clear()
    st.rerun()

patente_asignada, envios_disponibles = obtener_asignaciones_chofer(chofer_actual)

if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

if st.session_state.envio_index >= len(envios_disponibles) and len(envios_disponibles) > 0:
    st.session_state.envio_index = 0

tab1, tab2 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje"])

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
                except Exception as ex:
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
                folder_id = "1THxT45-t-VFWU0JmWD2kR2WDCwmA9vdW"
                link_foto = f'=HYPERLINK("https://drive.google.com/drive/folders/{folder_id}", "Abrir Carpeta Drive")'

            try:
                worksheet_cierres = sheet.worksheet("Cierres")
            except:
                worksheet_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                worksheet_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones", "Acceso Foto Odómetro"])

            fila_datos = [fecha_cierre, chofer_actual, vehiculo_id, envio_cierre, finalizo_viaje, km_actual, observaciones, link_foto]
            worksheet_cierres.append_row(fila_datos, value_input_option='USER_ENTERED')
            st.success("¡Cierre de viaje registrado con éxito!")
