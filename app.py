import io
import re
import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Análisis de Sintesis y Medios RTP",
    page_icon="🚌",
    layout="wide"
)

st.title("🚌 Análisis Automático de Síntesis Informativas y Medios")
st.write(
    "Sube tus archivos (PDF de síntesis, planillas de seguimiento, CSV o Excel). "
    "El sistema procesará la información, generará reportes en pantalla y permitirá exportar los datos a Excel."
)

# Sidebar para carga de archivos
st.sidebar.header("📁 Carga de Documentos")
uploaded_file = st.sidebar.file_uploader(
    "Selecciona un archivo PDF, XLSX o CSV", 
    type=["pdf", "xlsx", "csv"]
)

def extract_data_from_pdf(pdf_file):
    """
    Extrae texto y URLs de archivos PDF tipo síntesis informativa o boletines.
    """
    records = []
    with pdfplumber.open(pdf_file) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            
            # Búsqueda de URLs dentro de la página
            urls = re.findall(r'https?://[^\s]+', text)
            
            # Detección de clasificación de la nota
            sentiment = "Informativa"
            if "Positivas" in text or "Positiva" in text:
                sentiment = "Positiva"
            elif "Negativas" in text or "Negativa" in text:
                sentiment = "Negativa"

            # Extracción del medio
            medio_match = re.search(r'MEDIOS?:?\s*([^\n]+)', text, re.IGNORECASE)
            medio = medio_match.group(1).strip() if medio_match else "No especificado"

            # Agregado de registros detectados
            if text.strip():
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                titulo = lines[0] if lines else f"Página {page_num}"
                
                records.append({
                    "Página": page_num,
                    "Título / Encabezado": titulo[:100],
                    "Medio": medio,
                    "Clasificación": sentiment,
                    "URLs Detectadas": ", ".join(urls) if urls else "Ninguna",
                    "Extracto Texto": text[:200].replace("\n", " ") + "..."
                })
    return pd.DataFrame(records)

if uploaded_file is not None:
    file_type = uploaded_file.name.split(".")[-1].lower()
    df = pd.DataFrame()

    try:
        # Procesar según el tipo de archivo subido
        if file_type == "pdf":
            st.info("📄 Procesando archivo PDF... Extrayendo texto, enlaces y estructura de notas.")
            df = extract_data_from_pdf(uploaded_file)
        elif file_type == "csv":
            df = pd.read_csv(uploaded_file)
        elif file_type == "xlsx":
            df = pd.read_excel(uploaded_file)

        if not df.empty:
            st.success(f"✅ Archivo procesado correctamente: **{uploaded_file.name}** ({len(df)} registros encontrados)")
            
            # Tabs principales de la interfaz
            tab1, tab2, tab3, tab4 = st.tabs([
                "📋 Vista General de Tablas", 
                "📊 Gráficos e Indicadores", 
                "⚙️ Tabla Dinámica", 
                "📥 Exportar a Excel"
            ])

            # --- TAB 1: TABLA DE DATOS ---
            with tab1:
                st.subheader("Registros Extraídos y Estructurados")
                st.dataframe(df, use_container_width=True)

            # --- TAB 2: GRÁFICOS ---
            with tab2:
                st.subheader("Análisis Visual de los Datos")
                col_chart1, col_chart2 = st.columns(2)

                # Detección de columnas útiles para graficar
                cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
                num_cols = df.select_dtypes(include=['number']).columns.tolist()

                with col_chart1:
                    if cat_cols:
                        selected_cat = st.selectbox("Selecciona Categoría para Distribución:", cat_cols, index=0)
                        df_counts = df[selected_cat].value_counts().reset_index()
                        df_counts.columns = [selected_cat, 'Cantidad']
                        
                        fig_pie = px.pie(
                            df_counts, 
                            names=selected_cat, 
                            values='Cantidad', 
                            title=f"Distribución por {selected_cat}",
                            hole=0.4
                        )
                        st.plotly_chart(fig_pie, use_container_width=True)

                with col_chart2:
                    if cat_cols:
                        fig_bar = px.bar(
                            df_counts, 
                            x=selected_cat, 
                            y='Cantidad', 
                            color=selected_cat,
                            title=f"Frecuencia por {selected_cat}"
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)

            # --- TAB 3: TABLA DINÁMICA ---
            with tab3:
                st.subheader("Configurador estilo Excel")
                cols = df.columns.tolist()
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    row_sel = st.selectbox("Filas (Index):", options=cols, index=0)
                with c2:
                    col_sel = st.selectbox("Columnas (Opcional):", options=["Ninguna"] + cols, index=0)
                with c3:
                    val_sel = st.selectbox("Valores:", options=cols, index=min(1, len(cols)-1))
                with c4:
                    agg_func = st.selectbox("Agregación:", options=["count", "sum", "mean", "min", "max"], index=0)

                if col_sel == "Ninguna":
                    pivot = df.groupby(row_sel)[val_sel].agg(agg_func).reset_index()
                else:
                    pivot = pd.pivot_table(
                        df, 
                        values=val_sel, 
                        index=row_sel, 
                        columns=col_sel, 
                        aggfunc=agg_func, 
                        fill_value=0
                    ).reset_index()

                st.write("### Resultado de la Tabla Dinámica:")
                st.dataframe(pivot, use_container_width=True)

            # --- TAB 4: EXPORTACIÓN ---
            with tab4:
                st.subheader("Generar Reporte Procesado")
                
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="Datos_Procesados", index=False)
                    if 'pivot' in locals():
                        pivot.to_excel(writer, sheet_name="Tabla_Dinamica", index=False)
                
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 Descargar Reporte Completo en Excel (.xlsx)",
                    data=excel_data,
                    file_name=f"Reporte_Procesado_{uploaded_file.name.split('.')[0]}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

    except Exception as e:
        st.error(f"Error procesando el documento: {str(e)}")

else:
    st.info("👆 Por favor sube tu archivo en la barra lateral para comenzar la extracción y análisis.")