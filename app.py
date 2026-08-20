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
api_key = st.sidebar.text_input("Gemini API Key (Obligatoria para IA):", type="password")
use_ai = False
model = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        use_ai = True
        st.sidebar.success("✅ IA Gemini Activada")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error al configurar IA: {e}")
        use_ai = False
else:
    st.sidebar.warning("⚠️ Se requiere API Key de Gemini para procesar PDFs")
    st.sidebar.info("Obtén tu API Key en: https://ai.google.dev")

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

def split_into_sections(text, max_chunk_size=3000):
    """Divide el texto en secciones más pequeñas para procesar"""
    # Buscar patrones de separación comunes
    separators = [
        r'\n\s*\n\s*\d+\s*\n',  # Número de página
        r'\n\s*MEDIOS:',         # Inicio de una nota con MEDIOS
        r'\n\s*[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]{10,}\n',  # Título en mayúsculas
        r'\n\s*[-–—]\s*\n',      # Línea separadora
    ]
    
    # Intentar dividir por MEDIOS: primero
    sections = re.split(r'(?=\n\s*MEDIOS:)', text)
    if len(sections) > 1:
        return sections
    
    # Dividir por líneas en blanco
    sections = re.split(r'\n\s*\n', text)
    sections = [s for s in sections if len(s.strip()) > 50]
    
    # Si las secciones son muy grandes, dividirlas
    final_sections = []
    for section in sections:
        if len(section) > max_chunk_size:
            # Dividir por párrafos
            paragraphs = re.split(r'\n(?=[A-ZÁÉÍÓÚÑ][a-záéíóúñ])', section)
            current_chunk = ""
            for p in paragraphs:
                if len(current_chunk) + len(p) < max_chunk_size:
                    current_chunk += p + "\n"
                else:
                    if current_chunk.strip():
                        final_sections.append(current_chunk)
                    current_chunk = p + "\n"
            if current_chunk.strip():
                final_sections.append(current_chunk)
        else:
            final_sections.append(section)
    
    return final_sections

def analyze_section_with_ai(section_text, model):
    """Analiza una sección del PDF con IA y extrae notas"""
    if not model:
        return []
    
    prompt = f"""
    Eres un asistente especializado en análisis de notas periodísticas sobre la Red de Transporte de Pasajeros (RTP) de la CDMX.
    
    Analiza el siguiente texto que contiene UNA O MÁS notas periodísticas.
    
    TEXTO:
    {section_text[:2500]}
    
    IMPORTANTE: Identifica TODAS las notas en este texto. Cada nota normalmente tiene:
    - Un TÍTULO en mayúsculas o con formato de encabezado
    - Una mención al MEDIO (ej: "MEDIOS: El Universal")
    - Un CONTENIDO que describe la noticia
    - Posiblemente un AUTOR y un LINK
    
    Para CADA NOTA, extrae:
    1. "titulo": El título de la nota
    2. "resumen": El contenido/resumen de la nota
    3. "medio": El nombre del medio de comunicación
    4. "tono": "Positivo", "Negativo" o "Informativo"
    5. "relevante": "Sí" o "No" (¿habla sobre RTP?)
    6. "tema": El tema principal
    7. "autor": El autor si se menciona
    8. "link": URL si aparece
    
    Responde SOLO con un array JSON. Si hay múltiples notas, inclúyelas todas.
    Ejemplo: [{{"titulo": "...", "resumen": "...", ...}}, {{...}}]
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Intentar extraer JSON
        json_match = re.search(r'\[\s*\{.*\}\s*\]', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                # Intentar reparar JSON
                fixed = re.sub(r',\s*}', '}', response_text)
                fixed = re.sub(r',\s*]', ']', fixed)
                json_match = re.search(r'\[\s*\{.*\}\s*\]', fixed, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except:
                        pass
        return []
    except Exception as e:
        st.warning(f"⚠️ Error en análisis IA: {e}")
        return []

def process_pdf_file(pdf_file, model):
    """Procesa un archivo PDF usando IA para extraer notas estructuradas"""
    if not model:
        st.error("❌ Se requiere IA (Gemini) para procesar PDFs")
        return pd.DataFrame()
    
    # Extraer texto del PDF
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
    
    if not full_text.strip():
        st.error("❌ No se pudo extraer texto del PDF")
        return pd.DataFrame()
    
    # Mostrar vista previa del texto
    with st.expander("📄 Vista previa del texto extraído"):
        st.text(full_text[:3000] + ("..." if len(full_text) > 3000 else ""))
        st.caption(f"Total de caracteres: {len(full_text)}")
    
    # Dividir en secciones
    with st.spinner("🔄 Dividiendo el texto en secciones..."):
        sections = split_into_sections(full_text)
        st.info(f"📊 Se encontraron {len(sections)} secciones para procesar")
    
    # Procesar cada sección con IA
    all_notes = []
    progress_bar = st.progress(0)
    
    for i, section in enumerate(sections):
        if len(section.strip()) < 50:
            continue
        
        with st.spinner(f"🧠 Analizando sección {i+1}/{len(sections)}..."):
            notes = analyze_section_with_ai(section, model)
            if notes:
                all_notes.extend(notes)
        
        progress_bar.progress((i + 1) / len(sections))
    
    if not all_notes:
        st.warning("⚠️ No se encontraron notas en el PDF. Intenta con otro archivo.")
        return pd.DataFrame()
    
    # Mostrar resultados de IA
    with st.expander("📋 Resultados de IA (primeras notas)"):
        st.json(all_notes[:3])
    
    # Convertir a DataFrame
    records = []
    today = datetime.now()
    
    for note in all_notes:
        titulo = note.get('titulo', 'Sin título')
        resumen = note.get('resumen', '')
        medio = note.get('medio', '')
        tono = note.get('tono', 'Informativo')
        relevante = note.get('relevante', 'Sí' if 'rtp' in resumen.lower() or 'rtp' in titulo.lower() else 'No')
        tema = note.get('tema', f"Nota: {titulo[:50]}")
        autor = note.get('autor', 'Redacción')
        link = note.get('link', '')
        
        # Determinar categoría del medio
        medio_lower = medio.lower()
        if any(x in medio_lower for x in ['twitter', 'x.com', 'facebook', 'youtube', 'instagram']):
            categoria = 'Redes Sociales'
        elif any(x in medio_lower for x in ['radio', 'fm']):
            categoria = 'Radio'
        elif any(x in medio_lower for x in ['tv', 'canal', 'televisa']):
            categoria = 'TV'
        elif any(x in medio_lower for x in ['.com', 'portal', 'digital', 'noticias']):
            categoria = 'Digital'
        else:
            categoria = 'Digital'  # Default
        
        # Mapear categoría a columna
        if categoria == 'Impreso':
            medio_col = 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *'
        elif categoria == 'Radio':
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
        elif categoria == 'TV':
            medio_col = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
        elif categoria == 'Redes Sociales':
            medio_col = 'OTROS (Twitter, Facebook, You Tube, etc.).'
        else:
            medio_col = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
        
        record = {
            'Año': today.year,
            '# Mes': today.month,
            'Mes': today.strftime("%B").capitalize(),
            'Fecha ': today.strftime("%Y-%m-%d"),
            'Título de la nota': titulo,
            'RTP, ¿Es relevante en la nota?': relevante,
            'Tema de la nota': tema,
            'Campaña': map_campana(tono),
            'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if categoria == 'Radio' else None,
            'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if categoria == 'TV' else None,
            'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if categoria == 'Digital' else None,
            'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if categoria == 'Impreso' else None,
            'OTROS (Twitter, Facebook, You Tube, etc.).': medio if categoria == 'Redes Sociales' else None,
            'Informativo / Positivo/ Negativo': tono,
            'LINK': link,
            'Autor': autor,
            'PUBLICACIÓN BOLETÍN': 'NO',
            'RESUMEN  DE LA NOTA (RTP)': resumen
        }
        records.append(record)
    
    if not records:
        st.warning("⚠️ No se pudieron extraer notas del PDF")
        return pd.DataFrame()
    
    st.success(f"✅ Se extrajeron {len(records)} notas del PDF")
    return pd.DataFrame(records)

# --- PANEL LATERAL ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

# Opción para ingresar URL de nota
st.sidebar.header("🔗 Ingresar Nota Manual")
manual_url = st.sidebar.text_input("URL de la nota:")
manual_titulo = st.sidebar.text_input("Título:")
manual_resumen = st.sidebar.text_area("Resumen:", height=100)
manual_medio = st.sidebar.text_input("Medio:", placeholder="Ej: El Universal, Reforma, etc.")
manual_tono = st.sidebar.selectbox("Tono:", ["Informativo", "Positivo", "Negativo"])

df = pd.DataFrame()

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    try:
        if ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.sidebar.selectbox("Selecciona pestaña:", xls.sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
            st.success("✅ Archivo Excel cargado correctamente")
        elif ext == "pdf":
            if not use_ai:
                st.error("❌ Se requiere API Key de Gemini para procesar PDFs")
                st.info("Obtén tu API Key en: https://ai.google.dev")
            else:
                with st.spinner("📄 Procesando PDF con IA..."):
                    df = process_pdf_file(uploaded_file, model)
                if not df.empty:
                    st.success(f"✅ PDF procesado exitosamente: {len(df)} notas extraídas")
                else:
                    st.warning("⚠️ No se pudieron extraer notas del PDF. Verifica el formato.")
    except Exception as e:
        st.error(f"❌ Error al procesar archivo: {e}")
        import traceback
        st.code(traceback.format_exc())

# Agregar nota manual
if manual_url and manual_titulo:
    new_record = {
        'Año': datetime.now().year,
        '# Mes': datetime.now().month,
        'Mes': datetime.now().strftime("%B").capitalize(),
        'Fecha ': datetime.now().strftime("%Y-%m-%d"),
        'Título de la nota': manual_titulo,
        'RTP, ¿Es relevante en la nota?': 'Sí' if 'rtp' in manual_titulo.lower() or 'rtp' in manual_resumen.lower() else 'No',
        'Tema de la nota': manual_titulo[:50],
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

if not df.empty:
    # Asegurar columnas estándar
    for col in OFFICIAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Normalización de datos
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
        "📊 Gráficas de Tendencia", 
        "📋 Tabla de Registros", 
        "📻 Medios y Relevancia", 
        "📥 Exportar Excel"
    ])

    # TAB 1: GRÁFICAS
    with tab1:
        st.subheader("Análisis Temporal y Semáforo de Cobertura")
        c_g1, c_g2 = st.columns(2)

        with c_g1:
            if not df['Fecha_Limpia'].isna().all():
                df_fecha_postura = df.groupby(['Fecha_Limpia', 'Informativo / Positivo/ Negativo']).size().reset_index(name='Cantidad')
                fig_line = px.bar(
                    df_fecha_postura, 
                    x='Fecha_Limpia', 
                    y='Cantidad', 
                    color='Informativo / Positivo/ Negativo',
                    title="Volumen Diario de Notas por Postura",
                    color_discrete_map={'Positivo': '#28a745', 'Informativo': '#ffc107', 'Negativo': '#dc3545'},
                    barmode='stack'
                )
                fig_line.update_layout(xaxis_title="Fecha", yaxis_title="Número de Notas")
                st.plotly_chart(fig_line, use_container_width=True)
            else:
                st.info("No hay suficientes datos para mostrar tendencia temporal")

        with c_g2:
            fig_pie = px.pie(
                df, 
                names='Informativo / Positivo/ Negativo', 
                title="Distribución Semáforo General",
                color='Informativo / Positivo/ Negativo',
                color_discrete_map={'Positivo': '#28a745', 'Informativo': '#ffc107', 'Negativo': '#dc3545'},
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # TAB 2: TABLA PRINCIPAL
    with tab2:
        st.subheader("Estructura Oficial de Monitoreo")
        st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True, height=400)

    # TAB 3: MEDIOS Y RELEVANCIA
    with tab3:
        st.subheader("Análisis de Relevancia y Presencia")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.write("### Desglose por Campaña")
            campana_counts = df['Campaña'].value_counts().reset_index()
            campana_counts.columns = ['Campaña', 'Cantidad']
            st.dataframe(campana_counts, use_container_width=True)
            
            if not campana_counts.empty:
                fig_campana = px.pie(
                    campana_counts,
                    names='Campaña',
                    values='Cantidad',
                    title="Distribución por Campaña"
                )
                st.plotly_chart(fig_campana, use_container_width=True)

        with col_m2:
            st.write("### Relevancia de RTP en las Notas")
            df_rel = df['RTP, ¿Es relevante en la nota?'].value_counts().reset_index()
            df_rel.columns = ['Relevancia', 'Cantidad']
            
            if not df_rel.empty:
                fig_rel = px.bar(
                    df_rel,
                    x='Relevancia',
                    y='Cantidad',
                    color='Relevancia',
                    title="Notas Relevantes para RTP",
                    color_discrete_map={'Sí': '#007bff', 'No': '#6c757d', 'Si': '#007bff'}
                )
                st.plotly_chart(fig_rel, use_container_width=True)

    # TAB 4: EXPORTACIÓN
    with tab4:
        st.subheader("Exportar Excel Actualizado")
        
        # Mostrar vista previa de exportación
        st.write("### Vista previa de datos a exportar")
        st.dataframe(df[OFFICIAL_COLUMNS].head(10), use_container_width=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Seguimiento_en_Medios_RTP_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.info("💡 El archivo exportado mantiene la estructura exacta de la plantilla oficial de RTP.")

else:
    st.info("👈 Por favor sube un archivo en la barra lateral o agrega una nota manual para comenzar.")
    
    # Mostrar ayuda
    with st.expander("📖 ¿Cómo usar esta herramienta?"):
        st.markdown("""
        ### 🧠 Sistema de Análisis con IA
        
        Este sistema usa **Gemini AI** para extraer automáticamente la información de los PDFs.
        
        ### Instrucciones de uso:
        
        1. **Obtén tu API Key** en [ai.google.dev](https://ai.google.dev)
        2. **Pega tu API Key** en la barra lateral
        3. **Sube un archivo PDF** con la síntesis informativa
        4. La IA extraerá automáticamente:
           - Títulos de las notas
           - Resúmenes
           - Medio de comunicación
           - Tono (Positivo/Negativo/Informativo)
           - Autor
           - Links
           - Categoría del medio
        5. **Explora** las pestañas de gráficas y tablas
        6. **Exporta** el resultado en formato Excel
        
        ### Formatos soportados:
        - **Excel**: Archivos con estructura de la plantilla de RTP
        - **PDF**: Síntesis informativas (procesadas con IA)
        - **Manual**: Ingreso directo de notas
        
        ### Ejemplo de PDF que funciona:
        - Síntesis informativa con encabezados "SÍNTESIS INFORMATIVA" y "NOTAS DE MOVILIDAD"
        - Notas separadas con títulos y mención del medio
        """)