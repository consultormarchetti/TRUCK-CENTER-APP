import streamlit as st
from groq import Groq # Precisamos adicionar groq no requirements.txt
from datetime import datetime
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# --- CONFIGURAÇÃO GROQ (Muito mais rápido e estável que o Gemini para áudio) ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("Configure a GROQ_API_KEY nos Secrets.")

if 'historico' not in st.session_state:
    st.session_state.historico = []

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📲 Entrada")
    foto = st.camera_input("Foto")
    audio = st.audio_input("Fale os dados do caminhão")
    
    if st.button("🚀 Processar"):
        if audio:
            with st.spinner("Traduzindo áudio..."):
                try:
                    # 1. Transcreve o áudio usando Whisper (O melhor do mundo para isso)
                    transcription = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. Formata o texto com Llama 3 (IA da Meta)
                    prompt = f"""
                    Pegue este texto: "{transcription}"
                    Formate EXATAMENTE assim: MARCA MODELO PLACA ANO/
                    Regras: 
                    - VOLKSWAGEN vira V.W.
                    - Placa com hífen (Ex: GAH-2H67).
                    - Se não houver ano, deixe vazio antes da barra.
                    - Responda APENAS a linha.
                    """
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    resultado = completion.choices[0].message.content.strip()
                    hora = datetime.now().strftime("%H:%M")
                    
                    st.session_state.historico.insert(0, {"Hora": hora, "Dados": resultado})
                    st.success("Pronto!")
                    st.code(resultado)
                    
                    # WhatsApp
                    texto_zap = urllib.parse.quote(f"🚛 *Check-in*\n{resultado}")
                    st.markdown(f'<a href="https://wa.me/?text={texto_zap}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">📲 Enviar WhatsApp</button></a>', unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

with col2:
    st.subheader("📋 Painel do PC")
    if st.session_state.historico:
        st.table(pd.DataFrame(st.session_state.historico))
    else:
        st.info("Aguardando entrada...")
