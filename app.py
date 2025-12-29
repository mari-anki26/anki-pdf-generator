import streamlit as st
import pandas as pd
import PyPDF2
from sudachipy import tokenizer, dictionary
from pykakasi import kakasi
from io import BytesIO

# =========================
# Configuración de la página
# =========================
st.set_page_config(
    page_title="Generador Anki",
    page_icon="📚",
    layout="wide"
)

# =========================
# Estilos CSS personalizados
# =========================
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Título y descripción
# =========================
st.markdown('<p class="main-header">📚 Generador de Tarjetas Anki desde PDF</p>', unsafe_allow_html=True)
st.markdown("### Convierte PDFs en japonés en tarjetas de vocabulario para Anki")
st.markdown("---")

# Mapeo de partes de habla
POS_MAP = {
    "名詞": "Noun",
    "動詞": "Verb",
    "形容詞": "Adjective",
    "副詞": "Adverb"
}

# Inicializar tokenizador
@st.cache_resource
def init_tokenizer():
    """Inicializa el tokenizador de japonés"""
    try:
        tokenizer_obj = dictionary.Dictionary().create()
        return tokenizer_obj
    except Exception as e:
        st.error(f"Error al inicializar tokenizador: {e}")
        return None

@st.cache_resource
def init_kakasi():
    """Inicializa el conversor de kanji a hiragana"""
    try:
        kks = kakasi()
        return kks
    except Exception as e:
        st.error(f"Error al inicializar kakasi: {e}")
        return None

# Inicializar herramientas
with st.spinner("Cargando herramientas de procesamiento..."):
    tokenizer_obj = init_tokenizer()
    conv = init_kakasi()
    MODE = tokenizer.Tokenizer.SplitMode.C

# Función para limpiar texto
def limpiar_texto(texto):
    """Limpia el texto eliminando espacios y saltos de línea"""
    return texto.replace("\n", "").replace(" ", "").replace("　", "")

# =========================
# Interfaz de usuario
# =========================

# Columnas para mejor organización
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("#### 📁 Archivos requeridos")
    
    pdf_file = st.file_uploader(
        "1️⃣ PDF en japonés",
        type=["pdf"],
        help="Sube el PDF del que quieres extraer vocabulario"
    )
    
    jlpt_file = st.file_uploader(
        "2️⃣ CSV de niveles JLPT",
        type=["csv"],
        help="Formato: palabra,nivel (ej: 食べる,N5)"
    )
    
    freq_file = st.file_uploader(
        "3️⃣ CSV de frecuencias",
        type=["csv"],
        help="Formato: palabra,frecuencia (ej: 食べる,5000)"
    )
    
    dict_en_file = st.file_uploader(
        "4️⃣ CSV de diccionario JP-EN",
        type=["csv"],
        help="Formato: palabra,significado (ej: 食べる,to eat)"
    )

with col2:
    st.markdown("#### ⚙️ Configuración")
    
    min_jlpt = st.selectbox(
        "Nivel JLPT mínimo:",
        ["N5", "N4", "N3", "N2", "N1"],
        index=2,
        help="Solo incluir palabras hasta este nivel"
    )
    
    st.markdown("---")
    st.markdown("#### 📊 Información")
    st.info("**Formato de los CSV:**\n\n- Primera fila: encabezados\n- Segunda columna: datos\n- Separador: coma (,)")

st.markdown("---")

# Botón de procesamiento
process = st.button("🚀 **GENERAR TARJETAS ANKI**", type="primary", use_container_width=True)

# =========================
# Procesamiento
# =========================
if process:
    if not all([pdf_file, jlpt_file, freq_file, dict_en_file]):
        st.error("⚠️ Por favor, sube todos los archivos requeridos antes de procesar.")
    elif not tokenizer_obj or not conv:
        st.error("❌ Error: Las herramientas de procesamiento no se cargaron correctamente.")
    else:
        with st.spinner("📖 Procesando PDF... Esto puede tomar unos minutos."):
            try:
                # Cargar CSVs
                jlpt_df = pd.read_csv(jlpt_file)
                freq_df = pd.read_csv(freq_file)
                dict_df = pd.read_csv(dict_en_file)
                
                # Crear diccionarios
                jlpt_dict = dict(zip(jlpt_df.iloc[:, 0], jlpt_df.iloc[:, 1]))
                freq_dict = dict(zip(freq_df.iloc[:, 0], freq_df.iloc[:, 1]))
                en_dict = dict(zip(dict_df.iloc[:, 0], dict_df.iloc[:, 1]))
                
                vocab = {}
                
                # Leer PDF
                pdf_file.seek(0)
                reader = PyPDF2.PdfReader(pdf_file)
                total_pages = len(reader.pages)
                
                # Barra de progreso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for p in range(total_pages):
                    # Actualizar progreso
                    progress = (p + 1) / total_pages
                    progress_bar.progress(progress)
                    status_text.text(f"Procesando página {p + 1} de {total_pages}...")
                    
                    page = reader.pages[p]
                    raw_text = page.extract_text()
                    
                    if not raw_text:
                        continue
                    
                    clean = limpiar_texto(raw_text)
                    
                    if not clean:
                        continue
                    
                    # Tokenizar
                    tokens = tokenizer_obj.tokenize(clean, MODE)
                    
                    for t in tokens:
                        try:
                            pos_jp = t.part_of_speech()[0]
                            
                            # Filtrar partículas y auxiliares
                            if pos_jp in ("助詞", "助動詞"):
                                continue
                            
                            base = t.dictionary_form()
                            pos = POS_MAP.get(pos_jp, "Other")
                            
                            if base not in vocab:
                                vocab[base] = {
                                    "count": 0,
                                    "pos": pos
                                }
                            vocab[base]["count"] += 1
                        except:
                            continue
                
                # Limpiar barra de progreso
                progress_bar.empty()
                status_text.empty()
                
                # Crear DataFrame
                rows = []
                jlpt_rank = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}
                
                for word, info in vocab.items():
                    jlpt = jlpt_dict.get(word, "")
                    
                    # Filtrar por nivel JLPT
                    if jlpt and jlpt in jlpt_rank and jlpt_rank[jlpt] > jlpt_rank[min_jlpt]:
                        continue
                    
                    # Convertir a hiragana
                    reading = conv.convert(word)
                    reading_text = "".join([item['hira'] for item in reading])
                    furigana = f"<ruby>{word}<rt>{reading_text}</rt></ruby>"
                    
                    rows.append({
                        "Front": word,
                        "Reading": reading_text,
                        "Furigana": furigana,
                        "POS": info["pos"],
                        "Meaning_EN": en_dict.get(word, ""),
                        "JLPT": jlpt,
                        "Frequency_PDF": info["count"],
                        "Frequency_Global": freq_dict.get(word, "")
                    })
                
                df = pd.DataFrame(rows)
                
                # Ordenar por JLPT y frecuencia
                df = df.sort_values(by=["JLPT", "Frequency_PDF"], ascending=[True, False])
                
                # Mostrar resultados
                st.markdown(f'<div class="success-box">✅ <strong>¡Éxito!</strong> Se generaron {len(df)} palabras únicas.</div>', unsafe_allow_html=True)
                
                # Mostrar tabla
                st.markdown("### 📋 Primeras 50 palabras:")
                st.dataframe(df.head(50), use_container_width=True)
                
                # Botón de descarga
                buffer = BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                buffer.seek(0)
                
                st.download_button(
                    label="⬇️ **DESCARGAR EXCEL PARA ANKI**",
                    data=buffer,
                    file_name="anki_vocab.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True
                )
                
                # Estadísticas adicionales
                st.markdown("---")
                st.markdown("### 📊 Estadísticas")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total de palabras", len(df))
                
                with col2:
                    jlpt_counts = df['JLPT'].value_counts()
                    st.metric("Niveles JLPT encontrados", len(jlpt_counts))
                
                with col3:
                    avg_freq = df['Frequency_PDF'].mean()
                    st.metric("Frecuencia promedio", f"{avg_freq:.1f}")
            
            except Exception as e:
                st.error(f"❌ Error durante el procesamiento: {str(e)}")
                st.exception(e)

# =========================
# Instrucciones en el sidebar
# =========================
with st.sidebar:
    st.markdown("## 📖 Guía de uso")
    st.markdown("""
    ### Pasos:
    1. Sube tu PDF en japonés
    2. Sube los 3 archivos CSV con datos
    3. Selecciona el nivel JLPT
    4. Haz clic en generar
    5. Descarga el Excel
    
    ### Formato de CSV:
    Los archivos CSV deben tener:
    - **Primera fila**: encabezados
    - **Primera columna**: palabra en japonés
    - **Segunda columna**: dato correspondiente
    
    ### Importar a Anki:
    1. Abre Anki
    2. Archivo → Importar
    3. Selecciona el Excel descargado
    4. Configura los campos
    5. ¡Listo! 🎉
    """)
    
    st.markdown("---")
    st.markdown("### 💡 Consejos")
    st.info("Para mejores resultados, usa PDFs con texto seleccionable (no imágenes escaneadas).")
    
    st.markdown("---")
    st.markdown("Hecho con ❤️ usando Streamlit")
