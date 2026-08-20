import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime
import base64

# Configuración de página
st.set_page_config(
    page_title="Monitoreo RTP - Captura de Notas",
    page_icon="🚌",
    layout="wide"
)

# Estilos visuales mejorados
st.markdown("""
<style>
    .badge-positivo { background-color: #28a745; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-informativo { background-color: #ffc107; color: black; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    .badge-negativo { background-color: #dc3545; color: white; padding: 4px 10px; border-radius: 5px; font-weight: bold; }
    
    .campo-titulo { background: linear-gradient(135deg, #e3f2fd, #bbdefb); border-left: 5px solid #007bff; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #004085; }
    .campo-resumen { background: linear-gradient(135deg, #e8f5e9, #c8e6c9); border-left: 5px solid #28a745; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #155724; }
    .campo-medio { background: linear-gradient(135deg, #fff8e1, #ffecb3); border-left: 5px solid #ffc107; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #856404; }
    .campo-autor { background: linear-gradient(135deg, #fce4ec, #f8bbd0); border-left: 5px solid #dc3545; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #721c24; }
    .campo-link { background: linear-gradient(135deg, #e0f7fa, #b2ebf2); border-left: 5px solid #17a2b8; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #0c5460; }
    .campo-tema { background: linear-gradient(135deg, #f3e5f5, #e1bee7); border-left: 5px solid #6f42c1; padding: 10px 15px; margin: 6px 0; border-radius: 4px; font-weight: bold; color: #3d1a6e; }
    
    .btn-asignar { border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; color: white; width: 100%; margin: 3px 0; font-size: 13px; text-align: center; transition: all 0.3s; }
    .btn-asignar:hover { transform: scale(1.05); opacity: 0.9; }
    .btn-titulo { background: #007bff; }
    .btn-resumen { background: #28a745; }
    .btn-medio { background: #ffc107; color: black; }
    .btn-autor { background: #dc3545; }
    .btn-link { background: #17a2b8; }
    .btn-tema { background: #6f42c1; }
    
    .pdf-viewer {
        border: 2px solid #dee2e6;
        border-radius: 8px;
        height: 600px;
        overflow: hidden;
    }
    .pdf-viewer iframe {
        width: 100%;
        height: 100%;
        border: none;
    }
    
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
    .leyenda-item { display: flex; align-items: center; gap: 6px; font-size: 12px; }
    .leyenda-color { width: 18px; height: 18px; border-radius: 4px; border: 1px solid #ccc; }
    
    .btn-descarga-grande {
        background: linear-gradient(135deg, #28a745, #20c997);
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
        box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
    }
    .btn-descarga-grande:hover { transform: scale(1.02); box-shadow: 0 6px 20px rgba(40, 167, 69, 0.4); }
    
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

def extract_pdf_text(pdf_file):
    """Extrae texto del PDF para mostrar en vista previa"""
    full_text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                full_text += text + "\n"
    except:
        pass
    return full_text

def get_pdf_download_link(pdf_bytes, filename):
    """Genera un link para descargar/ver el PDF"""
    b64 = base64.b64encode(pdf_bytes).decode()
    return f'data:application/pdf;base64,{b64}'

# --- INICIALIZAR SESSION STATE ---
if 'notas_capturadas' not in st.session_state:
    st.session_state.notas_capturadas = []
if 'nota_actual' not in st.session_state:
    st.session_state.nota_actual = {}
if 'notas_extraidas' not in st.session_state:
    st.session_state.notas_extraidas = []
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
                for _, row in df_existente.iterrows():
                    nota = {col: row[col] for col in OFFICIAL_COLUMNS if col in df_existente.columns}
                    st.session_state.notas_capturadas.append(nota)
        except Exception as e:
            st.sidebar.error(f"❌ Error: {e}")
    
    elif ext == "pdf":
        # Guardar el PDF en session state para mostrarlo
        pdf_bytes = uploaded_file.getvalue()
        st.session_state.pdf_bytes = pdf_bytes
        st.session_state.pdf_filename = uploaded_file.name
        st.sidebar.success(f"✅ PDF cargado: {uploaded_file.name}")
        
        # Extraer texto para ayuda (opcional)
        with st.spinner("📄 Preparando PDF..."):
            full_text = extract_pdf_text(uploaded_file)
            if full_text.strip():
                st.session_state.notas_extraidas = full_text.split('\n\n')
                st.sidebar.info(f"📊 Texto extraído: {len(full_text)} caracteres")

# --- INTERFAZ PRINCIPAL ---
# TABS principales
tab1, tab2, tab3, tab4 = st.tabs(["📄 Visualizar PDF y Capturar", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])

# --- TAB 1: VISUALIZAR PDF Y CAPTURAR ---
with tab1:
    if st.session_state.pdf_bytes:
        
        # Mostrar el PDF original
        st.markdown("### 📄 PDF Original")
        st.markdown("**💡 Instrucción:** Selecciona y copia texto del PDF, pégalo en el campo de abajo, luego presiona el botón del campo correspondiente")
        
        # Visor del PDF
        pdf_link = get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename)
        
        st.markdown(f"""
        <div class="pdf-viewer">
            <iframe src="{pdf_link}#toolbar=1&navpanes=1&scrollbar=1" 
                    allow="fullscreen" 
                    title="Visor PDF">
            </iframe>
        </div>
        """, unsafe_allow_html=True)
        
        # Opción de descarga del PDF
        st.download_button(
            label="📄 Descargar PDF original",
            data=st.session_state.pdf_bytes,
            file_name=st.session_state.pdf_filename,
            mime="application/pdf"
        )
        
        st.markdown("---")
        
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
        
        # Área de captura
        col_texto, col_botones = st.columns([1, 1])
        
        with col_texto:
            st.markdown("### 📝 Texto seleccionado")
            
            # Campo para pegar texto
            texto_pegado = st.text_area(
                "Pega aquí el texto que copiaste del PDF",
                value=st.session_state.texto_seleccionado,
                height=150,
                placeholder="1. Selecciona texto en el PDF\n2. Cópialo (Ctrl+C)\n3. Pégalo aquí (Ctrl+V)\n4. Presiona el botón correspondiente",
                key="texto_pegado_input"
            )
            
            if texto_pegado != st.session_state.texto_seleccionado:
                st.session_state.texto_seleccionado = texto_pegado
        
        with col_botones:
            st.markdown("### 🎯 Asignar a campo")
            st.markdown("**Presiona el botón del campo donde quieras guardar el texto**")
            
            # Botones en el orden del Excel
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button("📌 Título de la nota", use_container_width=True, key="btn_titulo"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['titulo'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Título")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                if st.button("📝 RESUMEN DE LA NOTA", use_container_width=True, key="btn_resumen"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['resumen'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Resumen")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                if st.button("📰 MEDIOS DE COMUNICACIÓN", use_container_width=True, key="btn_medio"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['medio'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Medio")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
            
            with col_btn2:
                if st.button("✍️ Autor", use_container_width=True, key="btn_autor"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['autor'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Autor")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
                if st.button("🔗 LINK", use_container_width=True, key="btn_link"):
                    if st.session_state.texto_seleccionado.strip():
                        st.session_state.nota_actual['link'] = st.session_state.texto_seleccionado.strip()
                        st.success("✅ Asignado a Link")
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.warning("⚠️ Primero copia y pega texto del PDF")
                
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
            # Mostrar resumen de campos asignados
            campos_asignados = []
            if st.session_state.nota_actual.get('titulo'):
                campos_asignados.append("Título")
            if st.session_state.nota_actual.get('resumen'):
                campos_asignados.append("Resumen")
            if st.session_state.nota_actual.get('medio'):
                campos_asignados.append("Medio")
            if st.session_state.nota_actual.get('autor'):
                campos_asignados.append("Autor")
            if st.session_state.nota_actual.get('link'):
                campos_asignados.append("Link")
            if st.session_state.nota_actual.get('tema'):
                campos_asignados.append("Tema")
            
            if campos_asignados:
                st.success(f"✅ Campos asignados: {', '.join(campos_asignados)}")
            else:
                st.info("⬜ Ningún campo asignado aún")
        
        # Botón guardar
        st.markdown("---")
        col_guardar1, col_guardar2, col_guardar3 = st.columns([1, 2, 1])
        with col_guardar2:
            if st.button("💾 GUARDAR NOTA COMPLETA", use_container_width=True, key="btn_guardar_completa"):
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
                    st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada")
                    # Limpiar nota actual
                    st.session_state.nota_actual = {}
                    st.session_state.texto_seleccionado = ""
                    st.rerun()
                else:
                    st.error("⚠️ El Título es obligatorio")
    
    else:
        st.info("📄 Sube un archivo PDF en la barra lateral para visualizarlo y capturar notas")

# --- TAB 2: TABLA DE NOTAS ---
with tab2:
    st.subheader("📋 Tabla de Notas Capturadas")
    if st.session_state.notas_capturadas:
        df_show = pd.DataFrame(st.session_state.notas_capturadas)
        st.dataframe(df_show[OFFICIAL_COLUMNS], use_container_width=True, height=500)
        
        st.markdown("### 📊 Estadísticas")
        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
        col_est1.metric("Total Notas", len(df_show))
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
            df_graph['Campaña'] = df_graph['Campaña'].fillna('RTP informa')
            fig_campana = px.pie(
                df_graph,
                names='Campaña',
                title="Distribución por Campaña",
                color_discrete_sequence=['#007bff', '#6c757d']
            )
            st.plotly_chart(fig_campana, use_container_width=True)
        
        # Gráfica de relevancia
        fig_relevancia = px.bar(
            df_graph,
            x='RTP, ¿Es relevante en la nota?',
            title="Relevancia para RTP",
            color='RTP, ¿Es relevante en la nota?',
            color_discrete_map={'Sí': '#28a745', 'No': '#dc3545'}
        )
        st.plotly_chart(fig_relevancia, use_container_width=True)
        
        # Gráfica de temas
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
        st.dataframe(df_export[OFFICIAL_COLUMNS].head(10), use_container_width=True)
        
        st.markdown("---")
        st.markdown("### 📥 Descargar archivo Excel")
        
        col_exp1, col_exp2, col_exp3 = st.columns([1, 2, 1])
        with col_exp2:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_export[OFFICIAL_COLUMNS].to_excel(writer, sheet_name="Seguimiento_Medios", index=False)
            
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
        col_r2.metric("Columnas", len(OFFICIAL_COLUMNS))
        col_r3.metric("Formato", "Excel (.xlsx)")
    else:
        st.info("No hay notas para exportar")

# --- INSTRUCCIONES ---
with st.expander("📖 ¿Cómo usar esta herramienta?"):
    st.markdown("""
    ### 📊 Sistema de Captura de Notas RTP
    
    **1. Carga un archivo PDF** en la barra lateral
    
    **2. Visualiza el PDF:**
    - El PDF se muestra completo en la pestaña principal
    - Puedes hacer scroll, zoom y seleccionar texto directamente
    
    **3. Captura el texto:**
    - **Selecciona** el texto en el PDF
    - **Cópialo** (Ctrl+C)
    - **Pégalo** en el campo "Texto seleccionado"
    - **Presiona el botón** del campo correspondiente
    
    **4. Colores de los campos:**
    - 🔵 **Título de la nota** (Azul)
    - 🟢 **RESUMEN DE LA NOTA (RTP)** (Verde)
    - 🟡 **MEDIOS DE COMUNICACIÓN** (Amarillo)
    - 🔴 **Autor** (Rojo)
    - 🔷 **LINK** (Celeste)
    - 🟣 **Tema de la nota** (Morado)
    
    **5. Guarda y exporta:**
    - Configura relevancia y tono
    - Presiona **"GUARDAR NOTA COMPLETA"**
    - Revisa todas las notas en "Tabla de Notas"
    - Analiza en "Gráficas"
    - Descarga el Excel con el botón grande
    """)