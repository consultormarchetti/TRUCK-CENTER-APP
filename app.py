import streamlit as st
import google.generativeai as genai

# Configuração da Página
st.set_page_config(page_title="Truck Center - Entrada", page_icon="🚛")

# Tenta ler a chave de segurança que vamos configurar depois
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Erro: Chave API não configurada.")

st.title("🚛 Check-in Rápido de Caminhões")

# Captura de Foto e Áudio
foto = st.camera_input("1. Foto do Caminhão (ou Placa)")
audio = st.audio_input("2. Relato do Consultor (Modelo e Defeito)")

if st.button("🚀 Processar Entrada"):
    if foto and audio:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        with st.spinner("IA Analisando dados híbridos..."):
            prompt = """
            Você é um consultor técnico de caminhões experiente.
            Analise a FOTO e o ÁUDIO. 
            No ÁUDIO, o consultor dirá o modelo e o defeito. 
            Priorize o áudio para o Modelo e Placa se houver conflito com a imagem.
            Retorne um resumo organizado com:
            - VEÍCULO (Marca/Modelo)
            - PLACA
            - RELATO DO PROBLEMA
            Seja direto e profissional.
            """
            response = model.generate_content([prompt, foto, audio])
            
            st.success("Entrada Processada com Sucesso!")
            st.markdown(f"### 📋 Dados da OS:\n {response.text}")
    else:
        st.warning("Por favor, capture a foto e o áudio primeiro.")
