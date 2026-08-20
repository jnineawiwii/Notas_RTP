import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime

# Configuración de página
st.set_page_config(
    page_title="Monitoreo RTP - Captura de Notas",
    page_icon="🚌",
    layout="wide"
)

# Estilos visuales
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .campo-titulo { background-color: #cce5ff; border-left: 4px solid #007bff; padding: 8px; margin: 4px 0; }
    .campo-resumen { background-color: #d4edda; border-left: 4px solid #28a745; padding: 8px; margin: 4px 0; }
    .campo-medio { background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 8px; margin: 4px 0; }
    .campo-autor { background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 8px; margin: 4px 0; }
    .campo-link { background-color: #d1ecf1; border-left: 4px solid #17a2b8; padding: 8px; margin: 4px 0; }
    .campo-tema { background-color: #e8d5f5; border-left: 4px solid #6f42c1; padding: 8px; margin: 4px 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px 4px 0px 0px; padding: 10px 16px; background-color: #f0f2f6; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Captura de Notas - Monitoreo RTP")
st.caption("Selecciona el texto del PDF y asígnalo a cada campo de la nota")

# Columnas oficiales (18 columnas)
OFFICIAL_COLUMNS = [
    'Año', '# Mes', 'Mes', 'Fecha ',
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

def clean_sentiment(val):
    if pd.isna(val):
        return "Informativo"
    v = str(val).strip().capitalize()
    if "Posit" in v:
        return "Positivo"
    if "Negat" in v:
        return "Negativo"
    return "Informativo"

def map_campana(sentiment):
    if sentiment == "Positivo":
        return "RTP avanza"
    return "RTP informa"

def extract_pdf_text(pdf_file):
    """Extrae todo el texto del PDF"""
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
    return full_text

def split_into_notes(text):
    """Divide el texto en notas individuales"""
    notes = []
    
    # Método 1: Buscar "MEDIOS:" como separador
    sections = re.split(r'(?=\n\s*MEDIOS?:)', text)
    
    if len(sections) > 1:
        for section in sections:
            if len(section.strip()) > 50:
                notes.append(section.strip())
    else:
        # Método 2: Dividir por líneas en blanco
        sections = re.split(r'\n\s*\n', text)
        for section in sections:
            if len(section.strip()) > 100:
                notes.append(section.strip())
    
    # Si no hay secciones, tratar todo como una nota
    if not notes and text.strip():
        notes = [text.strip()]
    
    return notes

def auto_detect_fields(text):
    """Detecta automáticamente campos del texto"""
    fields = {}
    lines = text.split('\n')
    
    # Buscar título (primera línea significativa)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Saltar encabezados de sección
        if any(x in line.upper() for x in ['SÍNTESIS INFORMATIVA', 'NOTAS DE MOVILIDAD', 'RED DE TRANSPORTE']):
            continue
        if len(line) < 100 and (line.isupper() or (line[0].isupper() and not line.endswith(('.', ':')))):
            fields['titulo'] = line
            break
    
    # Buscar medio
    media_match = re.search(r'MEDIOS?:\s*(.+?)(?:\s*https?://|\s*$|\n)', text, re.IGNORECASE)
    if media_match:
        fields['medio'] = media_match.group(1).strip()
    
    # Buscar autor
    autor_match = re.search(r'(?:Autor|Por|Redacción)[:\s]+(.+?)(?:\s*$|\n)', text, re.IGNORECASE)
    if autor_match:
        fields['autor'] = autor_match.group(1).strip()
    
    # Buscar link
    link_match = re.search(r'https?://[^\s\n]+', text)
    if link_match:
        fields['link'] = link_match.group(0)
    
    # Buscar resumen (el resto del texto después del título)
    if fields.get('titulo'):
        text_parts = text.split(fields['titulo'])
        if len(text_parts) > 1:
            content = text_parts[1].strip()
            if len(content) > 500:
                content = content[:500] + "..."
            fields['resumen'] = content
    else:
        fields['resumen'] = text[:500]
    
    # Detectar tono
    text_lower = text.lower()
    if 'positivo' in text_lower or 'avanza' in text_lower or 'éxito' in text_lower:
        fields['tono'] = 'Positivo'
    elif 'negativo' in text_lower or 'problema' in text_lower or 'falla' in text_lower or 'queja' in text_lower:
        fields['tono'] = 'Negativo'
    else:
        fields['tono'] = 'Informativo'
    
    # Detectar relevancia
    fields['relevante'] = 'Sí' if 'rtp' in text_lower else 'No'
    
    # Detectar tema (por palabras clave)
    temas = {
        'Movilidad CDMX': ['movilidad', 'transporte', 'ruta', 'recorrido', 'metro', 'metrobús'],
        'Unidades de RTP': ['unidad', 'autobús', 'flota', 'camión', 'vehículo'],
        'Accidentes': ['accidente', 'choque', 'atropell', 'siniestro', 'colisión'],
        'Sindicato': ['sindicato', 'trabajador', 'huelga', 'paro', 'protesta'],
        'Mantenimiento': ['mantenimiento', 'reparación', 'falla', 'avería', 'daño'],
        'Seguridad': ['seguridad', 'vigilancia', 'protección', 'robo'],
        'Nuevas rutas': ['nueva ruta', 'nuevo tramo', 'ampliación', 'prueba piloto'],
        'Horarios': ['horario', 'puente', 'festivo', 'cierre'],
        'Tarifas': ['tarifa', 'precio', 'costo', 'peso', 'gratuito']
    }
    tema_detectado = 'General'
    for tema, keywords in temas.items():
        if any(k in text_lower for k in keywords):
            tema_detectado = tema
            break
    
    fields['tema'] = tema_detectado
    
    # Detectar tipo de medio
    if any(x in text_lower for x in ['twitter', 'x.com', 'facebook', 'youtube', 'instagram']):
        fields['tipo_medio'] = 'OTROS (Twitter, Facebook, You Tube, etc.).'
    elif any(x in text_lower for x in ['radio', 'fm']):
        fields['tipo_medio'] = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
    elif any(x in text_lower for x in ['tv', 'canal', 'televisa', 'foro tv']):
        fields['tipo_medio'] = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
    elif any(x in text_lower for x in ['.com', 'portal', 'digital', 'noticias']):
        fields['tipo_medio'] = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
    else:
        fields['tipo_medio'] = 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *'
    
    return fields

def get_detected_value(field_name, detected_fields):
    """Obtiene el valor detectado para un campo"""
    mapping = {
        'Título de la nota': 'titulo',
        'RESUMEN  DE LA NOTA (RTP)': 'resumen',
        'Autor': 'autor',
        'LINK': 'link',
        'Tema de la nota': 'tema',
        'Informativo / Positivo/ Negativo': 'tono',
        'RTP, ¿Es relevante en la nota?': 'relevante'
    }
    if field_name in mapping and mapping[field_name] in detected_fields:
        return detected_fields[mapping[field_name]]
    return ""

# --- INICIALIZAR SESSION STATE ---
if 'notas_capturadas' not in st.session_state:
    st.session_state.notas_capturadas = []
if 'nota_actual' not in st.session_state:
    st.session_state.nota_actual = {}
if 'indice_nota' not in st.session_state:
    st.session_state.indice_nota = 0
if 'notas_extraidas' not in st.session_state:
    st.session_state.notas_extraidas = []

# --- SIDEBAR ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

st.sidebar.header("📊 Notas Capturadas")
st.sidebar.metric("Total Notas", len(st.session_state.notas_capturadas))

if st.sidebar.button("🗑️ Limpiar todas las notas"):
    st.session_state.notas_capturadas = []
    st.session_state.nota_actual = {}
    st.rerun()

# --- PROCESAR ARCHIVO ---
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    
    if ext == "xlsx":
        try:
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.sidebar.selectbox("Selecciona pestaña:", xls.sheet_names)
            df_existente = pd.read_excel(uploaded_file, sheet_name=sheet)
            st.sidebar.success(f"✅ Excel cargado: {len(df_existente)} notas")
            
            # Cargar notas existentes al session state
            if not df_existente.empty:
                for _, row in df_existente.iterrows():
                    nota = {col: row[col] for col in OFFICIAL_COLUMNS if col in df_existente.columns}
                    st.session_state.notas_capturadas.append(nota)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    elif ext == "pdf":
        with st.spinner("📄 Extrayendo texto del PDF..."):
            full_text = extract_pdf_text(uploaded_file)
        
        if full_text.strip():
            st.sidebar.success(f"✅ PDF procesado: {len(full_text)} caracteres")
            
            # Dividir en notas
            st.session_state.notas_extraidas = split_into_notes(full_text)
            st.sidebar.info(f"📊 {len(st.session_state.notas_extraidas)} notas encontradas")
            
            if st.session_state.notas_extraidas and st.session_state.indice_nota < len(st.session_state.notas_extraidas):
                # Auto detectar campos para la primera nota
                texto_nota = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos_detectados = auto_detect_fields(texto_nota)
                st.session_state.nota_actual = campos_detectados
                st.session_state.nota_actual['texto_original'] = texto_nota

# --- INTERFAZ PRINCIPAL ---
st.subheader("✏️ Captura de Nota")

# Mostrar progreso
if st.session_state.notas_extraidas:
    total_notas = len(st.session_state.notas_extraidas)
    actual = st.session_state.indice_nota + 1
    st.progress(actual / total_notas if total_notas > 0 else 0)
    st.caption(f"Nota {actual} de {total_notas}")

# Crear pestañas
tab_texto, tab_campos, tab_previa = st.tabs(["📄 Texto Original", "📝 Campos de la Nota", "📋 Vista Previa"])

# --- TAB 1: TEXTO ORIGINAL ---
with tab_texto:
    if st.session_state.nota_actual.get('texto_original'):
        st.markdown("### Texto extraído de la nota")
        st.text_area(
            "Texto original",
            value=st.session_state.nota_actual['texto_original'],
            height=400,
            key="texto_original_display",
            disabled=True
        )
        
        # Botones de navegación
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1:
            if st.button("⬅️ Anterior") and st.session_state.indice_nota > 0:
                st.session_state.indice_nota -= 1
                texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos = auto_detect_fields(texto)
                campos['texto_original'] = texto
                st.session_state.nota_actual = campos
                st.rerun()
        with col2:
            if st.button("➡️ Siguiente") and st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                st.session_state.indice_nota += 1
                texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos = auto_detect_fields(texto)
                campos['texto_original'] = texto
                st.session_state.nota_actual = campos
                st.rerun()
        with col3:
            if st.button("🔄 Detectar automático"):
                if st.session_state.nota_actual.get('texto_original'):
                    campos = auto_detect_fields(st.session_state.nota_actual['texto_original'])
                    campos['texto_original'] = st.session_state.nota_actual['texto_original']
                    st.session_state.nota_actual = campos
                    st.rerun()
    else:
        st.info("No hay texto cargado. Sube un PDF o selecciona una nota.")

# --- TAB 2: CAMPOS DE LA NOTA ---
with tab_campos:
    st.markdown("### Asigna el texto a cada campo")
    
    # Usar un formulario para evitar recargas constantes
    with st.form(key="form_nota"):
        # Dividir en columnas para mejor organización
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("#### 📋 Información básica")
            
            # Título
            titulo = st.text_area(
                "📌 Título de la nota",
                value=get_detected_value('Título de la nota', st.session_state.nota_actual),
                height=60,
                key="campo_titulo",
                placeholder="Pega el título aquí o usa la detección automática"
            )
            
            # Tema
            tema = st.text_input(
                "📂 Tema de la nota",
                value=get_detected_value('Tema de la nota', st.session_state.nota_actual),
                key="campo_tema",
                placeholder="Ej: Movilidad CDMX, Accidentes, Nuevas rutas..."
            )
            
            # Tono
            tono = st.selectbox(
                "🎯 Tono de la nota",
                ["Informativo", "Positivo", "Negativo"],
                index=["Informativo", "Positivo", "Negativo"].index(
                    get_detected_value('Informativo / Positivo/ Negativo', st.session_state.nota_actual) or "Informativo"
                ),
                key="campo_tono"
            )
            
            # Relevancia
            relevancia = st.selectbox(
                "🎯 ¿Es relevante para RTP?",
                ["Sí", "No"],
                index=0 if get_detected_value('RTP, ¿Es relevante en la nota?', st.session_state.nota_actual) == "Sí" else 1,
                key="campo_relevancia"
            )
        
        with col_b:
            st.markdown("#### 📎 Información del medio")
            
            # Medio
            medio = st.text_input(
                "📰 Medio de comunicación",
                value=get_detected_value('Medio', st.session_state.nota_actual),
                key="campo_medio",
                placeholder="Ej: El Universal, Reforma, Milenio..."
            )
            
            # Autor
            autor = st.text_input(
                "✍️ Autor",
                value=get_detected_value('Autor', st.session_state.nota_actual),
                key="campo_autor",
                placeholder="Nombre del autor o Redacción"
            )
            
            # Link
            link = st.text_input(
                "🔗 LINK",
                value=get_detected_value('LINK', st.session_state.nota_actual),
                key="campo_link",
                placeholder="https://..."
            )
            
            # Tipo de medio (radio, tv, digital, impreso, otros)
            tipo_medio = st.selectbox(
                "📻 Tipo de medio",
                [
                    "MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *",
                    "MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *",
                    "MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ",
                    "MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *",
                    "OTROS (Twitter, Facebook, You Tube, etc.)."
                ],
                index=0,
                key="campo_tipo_medio"
            )
        
        # Resumen - Ancho completo
        st.markdown("#### 📝 Resumen de la nota")
        resumen = st.text_area(
            "RESUMEN DE LA NOTA (RTP)",
            value=get_detected_value('RESUMEN  DE LA NOTA (RTP)', st.session_state.nota_actual),
            height=150,
            key="campo_resumen",
            placeholder="Pega el resumen de la nota aquí"
        )
        
        # Botones de acción
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
        
        with col_btn1:
            submitted = st.form_submit_button("💾 Guardar Nota", use_container_width=True)
        
        with col_btn2:
            if st.form_submit_button("⏭️ Guardar y Siguiente", use_container_width=True):
                submitted = True
                avanzar = True
        
        with col_btn3:
            if st.form_submit_button("❌ Descartar", use_container_width=True):
                st.session_state.nota_actual = {}
                st.rerun()
        
        # Procesar guardado
        if submitted:
            if titulo.strip():
                # Crear registro completo
                today = datetime.now()
                nota_completa = {
                    'Año': today.year,
                    '# Mes': today.month,
                    'Mes': today.strftime("%B").capitalize(),
                    'Fecha ': today.strftime("%Y-%m-%d"),
                    'Título de la nota': titulo.strip(),
                    'RTP, ¿Es relevante en la nota?': relevancia,
                    'Tema de la nota': tema.strip() or 'General',
                    'Campaña': map_campana(tono),
                    'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ' else None,
                    'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *' else None,
                    'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if tipo_medio == 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *' else None,
                    'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if tipo_medio == 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *' else None,
                    'OTROS (Twitter, Facebook, You Tube, etc.).': medio if tipo_medio == 'OTROS (Twitter, Facebook, You Tube, etc.).' else None,
                    'Informativo / Positivo/ Negativo': tono,
                    'LINK': link.strip(),
                    'Autor': autor.strip() or 'Redacción',
                    'PUBLICACIÓN BOLETÍN': 'NO',
                    'RESUMEN  DE LA NOTA (RTP)': resumen.strip()
                }
                
                st.session_state.notas_capturadas.append(nota_completa)
                st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada correctamente")
                
                # Avanzar a la siguiente nota
                if st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                    st.session_state.indice_nota += 1
                    texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                    campos = auto_detect_fields(texto)
                    campos['texto_original'] = texto
                    st.session_state.nota_actual = campos
                else:
                    st.session_state.nota_actual = {}
                    st.info("🎉 ¡Todas las notas han sido procesadas!")
                
                st.rerun()
            else:
                st.error("⚠️ El título es obligatorio para guardar la nota")

# --- TAB 3: VISTA PREVIA ---
with tab_previa:
    if st.session_state.notas_capturadas:
        st.markdown("### 📋 Notas capturadas")
        df_preview = pd.DataFrame(st.session_state.notas_capturadas)
        st.dataframe(df_preview[OFFICIAL_COLUMNS], use_container_width=True, height=400)
        
        # Exportar
        st.markdown("### 📥 Exportar datos")
        
        col_exp1, col_exp2 = st.columns(2)
        
        with col_exp1:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_preview[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
            
            st.download_button(
                label="📥 Descargar Excel",
                data=output.getvalue(),
                file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col_exp2:
            if st.button("🗑️ Limpiar todas", use_container_width=True):
                st.session_state.notas_capturadas = []
                st.rerun()
    else:
        st.info("No hay notas capturadas aún. Usa la pestaña 'Campos de la Nota' para capturar.")

# --- INSTRUCCIONES ---
with st.expander("📖 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    ### 📊 Sistema de Captura de Notas RTP
    
    **1. Carga un archivo:**
    - **PDF**: Sube una síntesis informativa para extraer notas automáticamente
    - **Excel**: Carga un archivo existente para continuar trabajando
    
    **2. Navega entre notas:**
    - Usa los botones **Anterior/Siguiente** para moverte entre notas
    - La detección automática intenta llenar los campos por ti
    
    **3. Asigna los campos:**
    - **Título**: El encabezado de la nota
    - **Tema**: Clasifica la nota (Movilidad, Accidentes, etc.)
    - **Tono**: Positivo, Negativo o Informativo
    - **Relevancia**: ¿Habla sobre RTP?
    - **Medio/Autor/Link**: Información de la fuente
    - **Resumen**: El contenido de la nota
    
    **4. Guarda la nota:**
    - **Guardar Nota**: Guarda la nota actual
    - **Guardar y Siguiente**: Guarda y pasa a la siguiente nota
    
    **5. Exporta:**
    - Descarga todas las notas capturadas en formato Excel
    - El archivo mantiene la estructura exacta de la plantilla RTP
    """)