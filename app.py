import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from PIL import Image
import io
import folium
from streamlit_folium import st_folium
import pandas as pd

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

@st.cache_data(ttl=60, show_spinner=False)
def cargar_datos_asignacion():
    try:
        ws = sheet.worksheet("Asignación")
        return ws.get_all_values()
    except Exception as e:
        return []

@st.cache_data(ttl=60, show_spinner=False)
def cargar_datos_vehiculos():
    try:
        ws_veh = None
        for ws in sheet.worksheets():
            if "vehiculo" in ws.title.lower() or "vehículo" in ws.title.lower():
                ws_veh = ws
                break
        if ws_veh:
            return ws_veh.get_all_values()
    except Exception:
        pass
    return []

def obtener_km_actual_vehiculo(patente):
    """Busca el kilometraje actual en la base de datos de vehículos usando las columnas exactas de la planilla"""
    if not patente or patente == "Sin Asignar":
        return 0
    try:
        filas_veh = cargar_datos_vehiculos()
        if not filas_veh or len(filas_veh) < 2:
            return 0
            
        idx_pat = 1 
        idx_km = 3  

        patente_clean = patente.strip().upper()
        
        for fila in filas_veh[1:]:
            if len(fila) > max(idx_pat, idx_km):
                pat = str(fila[idx_pat]).strip().upper()
                if pat == patente_clean:
                    val_str = str(fila[idx_km]).replace(".", "").replace(",", "").strip()
                    if val_str.isdigit():
                        return int(val_str)
    except Exception as e:
        print(f"Error al buscar km: {e}")
        
    return 0

def obtener_asignaciones_chofer(chofer):
    envios_lista = []
    patente_asignada = "Sin Asignar"
    try:
        filas = cargar_datos_asignacion()
        if not filas or len(filas) < 2:
            return patente_asignada, envios_lista

        encabezados = [str(h).strip().lower() for h in filas[0]]
        
        idx_chofer = 4  # Columna E
        idx_envio = 2   # Columna C (Envío N°)
        idx_pedido = 3  # Columna D (Pedido N°)
        idx_dominio = 5 # Columna F (Dominio)
        idx_destino = 9 # Columna J (Destino)
        idx_estado = 7  # Columna H (Estado)
        idx_despachar = 13 # Columna N (¿Despachar?) -> Índice 13
        idx_orden = 15     # Columna P (Orden de paradas) -> Índice 15

        for fila in filas[1:]:
            if len(fila) <= max(idx_chofer, idx_dominio):
                continue
                
            chofer_fila = str(fila[idx_chofer]).strip()
            
            if chofer_fila.lower() == chofer.strip().lower():
                envio = str(fila[idx_envio]).strip() if idx_envio < len(fila) else "ENV-000"
                pedido = str(fila[idx_pedido]).strip() if idx_pedido < len(fila) else "PED-000"
                dominio = str(fila[idx_dominio]).strip() if idx_dominio < len(fila) else "Sin Asignar"
                destino = str(fila[idx_destino]).strip() if idx_destino < len(fila) else "Sin Destino"
                estado = str(fila[idx_estado]).strip() if idx_estado < len(fila) else "Pendiente"
                
                val_despachar = str(fila[idx_despachar]).strip().upper() if idx_despachar < len(fila) else ""
                is_checked = val_despachar in ["TRUE", "VERDADERO", "1", "X", "YES"]

                nro_orden = 99
                if idx_orden < len(fila):
                    val_ord = str(fila[idx_orden]).strip()
                    if val_ord.isdigit():
                        nro_orden = int(val_ord)

                if patente_asignada == "Sin Asignar" and dominio and dominio != "Sin Asignar":
                    patente_asignada = dominio

                if is_checked and nro_orden != 99 and estado.strip().lower() != "entregado":
                    envios_lista.append({
                        "envio": envio, 
                        "pedido": pedido, 
                        "bultos": 1, 
                        "destino": destino, 
                        "dominio": dominio,
                        "orden": nro_orden
                    })
                    
        envios_lista = sorted(envios_lista, key=lambda x: x["orden"])

    except Exception as e:
        st.error(f"Error al leer la solapa Asignación: {e}")
        
    return patente_asignada, envios_lista

# --- 6. AUTENTICACIÓN Y PANEL DE LOGÍSTICA ---
st.markdown("<h1 style='text-align: center; margin-bottom: 5px;'>🚚 DM MAESTRO S.R.L. </h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 25px;'>Sistema de Flota y Logística</p>", unsafe_allow_html=True)

choferes_lista = list(PINES_CHOFERES.keys())
params = st.query_params
chofer_en_url = params.get("chofer", None)
es_encargado = params.get("admin", None) == "logadmin2026"

# -------------------------------------------------------------
# PANEL EXCLUSIVO PARA EL ENCARGADO DE LOGÍSTICA
# -------------------------------------------------------------
if es_encargado:
    st.markdown("---")
    st.subheader("🛠️ Panel de Verificación y Control de Flota (Logística)")
    st.markdown("Revise los datos de la base de vehículos, corrija cualquier error de carga y actualice los kilómetros. Al guardar, el sistema pasará automáticamente el valor actual al **Odómetro anterior** (Columna E) y guardará el nuevo valor en el **Odómetro actual** (Columna D).")

    try:
        ws_vehiculos = sheet.worksheet("Base de datos VEHICULOS")
        data_vehiculos = ws_vehiculos.get_all_records()
        df_vehiculos = pd.DataFrame(data_vehiculos)

        df_editado = st.data_editor(df_vehiculos, num_rows="fixed", use_container_width=True, key="editor_logistica_admin")

        if st.button("💾 Guardar Cambios y Actualizar Odómetros"):
            actualizaciones = 0
            for index, row in df_editado.iterrows():
                fila_excel = index + 4  
                
                km_actual_en_sheet = ws_vehiculos.cell(fila_excel, 4).value
                km_nuevo_modificado = row["Odómetro actual (km/horas)"]
                
                if str(km_nuevo_modificado) != str(km_actual_en_sheet) and km_nuevo_modificado != "":
                    ws_vehiculos.update_cell(fila_excel, 5, km_actual_en_sheet)
                    ws_vehiculos.update_cell(fila_excel, 4, km_nuevo_modificado)
                    actualizaciones += 1

            st.success(f"¡Se actualizaron y desplazaron correctamente {actualizaciones} registros en la flota!")
            st.rerun()

    except Exception as e:
        st.error(f"Error al cargar el panel de logística: {e}")

    st.stop()

# -------------------------------------------------------------
# VISTA NORMAL DE CHOFERES
# -------------------------------------------------------------
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
km_inicial_sugerido = obtener_km_actual_vehiculo(patente_asignada)

if "envio_index" not in st.session_state:
    st.session_state.envio_index = 0

# --- 7. CONTROL DE FLUJO Y PANTALLA PRINCIPAL ---

if not st.session_state.checklist_realizado:
    st.warning("⚠️ **CHECKLIST OBLIGATORIO:** Para habilitar la salida del camión y desbloquear el menú principal, debe completar la inspección.")
    
    st.markdown("<div class='orion-card'><h3>📋 1. Checklist Pre-operacional</h3><p style='color:#94a3b8;'>Verificación obligatoria de la unidad asignada.</p></div>", unsafe_allow_html=True)
    
    with st.form("form_checklist_obligatorio"):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Chofer", value=chofer_actual, disabled=True)
            patente_in = st.text_input("Patente / Dominio Asignado (Bloqueado)", value=patente_asignada, disabled=True)
            neumaticos = st.checkbox("Presión y estado de neumáticos")
            luces = st.checkbox("Luces altas, bajas y guiños")
        with col2:
            kilometraje = st.number_input("Kilometraje Actual de Salida (Km)", value=km_inicial_sugerido, disabled=True)
            frenos = st.checkbox("Liquido de Freno")
            fluidos = st.checkbox("Niveles de agua y aceite")
            documentacion = st.checkbox("Documentación y seguros vigentes")
        
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
    # --- MENÚ TÁCTIL PRINCIPAL ---
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
                    
                    estado_entrega = st.selectbox("Estado", ["ENTREGADO", "NO ENTREGADO", "PASÓ A COBRAR"])
                    forma_cobro = st.selectbox("Forma de cobro", ["Efectivo", "Transferencia", "Cheque", "Sin Cobro"])
                    monto = st.number_input("Monto ($)", min_value=0.0, step=0.01)
                    dni_recibe = st.text_input("DNI de quien recibe")
                    
                    if st.form_submit_button("REGISTRAR Y CERRAR ENTREGA"):
                        try:
                            ws_ent = sheet.worksheet("Entregas")
                            filas_entregas = ws_ent.get_all_values()
                            
                            fecha_cierre_actual = datetime.now().strftime("%d/%m/%Y")
                            envio_a_actualizar = str(envio_n).strip().upper()
                            
                            fila_encontrada = -1
                            # Buscamos en la pestaña Entregas el Envío N° en la Columna D (índice 3)
                            for idx, fila in enumerate(filas_entregas[1:], start=2):
                                if len(fila) > 3:
                                    envio_en_fila = str(fila[3]).strip().upper()
                                    if envio_en_fila == envio_a_actualizar:
                                        fila_encontrada = idx
                                        break
                                        
                            if fila_encontrada != -1:
                                # Si existe el envío en la tabla Entregas, actualizamos la Fecha en Columna B (2)
                                ws_ent.update_cell(fila_encontrada, 2, fecha_cierre_actual)
                                # Opcional: También podemos actualizar Estado (G), Monto (I) y DNI (K) si lo deseas en su respectiva fila
                                ws_ent.update_cell(fila_encontrada, 7, estado_entrega)
                                ws_ent.update_cell(fila_encontrada, 9, monto)
                                ws_ent.update_cell(fila_encontrada, 11, dni_recibe)
                            else:
                                # Si no existía, añadimos la fila ubicando Fecha en B, Envío en D, etc.
                                nueva_fila = ["", fecha_cierre_actual, "", envio_a_actualizar, pedido_n, cant_bultos, estado_entrega, forma_cobro, monto, "", dni_recibe]
                                ws_ent.append_row(nueva_fila)
                          
                        # Actualizar el estado en la solapa Asignación
                            ws_asig = sheet.worksheet("Asignación")
                            cell = ws_asig.find(envio_n, in_column=3)
                            if cell:
                                ws_asig.update_cell(cell.row, 11, estado_entrega)

                            st.success(f"¡Pedido {envio_a_actualizar} cerrado y registrado con éxito!")
                            if st.session_state.envio_index < len(envios_disponibles) - 1:
                                st.session_state.envio_index += 1
                            else:
                                st.session_state.envio_index = 0
                            st.rerun()
        # --- MÓDULO 2: CIERRE DE VIAJE ---
        elif st.session_state.menu_activo == "Cierre":
            st.subheader("⚙️ Cierre de Viaje y Rendición")
            
            envio_actual_texto = "ENV-000"
            if envios_disponibles and len(envios_disponibles) > 0:
                if st.session_state.envio_index >= len(envios_disponibles):
                    st.session_state.envio_index = 0
                envio_actual_texto = envios_disponibles[st.session_state.envio_index]["envio"]

            with st.form("form_cierre_mod"):
                vehiculo_id = st.text_input("Dominio", value=patente_asignada, disabled=True)
                envio_cierre = st.text_input("Envío Actual", value=envio_actual_texto, disabled=True)
                finalizo_viaje = st.selectbox("¿Finalizó el viaje?", ["Sí", "No"])
                km_actual_ingresado = st.number_input("Kilometraje Actual", min_value=0.0, step=1.0)
                
                if st.form_submit_button("FINALIZAR Y ENVIAR CIERRE"):
                    try:
                        try:
                            ws_cierres = sheet.worksheet("Cierres")
                        except Exception:
                            ws_cierres = sheet.add_worksheet(title="Cierres", rows=100, cols=10)
                            ws_cierres.append_row(["Fecha", "Chofer", "Patente", "Envio", "Finalizo Viaje", "Km Actual", "Observaciones"])

                        ws_cierres.append_row([
                            datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, vehiculo_id, envio_cierre, 
                            finalizo_viaje, km_actual_ingresado, "Sin observaciones"
                        ], value_input_option='USER_ENTERED')

                        km_anterior_capturado = 0
                        
                        try:
                            ws_vehiculos = None
                            for ws in sheet.worksheets():
                                if "vehiculo" in ws.title.lower() or "vehículo" in ws.title.lower():
                                    ws_vehiculos = ws
                                    break
                            
                            if ws_vehiculos:
                                patente_buscada = patente_asignada.strip().upper()
                                col_patentes = ws_vehiculos.col_values(2)
                                fila_encontrada = None
                                
                                for idx, pat in enumerate(col_patentes):
                                    if pat.strip().upper() == patente_buscada:
                                        fila_encontrada = idx + 1
                                        break
                                
                                if fila_encontrada:
                                    val_viejo = ws_vehiculos.cell(fila_encontrada, 4).value
                                    if val_viejo is not None and str(val_viejo).strip() != "":
                                        val_limpio = str(val_viejo).replace(".", "").replace(",", "").strip()
                                        if val_limpio.isdigit():
                                            km_anterior_capturado = float(val_limpio)
                                
                                    ws_vehiculos.update_cell(fila_encontrada, 6, val_viejo if val_viejo else 0)
                                    ws_vehiculos.update_cell(fila_encontrada, 4, km_actual_ingresado)
                        except Exception as e_veh:
                            st.warning(f"Error en Base Vehículos: {e_veh}")

                        try:
                            ws_odometro = sheet.worksheet("Odometro")
                            columna_dominios = ws_odometro.col_values(3)
                            siguiente_fila = len(columna_dominios) + 1
                            if siguiente_fila < 2:
                                siguiente_fila = 2
                                
                            fecha_actual_str = datetime.now().strftime("%d/%m/%Y")
                            
                            ws_odometro.update_cell(siguiente_fila, 1, False)               # Columna A: Checkbox
                            ws_odometro.update_cell(siguiente_fila, 2, fecha_actual_str)      # Columna B: Fecha
                            ws_odometro.update_cell(siguiente_fila, 3, patente_asignada)        # Columna C: Dominio
                            ws_odometro.update_cell(siguiente_fila, 4, km_anterior_capturado)   # Columna D: Km anterior
                            ws_odometro.update_cell(siguiente_fila, 5, km_actual_ingresado)     # Columna E: Km actual
                            ws_odometro.update_cell(siguiente_fila, 10, chofer_actual)          # Columna J: Chofer

                        except Exception as e_odo:
                            st.warning(f"Nota al actualizar pestaña Odometro: {e_odo}")

                        st.success("¡Cierre de viaje registrado con éxito!")

                    except Exception as e:
                        st.error(f"Error al procesar el cierre: {e}")

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
                    <p>Utilice este módulo únicamente si detecta una anomalía mecánica que requiera intervención inmediata del taller.</p>
                </div>
            """, unsafe_allow_html=True)
            with st.form("form_mecanica"):
                tipo_falla = st.selectbox("Sistema afectado", ["Motor", "Frenos", "Suspensión", "Transmisión", "Eléctrico", "Neumáticos"])
                desc_falla = st.text_area("Describa la falla detectada")
                if st.form_submit_button("REPORTAR FALLA TÉCNICA"):
                    if desc_falla:
                        try:
                            ws_mec = sheet.worksheet("Mecanica")
                        except:
                            ws_mec = sheet.add_worksheet(title="Mecanica", rows=100, cols=10)
                            ws_mec.append_row(["Fecha", "Chofer", "Patente", "Sistema", "Descripcion"])
                        
                        ws_mec.append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), chofer_actual, patente_asignada, tipo_falla, desc_falla])
                        st.success("🛠️ Falla reportada al área de mecánica con éxito.")
                    else:
                        st.warning("Por favor, ingrese una descripción de la falla.")
