import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime
import base64
import os
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode

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
    .link-error {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 10px;
        border-radius: 5px;
        margin: 5px 0;
    }
    .field-assigned {
        background-color: #d4edda;
        padding: 5px 10px;
        border-radius: 4px;
        margin: 2px 0;
        font-size: 13px;
        border-left: 3px solid #28a745;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0px 0px; padding: 12px 20px; background-color: #f0f2f6; font-weight: bold; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #007bff; color: white; }
    .editable-cell {
        background-color: #fff3cd !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🚌 Captura de Notas - Monitoreo RTP")
st.caption("Abre el PDF, copia el texto y asígnalo a cada campo con los botones")

# Columnas oficiales - TODAS las columnas del Excel
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

# Mapeo de nombres amigables para los botones
FIELD_NAMES = {
    'Año': '📅 Año',
    '# Mes': '🔢 # Mes',
    'Mes': '📆 Mes',
    'Fecha ': '📅 Fecha',
    'Título de la nota': '📌 Título de la nota',
    'RTP, ¿Es relevante en la nota?': '🎯 ¿Es relevante para RTP?',
    'Tema de la nota': '📂 Tema de la nota',
    'Campaña': '🏷️ Campaña',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: RADIO * ': '📻 Radio',
    'MEDIOS ELECTRÓNICOS TRADICIONALES: TELEVISIÓN *': '📺 Televisión',
    'MEDIOS DE COMUNICACIÓN DIGITALES (Internet: portales de noticias, canales de tv y radio digitales) *': '🌐 Medios Digitales',
    'MEDIOS IMPRESOS (Publicación de inserciones en revistas y periódicos) *': '📰 Medios Impresos',
    'OTROS (Twitter, Facebook, You Tube, etc.).': '📱 Otros (Redes Sociales)',
    'Informativo / Positivo/ Negativo': '📊 Tono',
    'LINK': '🔗 LINK',
    'Autor': '✍️ Autor',
    'PUBLICACIÓN BOLETÍN': '📄 Publicación Boletín',
    'RESUMEN  DE LA NOTA (RTP)': '📝 Resumen de la nota'
}

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

def validate_and_format_link(link):
    """Valida y formatea un link correctamente"""
    if not link or pd.isna(link):
        return None
    
    link = str(link).strip()
    
    if link.startswith('\\\\') or link.startswith('\\'):
        return None
    
    if not link.startswith(('http://', 'https://')):
        if re.match(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}', link):
            return f'https://{link}'
        return None
    
    if re.match(r'^https?://[^\s]+', link):
        return link
    
    return None

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
if 'fecha_editable' not in st.session_state:
    st.session_state.fecha_editable = datetime.now().strftime("%Y-%m-%d")
if 'mes_editable' not in st.session_state:
    st.session_state.mes_editable = datetime.now().strftime("%B").capitalize()
if 'anio_editable' not in st.session_state:
    st.session_state.anio_editable = str(datetime.now().year)
if 'num_mes_editable' not in st.session_state:
    st.session_state.num_mes_editable = str(datetime.now().month)

# --- SIDEBAR ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

st.sidebar.header("📊 Notas Capturadas")
st.sidebar.metric("Total Notas", len(st.session_state.notas_capturadas))

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🗑️ Limpiar todas", use_container_width=True):
        st.session_state.notas_capturadas = []
        st.session_state.nota_actual = {}
        st.session_state.texto_seleccionado = ""
        st.rerun()
with col2:
    if st.button("📋 Ver tabla", use_container_width=True):
        st.session_state.show_table = True

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
        st.session_state.pdf_text = extract_text_from_pdf(pdf_bytes)
        st.sidebar.success(f"✅ PDF cargado: {uploaded_file.name}")

# --- INTERFAZ PRINCIPAL ---
tab1, tab2, tab3, tab4 = st.tabs(["📄 Visualizar PDF y Capturar", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])

# --- TAB 1: VISUALIZAR PDF Y CAPTURAR ---
with tab1:
    if st.session_state.pdf_bytes:
        
        st.markdown("### 📄 PDF Original")
        
        view_option = st.radio(
            "Selecciona cómo ver el PDF:",
            ["📝 Ver texto extraído", "📄 Descargar y abrir PDF"],
            horizontal=True
        )
        
        if view_option == "📝 Ver texto extraído":
            st.markdown("**💡 Instrucción:** Selecciona y copia el texto del PDF desde abajo, pégalo en el campo correspondiente")
            
            if st.session_state.pdf_text:
                st.markdown("#### 📄 Contenido del PDF (texto extraído)")
                st.markdown(
                    f'<div class="pdf-text-container">{st.session_state.pdf_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.warning("No se pudo extraer texto del PDF. Intenta con el visor nativo.")
                st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
        
        else:
            st.markdown("**💡 Haz clic en el botón para descargar y abrir el PDF en tu visor predeterminado**")
            st.markdown(get_pdf_download_link(st.session_state.pdf_bytes, st.session_state.pdf_filename), unsafe_allow_html=True)
            st.info("📌 Después de abrir el PDF, selecciona y copia el texto que necesites, luego pégalo abajo.")
        
        st.markdown("---")
        
        # Área de captura - con botones para TODAS las columnas
        col_texto, col_botones = st.columns([1, 1.5])
        
        with col_texto:
            st.markdown("### 📝 Texto seleccionado")
            
            st.info("📋 **Instrucciones:**\n1. Selecciona texto del PDF\n2. Cópialo (Ctrl+C o Cmd+C)\n3. Pégalo aquí abajo\n4. Presiona el botón del campo correspondiente")
            
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
            
            # Mostrar los campos asignados
            if st.session_state.nota_actual:
                st.markdown("#### 📋 Campos asignados en esta nota:")
                for col, value in st.session_state.nota_actual.items():
                    if value:
                        display_name = FIELD_NAMES.get(col, col)
                        st.markdown(f'<div class="field-assigned">✅ {display_name}: {str(value)[:60]}...</div>', unsafe_allow_html=True)
            else:
                st.info("⬜ Ningún campo asignado aún")
        
        with col_botones:
            st.markdown("### 🎯 Asignar a campo")
            st.markdown("**Presiona el botón del campo donde quieras guardar el texto**")
            
            # Organizar botones en 3 columnas
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            
            # Campos que NO deben tener botón (se configuran automáticamente)
            AUTO_FIELDS = ['Año', '# Mes', 'Mes', 'Fecha ', 'Campaña', 'Informativo / Positivo/ Negativo']
            
            # Campos que tienen botón
            BUTTON_FIELDS = [col for col in OFFICIAL_COLUMNS if col not in AUTO_FIELDS]
            
            # Distribuir botones en 3 columnas
            for idx, col_name in enumerate(BUTTON_FIELDS):
                col_idx = idx % 3
                target_col = [col_btn1, col_btn2, col_btn3][col_idx]
                
                display_name = FIELD_NAMES.get(col_name, col_name)
                button_key = f"btn_{col_name.replace(' ', '_').replace('*', '').replace('(', '').replace(')', '').replace('/', '_')}"
                
                with target_col:
                    if st.button(display_name, use_container_width=True, key=button_key):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.nota_actual[col_name] = st.session_state.texto_seleccionado.strip()
                            st.success(f"✅ Asignado a {display_name}")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
        
        # Configuración adicional (campos automáticos EDITABLES)
        st.markdown("---")
        st.markdown("### ⚙️ Configuración de la nota")
        
        col_config1, col_config2, col_config3, col_config4 = st.columns(4)
        
        with col_config1:
            st.markdown("**📅 Fecha y hora (editable)**")
            
            # Fecha editable
            fecha_val = st.date_input(
                "📅 Fecha",
                value=datetime.strptime(st.session_state.fecha_editable, "%Y-%m-%d") if st.session_state.fecha_editable else datetime.now(),
                key="fecha_input"
            )
            st.session_state.fecha_editable = fecha_val.strftime("%Y-%m-%d")
            st.session_state.nota_actual['Fecha '] = st.session_state.fecha_editable
            
            # Mes editable
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            mes_idx = meses.index(st.session_state.mes_editable) if st.session_state.mes_editable in meses else fecha_val.month - 1
            mes_seleccionado = st.selectbox("📆 Mes", meses, index=mes_idx, key="mes_select")
            st.session_state.mes_editable = mes_seleccionado
            st.session_state.nota_actual['Mes'] = mes_seleccionado
            
            # Año editable
            anio_val = st.number_input("📅 Año", min_value=2020, max_value=2030, 
                                       value=int(st.session_state.anio_editable) if st.session_state.anio_editable else fecha_val.year,
                                       key="anio_input")
            st.session_state.anio_editable = str(anio_val)
            st.session_state.nota_actual['Año'] = anio_val
            
            # Número de mes editable
            num_mes_val = st.number_input("🔢 # Mes", min_value=1, max_value=12,
                                          value=int(st.session_state.num_mes_editable) if st.session_state.num_mes_editable else fecha_val.month,
                                          key="num_mes_input")
            st.session_state.num_mes_editable = str(num_mes_val)
            st.session_state.nota_actual['# Mes'] = num_mes_val
        
        with col_config2:
            relevancia = st.selectbox(
                "🎯 ¿Es relevante para RTP?",
                ["Sí", "No"],
                index=0 if st.session_state.relevancia_seleccionada == "Sí" else 1,
                key="select_relevancia"
            )
            st.session_state.relevancia_seleccionada = relevancia
            st.session_state.nota_actual['RTP, ¿Es relevante en la nota?'] = relevancia
        
        with col_config3:
            tono = st.selectbox(
                "📊 Tono de la nota",
                ["Informativo", "Positivo", "Negativo"],
                index=["Informativo", "Positivo", "Negativo"].index(st.session_state.tono_seleccionado),
                key="select_tono"
            )
            st.session_state.tono_seleccionado = tono
            st.session_state.nota_actual['Informativo / Positivo/ Negativo'] = tono
        
        with col_config4:
            # Mostrar campaña automática
            campana = map_campana(tono)
            st.text_input("🏷️ Campaña", value=campana, disabled=True)
            st.session_state.nota_actual['Campaña'] = campana
            
            # Mostrar link si existe
            link = st.session_state.nota_actual.get('LINK', '')
            if link:
                formatted_link = validate_and_format_link(link)
                if formatted_link:
                    st.markdown(f'🔗 <a href="{formatted_link}" target="_blank">Abrir link</a>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="link-error">⚠️ Link no válido</div>', unsafe_allow_html=True)
        
        # Botón guardar
        st.markdown("---")
        col_guardar1, col_guardar2, col_guardar3 = st.columns([1, 2, 1])
        with col_guardar2:
            if st.button("💾 GUARDAR NOTA COMPLETA", use_container_width=True, key="btn_guardar_completa"):
                if st.session_state.nota_actual.get('Título de la nota'):
                    # Construir la nota completa con todos los campos
                    nota_completa = {}
                    for col in OFFICIAL_COLUMNS:
                        if col in ['Año', '# Mes', 'Mes', 'Fecha ']:
                            continue
                        
                        if col == 'Campaña':
                            nota_completa[col] = map_campana(st.session_state.tono_seleccionado)
                        elif col == 'Informativo / Positivo/ Negativo':
                            nota_completa[col] = st.session_state.tono_seleccionado
                        elif col == 'RTP, ¿Es relevante en la nota?':
                            nota_completa[col] = st.session_state.relevancia_seleccionada
                        else:
                            value = st.session_state.nota_actual.get(col, '')
                            if col == 'LINK' and value:
                                formatted = validate_and_format_link(value)
                                nota_completa[col] = formatted if formatted else value
                            else:
                                nota_completa[col] = value
                    
                    # Agregar campos editables
                    nota_completa['Año'] = int(st.session_state.anio_editable)
                    nota_completa['# Mes'] = int(st.session_state.num_mes_editable)
                    nota_completa['Mes'] = st.session_state.mes_editable
                    nota_completa['Fecha '] = st.session_state.fecha_editable
                    
                    # Valores por defecto
                    if not nota_completa.get('Autor'):
                        nota_completa['Autor'] = 'Redacción'
                    if not nota_completa.get('PUBLICACIÓN BOLETÍN'):
                        nota_completa['PUBLICACIÓN BOLETÍN'] = 'NO'
                    if not nota_completa.get('Tema de la nota'):
                        nota_completa['Tema de la nota'] = 'General'
                    
                    st.session_state.notas_capturadas.append(nota_completa)
                    st.success(f"✅ Nota {len(st.session_state.notas_capturadas)} guardada")
                    
                    # Limpiar nota actual
                    st.session_state.nota_actual = {}
                    st.session_state.texto_seleccionado = ""
                    st.rerun()
                else:
                    st.error("⚠️ El Título de la nota es obligatorio")
    
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

# --- TAB 2: TABLA DE NOTAS (EDITABLE CON AG-GRID) ---
with tab2:
    st.subheader("📋 Tabla de Notas Capturadas (Editable)")
    
    if st.session_state.notas_capturadas:
        df_show = pd.DataFrame(st.session_state.notas_capturadas)
        columns_to_show = [col for col in OFFICIAL_COLUMNS if col in df_show.columns]
        df_display = df_show[columns_to_show].copy()
        
        # Reemplazar NaN con strings vacíos
        df_display = df_display.fillna('')
        
        # Configurar AgGrid
        gb = GridOptionsBuilder.from_dataframe(df_display)
        
        # Hacer todas las columnas editables
        gb.configure_default_column(editable=True, resizable=True, filter=True, sortable=True)
        
        # Configurar columnas específicas
        for col in df_display.columns:
            if col in ['Año', '# Mes']:
                gb.configure_column(col, type=["numericColumn"], width=80)
            elif col == 'Fecha ':
                gb.configure_column(col, width=120)
            elif col == 'LINK':
                gb.configure_column(col, width=200)
            elif col in ['Título de la nota', 'RESUMEN  DE LA NOTA (RTP)']:
                gb.configure_column(col, width=250)
            else:
                gb.configure_column(col, width=150)
        
        # Permitir selección de filas
        gb.configure_selection(selection_mode="single", use_checkbox=True)
        
        # Agregar botones de acción en la tabla
        gb.configure_grid_options(
            enableCellTextSelection=True,
            ensureDomOrder=True,
            rowHeight=35,
            headerHeight=40,
        )
        
        grid_options = gb.build()
        
        st.info("💡 Haz clic en cualquier celda para editarla. Los cambios se guardan automáticamente.")
        
        # Mostrar la tabla editable
        grid_response = AgGrid(
            df_display,
            gridOptions=grid_options,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            allow_unsafe_jscode=True,
            theme='streamlit',
            height=500,
            width='100%',
            key='tabla_editable'
        )
        
        # Obtener los datos actualizados
        if grid_response['data'] is not None:
            df_updated = pd.DataFrame(grid_response['data'])
            
            # Actualizar las notas capturadas con los cambios
            if not df_updated.empty and len(df_updated) == len(st.session_state.notas_capturadas):
                # Actualizar cada fila
                for idx, row in df_updated.iterrows():
                    if idx < len(st.session_state.notas_capturadas):
                        for col in columns_to_show:
                            if col in row and pd.notna(row[col]):
                                st.session_state.notas_capturadas[idx][col] = row[col]
        
        # Botones para acciones sobre la tabla
        st.markdown("---")
        col_btn_tabla1, col_btn_tabla2, col_btn_tabla3, col_btn_tabla4 = st.columns(4)
        
        with col_btn_tabla1:
            if st.button("➕ Agregar fila", use_container_width=True):
                # Crear una fila vacía
                new_row = {col: '' for col in columns_to_show}
                # Valores por defecto para campos automáticos
                today = datetime.now()
                new_row['Año'] = today.year
                new_row['# Mes'] = today.month
                new_row['Mes'] = today.strftime("%B").capitalize()
                new_row['Fecha '] = today.strftime("%Y-%m-%d")
                new_row['Campaña'] = 'RTP informa'
                new_row['Informativo / Positivo/ Negativo'] = 'Informativo'
                new_row['RTP, ¿Es relevante en la nota?'] = 'Sí'
                new_row['PUBLICACIÓN BOLETÍN'] = 'NO'
                new_row['Autor'] = 'Redacción'
                
                st.session_state.notas_capturadas.append(new_row)
                st.rerun()
        
        with col_btn_tabla2:
            if st.button("🗑️ Eliminar seleccionada", use_container_width=True):
                selected_rows = grid_response['selected_rows']
                if selected_rows is not None and not selected_rows.empty:
                    indices = selected_rows.index.tolist()
                    # Eliminar en orden inverso
                    for idx in sorted(indices, reverse=True):
                        if idx < len(st.session_state.notas_capturadas):
                            del st.session_state.notas_capturadas[idx]
                    st.rerun()
                else:
                    st.warning("Selecciona una fila para eliminar")
        
        with col_btn_tabla3:
            if st.button("📋 Duplicar seleccionada", use_container_width=True):
                selected_rows = grid_response['selected_rows']
                if selected_rows is not None and not selected_rows.empty:
                    idx = selected_rows.index[0]
                    if idx < len(st.session_state.notas_capturadas):
                        # Crear una copia de la fila seleccionada
                        new_row = st.session_state.notas_capturadas[idx].copy()
                        # Cambiar título para evitar duplicados
                        if 'Título de la nota' in new_row and new_row['Título de la nota']:
                            new_row['Título de la nota'] = new_row['Título de la nota'] + " (copia)"
                        st.session_state.notas_capturadas.append(new_row)
                        st.rerun()
                else:
                    st.warning("Selecciona una fila para duplicar")
        
        with col_btn_tabla4:
            if st.button("🔄 Recargar tabla", use_container_width=True):
                st.rerun()
        
        # Estadísticas
        st.markdown("---")
        st.markdown("### 📊 Estadísticas")
        col_est1, col_est2, col_est3, col_est4 = st.columns(4)
        col_est1.metric("Total Notas", len(df_show))
        if 'Informativo / Positivo/ Negativo' in df_show.columns:
            col_est2.metric("Positivas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Positivo']))
            col_est3.metric("Informativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Informativo']))
            col_est4.metric("Negativas", len(df_show[df_show['Informativo / Positivo/ Negativo'] == 'Negativo']))
    else:
        st.info("No hay notas capturadas aún. Captura notas en la pestaña 'Visualizar PDF y Capturar'")

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
    
    **4. Campos disponibles (todos tienen botón):**
    - 📌 **Título de la nota** - Campo obligatorio
    - 📝 **RESUMEN DE LA NOTA (RTP)**
    - 📰 **MEDIOS DE COMUNICACIÓN DIGITALES**
    - 📻 **Radio**
    - 📺 **Televisión**
    - 📰 **Medios Impresos**
    - 📱 **Otros (Redes Sociales)**
    - ✍️ **Autor**
    - 🔗 **LINK**
    - 📂 **Tema de la nota**
    - 📄 **Publicación Boletín**
    
    **5. Campos editables:**
    - 📅 Año, Mes, Fecha (editables en la configuración)
    - 🏷️ Campaña (se calcula según el tono)
    - 📊 Tono (se selecciona en configuración)
    - 🎯 Relevancia (se selecciona en configuración)
    
    **6. Tabla editable:**
    - Haz clic en cualquier celda para editarla
    - Los cambios se guardan automáticamente
    - Puedes agregar, eliminar o duplicar filas
    - Selecciona una fila con el checkbox para eliminar o duplicar
    
    **7. Guarda y exporta:**
    - Configura relevancia, tono y fecha
    - Presiona **"GUARDAR NOTA COMPLETA"**
    - Revisa y edita todas las notas en "Tabla de Notas"
    - Analiza en "Gráficas"
    - Descarga el Excel con el botón grande
    """)