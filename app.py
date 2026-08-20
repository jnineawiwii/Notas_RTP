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

# Estilos visuales
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px 4px 0px 0px; padding: 10px 16px; background-color: #f0f2f6; }
    .edit-box { background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 5px; padding: 15px; margin: 10px 0; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Procesamiento inteligente con IA para síntesis informativas, PDFs y reportes Excel.")

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

# Configuración de IA Gemini
st.sidebar.header("🤖 Configuración de IA (Gemini)")
api_key = st.sidebar.text_input("Gemini API Key:", type="password")
use_ai = False
model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        use_ai = True
        st.sidebar.success("✅ IA Gemini Activada")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error: {e}")
else:
    st.sidebar.warning("⚠️ Sin IA - Extracción por reglas")

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

def clean_title(title):
    """Limpia títulos que tienen fechas pegadas"""
    if not title:
        return "Sin título"
    # Eliminar fechas al inicio (ej: "2026-08-20 Notas de ayer" -> "Notas de ayer")
    title = re.sub(r'^\d{4}-\d{2}-\d{2}\s*', '', title)
    # Eliminar números de página
    title = re.sub(r'^\d+\s*', '', title)
    # Eliminar "Notas de ayer" si es un encabezado
    if title.strip().upper() == "NOTAS DE AYER":
        return None
    return title.strip()

def extract_notes_with_ai(text, model):
    """Extrae notas usando IA con un prompt específico para el formato"""
    if not model:
        return None
    
    prompt = f"""
    Analiza el siguiente texto de una SÍNTESIS INFORMATIVA de la RTP.
    
    TEXTO:
    {text[:4000]}
    
    Este texto contiene varias notas periodísticas. Cada nota típicamente tiene:
    1. Un TÍTULO en negritas o mayúsculas (ej: "Mujeres conductoras marcan ruta en la CDMX")
    2. Una mención al MEDIO (ej: "Medio: El Heraldo" o "MEDIOS: El Universal")
    3. Un CONTENIDO/RESUMEN de la nota
    4. Posiblemente un AUTOR y un LINK
    
    IMPORTANTE: 
    - NO incluyas "Notas de ayer" como título
    - NO incluyas fechas en el título
    - El título debe ser el encabezado REAL de la nota
    
    Para CADA nota, extrae:
    {{
        "titulo": "El título real de la nota",
        "resumen": "El contenido de la nota (máximo 300 palabras)",
        "medio": "El nombre del medio",
        "autor": "El autor si aparece",
        "link": "URL si aparece",
        "tono": "Positivo, Negativo o Informativo"
    }}
    
    Responde SOLO con un JSON array de notas.
    Si solo hay una nota, devuelve un array con un solo elemento.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Extraer JSON
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        
        # Intentar extraer objetos individuales
        json_objects = re.findall(r'\{[^{}]*\}', response_text)
        if json_objects:
            results = []
            for obj in json_objects:
                try:
                    results.append(json.loads(obj))
                except:
                    pass
            if results:
                return results
        
        return None
    except Exception as e:
        st.warning(f"⚠️ Error en IA: {e}")
        return None

def extract_notes_manually(text):
    """Extrae notas manualmente sin IA"""
    notes = []
    lines = text.split('\n')
    
    current_note = {}
    buffer = []
    in_note = False
    
    # Patrones para identificar elementos
    title_pattern = r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{5,}$|^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){2,}'
    media_pattern = r'MEDIOS?:\s*(.+)'
    autor_pattern = r'(?:Autor|Por|Redacción)[:\s]+(.+)'
    link_pattern = r'https?://[^\s]+'
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Saltar encabezados de sección
        if any(x in line.upper() for x in ['SÍNTESIS INFORMATIVA', 'NOTAS DE MOVILIDAD', 'RED DE TRANSPORTE']):
            i += 1
            continue
        
        # Detectar título (línea en mayúsculas o con formato de título)
        if re.match(title_pattern, line) and len(line) < 100:
            # Guardar nota anterior
            if current_note and buffer:
                current_note['resumen'] = '\n'.join(buffer)[:500]
                notes.append(current_note)
            
            # Iniciar nueva nota
            current_note = {'titulo': line}
            buffer = []
            in_note = True
            i += 1
            continue
        
        # Detectar medio
        media_match = re.search(media_pattern, line, re.IGNORECASE)
        if media_match and current_note:
            current_note['medio'] = media_match.group(1).strip()
            i += 1
            continue
        
        # Detectar autor
        autor_match = re.search(autor_pattern, line, re.IGNORECASE)
        if autor_match and current_note:
            current_note['autor'] = autor_match.group(1).strip()
            i += 1
            continue
        
        # Detectar link
        link_match = re.search(link_pattern, line)
        if link_match and current_note:
            current_note['link'] = link_match.group(0)
            i += 1
            continue
        
        # Si estamos en una nota, agregar al buffer
        if in_note and line and len(line) > 5:
            buffer.append(line)
        
        i += 1
    
    # Guardar última nota
    if current_note and buffer:
        current_note['resumen'] = '\n'.join(buffer)[:500]
        # Limpiar título
        if current_note.get('titulo'):
            clean = clean_title(current_note['titulo'])
            if clean:
                current_note['titulo'] = clean
                notes.append(current_note)
    
    return notes

def process_pdf_file(pdf_file, model):
    """Procesa archivo PDF"""
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
        st.text(full_text[:2000])
        st.caption(f"Total: {len(full_text)} caracteres")
    
    # Intentar extraer con IA primero
    notes = []
    if model:
        with st.spinner("🧠 Analizando con IA..."):
            ai_notes = extract_notes_with_ai(full_text, model)
            if ai_notes:
                notes = ai_notes
                st.success(f"✅ IA extrajo {len(notes)} notas")
    
    # Si no hay notas de IA, usar método manual
    if not notes:
        with st.spinner("📋 Extrayendo manualmente..."):
            notes = extract_notes_manually(full_text)
            if notes:
                st.info(f"📋 Extracción manual: {len(notes)} notas")
    
    if not notes:
        st.warning("⚠️ No se encontraron notas en el PDF")
        return pd.DataFrame()
    
    # Mostrar resultados crudos
    with st.expander("📋 Resultados extraídos"):
        st.json(notes[:3])
    
    # Convertir a DataFrame
    records = []
    today = datetime.now()
    
    for note in notes:
        titulo = clean_title(note.get('titulo', 'Sin título'))
        if not titulo:  # Saltar si el título es inválido
            continue
            
        resumen = note.get('resumen', '')
        medio = note.get('medio', '')
        tono = note.get('tono', 'Informativo')
        autor = note.get('autor', 'Redacción')
        link = note.get('link', '')
        
        # Determinar relevancia
        texto_completo = (titulo + " " + resumen).lower()
        relevante = "Sí" if 'rtp' in texto_completo else "No"
        
        # Clasificar medio
        medio_lower = medio.lower()
        if any(x in medio_lower for x in ['twitter', 'x.com', 'facebook', 'youtube']):
            medio_col = 'OTROS (Twitter, Facebook, You Tube, etc.).'
        elif any(x in medio_lower for x in ['radio', 'fm']):
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
        elif any(x in medio_lower for x in ['tv', 'canal', 'televisa']):
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
        elif any(x in medio_lower for x in ['.com', 'portal', 'digital', 'noticias']):
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
            'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if 'radio' in medio_lower else None,
            'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if any(x in medio_lower for x in ['tv', 'canal', 'televisa']) else None,
            'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if any(x in medio_lower for x in ['.com', 'portal', 'digital']) or not medio else None,
            'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if not any(x in medio_lower for x in ['com', 'radio', 'tv', 'twitter', 'facebook']) and medio else None,
            'OTROS (Twitter, Facebook, You Tube, etc.).': medio if any(x in medio_lower for x in ['twitter', 'facebook', 'youtube']) else None,
            'Informativo / Positivo/ Negativo': tono,
            'LINK': link,
            'Autor': autor,
            'PUBLICACIÓN BOLETÍN': 'NO',
            'RESUMEN  DE LA NOTA (RTP)': resumen
        }
        records.append(record)
    
    if not records:
        st.warning("⚠️ No se pudieron procesar las notas")
        return pd.DataFrame()
    
    return pd.DataFrame(records)

# --- PANEL LATERAL ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

df = pd.DataFrame()

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        if ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.sidebar.selectbox("Selecciona pestaña:", xls.sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            st.success(f"✅ Excel cargado: {len(df)} notas")
        elif ext == "pdf":
            if not use_ai:
                st.info("ℹ️ Procesando con extracción manual (sin IA)")
            with st.spinner("📄 Procesando PDF..."):
                df = process_pdf_file(uploaded_file, model if use_ai else None)
            if not df.empty:
                st.success(f"✅ PDF procesado: {len(df)} notas extraídas")
    except Exception as e:
        st.error(f"❌ Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# --- SECCIÓN DE EDICIÓN MANUAL ---
st.sidebar.header("✏️ Edición Manual")
with st.sidebar.expander("➕ Agregar nota manual"):
    manual_titulo = st.text_input("Título:")
    manual_resumen = st.text_area("Resumen:", height=80)
    manual_medio = st.text_input("Medio:")
    manual_tono = st.selectbox("Tono:", ["Informativo", "Positivo", "Negativo"], index=0)
    manual_url = st.text_input("URL (opcional):")
    if st.button("➕ Agregar nota"):
        if manual_titulo:
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
    # Asegurar columnas
    for col in OFFICIAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Normalizar
    df['Informativo / Positivo/ Negativo'] = df['Informativo / Positivo/ Negativo'].apply(clean_sentiment)
    df['Campaña'] = df['Informativo / Positivo/ Negativo'].apply(map_campana)

    if 'Fecha ' in df.columns:
        df['Fecha_Limpia'] = pd.to_datetime(df['Fecha '], errors='coerce').dt.strftime('%Y-%m-%d')
    else:
        df['Fecha_Limpia'] = "Sin Fecha"

    # --- MÉTRICAS ---
    st.subheader("📌 Resumen")
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
        "📻 Análisis por Medio", 
        "📥 Exportar"
    ])

    with tab1:
        st.subheader("Distribución de Cobertura")
        c1, c2 = st.columns(2)
        
        with c1:
            fig_pie = px.pie(
                df, 
                names='Informativo / Positivo/ Negativo',
                title="Semáforo General",
                color='Informativo / Positivo/ Negativo',
                color_discrete_map={'Positivo': '#28a745', 'Informativo': '#ffc107', 'Negativo': '#dc3545'},
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with c2:
            campana_counts = df['Campaña'].value_counts().reset_index()
            campana_counts.columns = ['Campaña', 'Cantidad']
            fig_campana = px.pie(
                campana_counts,
                names='Campaña',
                values='Cantidad',
                title="Distribución por Campaña"
            )
            st.plotly_chart(fig_campana, use_container_width=True)

    with tab2:
        st.subheader("Registros de Monitoreo")
        st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True, height=500)

    with tab3:
        st.subheader("Análisis por Medio")
        col1, col2 = st.columns(2)
        
        with col1:
            df_rel = df['RTP, ¿Es relevante en la nota?'].value_counts().reset_index()
            df_rel.columns = ['Relevancia', 'Cantidad']
            if not df_rel.empty:
                fig_rel = px.bar(
                    df_rel,
                    x='Relevancia',
                    y='Cantidad',
                    color='Relevancia',
                    title="Relevancia para RTP",
                    color_discrete_map={'Sí': '#007bff', 'No': '#6c757d'}
                )
                st.plotly_chart(fig_rel, use_container_width=True)
        
        with col2:
            medios_cols = [
                'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *',
                'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *',
                'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ',
                'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *',
                'OTROS (Twitter, Facebook, You Tube, etc.).'
            ]
            medios = []
            for col in medios_cols:
                if col in df.columns:
                    for val in df[col].dropna():
                        if val:
                            medios.append(val)
            if medios:
                medios_counts = pd.Series(medios).value_counts().reset_index()
                medios_counts.columns = ['Medio', 'Cantidad']
                st.dataframe(medios_counts.head(10), use_container_width=True)

    with tab4:
        st.subheader("Exportar Datos")
        st.write("### Vista previa")
        st.dataframe(df[OFFICIAL_COLUMNS].head(10), use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel",
            data=output.getvalue(),
            file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👈 Sube un archivo en la barra lateral o agrega una nota manual")
    
    with st.expander("📖 Guía de uso"):
        st.markdown("""
        ### 📊 Cómo usar el sistema
        
        **1. Sin IA (recomendado para empezar)**
        - Sube tu PDF y se extraerán las notas automáticamente
        - Los títulos se limpian de fechas y encabezados
        
        **2. Con IA (requiere API Key)**
        - Mayor precisión en la extracción
        - Mejor identificación de medios y autores
        
        **3. Edición manual**
        - Puedes agregar notas manualmente
        - Los títulos se pueden editar en la tabla
        
        ### 📝 Formato esperado del PDF
        - Síntesis informativa con secciones "SÍNTESIS INFORMATIVA" y "NOTAS DE MOVILIDAD"
        - Títulos en mayúsculas o negritas
        - Mención de "MEDIOS:" o "Medio:"
        - Autor y URL si están disponibles
        """)