import io
import re
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import google.generativeai as genai
from datetime import datetime

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
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Procesamiento inteligente de síntesis informativas, PDFs y reportes Excel.")

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

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro')
        use_ai = True
        st.sidebar.success("✅ IA Gemini Activada")
    except Exception as e:
        st.sidebar.error(f"⚠️ Error al configurar IA: {e}")
        use_ai = False

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

def detect_media_type(text):
    """Detecta el tipo de medio basado en el texto"""
    text_lower = text.lower()
    if 'twitter' in text_lower or 'x.com' in text_lower or 'facebook' in text_lower:
        return 'OTROS (Twitter, Facebook, You Tube, etc.).'
    elif 'youtube' in text_lower or 'tiktok' in text_lower:
        return 'OTROS (Twitter, Facebook, You Tube, etc.).'
    elif 'radio' in text_lower or 'fm' in text_lower:
        return 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
    elif 'televisa' in text_lower or 'tv' in text_lower or 'canal' in text_lower:
        return 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
    elif '.com' in text_lower or 'portal' in text_lower:
        return 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
    else:
        return 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *'

def extract_author(text):
    """Intenta extraer el autor del texto"""
    patterns = [
        r'(?:Autor(?:a)?|Por|Escrito por|Redacción|Fotos?)\s*[:：]?\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)',
        r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*)\s*(?:[A-Z]{2,}|\d+)?$',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return "Redacción"

def extract_links(text):
    """Extrae URLs del texto"""
    urls = re.findall(r'https?://[^\s\n<>"]+', text)
    return urls[0] if urls else ""

def extract_title_from_line(line):
    """Intenta extraer un título de una línea de texto"""
    line = line.strip()
    if not line:
        return None
    
    # Eliminar números de página o indicadores de sección al inicio
    line = re.sub(r'^\d+\s*', '', line)
    
    # Si la línea es corta o tiene caracteres especiales, probablemente es un título
    if len(line) < 100 and not line.endswith('.') and not line.endswith(','):
        # Verificar que no sea un encabezado de sección conocido
        skip_patterns = [
            r'^SÍNTESIS INFORMATIVA',
            r'^NOTAS DE MOVILIDAD',
            r'^RED DE TRANSPORTE',
            r'^Página',
            r'^MEDIOS:',
            r'^[A-Z\s]{10,}$'  # Solo mayúsculas sin contenido
        ]
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return None
        return line
    return None

def process_pdf_content(full_text):
    """Procesa el texto del PDF dividiéndolo en notas individuales"""
    records = []
    
    # Dividir por páginas o secciones
    lines = full_text.split('\n')
    
    # Buscar estructura de "SÍNTESIS INFORMATIVA" y "NOTAS DE MOVILIDAD"
    current_section = "notas"
    current_note = {}
    buffer = []
    titles_found = []
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Detectar secciones
        if "SÍNTESIS INFORMATIVA" in line.upper():
            current_section = "sintesis"
            i += 1
            continue
        elif "NOTAS DE MOVILIDAD" in line.upper():
            current_section = "notas"
            i += 1
            continue
        elif "MEDIOS:" in line:
            # Esta línea contiene el medio
            if buffer:
                # Procesar nota anterior
                note_text = '\n'.join(buffer)
                title = extract_titles_from_buffer(buffer, titles_found)
                if title:
                    record = create_record_from_note(note_text, title)
                    if record:
                        # Agregar medio desde esta línea
                        media_match = re.search(r'MEDIOS:\s*(.*?)(?:\s*https?://|\s*$)', line, re.IGNORECASE)
                        if media_match:
                            record['MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'] = media_match.group(1).strip()
                        records.append(record)
                buffer = []
                titles_found = []
            i += 1
            continue
        
        # Intentar extraer título de la línea
        potential_title = extract_title_from_line(line)
        if potential_title and len(potential_title) > 5:
            titles_found.append(potential_title)
            # Si hay un título y buffer no está vacío, es una nueva nota
            if buffer and len(buffer) > 3:
                note_text = '\n'.join(buffer)
                title = extract_titles_from_buffer(buffer, titles_found[:-1]) or titles_found[-2] if len(titles_found) > 1 else None
                if title:
                    record = create_record_from_note(note_text, title)
                    if record:
                        records.append(record)
                buffer = [line]
            else:
                buffer.append(line)
        elif line and len(line) > 10:
            buffer.append(line)
        
        i += 1
    
    # Procesar última nota
    if buffer:
        note_text = '\n'.join(buffer)
        title = extract_titles_from_buffer(buffer, titles_found)
        if title:
            record = create_record_from_note(note_text, title)
            if record:
                records.append(record)
    
    return records

def extract_titles_from_buffer(buffer, titles_found):
    """Extrae el título más probable de un buffer de líneas"""
    for line in buffer[:5]:
        title = extract_title_from_line(line)
        if title:
            return title
    # Si no se encontró, buscar en títulos encontrados
    for title in titles_found:
        if title and len(title) > 5:
            return title
    return None

def create_record_from_note(text, title):
    """Crea un registro estructurado a partir de una nota"""
    if not text or len(text) < 20:
        return None
    
    # Limpiar título
    title = re.sub(r'^\d+\s*', '', title).strip()
    
    # Usar IA si está disponible
    ai_data = None
    if use_ai and model:
        ai_data = analyze_with_ai(text, model)
    
    if ai_data:
        final_title = ai_data.get('titulo', title)
        resumen = ai_data.get('resumen', extract_summary(text))
        tono = ai_data.get('tono', 'Informativo')
        relevante = ai_data.get('relevante', 'Sí' if 'rtp' in text.lower() else 'No')
        tema = ai_data.get('tema', f"Nota: {final_title[:50]}")
        autor = ai_data.get('autor', extract_author(text))
    else:
        final_title = title
        resumen = extract_summary(text)
        tono = "Positivo" if "positivo" in text.lower() else "Negativo" if "negativo" in text.lower() else "Informativo"
        relevante = "Sí" if "rtp" in text.lower() else "No"
        tema = f"Nota: {final_title[:50]}"
        autor = extract_author(text)
    
    # Detectar medio
    medio_digital = detect_media_type(text)
    
    # Buscar medio específico en el texto
    media_match = re.search(r'MEDIOS?:\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+(?:,\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ\s]+)*)', text, re.IGNORECASE)
    if media_match:
        medio_digital = media_match.group(1).strip()
    
    link = extract_links(text)
    
    record = {
        'Año': datetime.now().year,
        '# Mes': datetime.now().month,
        'Mes': datetime.now().strftime("%B").capitalize(),
        'Fecha ': datetime.now().strftime("%Y-%m-%d"),
        'Título de la nota': final_title,
        'RTP, ¿Es relevante en la nota?': relevante,
        'Tema de la nota': tema,
        'Campaña': map_campana(tono),
        'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
        'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
        'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio_digital,
        'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
        'OTROS (Twitter, Facebook, You Tube, etc.).': None,
        'Informativo / Positivo/ Negativo': tono,
        'LINK': link,
        'Autor': autor,
        'PUBLICACIÓN BOLETÍN': 'NO',
        'RESUMEN  DE LA NOTA (RTP)': resumen
    }
    return record

def analyze_with_ai(text, model):
    """Usa Gemini AI para analizar el texto de la nota"""
    if not model:
        return None
    
    prompt = f"""
    Analiza la siguiente nota periodística sobre la Red de Transporte de Pasajeros (RTP) de la CDMX.
    
    Texto de la nota:
    {text[:3000]}
    
    Extrae la siguiente información en formato JSON:
    {{
        "titulo": "El título principal de la nota",
        "resumen": "Un resumen conciso de la nota (máximo 200 palabras)",
        "tono": "Positivo, Negativo o Informativo",
        "relevante": "Sí o No dependiendo si RTP es relevante",
        "tema": "El tema principal de la nota",
        "autor": "El autor si se menciona"
    }}
    
    Responde SOLO con el JSON, sin texto adicional.
    """
    
    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Limpiar respuesta
        json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())
        return None
    except Exception as e:
        st.warning(f"⚠️ Error en análisis IA: {e}")
        return None

def extract_summary(text, max_len=500):
    """Extrae un resumen del texto"""
    # Buscar secciones de resumen
    summary_patterns = [
        r'(?:Resumen|Síntesis|En resumen)\s*[:：]?\s*([^\n]+)',
        r'(?:La nota|El artículo|El reporte|La información)\s*(?:[^\n]{50,})'
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:max_len]
    
    # Si no hay resumen, tomar las primeras líneas significativas
    lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 30]
    if lines:
        summary = lines[0]
        if len(lines) > 1 and len(summary) < 100:
            summary += " " + lines[1]
        return summary[:max_len]
    
    return text[:max_len].replace('\n', ' ') + "..."

def process_pdf_file(pdf_file):
    """Procesa un archivo PDF extrayendo notas estructuradas"""
    records = []
    
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
        
        if not full_text.strip():
            st.error("❌ No se pudo extraer texto del PDF")
            return pd.DataFrame()
        
        # Mostrar vista previa del texto para debugging
        with st.expander("📄 Vista previa del texto extraído"):
            st.text(full_text[:2000])
        
        # Procesar el texto
        records = process_pdf_content(full_text)
    
    if not records:
        st.warning("⚠️ No se pudieron identificar notas en el PDF. Verifica el formato.")
        # Intentar método alternativo: dividir por líneas en blanco
        st.info("🔄 Intentando método alternativo de división...")
        sections = re.split(r'\n\s*\n', full_text)
        sections = [s for s in sections if len(s.strip()) > 50]
        
        for section in sections:
            lines = section.split('\n')
            first_line = lines[0].strip() if lines else ""
            title = extract_title_from_line(first_line) or first_line[:50]
            record = create_record_from_note(section, title)
            if record:
                records.append(record)
    
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
            with st.spinner("📄 Procesando PDF con IA..."):
                df = process_pdf_file(uploaded_file)
            if not df.empty:
                st.success(f"✅ PDF procesado: {len(df)} notas extraídas")
    except Exception as e:
        st.error(f"❌ Error al procesar archivo: {e}")

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
        'Campaña': 'RTP avanza' if 'positivo' in manual_resumen.lower() else 'RTP informa',
        'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
        'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
        'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': manual_medio or 'Portal Digital',
        'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
        'OTROS (Twitter, Facebook, You Tube, etc.).': None,
        'Informativo / Positivo/ Negativo': 'Positivo' if 'positivo' in manual_resumen.lower() else 'Informativo',
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
        ### Instrucciones de uso:
        
        1. **Sube un archivo** (Excel o PDF) en la barra lateral
        2. **Opcional**: Activa la IA con tu API Key de Gemini para mejor análisis
        3. **Agrega notas manuales** si lo deseas
        4. **Explora** las pestañas de gráficas y tablas
        5. **Exporta** el resultado en formato Excel
        
        ### Formatos soportados:
        - **Excel**: Archivos con estructura similar a la plantilla de RTP
        - **PDF**: Síntesis informativas con notas periodísticas
        - **Manual**: Ingreso directo de URL, título y resumen
        
        ### Requisitos para IA (Gemini):
        - Obtén tu API Key en [ai.google.dev](https://ai.google.dev)
        - La IA ayuda a extraer: título, resumen, tono, autor y medio
        """)