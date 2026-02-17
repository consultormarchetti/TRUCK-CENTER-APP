import streamlit as st
import google.generativeai as genai

# Configuração da Chave
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])

st.title("🚛 Ajuste de Sistema")

# Comando para listar os modelos permitidos para sua conta
st.write("Modelos disponíveis para sua chave:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        st.code(m.name)
except:
    st.error("Erro: Verifique a chave API nos Secrets.")

st.title("🚛 Check-in Rápido Truck Center")

# Função para converter arquivos do Streamlit para o formato da IA
def preparar_arquivo(uploaded_file):
    if uploaded_file is not None:
        return {
            "mime_type": uploaded_file.type,
            "data": uploaded_file.getvalue()
        }
    return None

# Interface
foto = st.camera_input("1. Foto do Caminhão")
audio = st.audio_input("2. Relato do Consultor")

if st.button("🚀 Processar Entrada"):
    if foto and audio:
        with st.spinner("IA analisando imagem e áudio..."):
            # Transformando os arquivos para o formato correto
            foto_blob = preparar_arquivo(foto)
            audio_blob = preparar_arquivo(audio)
            
            # Prompt focado no sistema JJW XP (MARCA MODELO PLACA ANO/)
            prompt = """
            Analise a FOTO e o ÁUDIO. 
            No ÁUDIO, o consultor dirá o modelo e o defeito. 
            
            Retorne PRIMEIRO uma linha EXATAMENTE neste formato para o sistema JJW:
            MARCA MODELO PLACA ANO/
            
            Abaixo dessa linha, escreva:
            ---
            RESUMO PARA OFICINA: (Descreva o defeito relatado no áudio)
            """
            
            try:
                # Enviando os blobs (dados puros) para a IA
                response = model.generate_content([prompt, foto_blob, audio_blob])
                
                st.success("Entrada Processada!")
                # st.code facilita o clique para copiar e colar no JJW
                st.code(response.text) 
                
            except Exception as e:
                st.error(f"Erro no processamento da IA: {e}")
    else:
        st.warning("Capture a foto e o áudio primeiro!")
