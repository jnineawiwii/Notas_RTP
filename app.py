import io
import re
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import google.generativeai as genai

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
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Procesamiento inteligente de síntesis informativas, PDFs y reportes Excel.")

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

# Configuración de IA Gemini (opcional vía API Key en Sidebar o Secrets)
st.sidebar.header("🤖 Configuración de IA (Gemini)")
api_key = st.sidebar.text_input("Gemini API Key (Opcional):", type="password")
use_ai = False

if api_key:
    genai.configure(api_key=api_key)
    use_ai = True
    st.sidebar.success("IA Gemini Activada 🧠")

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

def process_pdf_file(pdf_file):
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

            tono = "Informativo"
            if "positivo" in text.lower():
                tono = "Positivo"
            elif "negativo" in text.lower():
                tono = "Negativo"

            relevante = "Sí" if "rtp" in text.lower() else "No"
            
            record = {
                'Año': pd.Timestamp.now().year,
                '# Mes': pd.Timestamp.now().month,
                'Mes': pd.Timestamp.now().strftime("%B").capitalize(),
                'Fecha ': pd.Timestamp.now().strftime("%Y-%m-%d"),
                'Título de la nota': titulo,
                'RTP, ¿Es relevante en la nota?': relevante,
                'Tema de la nota': f"Breve resumen: {titulo[:50]}...",
                'Campaña': map_campana(tono),
                'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
                'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
                'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': 'Portal Digital',
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
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

df = pd.DataFrame()

if uploaded_file:
    ext = uploaded_file.name.split(".")[-1].lower()
    if ext == "xlsx":
        xls = pd.ExcelFile(uploaded_file)
        sheet = st.sidebar.selectbox("Selecciona pestaña:", xls.sheet_names)
        df = pd.read_excel(uploaded_file, sheet_name=sheet)
    elif ext == "pdf":
        st.info("📄 Extrayendo datos del PDF...")
        df = process_pdf_file(uploaded_file)

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
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total de Notas", len(df))
    k2.markdown(f"**🟢 Positivas (RTP avanza)**: <span class='badge-positivo'>{len(df[df['Informativo / Positivo/ Negativo'] == 'Positivo'])}</span>", unsafe_allow_html=True)
    k3.markdown(f"**🟡 Informativas (RTP informa)**: <span class='badge-informativo'>{len(df[df['Informativo / Positivo/ Negativo'] == 'Informativo'])}</span>", unsafe_allow_html=True)
    k4.markdown(f"**🔴 Negativas (RTP informa)**: <span class='badge-negativo'>{len(df[df['Informativo / Positivo/ Negativo'] == 'Negativo'])}</span>", unsafe_allow_html=True)

    st.markdown("---")

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Gráficas de Tendencia", 
        "📋 Tabla de Registros", 
        "📻 Medios y Relevancia", 
        "📥 Exportar Excel"
    ])

    # TAB 1: GRÁFICAS DE TENDENCIA Y SEMÁFORO
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
        st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True)

    # TAB 3: MEDIOS Y RELEVANCIA (AQUÍ ESTABA EL ERROR CORREGIDO)
    with tab3:
        st.subheader("Análisis de Relevancia y Presencia")
        col_m1, col_m2 = st.columns(2)

        with col_m1:
            st.write("### Desglose por Campaña")
            st.dataframe(df['Campaña'].value_counts().reset_index(), use_container_width=True)

        with col_m2:
            st.write("### Relevancia de RTP en las Notas")
            # Corrección del conteo de Plotly
            df_rel = df['RTP, ¿Es relevante en la nota?'].value_counts().reset_index()
            df_rel.columns = ['Relevancia', 'Cantidad']
            
            fig_rel = px.bar(
                df_rel,
                x='Relevancia',
                y='Cantidad',
                color='Relevancia',
                title="Notas Relevantes para RTP"
            )
            st.plotly_chart(fig_rel, use_container_width=True)

    # TAB 4: EXPORTACIÓN
    with tab4:
        st.subheader("Exportar Excel Actualizado")
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel (.xlsx)",
            data=output.getvalue(),
            file_name="Seguimiento_en_Medios_RTP_Procesado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("👈 Por favor sube un archivo en la barra lateral para comenzar.")