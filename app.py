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
    layout="wide"
)

# Estilos visuales mejorados
st.markdown("""
<style>
    .pdf-text-container {
        background: white;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #dee2e6;
        max-height: 600px;
        overflow-y: auto;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.6;
        color: #000000;
        white-space: pre-wrap;
    }
    .pdf-text-container p {
        color: #000000 !important;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0px 0px; padding: 12px 20px; background-color: #f0f2f6; font-weight: bold; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #007bff; color: white; }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Captura de Notas - Monitoreo RTP")
st.caption("Abre el PDF, copia el texto y asígnalo a cada campo con los botones")

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

def map_campana(sentiment):
    if sentiment == "Positivo":
        return "RTP avanza"
    return "RTP informa"

def extract_text_from_pdf(pdf_bytes):
    """Extrae texto de un PDF usando pdfplumber"""
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
    """Genera un enlace de descarga para el PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">📄 Descargar PDF</a>'

# --- INICIALIZAR SESSION STATE ---
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

# --- SIDEBAR ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

st.sidebar.header("📊 Notas Capturadas")
st.sidebar.metric("Total Notas", len(st.session_state.notas_capturadas))

if st.sidebar.button("🗑️ Limpiar todas las notas"):
    st.session_state.notas_capturadas = []
    st.session_state.nota_actual = {}
    st.session_state.texto_seleccionado = ""
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
        pdf_bytes = uploaded_file.getvalue()
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_filename = uploaded_file.name
        # Extraer texto del PDF
        st.session_state.pdf_text = extract_text_from_pdf(pdf_bytes)
        st.sidebar.success(f"✅ PDF cargado: {uploaded_file.name}")

# --- INTERFAZ PRINCIPAL ---
tab1, tab2, tab3, tab4 = st.tabs(["📄 Visualizar PDF y Capturar", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])

# --- TAB 1: VISUALIZAR PDF Y CAPTURAR ---
with tab1:
    if st.session_state.pdf_bytes:
        
        st.markdown("### 📄 PDF Original")
        
        # Opciones de visualización
        view_option = st.radio(
            "Selecciona cómo ver el PDF:",
            ["📝 Ver texto extraído", "📄 Descargar y abrir PDF"],
            horizontal=True
        )
        
        if view_option == "📝 Ver texto extraído":
            st.markdown("**💡 Instrucción:** Selecciona y copia el texto del PDF desde abajo, pégalo en el campo correspondiente")
            
            # Mostrar el texto extraído del PDF
            if st.session_state.pdf_text:
                st.markdown("#### 📄 Contenido del PDF (texto extraído)")
                st.markdown(
                    f'<div class="pdf-text-container">{st.session_state.pdf_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No se pudo extraer texto del PDF. Intenta con el visor nativo.")
                # Opción de descarga
                st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
        
        else:
            st.markdown("**💡 Haz clic en el botón para descargar y abrir el PDF en tu visor predeterminado**")
            st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
            st.info("📌 Después de abrir el PDF, selecciona y copia el texto que necesites, luego pégalo abajo.")
        
        st.markdown("---")
        
        # Área de captura - SIN COLORES
        col_texto, col_botones = st.columns([1, 1])
        
        with col_texto:
            st.markdown("### 📝 Texto seleccionado")
            
            st.info("📋 **Instrucciones:**\n1. Selecciona texto del PDF (de la vista de texto o del PDF descargado)\n2. Cópialo (Ctrl+C o Cmd+C)\n3. Pégalo aquí abajo\n4. Presiona el botón del campo correspondiente")
            
            texto_pegado = st.text_area(
                "Pega aquí el texto que copiaste del PDF",
                value=st.session_state.texto_seleccionado,
                height=150,
                placeholder="Ejemplo: 'RTP que fue transformado en Papamóvil...'",
                key="texto_pegado_input",
                label_visibility="collapsed"
            )
            
            if texto_pegado != st.session_state.texto_seleccionado:
                st.session_state.texto_seleccionado = texto_pegado
            
            # Mostrar el texto actual asignado
            if st.session_state.nota_actual:
                st.markdown("#### 📋 Campos asignados en esta nota:")
                campos_info = []
                if st.session_state.nota_actual.get('titulo'):
                    campos_info.append(f"✅ Título: {st.session_state.nota_actual['titulo'][:50]}...")
                if st.session_state.nota_actual.get('resumen'):
                    campos_info.append(f"✅ Resumen: {st.session_state.nota_actual['resumen'][:50]}...")
                if st.session_state.nota_actual.get('medio'):
                    campos_info.append(f"✅ Medio: {st.session_state.nota_actual['medio']}")
                if st.session_state.nota_actual.get('autor'):
                    campos_info.append(f"✅ Autor: {st.session_state.nota_actual['autor']}")
                if st.session_state.nota_actual.get('link'):
                    campos_info.append(f"✅ Link: {st.session_state.nota_actual['link'][:50]}...")
                if st.session_state.nota_actual.get('tema'):
                    campos_info.append(f"✅ Tema: {st.session_state.nota_actual['tema']}")
                
                if campos_info:
                    for info in campos_info:
                        st.text(info)
                else:
                    st.info("⬜ Ningún campo asignado aún")
        
        with col_botones:
            st.markdown("### 🎯 Asignar a campo")
            st.markdown("**Presiona el botón del campo donde quieras guardar el texto**")
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                # Título
                if st.button("📌 Título de la nota", use_container_width=True, key="btn_titulo"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['titulo'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Título")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                # Resumen
                if st.button("📝 RESUMEN DE LA NOTA (RTP)", use_container_width=True, key="btn_resumen"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['resumen'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Resumen")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                # Medio
                if st.button("📰 MEDIOS DE COMUNICACIÓN", use_container_width=True, key="btn_medio"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['medio'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Medio")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
            
            with col_btn2:
                # Autor
                if st.button("✍️ Autor", use_container_width=True, key="btn_autor"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['autor'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Autor")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                # Link
                if st.button("🔗 LINK", use_container_width=True, key="btn_link"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['link'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Link")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                # Tema
                if st.button("📂 Tema de la nota", use_container_width=True, key="btn_tema"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['tema'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Tema")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
        
        # Configuración adicional
        st.markdown("---")
        st.markdown("### ⚙️ Configuración de la nota")
        
        col_config1, col_config2, col_config3 = st.columns(3)
        
        with col_config1:
            relevancia = st.selectbox(
                "🎯 ¿Es relevante para RTP?",
                ["Sí", "No"],
                index=0 if st.session_state.relevancia_seleccionada == "Sí" else 1,
                key="select_relevancia"
            )
            st.session_state.relevancia_seleccionada = relevancia
        
        with col_config2:
            tono = st.selectbox(
                "🎯 Tono de la nota",
                ["Informativo", "Positivo", "Negativo"],
                index=["Informativo", "Positivo", "Negativo"].index(st.session_state.tono_seleccionado),
                key="select_tono"
            )
            st.session_state.tono_seleccionado = tono
        
        with col_config3:
            if st.session_state.nota_actual.get('link') and st.session_state.nota_actual['link'].startswith('http'):
                st.markdown(f'🔗 <a href="{st.session_state.nota_actual["link"]}" target="_blank">Abrir link</a>', unsafe_allow_html=True)
        
        # Botón guardar
        st.markdown("---")
        col_guardar1, col_guardar2, col_guardar3 = st.columns([1, 2, 1])
        with col_guardar2:
            if st.button("💾 GUARDAR NOTA COMPLETA", use_container_width=True, key="btn_guardar_completa"):
                if st.session_state.nota_actual.get('titulo'):
                    today = datetime.now()
                    medio = st.session_state.nota_actual.get('medio', '')
                    
                    tipo_medio = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
                    if any(x in medio.lower() for x in ['radio', 'fm', 'am']):
                        tipo_medio = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
                    elif any(x in medio.lower() for x in ['tv', 'canal', 'televisa', 'televisión']):
                        tipo_medio = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
                    elif any(x in medio.lower() for x in ['twitter', 'facebook', 'youtube', 'instagram']):
                        tipo_medio = 'OTROS (Twitter, Facebook, You Tube, etc.).'
                    
                    nota_completa = {
                        'Año': today.year,
                        '# Mes': today.month,
                        'Mes': today.strftime("%B").capitalize(),
                        'Fecha ': today.strftime("%Y-%m-%d"),
                        'Título de la nota': st.session_state.nota_actual.get('titulo', ''),
                        'RTP, ¿Es relevante en la nota?': relevancia,
                        'Tema de la nota': st.session_state.nota_actual.get('tema', 'General'),
                        'Campaña': map_campana(tono),
                        'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ' else '',
                        'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *' else '',
                        'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if tipo_medio == 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *' else '',
                        'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if tipo_medio == 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *' else '',
                        'OTROS (Twitter, Facebook, You Tube, etc.).': medio if tipo_medio == 'OTROS (Twitter, Facebook, You Tube, etc.).' else '',
                        'Informativo / Positivo/ Negativo': tono,
                        'LINK': st.session_state.nota_actual.get('link', ''),
                        'Autor': st.session_state.nota_actual.get('autor', 'Redacción'),
                        'PUBLICACIÓN BOLETÍN': 'NO',
                        'RESUMEN  DE LA NOTA (RTP)': st.session_state.nota_actual.get('resumen', '')
                    }
                    st.session_state.notas_capturadas.append(nota_completa)
                    st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada")
                    st.session_state.nota_actual = {}
                    st.session_state.texto_seleccionado = ""
                    st.rerun()
                else:
                    st.error("⚠️ El Título es obligatorio")
    
    else:
        st.info("📄 Sube un archivo PDF en la barra lateral para visualizarlo y capturar notas")
        st.markdown("""
        ### 📖 ¿Cómo empezar?
        
        1. **Sube un PDF** en la barra lateral izquierda
        2. El texto del PDF se extraerá automáticamente
        3. **Selecciona y copia** el texto que necesites
        4. **Pégalo** en el campo de texto
        5. **Presiona el botón** del campo correspondiente
        6. **Guarda** la nota completa
        """)

# --- TAB 2: TABLA DE NOTAS ---
with tab2:
    st.subheader("📋 Tabla de Notas Capturadas")
    if st.session_state.notas_capturadas:
        df_show = pd.DataFrame(st.session_state.notas_capturadas)
        columns_to_show = [col for col in OFFICIAL_COLUMNS if col in df_show.columns]
        st.dataframe(df_show[columns_to_show], use_container_width=True, height=500)
        
        st.markdown("### 📊 Estadísticas")
        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
        col_est1.metric("Total Notas", len(df_show))
        if 'Informativo / Positivo/ Negativo' in df_show.columns:
            col_est2.metric("Positivas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Positivo']))
            col_est3.metric("Informativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Informativo']))
            col_est4.metric("Negativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Negativo']))
    else:
        st.info("No hay notas capturadas aún")

# --- TAB 3: GRÁFICAS ---
with tab3:
    st.subheader("📊 Análisis Gráfico")
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
                st.plotly_chart(fig_campana, use_container_width=True)
        
        if 'RTP, ¿Es relevante en la nota?' in df_graph.columns:
            fig_relevancia = px.bar(
                df_graph,
                x='RTP, ¿Es relevante en la nota?',
                title="Relevancia para RTP",
                color='RTP, ¿Es relevante en la nota?',
                color_discrete_map={'Sí': '#28a745', 'No': '#dc3545'}
            )
            st.plotly_chart(fig_relevancia, use_container_width=True)
        
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
            st.plotly_chart(fig_temas, use_container_width=True)
    else:
        st.info("No hay suficientes datos para mostrar gráficas")

# --- TAB 4: EXPORTAR ---
with tab4:
    st.subheader("📥 Exportar a Excel")
    
    if st.session_state.notas_capturadas:
        df_export = pd.DataFrame(st.session_state.notas_capturadas)
        
        st.markdown("### Vista previa de datos a exportar")
        columns_to_show = [col for col in OFFICIAL_COLUMNS if col in df_export.columns]
        st.dataframe(df_export[columns_to_show].head(10), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Descargar archivo Excel")
        
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
        st.markdown("### 📋 Resumen de exportación")
        col_r1, col_r2, col_r3 = st.columns(3)
        col_r1.metric("Total Notas", len(df_export))
        col_r2.metric("Columnas", len(columns_to_show))
        col_r3.metric("Formato", "Excel (.xlsx)")
    else:
        st.info("No hay notas para exportar")

# --- INSTRUCCIONES ---
with st.expander("📖 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    ### 📊 Sistema de Captura de Notas RTP
    
    **1. Carga un archivo PDF** en la barra lateral
    
    **2. Visualiza el PDF:**
    - El texto del PDF se extrae automáticamente
    - Puedes seleccionar y copiar texto directamente desde la vista de texto
    - También puedes descargar el PDF para abrirlo en tu visor preferido
    
    **3. Captura el texto:**
    - **Selecciona** el texto del PDF (desde la vista de texto o del PDF descargado)
    - **Cópialo** (Ctrl+C o Cmd+C)
    - **Pégalo** en el campo "Texto seleccionado"
    - **Presiona el botón** del campo correspondiente
    
    **4. Campos disponibles:**
    - 📌 **Título de la nota** - Campo obligatorio
    - 📝 **RESUMEN DE LA NOTA (RTP)**
    - 📰 **MEDIOS DE COMUNICACIÓN**
    - ✍️ **Autor**
    - 🔗 **LINK** - Clickeable
    - 📂 **Tema de la nota**
    
    **5. Guarda y exporta:**
    - Configura relevancia y tono
    - Presiona **"GUARDAR NOTA COMPLETA"**
    - Revisa todas las notas en "Tabla de Notas"
    - Analiza en "Gráficas"
    - Descarga el Excel con el botón grande
    """)