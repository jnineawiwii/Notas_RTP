import io
import re
import urllib.request
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Monitoreo en Medios - RTP",
    page_icon="🚌",
    layout="wide"
)

# Estilos visuales con los colores requeridos (Semáforo)
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Procesamiento de síntesis en PDF, análisis de URLs de notas y reportes Excel con semáforo exacto.")

# Columnas oficiales según la plantilla SM_RTP_26_Ok.xlsx
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

def map_sentiment(val):
    """ Mapea la calificación estricta al semáforo: Positivo, Informativo o Negativo """
    if pd.isna(val):
        return "Informativo"
    val_str = str(val).strip().lower()
    if "positiv" in val_str:
        return "Positivo"
    if "negativ" in val_str:
        return "Negativo"
    return "Informativo"

def map_campana(sentiment, relevante):
    """
    Regla de Campaña:
    - Si la nota es Positiva -> 'RTP avanza'
    - Si no es positiva (Informativa o Negativa) -> 'RTP informa'
    """
    if sentiment == "Positivo":
        return "RTP avanza"
    return "RTP informa"

def extract_media_name(text):
    """ Detecta el nombre del medio en el texto """
    match = re.search(r'(?:medio|periódico|portal|fuente):\s*([^\n,]+)', text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Búsqueda de medios conocidos
    medios_conocidos = ["Milenio", "Televisa", "El Universal", "Reforma", "La Jornada", "Excélsior", "Telediario", "TV Azteca", "W Radio", "La Prensa", "Proceso", "N+"]
    for m in medios_conocidos:
        if m.lower() in text.lower():
            return m
    return "Portal Digital"

def process_url_note(url):
    """ Analiza el contenido básico de un Link/URL de una nota """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        html = urllib.request.urlopen(req, timeout=5).read().decode('utf-8', errors='ignore')
        
        # Extraer Título de la etiqueta <title>
        title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        titulo = title_match.group(1).strip() if title_match else url
        
        # Determinar tono por palabras clave en la página
        text_content = re.sub(r'<[^>]+>', ' ', html)
        tono = "Informativo"
        if any(w in text_content.lower() for w in ["beneficio", "mejora", "nuevo", "inaugura", "exito", "avanza"]):
            tono = "Positivo"
        elif any(w in text_content.lower() for w in ["falla", "queja", "retraso", "accidente", "caos", "bloqueo"]):
            tono = "Negativo"

        medio = extract_media_name(text_content)
        relevante = "Sí" if "rtp" in text_content.lower() or "red de transporte" in text_content.lower() else "No"
        
        return {
            'Año': pd.Timestamp.now().year,
            '# Mes': pd.Timestamp.now().month,
            'Mes': pd.Timestamp.now().strftime("%B").capitalize(),
            'Fecha ': pd.Timestamp.now().strftime("%Y-%m-%d"),
            'Título de la nota': titulo[:150],
            'RTP, ¿Es relevante en la nota?': relevante,
            'Tema de la nota': f"Nota web sobre: {titulo[:60]}...",
            'Campaña': map_campana(tono, relevante),
            'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
            'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
            'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio,
            'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
            'OTROS (Twitter, Facebook, You Tube, etc.).': None,
            'Informativo / Positivo/ Negativo': tono,
            'LINK': url,
            'Autor': 'Análisis de Link',
            'PUBLICACIÓN BOLETÍN': 'NO',
            'RESUMEN  DE LA NOTA (RTP)': text_content[:250].replace('\n', ' ') + "..."
        }
    except Exception as e:
        return None

def process_pdf_file(pdf_file):
    """ Procesa el PDF extrayendo estrictamente título, medio, link y tono semáforo """
    records = []
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            titulo = lines[0] if lines else f"Nota {i+1}"
            
            urls = re.findall(r'https?://[^\s]+', text)
            link = urls[0] if urls else ""

            # Detección estricta del sentido de la nota
            tono = "Informativo"
            if "positivo" in text.lower() or "positiva" in text.lower():
                tono = "Positivo"
            elif "negativo" in text.lower() or "negativa" in text.lower():
                tono = "Negativo"

            relevante = "Sí" if "rtp" in text.lower() else "No"
            medio = extract_media_name(text)
            tema_breve = f"Resumen de nota: {titulo[:50]}..."

            record = {
                'Año': pd.Timestamp.now().year,
                '# Mes': pd.Timestamp.now().month,
                'Mes': pd.Timestamp.now().strftime("%B").capitalize(),
                'Fecha ': pd.Timestamp.now().strftime("%Y-%m-%d"),
                'Título de la nota': titulo,
                'RTP, ¿Es relevante en la nota?': relevante,
                'Tema de la nota': tema_breve,
                'Campaña': map_campana(tono, relevante),
                'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
                'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
                'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio,
                'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
                'OTROS (Twitter, Facebook, You Tube, etc.).': None,
                'Informativo / Positivo/ Negativo': tono,
                'LINK': link,
                'Autor': 'Síntesis PDF',
                'PUBLICACIÓN BOLETÍN': 'NO',
                'RESUMEN  DE LA NOTA (RTP)': text[:300].replace('\n', ' ') + "..."
            }
            records.append(record)
    return pd.DataFrame(records)

# --- PANEL LATERAL ---
st.sidebar.header("📁 Carga de Información")
opcion_carga = st.sidebar.radio("Selecciona origen de datos:", ["Subir Archivo (Excel / PDF)", "Analizar Link de Nota Directa"])

df = pd.DataFrame()

if opcion_carga == "Subir Archivo (Excel / PDF)":
    uploaded_file = st.sidebar.file_uploader("Sube tu Excel o PDF:", type=["xlsx", "pdf"])
    if uploaded_file:
        ext = uploaded_file.name.split(".")[-1].lower()
        if ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            sheet = st.sidebar.selectbox("Selecciona la pestaña:", xls.sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet)
        elif ext == "pdf":
            st.info("📄 Procesando PDF de Síntesis Informativa...")
            df = process_pdf_file(uploaded_file)

elif opcion_carga == "Analizar Link de Nota Directa":
    url_input = st.sidebar.text_input("Ingresa la URL/Link de la nota:")
    if st.sidebar.button("Analizar Nota"):
        if url_input:
            with st.spinner("Analizando contenido del enlace..."):
                res = process_url_note(url_input)
                if res:
                    df = pd.DataFrame([res])
                    st.sidebar.success("¡Link analizado correctamente!")
                else:
                    st.sidebar.error("No se pudo extraer información de esa URL.")

# --- PROCESAMIENTO Y DASHBOARD ---
if not df.empty:
    # Asegurar columnas exactas
    for col in OFFICIAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # Normalizar Tono de la Nota
    df['Informativo / Positivo/ Negativo'] = df['Informativo / Positivo/ Negativo'].apply(map_sentiment)
    
    # Aplicar regla estricta de Campaña
    df['Campaña'] = df.apply(lambda row: map_campana(row['Informativo / Positivo/ Negativo'], row['RTP, ¿Es relevante en la nota?']), axis=1)

    # Formato de Fecha limpia
    if 'Fecha ' in df.columns:
        df['Fecha_Limpia'] = pd.to_datetime(df['Fecha '], errors='coerce').dt.strftime('%Y-%m-%d')
    else:
        df['Fecha_Limpia'] = "Sin Fecha"

    # --- MÉTRICAS EN PANTALLA ---
    st.subheader("📌 Resumen con Semáforo Informativo")
    
    k1, k2, k3, k4 = st.columns(4)
    tot_notas = len(df)
    pos_notas = len(df[df['Informativo / Positivo/ Negativo'] == 'Positivo'])
    inf_notas = len(df[df['Informativo / Positivo/ Negativo'] == 'Informativo'])
    neg_notas = len(df[df['Informativo / Positivo/ Negativo'] == 'Negativo'])

    k1.metric("Total de Notas", tot_notas)
    k2.markdown(f"**🟢 Positivas (RTP avanza)**: <span class='badge-positivo'>{pos_notas}</span>", unsafe_allow_html=True)
    k3.markdown(f"**🟡 Informativas (RTP informa)**: <span class='badge-informativo'>{inf_notas}</span>", unsafe_allow_html=True)
    k4.markdown(f"**🔴 Negativas (RTP informa)**: <span class='badge-negativo'>{neg_notas}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Gráficas de Tendencia y Análisis", 
        "📋 Tabla de Registros (Oficial)", 
        "📻 Medios y Campañas", 
        "📥 Exportar Excel"
    ])

    # TAB 1: GRÁFICAS DE TENDENCIA (LO SOLICITADO)
    with tab1:
        st.subheader("Análisis de Tendencias por Fecha y Postura")
        
        c_g1, c_g2 = st.columns(2)

        with c_g1:
            # 1. ¿Qué día salieron más notas y con qué postura?
            df_fecha_postura = df.groupby(['Fecha_Limpia', 'Informativo / Positivo/ Negativo']).size().reset_index(name='Cantidad')
            
            fig_line = px.bar(
                df_fecha_postura, 
                x='Fecha_Limpia', 
                y='Cantidad', 
                color='Informativo / Positivo/ Negativo',
                title="Volumen de Notas por Día y Tono (Semáforo)",
                color_discrete_map={
                    'Positivo': '#28a745',    # Verde
                    'Informativo': '#ffc107', # Amarillo
                    'Negativo': '#dc3545'     # Rojo
                },
                barmode='stack'
            )
            fig_line.update_layout(xaxis_title="Fecha de Publicación", yaxis_title="Número de Notas")
            st.plotly_chart(fig_line, use_container_width=True)

        with c_g2:
            # 2. Distribución Semáforo General
            fig_pie = px.pie(
                df, 
                names='Informativo / Positivo/ Negativo', 
                title="Proporción del Semáforo Informativo",
                color='Informativo / Positivo/ Negativo',
                color_discrete_map={
                    'Positivo': '#28a745',
                    'Informativo': '#ffc107',
                    'Negativo': '#dc3545'
                },
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # 3. Tendencia de Campaña (RTP avanza vs. RTP informa)
        st.subheader("Seguimiento por Campaña (RTP avanza / RTP informa)")
        df_camp = df.groupby(['Fecha_Limpia', 'Campaña']).size().reset_index(name='Cantidad')
        fig_camp = px.line(
            df_camp, 
            x='Fecha_Limpia', 
            y='Cantidad', 
            color='Campaña',
            markers=True,
            title="Evolución Diaria por Tipo de Campaña",
            color_discrete_map={'RTP avanza': '#28a745', 'RTP informa': '#0066cc'}
        )
        st.plotly_chart(fig_camp, use_container_width=True)

    # TAB 2: TABLA COMPLETA
    with tab2:
        st.subheader("Registro de Datos con Filtros")
        st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True)

    # TAB 3: MEDIOS
    with tab3:
        st.subheader("Distribución de Notas por Medios")
        
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            # Conteo de Campañas
            st.write("### Resumen por Campaña")
            st.dataframe(df['Campaña'].value_counts().reset_index(name='Total'), use_container_width=True)

        with col_m2:
            # Relevancia RTP
            st.write("### ¿RTP es relevante en la nota?")
            fig_rel = px.bar(
                df['RTP, ¿Es relevante en la nota?'].value_counts().reset_index(),
                x='index', y='RTP, ¿Es relevante en la nota?',
                title="Menciones Relevantes de RTP",
                labels={'index':'Relevante', 'RTP, ¿Es relevante en la nota?':'Cantidad'}
            )
            st.plotly_chart(fig_rel, use_container_width=True)

    # TAB 4: EXPORTAR A EXCEL
    with tab4:
        st.subheader("Exportar Reporte Generado")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel Oficial (.xlsx)",
            data=output.getvalue(),
            file_name="Seguimiento_en_Medios_RTP_Actualizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👈 Por favor selecciona un origen de datos en el panel izquierdo (Archivo Excel/PDF o Link de Nota).")