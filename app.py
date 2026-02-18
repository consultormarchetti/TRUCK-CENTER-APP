import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
import urllib.parse

# Configuração da Página
st.set_page_config(page_title="Truck Center - Pátio", page_icon="🚛", layout="wide")

# --- CONEXÃO COM A PLANILHA (Onde os dados ficam salvos para o PC) ---
# Substitua pelo link da sua planilha se quiser conectar agora
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1o-t_0CWSwMQvVblb-G-9-LBbs61DynvO9EDwRtFgEsE/edit?usp=sharing"

# --- CONFIGURAÇÃO DA IA ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-pro')
except:
    st.error("Erro na chave da IA nos Secrets.")

# --- INICIALIZAÇÃO DO HISTÓRICO NO APP ---
if 'historico' not in st.session_state:
    st.session_state.historico = []

st.title("🚛 Truck Center - Check-in Inteligente")

# Interface em colunas: Esquerda para Input, Direita para o PC ver o Histórico
col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📲 Entrada no Pátio")
    foto = st.camera_input("Foto do Veículo")
    audio = st.audio_input("Fale: Marca, Modelo, Placa e Ano")
    
    if st.button("🚀 Processar Check-in"):
        if audio:
            with st.spinner("IA Processando..."):
                audio_blob = {"mime_type": audio.type, "data": audio.getvalue()}
                
                # Prompt Refinado (Regra VW, Hífen na Placa, Ano Nulo)
                prompt = """Extraia do áudio e formate como: MARCA MODELO PLACA ANO/
                Regras:
                1. Se for VOLKSWAGEN, mude para: V.W.
                2. Na PLACA, adicione hífen (Ex: ABC-1234 ou GAH-2H67).
                3. Se não falar o ANO, deixe o campo vazio antes da barra.
                4. Responda APENAS a linha."""
                
                try:
                    response = model.generate_content([prompt, audio_blob])
                    resultado = response.text.strip()
                    hora = datetime.now().strftime("%H:%M")
                    
                    # Salva na memória do app (para visualização instantânea no PC)
                    st.session_state.historico.insert(0, {"Hora": hora, "Dados": resultado})
                    
                    st.success("Gerado!")
                    st.code(resultado)
                    
                    # Botão WhatsApp para envio rápido
                    texto_zap = urllib.parse.quote(f"🚛 *Check-in Truck Center*\n{resultado}")
                    st.markdown(f'''<a href="https://wa.me/?text={texto_zap}" target="_blank">
                        <button style="width:100%;background-color:#25D366;border:none;padding:8px;color:white;border-radius:5px;">
                        📲 Enviar via WhatsApp</button></a>''', unsafe_allow_html=True)
                    
                    if foto:
                        st.image(foto, width=200) # Foto bem pequena para economizar espaço
                except Exception as e:
                    st.error(f"Erro: {e}")

with col2:
    st.subheader("📋 Painel do Consultor (PC)")
    if st.session_state.historico:
        # Transforma o histórico em tabela para o PC copiar rápido
        df = pd.DataFrame(st.session_state.historico)
        st.table(df)
        
        if st.button("🗑️ Limpar Painel"):
            st.session_state.historico = []
            st.rerun()
    else:
        st.info("Aguardando check-in no pátio...")

# Rodapé com instruções
st.sidebar.info(f"Trabalhando com: models/gemini-2.0-flash")
