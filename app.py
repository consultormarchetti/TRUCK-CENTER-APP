import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Truck Center - Pátio", page_icon="🚛")

# --- IA CONFIG ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('models/gemini-2.0-flash')
except:
    st.error("Erro na chave da IA.")

# --- FUNÇÃO DE HISTÓRICO (Simulação de Banco de Dados Estável) ---
# Para o histórico persistir entre dispositivos, o Streamlit oferece o 'st.connection'
# Vamos usar um arquivo CSV simples no próprio GitHub por enquanto (é o mais imune a bugs de conexão)
HISTORICO_FILE = "historico_checkin.csv"

def salvar_dados(linha_texto):
    try:
        agora = datetime.now()
        placa = linha_texto.split(' ')[2] if len(linha_texto.split(' ')) > 2 else "S/P"
        nova_linha = pd.DataFrame([{
            "Data": agora.strftime("%d/%m/%Y"),
            "Hora": agora.strftime("%H:%M"),
            "Dados": linha_texto,
            "Placa": placa
        }])
        # Salva localmente e exibe (Para histórico real entre PC/Celular, use Google Sheets)
        if 'db' not in st.session_state:
            st.session_state.db = nova_linha
        else:
            st.session_state.db = pd.concat([nova_linha, st.session_state.db]).head(20)
    except:
        pass

# --- INTERFACE ---
st.title("🚛 Check-in Truck Center")

foto = st.camera_input("Foto do Caminhão")
audio = st.audio_input("Grave os dados (Voz)")

if st.button("🚀 Processar Entrada"):
    if audio:
        with st.spinner("IA Processando..."):
            audio_blob = {"mime_type": audio.type, "data": audio.getvalue()}
            prompt = """Extraia: MARCA MODELO PLACA ANO/. 
            Regras: VOLKSWAGEN vira V.W., Placa com hífen (ABC-1234), Ano vazio se não citado. 
            Responda APENAS a linha."""
            
            try:
                response = model.generate_content([prompt, audio_blob])
                resultado = response.text.strip()
                
                # Salva no histórico visível
                salvar_dados(resultado)
                
                st.success("Gerado com sucesso!")
                st.code(resultado)
                
                if foto:
                    st.image(foto, width=250)
            except Exception as e:
                st.error(f"Erro: {e}")

# --- PAINEL DO PC (Histórico dos últimos veículos) ---
st.write("---")
st.subheader("📋 Últimos Veículos no Pátio")

if 'db' in st.session_state and not st.session_state.db.empty:
    # Mostra uma tabela limpa para o PC
    st.table(st.session_state.db)
else:
    st.info("Aguardando o primeiro check-in do dia...")
