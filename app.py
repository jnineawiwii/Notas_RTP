import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
from datetime import datetime

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
    
    .texto-extraido {
        background-color: #f8f9fa;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        font-family: 'Segoe UI', sans-serif;
        font-size: 14px;
        line-height: 1.8;
        max-height: 500px;
        overflow-y: auto;
        white-space: pre-wrap;
        user-select: text;
    }
    
    .texto-extraido .hl-titulo { background-color: #cce5ff; padding: 2px 6px; border-radius: 3px; border: 2px solid #007bff; }
    .texto-extraido .hl-resumen { background-color: #d4edda; padding: 2px 6px; border-radius: 3px; border: 2px solid #28a745; }
    .texto-extraido .hl-medio { background-color: #fff3cd; padding: 2px 6px; border-radius: 3px; border: 2px solid #ffc107; }
    .texto-extraido .hl-autor { background-color: #f8d7da; padding: 2px 6px; border-radius: 3px; border: 2px solid #dc3545; }
    .texto-extraido .hl-link { background-color: #d1ecf1; padding: 2px 6px; border-radius: 3px; border: 2px solid #17a2b8; }
    .texto-extraido .hl-tema { background-color: #e8d5f5; padding: 2px 6px; border-radius: 3px; border: 2px solid #6f42c1; }
    
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
st.caption("Selecciona texto del PDF, presiona un botón y el texto se asigna al campo correspondiente")

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
    full_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
    return full_text

def split_into_notes(text):
    notes = []
    sections = re.split(r'(?=\n\s*MEDIOS?:)', text)
    if len(sections) > 1:
        for section in sections:
            if len(section.strip()) > 50:
                notes.append(section.strip())
    else:
        sections = re.split(r'\n\s*\n', text)
        for section in sections:
            if len(section.strip()) > 100:
                notes.append(section.strip())
    if not notes and text.strip():
        notes = [text.strip()]
    return notes

def highlight_selected_text(text, selections):
    if not text or not selections:
        return text
    highlighted = text
    sorted_selections = sorted(selections, key=lambda x: len(x['text']), reverse=True)
    for sel in sorted_selections:
        if sel['text'] in highlighted:
            highlighted = highlighted.replace(sel['text'], f'<span class="{sel["class"]}">{sel["text"]}</span>')
    return highlighted

# --- INICIALIZAR SESSION STATE ---
if 'notas_capturadas' not in st.session_state:
    st.session_state.notas_capturadas = []
if 'nota_actual' not in st.session_state:
    st.session_state.nota_actual = {}
if 'indice_nota' not in st.session_state:
    st.session_state.indice_nota = 0
if 'notas_extraidas' not in st.session_state:
    st.session_state.notas_extraidas = []
if 'selecciones' not in st.session_state:
    st.session_state.selecciones = []
if 'texto_seleccionado' not in st.session_state:
    st.session_state.texto_seleccionado = ""
if 'relevancia_seleccionada' not in st.session_state:
    st.session_state.relevancia_seleccionada = "Sí"
if 'tono_seleccionado' not in st.session_state:
    st.session_state.tono_seleccionado = "Informativo"

# --- SIDEBAR ---
st.sidebar.header("📂 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader("Sube tu archivo (Excel o PDF):", type=["xlsx", "pdf"])

st.sidebar.header("📊 Notas Capturadas")
st.sidebar.metric("Total Notas", len(st.session_state.notas_capturadas))

if st.sidebar.button("🗑️ Limpiar todas las notas"):
    st.session_state.notas_capturadas = []
    st.session_state.nota_actual = {}
    st.session_state.selecciones = []
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
        with st.spinner("📄 Extrayendo texto del PDF..."):
            full_text = extract_pdf_text(uploaded_file)
        
        if full_text.strip():
            st.sidebar.success(f"✅ PDF procesado: {len(full_text)} caracteres")
            st.session_state.notas_extraidas = split_into_notes(full_text)
            st.sidebar.info(f"📊 {len(st.session_state.notas_extraidas)} notas encontradas")
            
            if st.session_state.notas_extraidas and st.session_state.indice_nota < len(st.session_state.notas_extraidas):
                texto_nota = st.session_state.notas_extraidas[st.session_state.indice_nota]
                st.session_state.nota_actual = {'texto_original': texto_nota}
                st.session_state.selecciones = []

# --- INTERFAZ PRINCIPAL ---
if st.session_state.nota_actual.get('texto_original') or st.session_state.notas_capturadas:
    
    # TABS principales
    tab1, tab2, tab3, tab4 = st.tabs(["📄 Captura de Nota", "📋 Tabla de Notas", "📊 Gráficas", "📥 Exportar"])
    
    # --- TAB 1: CAPTURA DE NOTA ---
    with tab1:
        if st.session_state.nota_actual.get('texto_original'):
            
            # Progreso
            if st.session_state.notas_extraidas:
                total_notas = len(st.session_state.notas_extraidas)
                actual = st.session_state.indice_nota + 1
                st.progress(actual / total_notas if total_notas > 0 else 0)
                st.caption(f"Nota {actual} de {total_notas}")
            
            col_texto, col_botones = st.columns([2, 1])
            
            with col_texto:
                st.markdown("### 📄 Texto del PDF")
                
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
                
                # Mostrar texto con resaltados
                texto_mostrar = st.session_state.nota_actual['texto_original']
                if st.session_state.selecciones:
                    texto_mostrar = highlight_selected_text(texto_mostrar, st.session_state.selecciones)
                
                st.markdown(f'<div class="texto-extraido">{texto_mostrar}</div>', unsafe_allow_html=True)
                
                # Navegación
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("⬅️ Anterior", use_container_width=True) and st.session_state.indice_nota > 0:
                        st.session_state.indice_nota -= 1
                        texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                        st.session_state.nota_actual = {'texto_original': texto}
                        st.session_state.selecciones = []
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                with col2:
                    if st.button("➡️ Siguiente", use_container_width=True) and st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                        st.session_state.indice_nota += 1
                        texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                        st.session_state.nota_actual = {'texto_original': texto}
                        st.session_state.selecciones = []
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
                with col3:
                    if st.button("🔄 Limpiar resaltados", use_container_width=True):
                        st.session_state.selecciones = []
                        st.session_state.texto_seleccionado = ""
                        st.rerun()
            
            with col_botones:
                st.markdown("### 🎯 Asignar texto")
                st.markdown("**1. Copia** texto del PDF")
                st.markdown("**2. Pégalo** abajo")
                st.markdown("**3. Presiona** el botón del campo")
                
                # Campo para pegar texto
                texto_pegado = st.text_area(
                    "📝 Texto seleccionado",
                    value=st.session_state.texto_seleccionado,
                    height=100,
                    placeholder="Pega aquí el texto que copiaste del PDF",
                    key="texto_pegado_input"
                )
                
                if texto_pegado != st.session_state.texto_seleccionado:
                    st.session_state.texto_seleccionado = texto_pegado
                
                st.markdown("---")
                st.markdown("### 📋 Botones de asignación")
                
                # Botones en el orden del Excel
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    if st.button("📌 Título de la nota", use_container_width=True, key="btn_titulo"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-titulo',
                                'campo': 'Título de la nota'
                            })
                            st.session_state.nota_actual['titulo'] = st.session_state.texto_seleccionado.strip()
                            st.success("✅ Asignado a Título")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                    
                    if st.button("📝 RESUMEN DE LA NOTA (RTP)", use_container_width=True, key="btn_resumen"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-resumen',
                                'campo': 'Resumen'
                            })
                            st.session_state.nota_actual['resumen'] = st.session_state.texto_seleccionado.strip()
                            st.success("✅ Asignado a Resumen")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                    
                    if st.button("📰 MEDIOS DE COMUNICACIÓN", use_container_width=True, key="btn_medio"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-medio',
                                'campo': 'Medio'
                            })
                            st.session_state.nota_actual['medio'] = st.session_state.texto_seleccionado.strip()
                            st.success("✅ Asignado a Medio")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                
                with col_btn2:
                    if st.button("✍️ Autor", use_container_width=True, key="btn_autor"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-autor',
                                'campo': 'Autor'
                            })
                            st.session_state.nota_actual['autor'] = st.session_state.texto_seleccionado.strip()
                            st.success("✅ Asignado a Autor")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                    
                    if st.button("🔗 LINK", use_container_width=True, key="btn_link"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-link',
                                'campo': 'Link'
                            })
                            st.session_state.nota_actual['link'] = st.session_state.texto_seleccionado.strip()
                            if st.session_state.texto_seleccionado.strip().startswith('http'):
                                st.success("✅ Asignado a Link (clickeable)")
                            else:
                                st.success("✅ Asignado a Link")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                    
                    if st.button("📂 Tema de la nota", use_container_width=True, key="btn_tema"):
                        if st.session_state.texto_seleccionado.strip():
                            st.session_state.selecciones.append({
                                'text': st.session_state.texto_seleccionado.strip(),
                                'class': 'hl-tema',
                                'campo': 'Tema'
                            })
                            st.session_state.nota_actual['tema'] = st.session_state.texto_seleccionado.strip()
                            st.success("✅ Asignado a Tema")
                            st.session_state.texto_seleccionado = ""
                            st.rerun()
                        else:
                            st.warning("⚠️ Primero copia y pega texto del PDF")
                
                st.markdown("---")
                st.markdown("### ⚙️ Configuración")
                
                col_add1, col_add2 = st.columns(2)
                with col_add1:
                    relevancia = st.selectbox(
                        "🎯 ¿Es relevante?",
                        ["Sí", "No"],
                        index=0 if st.session_state.relevancia_seleccionada == "Sí" else 1,
                        key="select_relevancia"
                    )
                    st.session_state.relevancia_seleccionada = relevancia
                
                with col_add2:
                    tono = st.selectbox(
                        "🎯 Tono",
                        ["Informativo", "Positivo", "Negativo"],
                        index=["Informativo", "Positivo", "Negativo"].index(st.session_state.tono_seleccionado),
                        key="select_tono"
                    )
                    st.session_state.tono_seleccionado = tono
                
                # Resumen de campos asignados
                st.markdown("---")
                st.markdown("### 📋 Campos asignados")
                campos = {
                    'Título': st.session_state.nota_actual.get('titulo', ''),
                    'Resumen': st.session_state.nota_actual.get('resumen', ''),
                    'Medio': st.session_state.nota_actual.get('medio', ''),
                    'Autor': st.session_state.nota_actual.get('autor', ''),
                    'Link': st.session_state.nota_actual.get('link', ''),
                    'Tema': st.session_state.nota_actual.get('tema', '')
                }
                for nombre, valor in campos.items():
                    if valor:
                        st.success(f"✅ {nombre}: {valor[:50]}{'...' if len(valor)>50 else ''}")
                    else:
                        st.info(f"⬜ {nombre}: Pendiente")
                
                # Botón guardar
                st.markdown("---")
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
                        
                        if st.session_state.indice_nota < len(st.session_state.notas_extraidas) - 1:
                            st.session_state.indice_nota += 1
                            texto = st.session_state.notas_extraidas[st.session_state.indice_nota]
                            st.session_state.nota_actual = {'texto_original': texto}
                            st.session_state.selecciones = []
                            st.session_state.texto_seleccionado = ""
                        st.rerun()
                    else:
                        st.error("⚠️ El Título es obligatorio")
        else:
            st.info("📄 No hay texto cargado. Sube un PDF en la barra lateral.")
    
    # --- TAB 2: TABLA DE NOTAS ---
    with tab2:
        st.subheader("📋 Tabla de Notas Capturadas")
        if st.session_state.notas_capturadas:
            df_show = pd.DataFrame(st.session_state.notas_capturadas)
            st.dataframe(df_show[OFFICIAL_COLUMNS], use_container_width=True, height=500)
            
            # Estadísticas rápidas
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
                # Gráfica de tonos
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
                # Gráfica de campaña
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
else:
    st.info("👈 Sube un archivo PDF o Excel en la barra lateral para comenzar")
    
    with st.expander("📖 ¿Cómo usar esta herramienta?"):
        st.markdown("""
        ### 📊 Sistema de Captura de Notas RTP
        
        **1. Carga un archivo PDF** en la barra lateral
        
        **2. Selecciona texto del PDF:**
        - En el panel izquierdo, **copia** cualquier parte del texto del PDF
        - **Pega** el texto en el campo "Texto seleccionado"
        - **Presiona el botón** del campo correspondiente (Título, Resumen, Medio, etc.)
        - El texto se asignará automáticamente y se resaltará en el PDF
        
        **3. Colores de los campos:**
        - 🔵 **Título de la nota** (Azul)
        - 🟢 **RESUMEN DE LA NOTA (RTP)** (Verde)
        - 🟡 **MEDIOS DE COMUNICACIÓN** (Amarillo)
        - 🔴 **Autor** (Rojo)
        - 🔷 **LINK** (Celeste)
        - 🟣 **Tema de la nota** (Morado)
        
        **4. Guarda y exporta:**
        - Presiona **"GUARDAR NOTA COMPLETA"**
        - Revisa todas las notas en la pestaña "Tabla de Notas"
        - Analiza los datos en "Gráficas"
        - Descarga el Excel con el botón grande
        """)