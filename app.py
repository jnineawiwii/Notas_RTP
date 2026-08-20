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

# Estilos visuales mejorados con colores
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    
    /* Campos con colores */
    .campo-titulo { 
        background-color: #cce5ff; 
        border-left: 5px solid #007bff; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #004085;
    }
    .campo-titulo span { color: #007bff; font-weight: normal; }
    
    .campo-resumen { 
        background-color: #d4edda; 
        border-left: 5px solid #28a745; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #155724;
    }
    .campo-resumen span { color: #28a745; font-weight: normal; }
    
    .campo-medio { 
        background-color: #fff3cd; 
        border-left: 5px solid #ffc107; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #856404;
    }
    .campo-medio span { color: #856404; font-weight: normal; }
    
    .campo-autor { 
        background-color: #f8d7da; 
        border-left: 5px solid #dc3545; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #721c24;
    }
    .campo-autor span { color: #dc3545; font-weight: normal; }
    
    .campo-link { 
        background-color: #d1ecf1; 
        border-left: 5px solid #17a2b8; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #0c5460;
    }
    .campo-link a { color: #17a2b8; text-decoration: underline; font-weight: normal; }
    .campo-link a:hover { color: #0d6efd; }
    
    .campo-tema { 
        background-color: #e8d5f5; 
        border-left: 5px solid #6f42c1; 
        padding: 10px 15px; 
        margin: 8px 0; 
        border-radius: 4px;
        font-weight: bold;
        color: #3d1a6e;
    }
    .campo-tema span { color: #6f42c1; font-weight: normal; }
    
    .texto-extraido {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.8;
        max-height: 400px;
        overflow-y: auto;
        white-space: pre-wrap;
        user-select: text;
    }
    
    .texto-extraido .hl-titulo { background-color: #cce5ff; padding: 2px 6px; border-radius: 3px; border: 2px solid #007bff; }
    .texto-extraido .hl-resumen { background-color: #d4edda; padding: 2px 6px; border-radius: 3px; border: 2px solid #28a745; }
    .texto-extraido .hl-medio { background-color: #fff3cd; padding: 2px 6px; border-radius: 3px; border: 2px solid #ffc107; }
    .texto-extraido .hl-autor { background-color: #f8d7da; padding: 2px 6px; border-radius: 3px; border: 2px solid #dc3545; }
    .texto-extraido .hl-link { background-color: #d1ecf1; padding: 2px 6px; border-radius: 3px; border: 2px solid #17a2b8; }
    .texto-extraido .hl-tema { background-color: #e8d5f5; padding: 2px 6px; border-radius: 3px; border: 2px solid #6f42c1; }
    
    .leyenda-colores {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        padding: 10px;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 10px 0;
        border: 1px solid #dee2e6;
    }
    .leyenda-item {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13px;
    }
    .leyenda-color {
        width: 20px;
        height: 20px;
        border-radius: 4px;
        border: 1px solid #ccc;
    }
    
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { 
        border-radius: 8px 8px 0px 0px; 
        padding: 12px 20px; 
        background-color: #f0f2f6;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #007bff;
        color: white;
    }
    
    .btn-descarga-grande {
        background-color: #28a745;
        color: white;
        border: none;
        padding: 20px 40px;
        font-size: 24px;
        font-weight: bold;
        border-radius: 12px;
        cursor: pointer;
        width: 100%;
        transition: all 0.3s;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .btn-descarga-grande:hover {
        background-color: #218838;
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Captura de Notas - Monitoreo RTP")
st.caption("Selecciona texto del PDF y asígnalo a cada campo de la nota")

# Columnas oficiales
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
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
    return full_text

def split_into_notes(text):
    notes = []
    sections = re.split(r'(?=\n\s*MEDIOS?:)', text)
    if len(sections) > 1:
        for section in sections:
            if len(section.strip()) > 50:
                notes.append(section.strip())
    else:
        sections = re.split(r'\n\s*\n', text)
        for section in sections:
            if len(section.strip()) > 100:
                notes.append(section.strip())
    if not notes and text.strip():
        notes = [text.strip()]
    return notes

def auto_detect_fields(text):
    fields = {'texto_original': text}
    lines = text.split('\n')
    
    # Buscar título
    for line in lines:
        line = line.strip()
        if not line:
            continue
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
    
    # Resumen
    if fields.get('titulo'):
        text_parts = text.split(fields['titulo'])
        if len(text_parts) > 1:
            content = text_parts[1].strip()
            if len(content) > 500:
                content = content[:500] + "..."
            fields['resumen'] = content
    else:
        fields['resumen'] = text[:500]
    
    # Tono
    text_lower = text.lower()
    if 'positivo' in text_lower or 'avanza' in text_lower or 'éxito' in text_lower:
        fields['tono'] = 'Positivo'
    elif 'negativo' in text_lower or 'problema' in text_lower or 'falla' in text_lower:
        fields['tono'] = 'Negativo'
    else:
        fields['tono'] = 'Informativo'
    
    fields['relevante'] = 'Sí' if 'rtp' in text_lower else 'No'
    
    # Tema
    temas = {
        'Movilidad CDMX': ['movilidad', 'transporte', 'ruta', 'recorrido', 'metro'],
        'Unidades de RTP': ['unidad', 'autobús', 'flota', 'camión'],
        'Accidentes': ['accidente', 'choque', 'atropell', 'siniestro'],
        'Sindicato': ['sindicato', 'trabajador', 'huelga', 'paro'],
        'Mantenimiento': ['mantenimiento', 'reparación', 'falla', 'avería'],
        'Nuevas rutas': ['nueva ruta', 'nuevo tramo', 'ampliación', 'prueba piloto'],
        'Horarios': ['horario', 'puente', 'festivo', 'cierre']
    }
    tema_detectado = 'General'
    for tema, keywords in temas.items():
        if any(k in text_lower for k in keywords):
            tema_detectado = tema
            break
    fields['tema'] = tema_detectado
    
    # Tipo de medio
    if any(x in text_lower for x in ['twitter', 'x.com', 'facebook', 'youtube']):
        fields['tipo_medio'] = 'OTROS (Twitter, Facebook, You Tube, etc.).'
    elif any(x in text_lower for x in ['radio', 'fm']):
        fields['tipo_medio'] = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
    elif any(x in text_lower for x in ['tv', 'canal', 'televisa']):
        fields['tipo_medio'] = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
    elif any(x in text_lower for x in ['.com', 'portal', 'digital']):
        fields['tipo_medio'] = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
    else:
        fields['tipo_medio'] = 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *'
    
    return fields

def highlight_selected_text(text, selections):
    """Resalta el texto seleccionado con colores"""
    if not text:
        return text
    
    highlighted = text
    # Ordenar por longitud (mayor a menor)
    sorted_selections = sorted(selections, key=lambda x: len(x['text']), reverse=True)
    
    for sel in sorted_selections:
        if sel['text'] in highlighted:
            color_class = sel.get('class', 'hl-resumen')
            highlighted = highlighted.replace(sel['text'], f'<span class="{color_class}">{sel["text"]}</span>')
    
    return highlighted

# --- INICIALIZAR SESSION STATE ---
if 'notas_capturadas' not in st.session_state:
    st.session_state.notas_capturadas = []
if 'nota_actual' not in st.session_state:
    st.session_state.nota_actual = {}
if 'indice_nota' not in st.session_state:
    st.session_state.indice_nota = 0
if 'notas_extraidas' not in st.session_state:
    st.session_state.notas_extraidas = []
if 'selecciones' not in st.session_state:
    st.session_state.selecciones = []
if 'modo_seleccion' not in st.session_state:
    st.session_state.modo_seleccion = 'Título'

# --- SIDEBAR ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

st.sidebar.header("📊 Notas Capturadas")
st.sidebar.metric("Total Notas", len(st.session_state.notas_capturadas))

if st.sidebar.button("🗑️ Limpiar todas las notas"):
    st.session_state.notas_capturadas = []
    st.session_state.nota_actual = {}
    st.session_state.selecciones = []
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
            st.session_state.notas_extraidas = split_into_notes(full_text)
            st.sidebar.info(f"📊 {len(st.session_state.notas_extraidas)} notas encontradas")
            
            if st.session_state.notas_extraidas and st.session_state.indice_nota < len(st.session_state.notas_extraidas):
                texto_nota = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos = auto_detect_fields(texto_nota)
                campos['texto_original'] = texto_nota
                st.session_state.nota_actual = campos
                st.session_state.selecciones = []

# --- INTERFAZ PRINCIPAL ---
st.subheader("✏️ Captura de Nota")

# Progreso
if st.session_state.notas_extraidas:
    total_notas = len(st.session_state.notas_extraidas)
    actual = st.session_state.indice_nota + 1
    st.progress(actual / total_notas if total_notas > 0 else 0)
    st.caption(f"Nota {actual} de {total_notas}")

# --- COLUMNAS: TEXTO Y SELECCIÓN ---
if st.session_state.nota_actual.get('texto_original'):
    col_texto, col_seleccion = st.columns([2, 1])
    
    with col_texto:
        st.markdown("### 📄 Texto extraído del PDF")
        st.markdown("**💡 Instrucción:** Selecciona cualquier parte del texto, elige a qué campo pertenece y presiona 'Aplicar Selección'")
        
        # Leyenda de colores
        st.markdown("""
        <div class="leyenda-colores">
            <div class="leyenda-item"><div class="leyenda-color" style="background:#cce5ff;border-color:#007bff;"></div> Título</div>
            <div class="leyenda-item"><div class="leyenda-color" style="background:#d4edda;border-color:#28a745;"></div> Resumen</div>
            <div class="leyenda-item"><div class="leyenda-color" style="background:#fff3cd;border-color:#ffc107;"></div> Medio</div>
            <div class="leyenda-item"><div class="leyenda-color" style="background:#f8d7da;border-color:#dc3545;"></div> Autor</div>
            <div class="leyenda-item"><div class="leyenda-color" style="background:#d1ecf1;border-color:#17a2b8;"></div> Link</div>
            <div class="leyenda-item"><div class="leyenda-color" style="background:#e8d5f5;border-color:#6f42c1;"></div> Tema</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Mostrar texto con resaltados
        texto_mostrar = st.session_state.nota_actual['texto_original']
        if st.session_state.selecciones:
            texto_mostrar = highlight_selected_text(texto_mostrar, st.session_state.selecciones)
        
        st.markdown(f'<div class="texto-extraido">{texto_mostrar}</div>', unsafe_allow_html=True)
        
        # Botones de navegación
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1:
            if st.button("⬅️ Anterior", use_container_width=True) and st.session_state.indice_nota > 0:
                st.session_state.indice_nota -= 1
                texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos = auto_detect_fields(texto)
                campos['texto_original'] = texto
                st.session_state.nota_actual = campos
                st.session_state.selecciones = []
                st.rerun()
        with col2:
            if st.button("➡️ Siguiente", use_container_width=True) and st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                st.session_state.indice_nota += 1
                texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                campos = auto_detect_fields(texto)
                campos['texto_original'] = texto
                st.session_state.nota_actual = campos
                st.session_state.selecciones = []
                st.rerun()
        with col3:
            if st.button("🔄 Auto-detectar", use_container_width=True):
                if st.session_state.nota_actual.get('texto_original'):
                    campos = auto_detect_fields(st.session_state.nota_actual['texto_original'])
                    campos['texto_original'] = st.session_state.nota_actual['texto_original']
                    st.session_state.nota_actual = campos
                    st.session_state.selecciones = []
                    st.rerun()
    
    with col_seleccion:
        st.markdown("### ✏️ Asignar texto seleccionado")
        
        # Campo de texto para pegar lo seleccionado
        texto_seleccionado = st.text_area(
            "📝 Texto seleccionado",
            value="",
            height=100,
            placeholder="Pega aquí el texto que seleccionaste del PDF",
            key="texto_seleccionado_input"
        )
        
        # Selector de campo
        campo_destino = st.selectbox(
            "🎯 Asignar a:",
            [
                "Título de la nota",
                "Resumen de la nota",
                "Medio de comunicación",
                "Autor",
                "Link",
                "Tema de la nota"
            ],
            key="campo_destino"
        )
        
        # Mapa de clases de color
        color_map = {
            "Título de la nota": "hl-titulo",
            "Resumen de la nota": "hl-resumen",
            "Medio de comunicación": "hl-medio",
            "Autor": "hl-autor",
            "Link": "hl-link",
            "Tema de la nota": "hl-tema"
        }
        
        # Mapa de campos
        field_map = {
            "Título de la nota": "titulo",
            "Resumen de la nota": "resumen",
            "Medio de comunicación": "medio",
            "Autor": "autor",
            "Link": "link",
            "Tema de la nota": "tema"
        }
        
        if st.button("✅ Aplicar Selección", use_container_width=True):
            if texto_seleccionado.strip():
                # Guardar selección
                st.session_state.selecciones.append({
                    'text': texto_seleccionado.strip(),
                    'class': color_map[campo_destino],
                    'campo': campo_destino
                })
                # Actualizar campo en nota_actual
                campo_key = field_map[campo_destino]
                st.session_state.nota_actual[campo_key] = texto_seleccionado.strip()
                st.success(f"✅ Texto asignado a '{campo_destino}'")
                # Limpiar el campo de texto
                st.rerun()
            else:
                st.warning("⚠️ Por favor, pega un texto para asignar")
        
        # Mostrar selecciones actuales
        if st.session_state.selecciones:
            st.markdown("### 📋 Selecciones asignadas")
            for i, sel in enumerate(st.session_state.selecciones):
                st.markdown(
                    f'<div style="background:#f8f9fa;padding:8px;margin:4px 0;border-radius:4px;border-left:4px solid {{
                        "hl-titulo":"#007bff",
                        "hl-resumen":"#28a745",
                        "hl-medio":"#ffc107",
                        "hl-autor":"#dc3545",
                        "hl-link":"#17a2b8",
                        "hl-tema":"#6f42c1"
                    }}[sel["class"]];">'
                    f'<strong>{sel["campo"]}:</strong> {sel["text"][:50]}{"..." if len(sel["text"])>50 else ""}'
                    f' <button onclick="alert(\'Eliminar selección\')" style="background:#dc3545;color:white;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;">✕</button>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                
            if st.button("🗑️ Limpiar selecciones", use_container_width=True):
                st.session_state.selecciones = []
                st.rerun()

# --- TAB: CAMPOS DE LA NOTA (vista consolidada) ---
st.markdown("---")
st.subheader("📋 Campos de la nota (completos)")

with st.form(key="form_nota_completa"):
    # Mostrar todos los campos con sus valores
    col_a, col_b = st.columns(2)
    
    with col_a:
        # Título - AZUL
        st.markdown('<div class="campo-titulo">📌 TÍTULO DE LA NOTA *</div>', unsafe_allow_html=True)
        titulo = st.text_area(
            "",
            value=st.session_state.nota_actual.get('titulo', ''),
            height=60,
            key="form_titulo",
            label_visibility="collapsed"
        )
        
        # Tema - MORADO
        st.markdown('<div class="campo-tema">📂 TEMA DE LA NOTA</div>', unsafe_allow_html=True)
        tema = st.text_input(
            "",
            value=st.session_state.nota_actual.get('tema', ''),
            key="form_tema",
            label_visibility="collapsed"
        )
        
        # Tono
        st.markdown('<div class="campo-medio">🎯 TONO</div>', unsafe_allow_html=True)
        tono = st.selectbox(
            "",
            ["Informativo", "Positivo", "Negativo"],
            index=["Informativo", "Positivo", "Negativo"].index(st.session_state.nota_actual.get('tono', 'Informativo')),
            key="form_tono",
            label_visibility="collapsed"
        )
        
        # Relevancia
        st.markdown('<div class="campo-medio">🎯 RELEVANTE PARA RTP</div>', unsafe_allow_html=True)
        relevancia = st.selectbox(
            "",
            ["Sí", "No"],
            index=0 if st.session_state.nota_actual.get('relevante', 'Sí') == "Sí" else 1,
            key="form_relevancia",
            label_visibility="collapsed"
        )
    
    with col_b:
        # Medio - AMARILLO
        st.markdown('<div class="campo-medio">📰 MEDIO</div>', unsafe_allow_html=True)
        medio = st.text_input(
            "",
            value=st.session_state.nota_actual.get('medio', ''),
            key="form_medio",
            label_visibility="collapsed"
        )
        
        # Tipo de medio
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
            key="form_tipo_medio"
        )
        
        # Autor - ROJO
        st.markdown('<div class="campo-autor">✍️ AUTOR</div>', unsafe_allow_html=True)
        autor = st.text_input(
            "",
            value=st.session_state.nota_actual.get('autor', ''),
            key="form_autor",
            label_visibility="collapsed"
        )
        
        # Link - CELESTE
        st.markdown('<div class="campo-link">🔗 LINK</div>', unsafe_allow_html=True)
        link = st.text_input(
            "",
            value=st.session_state.nota_actual.get('link', ''),
            key="form_link",
            label_visibility="collapsed"
        )
        if link and link.startswith('http'):
            st.markdown(f'🔗 <a href="{link}" target="_blank">Abrir link</a>', unsafe_allow_html=True)
    
    # Resumen - VERDE (ancho completo)
    st.markdown('<div class="campo-resumen">📝 RESUMEN DE LA NOTA (RTP)</div>', unsafe_allow_html=True)
    resumen = st.text_area(
        "",
        value=st.session_state.nota_actual.get('resumen', ''),
        height=120,
        key="form_resumen",
        label_visibility="collapsed"
    )
    
    # Botones
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 1])
    
    with col_btn1:
        if st.form_submit_button("💾 Guardar Nota", use_container_width=True):
            if titulo.strip():
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
                st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada")
                if st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                    st.session_state.indice_nota += 1
                    texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                    campos = auto_detect_fields(texto)
                    campos['texto_original'] = texto
                    st.session_state.nota_actual = campos
                    st.session_state.selecciones = []
                st.rerun()
            else:
                st.error("⚠️ El título es obligatorio")
    
    with col_btn2:
        if st.form_submit_button("🗑️ Limpiar campos", use_container_width=True):
            st.session_state.nota_actual = {}
            st.session_state.selecciones = []
            st.rerun()

# --- TAB: VISTA PREVIA Y EXPORTACIÓN ---
st.markdown("---")
st.subheader("📊 Vista Previa y Exportación")

if st.session_state.notas_capturadas:
    df_preview = pd.DataFrame(st.session_state.notas_capturadas)
    st.dataframe(df_preview[OFFICIAL_COLUMNS], use_container_width=True, height=300)
    
    # Botón de descarga GRANDE
    st.markdown("### 📥 Exportar a Excel")
    
    col_exp1, col_exp2, col_exp3 = st.columns([1, 2, 1])
    with col_exp2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_preview[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 DESCARGAR EXCEL",
            data=output.getvalue(),
            file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="btn_descarga_grande"
        )
        st.caption(f"📊 {len(st.session_state.notas_capturadas)} notas listas para exportar")
else:
    st.info("No hay notas capturadas. Usa las herramientas de selección y guarda tus notas.")

# --- INSTRUCCIONES ---
with st.expander("📖 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    ### 📊 Sistema de Captura de Notas RTP
    
    **1. Carga un archivo PDF** en la barra lateral
    
    **2. Selecciona texto del PDF:**
    - En el panel izquierdo, copia cualquier parte del texto
    - Pégala en el campo "Texto seleccionado"
    - Elige a qué campo pertenece (Título, Resumen, Medio, etc.)
    - Presiona "Aplicar Selección"
    
    **3. Colores por campo:**
    - 🔵 **Título** (Azul)
    - 🟢 **Resumen** (Verde)
    - 🟡 **Medio** (Amarillo)
    - 🔴 **Autor** (Rojo)
    - 🔷 **Link** (Celeste)
    - 🟣 **Tema** (Morado)
    
    **4. Guarda y navega:**
    - Completa todos los campos en la sección inferior
    - Presiona "Guardar Nota" para guardar y pasar a la siguiente
    - Usa Anterior/Siguiente para navegar
    
    **5. Exporta:**
    - Botón grande de "DESCARGAR EXCEL"
    - Estructura exacta de la plantilla RTP
    """)