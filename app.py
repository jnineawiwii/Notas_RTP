import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime
import base64
import os

# Configuración de página
st.set_page_config(
    page_title="Monitoreo RTP - Captura de Notas",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============== ESTILOS MODERNOS ==============
st.markdown("""
<style>
    /* Fuente y fondo general */
    .main {
        background-color: #f8f9fa;
    }
    
    /* Tarjetas modernas */
    .card {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border: 1px solid #e9ecef;
        transition: all 0.2s ease;
    }
    .card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }
    
    .card-header {
        font-size: 18px;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #e9ecef;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* Badges de estado */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge-success { background: #d4edda; color: #155724; }
    .badge-warning { background: #fff3cd; color: #856404; }
    .badge-danger { background: #f8d7da; color: #721c24; }
    .badge-info { background: #d1ecf1; color: #0c5460; }
    .badge-primary { background: #cce5ff; color: #004085; }
    
    /* Contenedor de texto PDF */
    .pdf-text-container {
        background: white;
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #dee2e6;
        max-height: 550px;
        overflow-y: auto;
        font-family: 'Segoe UI', 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.8;
        color: #1a1a2e;
        white-space: pre-wrap;
    }
    .pdf-text-container::-webkit-scrollbar {
        width: 8px;
    }
    .pdf-text-container::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
    }
    .pdf-text-container::-webkit-scrollbar-thumb {
        background: #c1c7cd;
        border-radius: 4px;
    }
    .pdf-text-container::-webkit-scrollbar-thumb:hover {
        background: #a8b0b8;
    }
    
    /* Campos asignados */
    .field-assigned {
        background: #e8f5e9;
        padding: 6px 14px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 13px;
        border-left: 4px solid #4caf50;
        color: #1b5e20;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .field-empty {
        background: #f5f5f5;
        padding: 6px 14px;
        border-radius: 8px;
        margin: 4px 0;
        font-size: 13px;
        border-left: 4px solid #bdbdbd;
        color: #757575;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    /* Botones de asignación */
    .btn-assign {
        border: none;
        padding: 8px 12px;
        border-radius: 8px;
        font-weight: 500;
        font-size: 13px;
        cursor: pointer;
        width: 100%;
        margin: 3px 0;
        transition: all 0.2s ease;
        background: white;
        border: 1px solid #dee2e6;
        color: #1a1a2e;
    }
    .btn-assign:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        border-color: #007bff;
    }
    
    /* Métricas */
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
        border: 1px solid #e9ecef;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1a1a2e;
    }
    .metric-label {
        font-size: 13px;
        color: #6c757d;
        margin-top: 4px;
    }
    .metric-icon {
        font-size: 24px;
        margin-bottom: 6px;
    }
    
    /* Tabs personalizados */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #f1f3f5;
        border-radius: 12px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px;
        padding: 10px 24px;
        font-weight: 500;
        color: #495057;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: #007bff;
        color: white;
        box-shadow: 0 2px 8px rgba(0,123,255,0.3);
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: #e9ecef;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"]:hover {
        background: #0069d9;
    }
    
    /* Link error */
    .link-error {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 8px 14px;
        border-radius: 8px;
        font-size: 13px;
        color: #856404;
    }
    
    /* Sidebar mejorado */
    .css-1d391kg {
        background: #f8f9fa;
    }
    
    /* Tabla mejorada */
    .dataframe {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e9ecef;
    }
    .dataframe thead tr th {
        background: #f1f3f5 !important;
        color: #1a1a2e !important;
        font-weight: 600 !important;
        padding: 10px 12px !important;
    }
    .dataframe tbody tr td {
        padding: 8px 12px !important;
    }
    .dataframe tbody tr:hover {
        background: #f8f9fa !important;
    }
    
    /* Scroll suave */
    html {
        scroll-behavior: smooth;
    }
    
    /* Tooltip */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }
    .tooltip .tooltiptext {
        visibility: hidden;
        width: 200px;
        background: #1a1a2e;
        color: white;
        text-align: center;
        border-radius: 6px;
        padding: 6px 10px;
        position: absolute;
        z-index: 1;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 12px;
    }
    .tooltip:hover .tooltiptext {
        visibility: visible;
        opacity: 1;
    }
    
    /* Estilo para las columnas de la tabla en data_editor */
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# ============== HEADER ==============
st.markdown("""
<div style="display: flex; align-items: center; gap: 16px; padding: 10px 0 20px 0;">
    <div style="font-size: 40px;">🚌</div>
    <div>
        <h1 style="margin: 0; font-size: 28px; font-weight: 700; color: #1a1a2e;">Monitoreo RTP</h1>
        <p style="margin: 0; color: #6c757d; font-size: 15px;">Captura de Notas - Sistema de Seguimiento a Medios</p>
    </div>
    <div style="margin-left: auto; background: #e8f5e9; padding: 6px 16px; border-radius: 20px; font-size: 13px; color: #2e7d32;">
        <span>🟢 Sistema en línea</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Columnas oficiales
OFFICIAL_COLUMNS = [
    'Año',
    '# Mes',
    'Mes',
    'Fecha ',
    'Título de la nota',
    'RTP, ¿Es relevante en la nota?',
    'Tema de la nota',
    'Campaña',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *',
    'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *',
    'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *',
    'OTROS (Twitter, Facebook, You Tube, etc.).',
    'Informativo / Positivo/ Negativo',
    'LINK',
    'Autor',
    'PUBLICACIÓN BOLETÍN',
    'RESUMEN  DE LA NOTA (RTP)'
]

# Nombres amigables para la tabla
FIELD_NAMES = {
    'Año': '📅 Año',
    '# Mes': '🔢 # Mes',
    'Mes': '📆 Mes',
    'Fecha ': '📅 Fecha',
    'Título de la nota': '📌 Título',
    'RTP, ¿Es relevante en la nota?': '🎯 Relevante',
    'Tema de la nota': '📂 Tema',
    'Campaña': '🏷️ Campaña',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': '📻 Radio',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': '📺 TV',
    'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': '🌐 Digitales',
    'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': '📰 Impresos',
    'OTROS (Twitter, Facebook, You Tube, etc.).': '📱 Redes Sociales',
    'Informativo / Positivo/ Negativo': '📊 Tono',
    'LINK': '🔗 Link',
    'Autor': '✍️ Autor',
    'PUBLICACIÓN BOLETÍN': '📄 Boletín',
    'RESUMEN  DE LA NOTA (RTP)': '📝 Resumen'
}

# Columnas para la tabla (versión resumida para mejor visualización)
TABLE_COLUMNS_DISPLAY = [
    'Fecha ',
    'Título de la nota',
    'RTP, ¿Es relevante en la nota?',
    'Tema de la nota',
    'Campaña',
    'Informativo / Positivo/ Negativo',
    'LINK',
    'Autor',
    'RESUMEN  DE LA NOTA (RTP)'
]

def map_campana(sentiment):
    if sentiment == "Positivo":
        return "RTP avanza"
    return "RTP informa"

def extract_text_from_pdf(pdf_bytes):
    text = ""
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
        return text
    except Exception as e:
        return f"Error al extraer texto: {str(e)}"

def get_pdf_download_link(pdf_bytes, filename):
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}" style="display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #007bff, #0056b3); color: white; text-decoration: none; border-radius: 10px; font-weight: 600; transition: all 0.2s ease;">📄 Descargar PDF</a>'

def validate_and_format_link(link):
    if not link or pd.isna(link):
        return None
    link = str(link).strip()
    if link.startswith('\\\\') or link.startswith('\\'):
        return None
    if not link.startswith(('http://', 'https://')):
        if re.match(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}', link):
            return f'https://{link}'
        return None
    if re.match(r'^https?://[^\s]+', link):
        return link
    return None

# ============== INICIALIZAR SESSION STATE ==============
if 'notas_capturadas' not in st.session_state:
    st.session_state.notas_capturadas = []
if 'nota_actual' not in st.session_state:
    st.session_state.nota_actual = {}
if 'texto_seleccionado' not in st.session_state:
    st.session_state.texto_seleccionado = ""
if 'relevancia_seleccionada' not in st.session_state:
    st.session_state.relevancia_seleccionada = "Sí"
if 'tono_seleccionado' not in st.session_state:
    st.session_state.tono_seleccionado = "Informativo"
if 'pdf_bytes' not in st.session_state:
    st.session_state.pdf_bytes = None
if 'pdf_filename' not in st.session_state:
    st.session_state.pdf_filename = None
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'fecha_editable' not in st.session_state:
    st.session_state.fecha_editable = datetime.now().strftime("%Y-%m-%d")
if 'mes_editable' not in st.session_state:
    st.session_state.mes_editable = datetime.now().strftime("%B").capitalize()
if 'anio_editable' not in st.session_state:
    st.session_state.anio_editable = str(datetime.now().year)
if 'num_mes_editable' not in st.session_state:
    st.session_state.num_mes_editable = str(datetime.now().month)
if 'show_all_columns' not in st.session_state:
    st.session_state.show_all_columns = False

# ============== SIDEBAR ==============
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 20px 0;">
        <div style="font-size: 48px;">🚌</div>
        <h3 style="margin: 8px 0 0 0; color: #1a1a2e;">Monitoreo RTP</h3>
        <p style="color: #6c757d; font-size: 12px; margin: 0;">v2.0 - Captura de Notas</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 📂 Carga de Documentos")
    uploaded_file = st.file_uploader("Sube tu archivo:", type=["xlsx", "pdf"], label_visibility="collapsed")
    
    st.markdown("---")
    
    st.markdown("### 📊 Notas Capturadas")
    
    # Métricas en sidebar
    total = len(st.session_state.notas_capturadas)
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Total", total, delta=None)
    with col_s2:
        if total > 0:
            df_temp = pd.DataFrame(st.session_state.notas_capturadas)
            positivas = len(df_temp[df_temp['Informativo / Positivo/ Negativo'] == 'Positivo']) if 'Informativo / Positivo/ Negativo' in df_temp.columns else 0
            st.metric("Positivas", positivas)
    
    if st.button("🗑️ Limpiar todas las notas", use_container_width=True):
        st.session_state.notas_capturadas = []
        st.session_state.nota_actual = {}
        st.session_state.texto_seleccionado = ""
        st.rerun()
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size: 12px; color: #6c757d; text-align: center;">
        <p>💡 Tip: Selecciona texto del PDF,</p>
        <p>cópialo y pégalo en el campo</p>
        <p>de texto para asignarlo a un campo.</p>
    </div>
    """, unsafe_allow_html=True)

# ============== PROCESAR ARCHIVO ==============
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    
    if ext == "xlsx":
        try:
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.selectbox("Selecciona pestaña:", xls.sheet_names, key="sheet_select")
            df_existente = pd.read_excel(uploaded_file, sheet_name=sheet)
            st.success(f"✅ Excel cargado: {len(df_existente)} notas")
            if not df_existente.empty:
                for _, row in df_existente.iterrows():
                    nota = {col: row[col] for col in OFFICIAL_COLUMNS if col in df_existente.columns}
                    st.session_state.notas_capturadas.append(nota)
        except Exception as e:
            st.error(f"❌ Error: {e}")
    
    elif ext == "pdf":
        pdf_bytes = uploaded_file.getvalue()
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_filename = uploaded_file.name
        with st.spinner("Extrayendo texto del PDF..."):
            st.session_state.pdf_text = extract_text_from_pdf(pdf_bytes)
        st.success(f"✅ PDF cargado: {uploaded_file.name}")

# ============== TABS ==============
tab1, tab2, tab3, tab4 = st.tabs(["📄 Captura de Notas", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])

# ============== TAB 1: CAPTURA DE NOTAS ==============
with tab1:
    if st.session_state.pdf_bytes:
        
        # ====== PDF VIEWER ======
        st.markdown("""
        <div class="card">
            <div class="card-header">📄 Visualizador del PDF</div>
        """, unsafe_allow_html=True)
        
        view_option = st.radio(
            "Selecciona cómo ver el PDF:",
            ["📝 Ver texto extraído", "📄 Descargar y abrir PDF"],
            horizontal=True
        )
        
        if view_option == "📝 Ver texto extraído":
            if st.session_state.pdf_text:
                st.markdown("""
                <div style="font-size: 13px; color: #6c757d; margin-bottom: 10px;">
                    💡 Selecciona y copia el texto que necesites
                </div>
                """, unsafe_allow_html=True)
                st.markdown(
                    f'<div class="pdf-text-container">{st.session_state.pdf_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No se pudo extraer texto del PDF.")
                st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
        else:
            st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
            st.info("📌 Descarga el PDF, ábrelo en tu visor, selecciona y copia el texto que necesites.")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # ====== CAPTURA ======
        st.markdown("""
        <div class="card">
            <div class="card-header">📝 Captura de Texto</div>
        """, unsafe_allow_html=True)
        
        col_texto, col_botones = st.columns([1, 1.2])
        
        with col_texto:
            st.markdown("""
            <div style="font-size: 13px; color: #6c757d; margin-bottom: 10px;">
                📋 Pega aquí el texto que copiaste del PDF
            </div>
            """, unsafe_allow_html=True)
            
            texto_pegado = st.text_area(
                "",
                value=st.session_state.texto_seleccionado,
                height=120,
                placeholder="Ejemplo: 'RTP que fue transformado en Papamóvil...'",
                key="texto_pegado_input",
                label_visibility="collapsed"
            )
            
            if texto_pegado != st.session_state.texto_seleccionado:
                st.session_state.texto_seleccionado = texto_pegado
            
            # Campos asignados
            st.markdown("##### 📋 Campos asignados:")
            if st.session_state.nota_actual:
                for col, value in st.session_state.nota_actual.items():
                    if value:
                        display_name = FIELD_NAMES.get(col, col)
                        st.markdown(f'<div class="field-assigned">✅ {display_name}: {str(value)[:55]}...</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="field-empty">⬜ Ningún campo asignado aún</div>', unsafe_allow_html=True)
        
        with col_botones:
            st.markdown("##### 🎯 Asignar a campo")
            st.markdown('<div style="font-size: 12px; color: #6c757d; margin-bottom: 10px;">Presiona el botón del campo donde quieras guardar el texto</div>', unsafe_allow_html=True)
            
            # Botones en 3 columnas
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            AUTO_FIELDS = ['Año', '# Mes', 'Mes', 'Fecha ', 'Campaña', 'Informativo / Positivo/ Negativo']
            BUTTON_FIELDS = [col for col in OFFICIAL_COLUMNS if col not in AUTO_FIELDS]
            
            for idx, col_name in enumerate(BUTTON_FIELDS):
                col_idx = idx % 3
                target_col = [col_btn1, col_btn2, col_btn3][col_idx]
                display_name = FIELD_NAMES.get(col_name, col_name)
                
                with target_col:
                    if st.button(display_name, use_container_width=True, key=f"btn_{idx}"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.nota_actual[col_name] = st.session_state.texto_seleccionado.strip()
                            st.success(f"✅ Asignado a {display_name}")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # ====== CONFIGURACIÓN ======
        st.markdown("""
        <div class="card">
            <div class="card-header">⚙️ Configuración de la nota</div>
        """, unsafe_allow_html=True)
        
        col_config1, col_config2, col_config3, col_config4 = st.columns(4)
        
        with col_config1:
            st.markdown("**📅 Fecha**")
            
            fecha_val = st.date_input(
                "Fecha",
                value=datetime.strptime(st.session_state.fecha_editable, "%Y-%m-%d") if st.session_state.fecha_editable else datetime.now(),
                key="fecha_input",
                label_visibility="collapsed"
            )
            st.session_state.fecha_editable = fecha_val.strftime("%Y-%m-%d")
            st.session_state.nota_actual['Fecha '] = st.session_state.fecha_editable
            
            anio_val = st.number_input("Año", min_value=2020, max_value=2030, 
                                       value=int(st.session_state.anio_editable) if st.session_state.anio_editable else fecha_val.year,
                                       key="anio_input", label_visibility="collapsed")
            st.session_state.anio_editable = str(anio_val)
            st.session_state.nota_actual['Año'] = anio_val
            
            num_mes_val = st.number_input("# Mes", min_value=1, max_value=12,
                                          value=int(st.session_state.num_mes_editable) if st.session_state.num_mes_editable else fecha_val.month,
                                          key="num_mes_input", label_visibility="collapsed")
            st.session_state.num_mes_editable = str(num_mes_val)
            st.session_state.nota_actual['# Mes'] = num_mes_val
        
        with col_config2:
            st.markdown("**📆 Mes**")
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            mes_idx = meses.index(st.session_state.mes_editable) if st.session_state.mes_editable in meses else fecha_val.month - 1
            mes_seleccionado = st.selectbox("Mes", meses, index=mes_idx, key="mes_select", label_visibility="collapsed")
            st.session_state.mes_editable = mes_seleccionado
            st.session_state.nota_actual['Mes'] = mes_seleccionado
            
            st.markdown("**🎯 Relevancia**")
            relevancia = st.selectbox(
                "Relevancia",
                ["Sí", "No"],
                index=0 if st.session_state.relevancia_seleccionada == "Sí" else 1,
                key="select_relevancia",
                label_visibility="collapsed"
            )
            st.session_state.relevancia_seleccionada = relevancia
            st.session_state.nota_actual['RTP, ¿Es relevante en la nota?'] = relevancia
        
        with col_config3:
            st.markdown("**📊 Tono**")
            tono = st.selectbox(
                "Tono",
                ["Informativo", "Positivo", "Negativo"],
                index=["Informativo", "Positivo", "Negativo"].index(st.session_state.tono_seleccionado),
                key="select_tono",
                label_visibility="collapsed"
            )
            st.session_state.tono_seleccionado = tono
            st.session_state.nota_actual['Informativo / Positivo/ Negativo'] = tono
            
            st.markdown("**🏷️ Campaña**")
            campana = map_campana(tono)
            st.text_input("Campaña", value=campana, disabled=True, label_visibility="collapsed")
            st.session_state.nota_actual['Campaña'] = campana
        
        with col_config4:
            st.markdown("**🔗 Link**")
            link = st.session_state.nota_actual.get('LINK', '')
            if link:
                formatted_link = validate_and_format_link(link)
                if formatted_link:
                    st.markdown(f'<a href="{formatted_link}" target="_blank" style="display: inline-block; padding: 8px 16px; background: #e3f2fd; color: #0d47a1; border-radius: 8px; text-decoration: none; font-weight: 500;">🔗 Abrir link</a>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="link-error">⚠️ Link no válido</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color: #6c757d; font-size: 13px;">Sin link asignado</div>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # ====== BOTÓN GUARDAR ======
        st.markdown("""
        <div class="card" style="text-align: center;">
        """, unsafe_allow_html=True)
        
        col_guardar1, col_guardar2, col_guardar3 = st.columns([1, 2, 1])
        with col_guardar2:
            if st.button("💾 GUARDAR NOTA COMPLETA", use_container_width=True, key="btn_guardar_completa"):
                if st.session_state.nota_actual.get('Título de la nota'):
                    nota_completa = {}
                    for col in OFFICIAL_COLUMNS:
                        if col in ['Año', '# Mes', 'Mes', 'Fecha ']:
                            continue
                        if col == 'Campaña':
                            nota_completa[col] = map_campana(st.session_state.tono_seleccionado)
                        elif col == 'Informativo / Positivo/ Negativo':
                            nota_completa[col] = st.session_state.tono_seleccionado
                        elif col == 'RTP, ¿Es relevante en la nota?':
                            nota_completa[col] = st.session_state.relevancia_seleccionada
                        else:
                            value = st.session_state.nota_actual.get(col, '')
                            if col == 'LINK' and value:
                                formatted = validate_and_format_link(value)
                                nota_completa[col] = formatted if formatted else value
                            else:
                                nota_completa[col] = value
                    
                    nota_completa['Año'] = int(st.session_state.anio_editable)
                    nota_completa['# Mes'] = int(st.session_state.num_mes_editable)
                    nota_completa['Mes'] = st.session_state.mes_editable
                    nota_completa['Fecha '] = st.session_state.fecha_editable
                    
                    if not nota_completa.get('Autor'):
                        nota_completa['Autor'] = 'Redacción'
                    if not nota_completa.get('PUBLICACIÓN BOLETÍN'):
                        nota_completa['PUBLICACIÓN BOLETÍN'] = 'NO'
                    if not nota_completa.get('Tema de la nota'):
                        nota_completa['Tema de la nota'] = 'General'
                    
                    st.session_state.notas_capturadas.append(nota_completa)
                    st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada")
                    st.session_state.nota_actual = {}
                    st.session_state.texto_seleccionado = ""
                    st.rerun()
                else:
                    st.error("⚠️ El Título de la nota es obligatorio")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    else:
        st.markdown("""
        <div class="card" style="text-align: center; padding: 60px 20px;">
            <div style="font-size: 64px; margin-bottom: 20px;">📄</div>
            <h3 style="color: #1a1a2e;">Sube un archivo PDF para comenzar</h3>
            <p style="color: #6c757d; max-width: 500px; margin: 10px auto;">
                Carga un PDF en la barra lateral izquierda para extraer su texto 
                y comenzar a capturar notas.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ============== TAB 2: TABLA DE NOTAS ==============
with tab2:
    st.markdown("""
    <div class="card">
        <div class="card-header">📋 Tabla de Notas Capturadas</div>
    """, unsafe_allow_html=True)
    
    if st.session_state.notas_capturadas:
        df_show = pd.DataFrame(st.session_state.notas_capturadas)
        
        # Opciones de visualización
        col_opciones1, col_opciones2, col_opciones3 = st.columns([1, 1, 1])
        with col_opciones1:
            st.session_state.show_all_columns = st.toggle("📋 Mostrar todas las columnas", value=st.session_state.show_all_columns)
        
        with col_opciones2:
            height_option = st.selectbox("📏 Altura de la tabla", ["Pequeña (300px)", "Mediana (450px)", "Grande (600px)"], index=1)
            height_map = {"Pequeña (300px)": 300, "Mediana (450px)": 450, "Grande (600px)": 600}
            table_height = height_map[height_option]
        
        with col_opciones3:
            st.write("")  # Espaciador
        
        # Seleccionar columnas a mostrar
        if st.session_state.show_all_columns:
            columns_to_show = [col for col in OFFICIAL_COLUMNS if col in df_show.columns]
        else:
            columns_to_show = [col for col in TABLE_COLUMNS_DISPLAY if col in df_show.columns]
        
        df_display = df_show[columns_to_show].copy()
        df_display = df_display.fillna('')
        
        # Configurar columnas para data_editor
        column_config = {}
        for col in columns_to_show:
            if col == 'Año':
                column_config[col] = st.column_config.NumberColumn("Año", min_value=2020, max_value=2030, width="small")
            elif col == '# Mes':
                column_config[col] = st.column_config.NumberColumn("# Mes", min_value=1, max_value=12, width="small")
            elif col == 'Fecha ':
                column_config[col] = st.column_config.TextColumn("Fecha", width="small")
            elif col == 'Título de la nota':
                column_config[col] = st.column_config.TextColumn("Título", width="medium")
            elif col == 'RESUMEN  DE LA NOTA (RTP)':
                column_config[col] = st.column_config.TextColumn("Resumen", width="large")
            elif col == 'LINK':
                column_config[col] = st.column_config.TextColumn("Link", width="medium")
            elif col == 'Informativo / Positivo/ Negativo':
                column_config[col] = st.column_config.TextColumn("Tono", width="small")
            elif col == 'RTP, ¿Es relevante en la nota?':
                column_config[col] = st.column_config.TextColumn("Relevante", width="small")
            else:
                column_config[col] = st.column_config.TextColumn(FIELD_NAMES.get(col, col), width="medium")
        
        st.info("💡 Haz clic en cualquier celda para editarla. Los cambios se guardan automáticamente.")
        
        edited_df = st.data_editor(
            df_display,
            use_container_width=True,
            height=table_height,
            num_rows="dynamic",
            key="tabla_editable",
            column_config=column_config,
            hide_index=True,
        )
        
        # Actualizar datos
        if not edited_df.empty and len(edited_df) == len(st.session_state.notas_capturadas):
            for idx, row in edited_df.iterrows():
                if idx < len(st.session_state.notas_capturadas):
                    for col in columns_to_show:
                        if col in row and pd.notna(row[col]):
                            current_val = st.session_state.notas_capturadas[idx].get(col, '')
                            new_val = row[col]
                            if str(current_val) != str(new_val):
                                st.session_state.notas_capturadas[idx][col] = new_val
        
        # Botones de acción
        st.markdown("---")
        col_btn1, col_btn2, col_btn3, col_btn4 = st.columns(4)
        
        with col_btn1:
            if st.button("➕ Agregar fila", use_container_width=True):
                today = datetime.now()
                new_row = {col: '' for col in OFFICIAL_COLUMNS}
                new_row['Año'] = today.year
                new_row['# Mes'] = today.month
                new_row['Mes'] = today.strftime("%B").capitalize()
                new_row['Fecha '] = today.strftime("%Y-%m-%d")
                new_row['Campaña'] = 'RTP informa'
                new_row['Informativo / Positivo/ Negativo'] = 'Informativo'
                new_row['RTP, ¿Es relevante en la nota?'] = 'Sí'
                new_row['PUBLICACIÓN BOLETÍN'] = 'NO'
                new_row['Autor'] = 'Redacción'
                st.session_state.notas_capturadas.append(new_row)
                st.rerun()
        
        with col_btn2:
            if st.button("🗑️ Eliminar última", use_container_width=True):
                if st.session_state.notas_capturadas:
                    st.session_state.notas_capturadas.pop()
                    st.rerun()
                else:
                    st.warning("No hay filas para eliminar")
        
        with col_btn3:
            if st.button("🔄 Recargar", use_container_width=True):
                st.rerun()
        
        with col_btn4:
            if st.button("📋 Ver estadísticas", use_container_width=True):
                st.session_state.show_stats = not st.session_state.get('show_stats', False)
                st.rerun()
        
        # Estadísticas expandibles
        if st.session_state.get('show_stats', False):
            st.markdown("---")
            st.markdown("### 📊 Estadísticas")
            
            col_est1, col_est2, col_est3, col_est4, col_est5 = st.columns(5)
            col_est1.metric("Total Notas", len(df_show))
            
            if 'Informativo / Positivo/ Negativo' in df_show.columns:
                col_est2.metric("Positivas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Positivo']))
                col_est3.metric("Informativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Informativo']))
                col_est4.metric("Negativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Negativo']))
            
            if 'RTP, ¿Es relevante en la nota?' in df_show.columns:
                relevantes = len(df_show[df_show['RTP, ¿Es relevante en la nota?'] == 'Sí'])
                col_est5.metric("Relevantes", relevantes)
        
        # Contador de filas
        st.markdown(f"""
        <div style="text-align: right; font-size: 13px; color: #6c757d; padding: 10px 0;">
            Mostrando {len(df_show)} notas
        </div>
        """, unsafe_allow_html=True)
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📋</div>
            <h3 style="color: #1a1a2e;">No hay notas capturadas</h3>
            <p style="color: #6c757d;">Captura notas en la pestaña "Captura de Notas"</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============== TAB 3: GRÁFICAS ==============
with tab3:
    st.markdown("""
    <div class="card">
        <div class="card-header">📊 Análisis Gráfico</div>
    """, unsafe_allow_html=True)
    
    if st.session_state.notas_capturadas:
        df_graph = pd.DataFrame(st.session_state.notas_capturadas)
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            if 'Informativo / Positivo/ Negativo' in df_graph.columns:
                fig_tono = px.pie(
                    df_graph,
                    names='Informativo / Positivo/ Negativo',
                    title="Distribución por Tono",
                    color='Informativo / Positivo/ Negativo',
                    color_discrete_map={'Positivo': '#28a745', 'Informativo': '#ffc107', 'Negativo': '#dc3545'},
                    hole=0.4
                )
                fig_tono.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a2e')
                )
                st.plotly_chart(fig_tono, use_container_width=True)
        
        with col_g2:
            if 'Campaña' in df_graph.columns:
                df_graph['Campaña'] = df_graph['Campaña'].fillna('RTP informa')
                fig_campana = px.pie(
                    df_graph,
                    names='Campaña',
                    title="Distribución por Campaña",
                    color_discrete_sequence=['#007bff', '#6c757d']
                )
                fig_campana.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a2e')
                )
                st.plotly_chart(fig_campana, use_container_width=True)
        
        col_g3, col_g4 = st.columns(2)
        
        with col_g3:
            if 'RTP, ¿Es relevante en la nota?' in df_graph.columns:
                fig_relevancia = px.bar(
                    df_graph,
                    x='RTP, ¿Es relevante en la nota?',
                    title="Relevancia para RTP",
                    color='RTP, ¿Es relevante en la nota?',
                    color_discrete_map={'Sí': '#28a745', 'No': '#dc3545'}
                )
                fig_relevancia.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a2e')
                )
                st.plotly_chart(fig_relevancia, use_container_width=True)
        
        with col_g4:
            if 'Tema de la nota' in df_graph.columns:
                temas_counts = df_graph['Tema de la nota'].value_counts().reset_index()
                temas_counts.columns = ['Tema', 'Cantidad']
                fig_temas = px.bar(
                    temas_counts.head(10),
                    x='Tema',
                    y='Cantidad',
                    title="Top 10 Temas",
                    color='Cantidad',
                    color_continuous_scale='Blues'
                )
                fig_temas.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#1a1a2e'),
                    xaxis=dict(tickangle=45)
                )
                st.plotly_chart(fig_temas, use_container_width=True)
    else:
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📊</div>
            <h3 style="color: #1a1a2e;">No hay suficientes datos</h3>
            <p style="color: #6c757d;">Captura al menos una nota para ver gráficas</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============== TAB 4: EXPORTAR ==============
with tab4:
    st.markdown("""
    <div class="card">
        <div class="card-header">📥 Exportar a Excel</div>
    """, unsafe_allow_html=True)
    
    if st.session_state.notas_capturadas:
        df_export = pd.DataFrame(st.session_state.notas_capturadas)
        columns_to_show = [col for col in OFFICIAL_COLUMNS if col in df_export.columns]
        
        st.markdown("### Vista previa de datos a exportar")
        st.dataframe(df_export[columns_to_show].head(10), use_container_width=True)
        
        st.markdown("---")
        
        col_exp1, col_exp2, col_exp3 = st.columns([1, 2, 1])
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_export[columns_to_show].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
            
            st.download_button(
                label="📥 DESCARGAR EXCEL",
                data=output.getvalue(),
                file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="btn_descarga_grande"
            )
            st.caption(f"📊 {len(st.session_state.notas_capturadas)} notas listas para exportar")
        
        st.markdown("---")
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        col_r1.metric("Total Notas", len(df_export))
        col_r2.metric("Columnas", len(columns_to_show))
        col_r3.metric("Formato", "Excel (.xlsx)")
        col_r4.metric("Tamaño aprox.", f"{len(df_export) * 0.5:.0f} KB")
    
    else:
        st.markdown("""
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 48px; margin-bottom: 16px;">📥</div>
            <h3 style="color: #1a1a2e;">No hay notas para exportar</h3>
            <p style="color: #6c757d;">Captura notas primero en la pestaña "Captura de Notas"</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)

# ============== FOOTER ==============
st.markdown("""
<div style="text-align: center; padding: 20px 0; color: #6c757d; font-size: 13px; border-top: 1px solid #e9ecef; margin-top: 20px;">
    🚌 Monitoreo RTP - Sistema de Captura de Notas v2.0
</div>
""", unsafe_allow_html=True)