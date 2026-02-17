import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Truck Center - Entrada", page_icon="🚛")

# Configuração com o modelo que apareceu na sua lista
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except:
    st.error("Erro na configuração da chave nos Secrets.")

st.title("🚛 Check-in Rápido Truck Center")

def preparar_arquivo(uploaded_file):
    if uploaded_file is not None:
        return {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
    return None

# Interface simplificada para o pátio
foto = st.camera_input("1. Foto do Caminhão")
audio = st.audio_input("2. Relato do Consultor")

if st.button("🚀 Processar Entrada"):
    if foto and audio:
        with st.spinner("IA analisando imagem e áudio..."):
            foto_blob = preparar_arquivo(foto)
            audio_blob = preparar_arquivo(audio)
            
            prompt = """
            Analise a FOTO e o ÁUDIO. 
            No ÁUDIO, identifique a MARCA, MODELO, PLACA e ANO do caminhão. 
            
            Retorne PRIMEIRO uma linha EXATAMENTE neste formato para o JJW:
            MARCA MODELO PLACA ANO/
            
            Abaixo, descreva o defeito relatado para a oficina.
            """
            
            try:
                response = model.generate_content([prompt, foto_blob, audio_blob])
                st.success("Entrada Processada!")
                # st.code cria a caixa que facilita copiar para o JJW
                st.code(response.text) 
            except Exception as e:
                st.error(f"Erro na IA: {e}")
    else:
        st.warning("Capture a foto e o áudio primeiro!")
