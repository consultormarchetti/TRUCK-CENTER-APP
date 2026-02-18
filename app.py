import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import urllib.parse

st.set_page_config(page_title="Truck Center - Pátio", page_icon="🚛", layout="wide")

# --- CONFIGURAÇÃO DA IA (Chave Nova + Modelo Lite) ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # O 'lite' é o melhor equilíbrio para evitar o erro 429 de limite
    model = genai.GenerativeModel('models/gemini-2.0-flash-lite')
except:
    st.error("Erro nos Secrets. Verifique a nova chave API.")

# --- BANCO DE DADOS EM SESSÃO ---
if 'historico' not in st.session_state:
    st.session_state.historico = []

st.title("🚛 Check-in Truck Center")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📲 Entrada")
    foto = st.camera_input("Foto")
    audio = st.audio_input("Fale: Marca, Modelo, Placa e Ano")
    
    if st.button("🚀 Processar"):
        if audio:
            with st.spinner("IA Processando..."):
                audio_blob = {"mime_type": audio.type, "data": audio.getvalue()}
                
                prompt = """Extraia: MARCA MODELO PLACA ANO/
                Regras:
                1. VOLKSWAGEN vira: V.W.
                2. Placa com hífen (Ex: GAH-2H67).
                3. Se não ouvir o ano, deixe vazio antes da barra.
                4. Responda APENAS a linha."""
                
                try:
                    response = model.generate_content([prompt, audio_blob])
                    resultado = response.text.strip()
                    hora = datetime.now().strftime("%H:%M")
                    
                    # Guarda no histórico para o PC ver
                    st.session_state.historico.insert(0, {"Hora": hora, "Dados": resultado})
                    
                    st.success("Pronto!")
                    st.code(resultado)
                    
                    # Botão WhatsApp
                    texto_zap = urllib.parse.quote(f"🚛 *Check-in*\n{resultado}")
                    st.markdown(f'<a href="https://wa.me/?text={texto_zap}" target="_blank"><button style="width:100%;background-color:#25D366;color:white;border:none;padding:10px;border-radius:5px;">📲 WhatsApp</button></a>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Erro: {e}")

with col2:
    st.subheader("📋 Painel do PC")
    if st.session_state.historico:
        st.table(pd.DataFrame(st.session_state.historico))
        if st.button("🗑️ Limpar"):
            st.session_state.historico = []
            st.rerun()
    else:
        st.info("Aguardando check-in...")
