import io
import re
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import google.generativeai as genai
from datetime import datetime
import json

# Configuración de página
st.set_page_config(
    page_title="Sistema de Monitoreo en Medios - RTP",
    page_icon="🚌",
    layout="wide"
)

# Estilos visuales para Semáforo
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px 4px 0px 0px; padding: 10px 16px; background-color: #f0f2f6; }
    .debug-box { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 10px; margin: 10px 0; }
    .edit-box { background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 10px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Procesamiento inteligente con IA para síntesis informativas, PDFs y reportes Excel.")

# Columnas oficiales según la plantilla SM_RTP_26_Ok.xlsx
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

# Configuración de IA Gemini
st.sidebar.header("🤖 Configuración de IA (Gemini)")
api_key = st.sidebar.text_input("Gemini API Key (Opcional):", type="password")
use_ai = False
model = None
ia_status = "⚠️ No configurada"

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        use_ai = True
        ia_status = "✅ Activada"
        st.sidebar.success("✅ IA Gemini Activada")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error: {e}")
        ia_status = "❌ Error"
else:
    st.sidebar.warning("⚠️ Sin IA - Se usará extracción por reglas")
    st.sidebar.info("Obtén API Key en: https://ai.google.dev")

# Mostrar estado de IA en la interfaz
st.sidebar.markdown(f"**Estado de IA:** {ia_status}")

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

def detect_title(line):
    """Detecta si una línea parece un título"""
    line = line.strip()
    if not line or len(line) < 5:
        return False
    
    # Patrones de título
    patterns = [
        r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,}$',  # Todo mayúsculas
        r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){2,}',  # Título con palabras capitalizadas
        r'^[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]{5,}(?:\?|\.\.\.)?$',  # Título con mayúscula inicial
    ]
    
    # No es título si contiene:
    skip_patterns = [
        r'^SÍNTESIS',
        r'^NOTAS DE MOVILIDAD',
        r'^RED DE TRANSPORTE',
        r'^Página',
        r'^MEDIOS:',
        r'^\d+$',
        r'^[A-Z]{2,}$',
    ]
    
    for pattern in skip_patterns:
        if re.search(pattern, line, re.IGNORECASE):
            return False
    
    for pattern in patterns:
        if re.match(pattern, line):
            return True
    
    return False

def extract_info_from_text(text):
    """Extrae información del texto sin usar IA"""
    lines = text.split('\n')
    records = []
    current_note = {}
    buffer = []
    reading_note = False
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Detectar título
        if detect_title(line):
            # Guardar nota anterior si existe
            if buffer:
                note_text = '\n'.join(buffer)
                if current_note.get('titulo'):
                    records.append(current_note)
                current_note = {}
                buffer = []
            
            current_note['titulo'] = line
            reading_note = True
            i += 1
            continue
        
        # Detectar medio
        if line.startswith('MEDIOS:') or line.startswith('MEDIO:'):
            medio = line.replace('MEDIOS:', '').replace('MEDIO:', '').strip()
            current_note['medio'] = medio
            i += 1
            continue
        
        # Detectar autor
        if 'Autor:' in line or 'Por:' in line:
            autor = line.replace('Autor:', '').replace('Por:', '').strip()
            current_note['autor'] = autor
            i += 1
            continue
        
        # Detectar link
        if 'http' in line:
            links = re.findall(r'https?://[^\s]+', line)
            if links:
                current_note['link'] = links[0]
            i += 1
            continue
        
        # Si estamos leyendo una nota, agregar al buffer
        if reading_note:
            buffer.append(line)
        
        i += 1
    
    # Guardar última nota
    if buffer and current_note.get('titulo'):
        current_note['resumen'] = '\n'.join(buffer)[:500]
        records.append(current_note)
    
    # Procesar notas sin título detectado (intento alternativo)
    if not records and len(lines) > 5:
        # Buscar patrones de notas
        sections = re.split(r'\n\s*\n', text)
        for section in sections:
            if len(section.strip()) < 30:
                continue
            lines_section = section.split('\n')
            first_line = lines_section[0].strip() if lines_section else ""
            record = {
                'titulo': first_line if len(first_line) < 100 else first_line[:80] + '...',
                'resumen': section[:500],
                'medio': '',
                'autor': '',
                'link': '',
                'tono': 'Informativo'
            }
            records.append(record)
    
    return records

def analyze_with_ai(text, model):
    """Usa IA para extraer información estructurada"""
    if not model:
        return extract_info_from_text(text)
    
    prompt = f"""
    Extrae las notas periodísticas del siguiente texto. 
    
    TEXTO:
    {text[:3000]}
    
    Para cada nota, identifica:
    - título: El encabezado de la nota
    - resumen: El contenido de la nota (máximo 200 palabras)
    - medio: El medio de comunicación
    - autor: El autor
    - link: URL si existe
    - tono: "Positivo", "Negativo" o "Informativo"
    
    Responde SOLO con un JSON array.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
    except:
        pass
    
    # Fallback a extracción por reglas
    return extract_info_from_text(text)

def process_pdf_file(pdf_file, model):
    """Procesa un archivo PDF"""
    # Extraer texto
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
    
    if not full_text.strip():
        st.error("❌ No se pudo extraer texto del PDF")
        return pd.DataFrame()
    
    # Mostrar vista previa
    with st.expander("📄 Vista previa del texto extraído"):
        st.text(full_text[:2000] + ("..." if len(full_text) > 2000 else ""))
        st.caption(f"Total: {len(full_text)} caracteres")
    
    # Extraer información
    with st.spinner("📊 Extrayendo notas..."):
        if use_ai and model:
            st.info("🧠 Usando IA para analizar...")
            raw_notes = analyze_with_ai(full_text, model)
        else:
            st.info("📋 Usando extracción por reglas...")
            raw_notes = extract_info_from_text(full_text)
    
    if not raw_notes:
        st.warning("⚠️ No se encontraron notas en el PDF")
        return pd.DataFrame()
    
    # Mostrar resultados crudos
    with st.expander("📋 Resultados extraídos (primeras 3 notas)"):
        st.json(raw_notes[:3])
    
    # Convertir a DataFrame
    records = []
    today = datetime.now()
    
    for note in raw_notes:
        titulo = note.get('titulo', 'Sin título')
        resumen = note.get('resumen', '')
        medio = note.get('medio', '')
        tono = note.get('tono', 'Informativo')
        autor = note.get('autor', 'Redacción')
        link = note.get('link', '')
        
        # Determinar relevancia
        relevante = "Sí" if any(x in (titulo + resumen).lower() for x in ['rtp', 'red de transporte']) else "No"
        
        # Determinar categoría de medio
        if any(x in medio.lower() for x in ['twitter', 'x.com', 'facebook', 'youtube']):
            medio_col = 'OTROS (Twitter, Facebook, You Tube, etc.).'
        elif any(x in medio.lower() for x in ['radio', 'fm']):
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
        elif any(x in medio.lower() for x in ['tv', 'canal', 'televisa']):
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
        elif any(x in medio.lower() for x in ['.com', 'portal', 'digital']):
            medio_col = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
        else:
            medio_col = 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *'
        
        record = {
            'Año': today.year,
            '# Mes': today.month,
            'Mes': today.strftime("%B").capitalize(),
            'Fecha ': today.strftime("%Y-%m-%d"),
            'Título de la nota': titulo,
            'RTP, ¿Es relevante en la nota?': relevante,
            'Tema de la nota': titulo[:80],
            'Campaña': map_campana(tono),
            'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if 'radio' in medio.lower() else None,
            'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if any(x in medio.lower() for x in ['tv', 'canal', 'televisa']) else None,
            'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if any(x in medio.lower() for x in ['.com', 'portal', 'digital']) or not medio else None,
            'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if not any(x in medio.lower() for x in ['com', 'radio', 'tv', 'twitter', 'facebook']) else None,
            'OTROS (Twitter, Facebook, You Tube, etc.).': medio if any(x in medio.lower() for x in ['twitter', 'facebook', 'youtube']) else None,
            'Informativo / Positivo/ Negativo': tono,
            'LINK': link,
            'Autor': autor,
            'PUBLICACIÓN BOLETÍN': 'NO',
            'RESUMEN  DE LA NOTA (RTP)': resumen
        }
        records.append(record)
    
    return pd.DataFrame(records)

# --- PANEL LATERAL ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

# Opción para ingresar URL de nota
st.sidebar.header("🔗 Ingresar Nota Manual")
with st.sidebar.expander("➕ Agregar nota manual"):
    manual_titulo = st.text_input("Título:")
    manual_resumen = st.text_area("Resumen:", height=80)
    manual_medio = st.text_input("Medio:")
    manual_tono = st.selectbox("Tono:", ["Informativo", "Positivo", "Negativo"])
    manual_url = st.text_input("URL (opcional):")
    agregar_manual = st.button("➕ Agregar nota")

df = pd.DataFrame()

# Procesar archivo subido
if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        if ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.sidebar.selectbox("Selecciona pestaña:", xls.sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            st.success(f"✅ Excel cargado: {len(df)} notas")
        elif ext == "pdf":
            with st.spinner("📄 Procesando PDF..."):
                df = process_pdf_file(uploaded_file, model)
            if not df.empty:
                st.success(f"✅ PDF procesado: {len(df)} notas extraídas")
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Agregar nota manual
if agregar_manual and manual_titulo:
    new_record = {
        'Año': datetime.now().year,
        '# Mes': datetime.now().month,
        'Mes': datetime.now().strftime("%B").capitalize(),
        'Fecha ': datetime.now().strftime("%Y-%m-%d"),
        'Título de la nota': manual_titulo,
        'RTP, ¿Es relevante en la nota?': 'Sí' if 'rtp' in manual_titulo.lower() or 'rtp' in manual_resumen.lower() else 'No',
        'Tema de la nota': manual_titulo[:80],
        'Campaña': map_campana(manual_tono),
        'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
        'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
        'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': manual_medio or 'Portal Digital',
        'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
        'OTROS (Twitter, Facebook, You Tube, etc.).': None,
        'Informativo / Positivo/ Negativo': manual_tono,
        'LINK': manual_url,
        'Autor': 'Usuario',
        'PUBLICACIÓN BOLETÍN': 'NO',
        'RESUMEN  DE LA NOTA (RTP)': manual_resumen
    }
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    st.success("✅ Nota manual agregada")
    st.rerun()

if not df.empty:
    # Asegurar columnas estándar
    for col in OFFICIAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Normalización
    df['Informativo / Positivo/ Negativo'] = df['Informativo / Positivo/ Negativo'].apply(clean_sentiment)
    df['Campaña'] = df['Informativo / Positivo/ Negativo'].apply(map_campana)

    if 'Fecha ' in df.columns:
        df['Fecha_Limpia'] = pd.to_datetime(df['Fecha '], errors='coerce').dt.strftime('%Y-%m-%d')
    else:
        df['Fecha_Limpia'] = "Sin Fecha"

    # --- MÉTRICAS ---
    st.subheader("📌 Resumen con Semáforo Informativo")
    total = len(df)
    positivos = len(df[df['Informativo / Positivo/ Negativo'] == 'Positivo'])
    informativos = len(df[df['Informativo / Positivo/ Negativo'] == 'Informativo'])
    negativos = len(df[df['Informativo / Positivo/ Negativo'] == 'Negativo'])
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Notas", total)
    k2.markdown(f"**🟢 Positivas**: <span class='badge-positivo'>{positivos}</span>", unsafe_allow_html=True)
    k3.markdown(f"**🟡 Informativas**: <span class='badge-informativo'>{informativos}</span>", unsafe_allow_html=True)
    k4.markdown(f"**🔴 Negativas**: <span class='badge-negativo'>{negativos}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Gráficas", 
        "📋 Tabla de Registros", 
        "📻 Medios y Relevancia", 
        "📥 Exportar Excel"
    ])

    # TAB 1: GRÁFICAS
    with tab1:
        st.subheader("Análisis de Cobertura")
        c_g1, c_g2 = st.columns(2)

        with c_g1:
            fig_pie = px.pie(
                df, 
                names='Informativo / Positivo/ Negativo', 
                title="Distribución Semáforo",
                color='Informativo / Positivo/ Negativo',
                color_discrete_map={'Positivo': '#28a745', 'Informativo': '#ffc107', 'Negativo': '#dc3545'},
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with c_g2:
            campana_counts = df['Campaña'].value_counts().reset_index()
            campana_counts.columns = ['Campaña', 'Cantidad']
            fig_campana = px.pie(
                campana_counts,
                names='Campaña',
                values='Cantidad',
                title="Distribución por Campaña"
            )
            st.plotly_chart(fig_campana, use_container_width=True)

    # TAB 2: TABLA PRINCIPAL
    with tab2:
        st.subheader("Registros de Monitoreo")
        st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True, height=500)

    # TAB 3: MEDIOS Y RELEVANCIA
    with tab3:
        st.subheader("Análisis de Medios")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.write("### Relevancia de RTP")
            df_rel = df['RTP, ¿Es relevante en la nota?'].value_counts().reset_index()
            df_rel.columns = ['Relevancia', 'Cantidad']
            if not df_rel.empty:
                fig_rel = px.bar(
                    df_rel,
                    x='Relevancia',
                    y='Cantidad',
                    color='Relevancia',
                    title="Notas Relevantes para RTP",
                    color_discrete_map={'Sí': '#007bff', 'No': '#6c757d'}
                )
                st.plotly_chart(fig_rel, use_container_width=True)

        with col_m2:
            st.write("### Medios más frecuentes")
            medios_cols = [
                'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *',
                'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *',
                'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ',
                'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *',
                'OTROS (Twitter, Facebook, You Tube, etc.).'
            ]
            medios_data = []
            for col in medios_cols:
                if col in df.columns:
                    for val in df[col].dropna():
                        if val:
                            medios_data.append(val)
            if medios_data:
                medios_counts = pd.Series(medios_data).value_counts().reset_index()
                medios_counts.columns = ['Medio', 'Cantidad']
                st.dataframe(medios_counts.head(10), use_container_width=True)

    # TAB 4: EXPORTACIÓN
    with tab4:
        st.subheader("Exportar Excel")
        
        st.write("### Vista previa")
        st.dataframe(df[OFFICIAL_COLUMNS].head(10), use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel",
            data=output.getvalue(),
            file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👈 Sube un archivo en la barra lateral o agrega una nota manual")
    
    with st.expander("📖 ¿Cómo usar esta herramienta?"):
        st.markdown("""
        ### 📊 Sistema de Monitoreo RTP
        
        **Sin IA (modo por defecto)**:
        - Extrae títulos y resúmenes automáticamente
        - Detecta medios de comunicación
        - Clasifica el tono de las notas
        
        **Con IA (requiere API Key)**:
        - Mayor precisión en extracción
        - Mejor identificación de autores
        - Análisis más detallado
        
        ### Cómo obtener API Key de Gemini:
        1. Ve a [ai.google.dev](https://ai.google.dev)
        2. Crea una cuenta o inicia sesión
        3. Ve a "Get API Key"
        4. Copia tu clave y pégala en la barra lateral
        """)