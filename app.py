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

# --- 4. COORDENADAS DE REFERENCIA PARA EL MAPA (NOA / ARGENTINA) ---
# Diccionario orientativo de coordenadas de destinos comunes para trazar el mapa
COORDS_DESTINOS = {
    "salta": (-24.7821, -65.4232),
    "jujuy": (-24.1858, -65.2995),
    "san salvador de jujuy": (-24.1858, -65.2995),
    "tucuman": (-26.8083, -65.2176),
    "san miguel de tucuman": (-26.8083, -65.2176),
    "santiago del estero": (-27.7951, -64.2615),
    "catamarca": (-28.4696, -65.7852),
    "san fernando del valle de catamarca": (-28.4696, -65.7852),
    "formosa": (-26.1853, -58.1758),
    "chaco": (-27.4512, -58.9866),
    "resistencia": (-27.4512, -58.9866),
    "corrientes": (-27.4692, -58.8306),
    "la rioja": (-29.4131, -66.8558)
}

def obtener_coordenada(destino_str):
    dest_clean = destino_str.strip().lower()
    for key, coords in COORDS_DESTINOS.items():
        if key in dest_clean:
            return coords
    # Coordenada por defecto en Salta Capital si no se reconoce
    return (-24.7821, -65.4232)

# --- 5. OBTENER ASIGNACIONES DESDE LA PLANILLA ---
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
st.title("🚚 Gestión de Logística - Choferes")

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
    st.markdown(
        """
        <style>
            [data-testid="stSidebar"] {
                display: none;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

if not chofer_en_url:
    st.info("👋 **Bienvenido al Sistema de Logística.**")
    chofer_actual = st.selectbox("Seleccione su Nombre y Apellido para ingresar:", choferes_lista)
else:
    chofer_actual = chofer_en_url

# --- SISTEMA DE AUTENTICACIÓN POR PIN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False
if "chofer_auth" not in st.session_state:
    st.session_state.chofer_auth = None

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
    st.stop()

# --- FUNCIONAMIENTO DE LA APP AUTENTICADA ---
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

# CREACIÓN DE LAS TRES SOLAPAS
tab1, tab2, tab3 = st.tabs(["📦 Solapa 1: Entregas", "📊 Solapa 2: Cierre de Viaje", "🗺️ Solapa 3: Hoja de Ruta y Mapa"])

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
                fecha_cierre,      # Fecha
                chofer_actual,     # Chofer
                vehiculo_id,       # Patente
                envio_cierre,      # Envio
                finalizo_viaje,    # Finalizo Viaje
                km_actual,         # Km Actual
                "Sin observaciones", # Observaciones
                link_foto          # Acceso Foto Odómetro
            ]
            
            worksheet_cierres.append_row(fila_datos, value_input_option='USER_ENTERED')
            st.success("¡Cierre de viaje registrado con éxito!")

# --- SOLAPA 3: HOJA DE RUTA Y MAPA DE SECUENCIA ÓPTIMA ---
with tab3:
    st.subheader("🗺️ Secuencia Óptima de Descarga y Mapa de Ruta")
    st.markdown("""
    * **Criterio LIFO (Carga y Descarga):** Los pedidos se ordenan de modo que el **último en cargarse al fondo del camión** sea el **primero en entregarse**.
    """)
    
    if not envios_disponibles:
        st.info("No hay rutas activas en este momento.")
    else:
        # Mostrar tabla de secuencia de entregas
        st.markdown("### 📋 Orden Secuencial de Visitas (Secuencia Logística)")
        
        # Generar lista numerada de paradas
        puntos_ruta = []
        for idx, envio in enumerate(envios_disponibles, start=1):
            coords = obtener_coordenada(envio["destino"])
            puntos_ruta.append({
                "Parada N°": idx,
                "Envío": envio["envio"],
                "Pedido": envio["pedido"],
                "Destino": envio["destino"],
                "Bultos": envio["bultos"],
                "Coordenadas": coords
            })
            st.markdown(f"**Parada #{idx}** ➔ **Envío:** `{envio['envio']}` | **Pedido:** `{envio['pedido']}` | **Destino:** `{envio['destino']}` (Bultos: {envio['bultos']})")
        
        st.markdown("---")
        st.markdown("### 📍 Visualización Interactiva del Recorrido")
        
        # Crear mapa centrado en el primer destino
        centro_mapa = puntos_ruta[0]["Coordenadas"]
        mapa_ruta = folium.Map(location=centro_mapa, zoom_start=8)
        
        # Lista de coordenadas para trazar la línea de ruta
        polyline_coords = []
        
        for parada in puntos_ruta:
            coords = parada["Coordenadas"]
            polyline_coords.append(coords)
            
            # Agregar marcador numerado
            popup_text = f"<b>Parada #{parada['Parada N°']}</b><br>Envío: {parada['Envio']}<br>Pedido: {parada['Pedido']}<br>Destino: {parada['Destino']}"
            
            folium.Marker(
                location=coords,
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=f"Parada {parada['Parada N°']}: {parada['Destino']}",
                icon=folium.Icon(color="blue" if parada["Parada N°"] > 1 else "green", icon="info-sign")
            ).add_to(mapa_ruta)
            
        # Trazar la línea de la ruta en orden secuencial
        if len(polyline_coords) > 1:
            folium.PolyLine(
                polyline_coords,
                color="red",
                weight=4,
                opacity=0.8,
                tooltip="Ruta Secuencial Óptima"
            ).add_to(mapa_ruta)
            
        # Renderizar el mapa en Streamlit
        st_folium(mapa_ruta, width=700, height=500)
