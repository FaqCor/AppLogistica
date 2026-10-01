import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Módulos de Choferes - Orion",
    page_icon="🚚",
    layout="wide"
)

# Estilos CSS personalizados (Diseño Oscuro / Tarjetas)
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

st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>PORTAL DEL CHOFER - OPERACIONES</h1>", unsafe_allow_html=True)

# Menú lateral o pestañas para navegar entre los módulos solicitados
menu = st.tabs(["1. Checklist Pre-operacional", "3. Reporte de Incidentes", "5. Gestión de Viáticos"])

# ==========================================
# MÓDULO 1: CHECKLIST PRE-OPERACIONAL
# ==========================================
with menu[0]:
    st.markdown("""
        <div class="orion-card">
            <h3>📋 Inspección Diaria del Vehículo</h3>
            <p style='color: #94a3b8;'>Verificá el estado general antes de iniciar tu recorrido.</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_checklist"):
        col1, col2 = st.columns(2)
        with col1:
            chofer = st.text_input("Nombre y Apellido del Chofer")
            patente = st.text_input("Patente / Unidad Asignada")
            neumaticos = st.checkbox("Presión y estado de neumáticos OK")
            luces = st.checkbox("Luces altas, bajas y guiños OK")
        with col2:
            kilometraje = st.number_input("Kilometraje Actual (Km)", min_value=0, step=100)
            frenos = st.checkbox("Sistema de frenos y estacionamiento OK")
            fluidos = st.checkbox("Niveles de agua y aceite OK")
            documentacion = st.checkbox("Documentación y seguros vigentes OK")
        
        submitted_check = st.form_submit_button("Enviar Checklist")
        if submitted_check:
            if chofer and patente:
                # Aquí conectarías con gspread para guardar en Google Sheets
                st.success(f"¡Checklist registrado con éxito para la unidad {patente}!")
            else:
                st.warning("Por favor completá el nombre del chofer y la patente.")

# ==========================================
# MÓDULO 3: REPORTE DE INCIDENTES EN RUTA
# ==========================================
with menu[1]:
    st.markdown("""
        <div class="orion-card">
            <h3>⚠️ Reporte de Novedades o Incidentes</h3>
            <p style='color: #94a3b8;'>Informá demoras, fallas mecánicas o imprevistos en el camino.</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_incidente"):
        col1, col2 = st.columns(2)
        with col1:
            id_viaje = st.text_input("Número de Viaje / ID")
            tipo_incidente = st.selectbox("Tipo de Incidente", [
                "Falla mecánica", 
                "Demora por tráfico / Corte de ruta", 
                "Incidente climático", 
                "Otro"
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

# ==========================================
# MÓDULO 5: GESTIÓN DE GASTOS DE VIAJE (VIÁTICOS)
# ==========================================
with menu[2]:
    st.markdown("""
        <div class="orion-card">
            <h3>💳 Rendición de Viáticos y Gastos</h3>
            <p style='color: #94a3b8;'>Cargá tus comprobantes por peajes, combustible o reparaciones menores.</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("form_viaticos"):
        col1, col2 = st.columns(2)
        with col1:
            viaje_v = st.text_input("Número de Viaje asociado")
            categoria_gasto = st.selectbox("Concepto", [
                "Peaje", 
                "Combustible extra", 
                "Estacionamiento", 
                "Reparación de emergencia", 
                "Comida / Viático diario"
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
