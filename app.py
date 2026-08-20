import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber

# Configuración de página
st.set_page_config(
    page_title="Sistema de Monitoreo y Seguimiento en Medios RTP",
    page_icon="🚌",
    layout="wide"
)

# Estilo visual personalizado
st.markdown("""
<style>
    .metric-box {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border-left: 5px solid #0066cc;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Monitoreo y Seguimiento en Medios - RTP")
st.caption("Sistema automatizado de análisis de notas informativas y reportes de medios.")

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

def clean_sentiment(val):
    """ Normaliza el sentido de la nota: Positivo, Negativo o Informativo """
    if pd.isna(val):
        return "Informativo"
    val = str(val).strip().capitalize()
    if "Posit" in val:
        return "Positivo"
    if "Negat" in val:
        return "Negativo"
    if "Inform" in val or "Info" in val:
        return "Informativo"
    return "Informativo"

def extract_pdf_to_official_df(pdf_file):
    """ Parsea el PDF de síntesis informativa al formato de 18 columnas """
    records = []
    
    with pdfplumber.open(pdf_file) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue
            
            # Buscar links en la página
            urls = re.findall(r'https?://[^\s]+', text)
            link = urls[0] if urls else ""

            # Extraer título y medio
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            titulo = lines[0] if lines else f"Nota {i+1}"
            
            # Tono de la nota
            tono = "Informativo"
            if "positiv" in text.lower():
                tono = "Positivo"
            elif "negativ" in text.lower():
                tono = "Negativo"

            record = {
                'Año': pd.Timestamp.now().year,
                '# Mes': pd.Timestamp.now().month,
                'Mes': pd.Timestamp.now().strftime("%B").capitalize(),
                'Fecha ': pd.Timestamp.now().strftime("%Y-%m-%d"),
                'Título de la nota': titulo[:150],
                'RTP, ¿Es relevante en la nota?': 'Si' if 'RTP' in text.upper() else 'NO',
                'Tema de la nota': 'Síntesis Informativa Diario',
                'Campaña': 'Monitoreo General',
                'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': None,
                'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': None,
                'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': 'Portal Web',
                'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': None,
                'OTROS (Twitter, Facebook, You Tube, etc.).': None,
                'Informativo / Positivo/ Negativo': tono,
                'LINK': link,
                'Autor': 'Síntesis RTP',
                'PUBLICACIÓN BOLETÍN': 'NO',
                'RESUMEN  DE LA NOTA (RTP)': text[:300].replace('\n', ' ') + "..."
            }
            records.append(record)

    return pd.DataFrame(records, columns=OFFICIAL_COLUMNS)

# Sidebar para carga
st.sidebar.header("📂 Carga de Archivo")
uploaded_file = st.sidebar.file_uploader(
    "Sube tu reporte (.xlsx) o síntesis (.pdf)", 
    type=["xlsx", "pdf"]
)

if uploaded_file is not None:
    file_ext = uploaded_file.name.split(".")[-1].lower()
    df = pd.DataFrame()

    try:
        if file_ext == "xlsx":
            xls = pd.ExcelFile(uploaded_file)
            sheet_name = st.sidebar.selectbox("Selecciona la pestaña:", xls.sheet_names)
            df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        elif file_ext == "pdf":
            st.info("📄 Extrayendo datos del PDF de síntesis informativa...")
            df = extract_pdf_to_official_df(uploaded_file)

        # Asegurar columnas estándar
        for col in OFFICIAL_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Limpieza de clasificación
        df['Informativo / Positivo/ Negativo'] = df['Informativo / Positivo/ Negativo'].apply(clean_sentiment)

        # FILTROS LATERALES
        st.sidebar.markdown("---")
        st.sidebar.header("🔍 Filtros de Búsqueda")
        
        # Filtro de Mes
        meses_disp = [m for m in df['Mes'].dropna().unique()]
        if meses_disp:
            selected_mes = st.sidebar.multiselect("Filtrar por Mes:", opciones:=meses_disp, default=meses_disp)
            df = df[df['Mes'].isin(selected_mes)]

        # Filtro de Clasificación
        tonos_disp = df['Informativo / Positivo/ Negativo'].unique().tolist()
        selected_tono = st.sidebar.multiselect("Filtrar por Sentido de la Nota:", tonos_disp, default=tonos_disp)
        df = df[df['Informativo / Positivo/ Negativo'].isin(selected_tono)]

        # --- PANEL PRINCIPAL ---
        st.subheader("📌 Resumen General")
        
        # Métricas principales
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Notas", len(df))
        m2.metric("Notas Positivas", len(df[df['Informativo / Positivo/ Negativo'] == 'Positivo']))
        m3.metric("Notas Negativas", len(df[df['Informativo / Positivo/ Negativo'] == 'Negativo']))
        m4.metric("Notas Informativas", len(df[df['Informativo / Positivo/ Negativo'] == 'Informativo']))

        # TABS DE NAVEGACIÓN
        tab_tabla, tab_graficos, tab_medios, tab_export = st.tabs([
            "📋 Tabla de Registro", 
            "📊 Dashboard de Análisis", 
            "📻 Análisis por Canal/Medio",
            "📥 Descargar Excel"
        ])

        # TAB 1: TABLA EXACTA COMO EL EXCEL
        with tab_tabla:
            st.subheader("Registro de Notas (Estructura Oficial)")
            st.dataframe(df[OFFICIAL_COLUMNS], use_container_width=True)

        # TAB 2: ANÁLISIS GRÁFICO
        with tab_graficos:
            st.subheader("Distribución de Notas y Tendencias")
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                # Gráfico Donut Tono
                tono_counts = df['Informativo / Positivo/ Negativo'].value_counts().reset_index()
                tono_counts.columns = ['Sentido', 'Cantidad']
                fig_pie = px.pie(
                    tono_counts, 
                    names='Sentido', 
                    values='Cantidad', 
                    title="Balance de Postura (Positivo / Negativo / Informativo)",
                    color='Sentido',
                    color_discrete_map={'Positivo': '#2ecc71', 'Negativo': '#e74c3c', 'Informativo': '#3498db'},
                    hole=0.4
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                # Gráfico por Temas Principales
                top_temas = df['Tema de la nota'].value_counts().head(10).reset_index()
                top_temas.columns = ['Tema', 'Cantidad']
                fig_bar_tema = px.bar(
                    top_temas, 
                    x='Cantidad', 
                    y='Tema', 
                    orientation='h',
                    title="Top 10 Temas Más Mencionados",
                    color='Cantidad',
                    color_continuous_scale='Blues'
                )
                fig_bar_tema.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar_tema, use_container_width=True)

        # TAB 3: MEDIOS
        with tab_medios:
            st.subheader("Desglose por Tipo de Medio")
            
            medios_cat = {
                'Radio': 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ',
                'Televisión': 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *',
                'Digitales / Internet': 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *',
                'Impresos': 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *',
                'Redes Sociales': 'OTROS (Twitter, Facebook, You Tube, etc.).'
            }

            conteo_medios = []
            for nombre, col in medios_cat.items():
                cant = df[col].dropna().count()
                conteo_medios.append({'Tipo de Medio': nombre, 'Total Notas': cant})

            df_medios_summary = pd.DataFrame(conteo_medios)
            
            col_m1, col_m2 = st.columns([1, 2])
            with col_m1:
                st.dataframe(df_medios_summary, use_container_width=True)
            
            with col_m2:
                fig_medios = px.bar(
                    df_medios_summary, 
                    x='Tipo de Medio', 
                    y='Total Notas',
                    title="Presencia por Tipo de Medio",
                    color='Tipo de Medio'
                )
                st.plotly_chart(fig_medios, use_container_width=True)

        # TAB 4: EXPORTAR A EXCEL
        with tab_export:
            st.subheader("Descargar Reporte Actualizado")
            st.write("Genera un archivo Excel con el formato exacto de 18 columnas y los filtros aplicados.")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_RTP", index=False)
            
            excel_bytes = output.getvalue()

            st.download_button(
                label="📥 Descargar Excel (.xlsx)",
                data=excel_bytes,
                file_name="Seguimiento_en_Medios_RTP_Procesado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Error procesando el archivo: {str(e)}")

else:
    st.info("👆 Por favor sube tu archivo `SM_RTP_26_Ok.xlsx` o tu síntesis en PDF para iniciar el análisis.")