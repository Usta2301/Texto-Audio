import streamlit as st
import os
import time
import glob
from gtts import gTTS
from PIL import Image
import base64
from pydub import AudioSegment
from io import BytesIO
from googletrans import Translator
from docx import Document
from PyPDF2 import PdfReader
# ElevenLabs stub (uncomment and install elevenlabs-sdk)
# from elevenlabs import generate, set_api_key

# Config
st.set_page_config(page_title="Texto a Audio Mejorado", layout="wide")

# Sidebar
st.sidebar.title("Opciones de Entrada")
input_mode = st.sidebar.selectbox("Modo de entrada", ["Texto manual", "Cargar archivo"])

# Load image
image = Image.open('gato_raton.png')
st.image(image, width=350)

# Input text
if input_mode == "Texto manual":
    text = st.text_area("Ingrese el texto a convertir", height=200)
else:
    uploaded = st.sidebar.file_uploader("Sube .txt, .pdf o .docx", type=["txt", "pdf", "docx"])
    text = ""
    if uploaded:
        if uploaded.type == "text/plain":
            text = uploaded.read().decode('utf-8')
        elif uploaded.type == "application/pdf":
            reader = PdfReader(uploaded)
            text = "".join(page.extract_text() for page in reader.pages)
        elif uploaded.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            doc = Document(uploaded)
            text = "".join(p.text for p in doc.paragraphs)

st.subheader("Texto a reproducir:")
st.write(text)

# Translation option
translate = st.sidebar.checkbox("Traducir antes de convertir")
if translate:
    target_lang = st.sidebar.selectbox("Idioma destino", ["es", "en", "fr", "de"])
    translator = Translator()
    text = translator.translate(text, dest=target_lang).text
    st.info(f"Texto traducido a {target_lang}")

# Engine selection
tts_engine = st.sidebar.selectbox("Motor TTS", ["gTTS", "ElevenLabs"])

# Voice controls
st.sidebar.subheader("Controles de voz")
speed = st.sidebar.slider("Velocidad (1.0 = normal)", 0.5, 2.0, 1.0)
pitch = st.sidebar.slider("Pitch (0.5 = bajo)", 0.5, 2.0, 1.0)

# Fragment selection
st.sidebar.subheader("Fragmento de texto")
start_idx = st.sidebar.number_input("Inicio (carácter)", 0, max(0, len(text)-1), 0)
end_idx = st.sidebar.number_input("Fin (carácter)", start_idx+1, len(text), len(text))
frag = text[start_idx:end_idx]

# Cache decorator for audio generation
@st.cache_data
def generate_audio(text, engine, speed, pitch):
    # generate mp3 bytes and length
    if engine == "gTTS":
        tts = gTTS(text, lang='es' if ' ' not in text else 'en', slow=False)
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio = AudioSegment.from_file(buffer, format="mp3")
    else:
        # ElevenLabs example
        # set_api_key(os.getenv('ELEVEN_API_KEY'))
        # audio_bytes = generate(text=text, voice="Rachel", model="eleven_multilingual_v1")
        # audio = AudioSegment.from_file(BytesIO(audio_bytes), format="mp3")
        st.warning("ElevenLabs no configurado, usando gTTS como fallback.")
        tts = gTTS(text, lang='es', slow=False)
        buffer = BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio = AudioSegment.from_file(buffer, format="mp3")
    # apply speed
    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * speed)})
    audio = audio.set_frame_rate(audio.frame_rate)
    # pitch shift approximation via speed change (simplified)
    audio = audio._spawn(audio.raw_data, overrides={"frame_rate": int(audio.frame_rate * pitch)})
    audio = audio.set_frame_rate(audio.frame_rate)
    return audio

if st.button("Convertir a Audio"):
    if not frag:
        st.error("Texto vacío.")
    else:
        audio = generate_audio(frag, tts_engine, speed, pitch)
        # export options
        fmt = st.selectbox("Formato de salida", ["mp3", "wav", "ogg"])
        buf = BytesIO()
        audio.export(buf, format=fmt)
        buf.seek(0)
        st.audio(buf.read(), format=f"audio/{fmt}")
        # Download link
        b64 = base64.b64encode(buf.getvalue()).decode()
        href = f'<a href="data:audio/{fmt};base64,{b64}" download="audio.{fmt}">Descargar {fmt.upper()}</a>'
        st.markdown(href, unsafe_allow_html=True)
        # Generate subtitles SRT approx
        words = frag.split()
        total_ms = len(audio)
        per_word = total_ms / len(words)
        srt = ""
        cum = 0
        for i, w in enumerate(words, 1):
            start = cum
            end = cum + per_word
            def ms_to_srt(ms):
                h = int(ms // 3600000)
                m = int((ms % 3600000) // 60000)
                s = int((ms % 60000) // 1000)
                ms_rem = int(ms % 1000)
                return f"{h:02}:{m:02}:{s:02},{ms_rem:03}"
            srt += f"{i}\n{ms_to_srt(start)} --> {ms_to_srt(end)}\n{w}\n\n"
            cum = end
        st.download_button("Descargar SRT", srt, file_name="subtitles.srt", mime="text/plain")

# Cleanup older files in temp
try:
    os.mkdir("temp")
except:
    pass

def cleanup(days=7):
    now = time.time()
    for f in glob.glob("temp/*"):
        if os.stat(f).st_mtime < now - days*86400:
            os.remove(f)
cleanup(7)
