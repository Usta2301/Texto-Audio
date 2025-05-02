import streamlit as st
import os
from gtts import gTTS
from PIL import Image
import base64
from io import BytesIO
from googletrans import Translator
from docx import Document
from PyPDF2 import PdfReader

# Config
st.set_page_config(page_title="Texto a Audio Mejorado", layout="wide")

# Sidebar
st.sidebar.title("Opciones de Entrada")
input_mode = st.sidebar.selectbox("Modo de entrada", ["Texto manual", "Cargar archivo"])

# Imagen decorativa
st.image("gato_raton.png", width=300)

# Entrada de texto
if input_mode == "Texto manual":
    text = st.text_area("Escribe el texto:", height=200)
else:
    uploaded = st.sidebar.file_uploader("Sube .txt, .pdf o .docx", type=["txt", "pdf", "docx"])
    text = ""
    if uploaded:
        if uploaded.type == "text/plain":
            text = uploaded.read().decode("utf-8")
        elif uploaded.type == "application/pdf":
            reader = PdfReader(uploaded)
            text = "".join(page.extract_text() or "" for page in reader.pages)
        elif uploaded.type.endswith("wordprocessingml.document"):
            doc = Document(uploaded)
            text = "\n".join(p.text for p in doc.paragraphs)

st.subheader("Previsualización del texto")
st.write(text or "_(aún no hay texto)_")

# Opción de traducción
if st.sidebar.checkbox("Traducir antes"):
    lang = st.sidebar.selectbox("Idioma destino", ["es", "en", "fr", "de"])
    translator = Translator()
    try:
        text = translator.translate(text, dest=lang).text
        st.success(f"Texto traducido a {lang}")
    except Exception as e:
        st.error("Error en la traducción: " + str(e))

# Botón de conversión
if st.button("Convertir a Audio"):
    if not text.strip():
        st.error("El texto está vacío.")
    else:
        # Generar TTS
        tts = gTTS(text, lang="es", slow=False)
        mp3_buf = BytesIO()
        tts.write_to_fp(mp3_buf)
        mp3_buf.seek(0)
        
        # Reproducir en la app
        st.audio(mp3_buf.getvalue(), format="audio/mp3")

        # Enlace de descarga
        b64 = base64.b64encode(mp3_buf.getvalue()).decode()
        href = f'<a href="data:audio/mp3;base64,{b64}" download="audio.mp3">📥 Descargar MP3</a>'
        st.markdown(href, unsafe_allow_html=True)
