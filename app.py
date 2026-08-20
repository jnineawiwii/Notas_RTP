import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime
import os

# Configuración de página
st.set_page_config(
    page_title="Monitoreo RTP - Captura de Notas",
    page_icon="🚌",
    layout="wide"
)

st.title("🚌 Captura de Notas - Monitoreo RTP")
st.caption("Visualiza el PDF, copia el texto y asígnalo a los campos correspondientes.")

# Columnas oficiales alineadas al Excel
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
                st.session_state.notas_capturadas = df_existente.to_dict('records')
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    elif ext == "pdf":
        st.session_state.pdf_bytes = uploaded_file.getvalue()
        st.session_state.pdf_filename = uploaded_file.name
        st.sidebar.success(f"✅ PDF cargado: {uploaded_file.name}")

# --- INTERFAZ PRINCIPAL ---
tab1, tab2, tab3, tab4 = st.tabs(["📄 Visualizar PDF y Capturar", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])

# --- TAB 1: VISUALIZAR PDF Y CAPTURAR ---
with tab1:
    if st.session_state.pdf_bytes:
        
        st.subheader("📄 Visor de PDF")
        
        # Renderizado de páginas del PDF como imagen con pdfplumber
        col_pdf, col_captura = st.columns([1, 1])
        
        with col_pdf:
            st.write(f"**Archivo:** {st.session_state.pdf_filename}")
            st.download_button(
                label="📥 Descargar PDF original",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.pdf_filename,
                mime="application/pdf",
                use_container_width=True
            )
            
            with pdfplumber.open(io.BytesIO(st.session_state.pdf_bytes)) as pdf:
                num_pages = len(pdf.pages)
                page_num = st.number_input("Página:", min_value=1, max_value=num_pages, value=1)
                
                # Renderizar la página seleccionada a imagen
                page = pdf.pages[page_num - 1]
                pix = page.to_image(resolution=150)
                img_bytes = io.BytesIO()
                pix.save(img_bytes, format="PNG")
                st.image(img_bytes.getvalue(), caption=f"Página {page_num} de {num_pages}", use_column_width=True)
                
                # Extraer texto de la página por si se prefiere copiar directo
                with st.expander("📄 Ver texto extraído de esta página"):
                    st.text_area("Texto detectado:", value=page.extract_text() or "", height=200)

        with col_captura:
            st.subheader("📝 Captura de Datos")
            
            # Campo para pegar el texto copiado
            texto_pegado = st.text_area(
                "Pega aquí el texto que copiaste del PDF:",
                value=st.session_state.texto_seleccionado,
                height=120,
                placeholder="Pega el texto aquí..."
            )
            st.session_state.texto_seleccionado = texto_pegado

            st.write("### Asignar texto a columna:")
            
            # Botones estándar por columna (sin colores CSS)
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                if st.button("📌 Título de la nota", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['titulo'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Título")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

                if st.button("📝 RESUMEN DE LA NOTA (RTP)", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['resumen'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Resumen")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

                if st.button("📰 MEDIOS DE COMUNICACIÓN", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['medio'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Medio")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

            with col_b2:
                if st.button("✍️ Autor", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['autor'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Autor")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

                if st.button("🔗 LINK", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['link'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Link")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

                if st.button("📂 Tema de la nota", use_container_width=True):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['tema'] = st.session_state.texto_seleccionado.strip()
                        st.success("Asignado a Tema")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()

            # Estado actual de los campos asignados
            st.write("---")
            st.write("**Campos capturados actualmente:**")
            st.json(st.session_state.nota_actual if st.session_state.nota_actual else {"Estado": "Vacío"})

            # Configuración
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                relevancia = st.selectbox("¿Es relevante para RTP?", ["Sí", "No"], index=0)
            with col_c2:
                tono = st.selectbox("Tono de la nota", ["Informativo", "Positivo", "Negativo"], index=0)

            # Botón Guardar
            if st.button("💾 GUARDAR NOTA COMPLETA", use_container_width=True):
                if st.session_state.nota_actual.get('titulo'):
                    today = datetime.now()
                    medio = st.session_state.nota_actual.get('medio', '')
                    
                    tipo_medio = 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *'
                    if any(x in medio.lower() for x in ['radio', 'fm']):
                        tipo_medio = 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * '
                    elif any(x in medio.lower() for x in ['tv', 'canal', 'televisa']):
                        tipo_medio = 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *'
                    elif any(x in medio.lower() for x in ['twitter', 'facebook', 'youtube']):
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
                        'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ' else None,
                        'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': medio if tipo_medio == 'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *' else None,
                        'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': medio if tipo_medio == 'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *' else None,
                        'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': medio if tipo_medio == 'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *' else None,
                        'OTROS (Twitter, Facebook, You Tube, etc.).': medio if tipo_medio == 'OTROS (Twitter, Facebook, You Tube, etc.).' else None,
                        'Informativo / Positivo/ Negativo': tono,
                        'LINK': st.session_state.nota_actual.get('link', ''),
                        'Autor': st.session_state.nota_actual.get('autor', 'Redacción'),
                        'PUBLICACIÓN BOLETÍN': 'NO',
                        'RESUMEN  DE LA NOTA (RTP)': st.session_state.nota_actual.get('resumen', '')
                    }
                    st.session_state.notas_capturadas.append(nota_completa)
                    st.success(f"✅ Nota guardada exitosamente (Total: {len(st.session_state.notas_capturadas)})")
                    st.session_state.nota_actual = {}
                    st.session_state.texto_seleccionado = ""
                    st.rerun()
                else:
                    st.error("⚠️ El Título es obligatorio para guardar")

    else:
        st.info("📄 Sube un archivo PDF en la barra lateral para comenzar.")

# --- TAB 2: TABLA DE NOTAS ---
with tab2:
    st.subheader("📋 Tabla de Notas Capturadas")
    if st.session_state.notas_capturadas:
        df_show = pd.DataFrame(st.session_state.notas_capturadas)
        cols_to_display = [c for c in OFFICIAL_COLUMNS if c in df_show.columns]
        st.dataframe(df_show[cols_to_display], use_container_width=True, height=500)
    else:
        st.info("No hay notas capturadas aún.")

# --- TAB 3: GRÁFICAS ---
with tab3:
    st.subheader("📊 Análisis Gráfico")
    if st.session_state.notas_capturadas:
        df_graph = pd.DataFrame(st.session_state.notas_capturadas)
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            if 'Informativo / Positivo/ Negativo' in df_graph.columns:
                fig_tono = px.pie(df_graph, names='Informativo / Positivo/ Negativo', title="Distribución por Tono", hole=0.3)
                st.plotly_chart(fig_tono, use_container_width=True)
        
        with col_g2:
            if 'Campaña' in df_graph.columns:
                fig_campana = px.pie(df_graph, names='Campaña', title="Distribución por Campaña")
                st.plotly_chart(fig_campana, use_container_width=True)
    else:
        st.info("No hay datos para generar gráficas.")

# --- TAB 4: EXPORTAR ---
with tab4:
    st.subheader("📥 Exportar a Excel")
    if st.session_state.notas_capturadas:
        df_export = pd.DataFrame(st.session_state.notas_capturadas)
        
        # Garantizar que todas las columnas oficiales existan en la exportación
        for col in OFFICIAL_COLUMNS:
            if col not in df_export.columns:
                df_export[col] = None
                
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_export[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
        
        st.download_button(
            label="📥 Descargar Excel (.xlsx)",
            data=output.getvalue(),
            file_name=f"Seguimiento_RTP_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.info("No hay notas capturadas para exportar.")