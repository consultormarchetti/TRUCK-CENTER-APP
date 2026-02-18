import streamlit as st
import google.generativeai as genai

# Configuração da Página
st.set_page_config(page_title="Truck Center - Entrada", page_icon="🚛")

# Configuração da IA com modelo estável
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    # Usando o Flash 1.5 que tem a maior cota para o plano gratuito
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except Exception as e:
    st.error("Erro na configuração da chave. Verifique os Secrets.")

st.title("🚛 Check-in Rápido Truck Center")
st.write("Gere a linha para o JJW XP usando apenas a voz.")

def preparar_arquivo(uploaded_file):
    if uploaded_file is not None:
        return {"mime_type": uploaded_file.type, "data": uploaded_file.getvalue()}
    return None

# Interface focada em economia de dados
foto = st.camera_input("1. Foto do Caminhão (Para registro)")
audio = st.audio_input("2. Fale: Marca, Modelo, Placa e Ano")

if st.button("🚀 Gerar Texto para o Sistema"):
    if audio:
        with st.spinner("IA processando seu áudio..."):
            audio_blob = preparar_arquivo(audio)
            
            # Prompt econômico: Ignora a foto no processamento da IA para economizar cota
            prompt = "Extraia do áudio apenas os dados do veículo e responda EXATAMENTE neste formato: MARCA MODELO PLACA ANO/"
            
            try:
                # Enviamos apenas o ÁUDIO. A foto fica salva apenas localmente no app.
                response = model.generate_content([prompt, audio_blob])
                
                st.success("Copiado com sucesso para o JJW!")
                # Caixa de texto fácil de copiar para o sistema oficial
                st.code(response.text) 
                
                if foto:
                    st.image(foto, caption="Foto registrada no check-in", width=300)
                    
            except Exception as e:
                st.error(f"Erro na IA: {e}")
                st.info("Dica: Se aparecer erro 429, aguarde 30 segundos e tente de novo.")
    else:
        st.warning("Por favor, grave o áudio com os dados do caminhão.")
