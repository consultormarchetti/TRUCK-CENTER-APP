import streamlit as st
from groq import Groq
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

# Força o Streamlit a aceitar caracteres brasileiros
st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Atualiza o PC sozinho a cada 10 segundos
st_autorefresh(interval=30000, key="datarefresh")

# --- CONEXÃO GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO GROQ ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Entrada") # Removi o emoji e acento do título para testar
    foto = st.camera_input("Foto")
    audio = st.audio_input("Fale os dados")
    
    if st.button("Salvar Check-in"):
        if audio:
            with st.spinner("IA Processando..."):
                try:
                    # Transcrição (Whisper)
                    transcription = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # Prompt sem caracteres especiais para evitar conflito na IA
                    prompt = f'Traduza "{transcription}" para este formato: MARCA MODELO PLACA ANO/. Regras: VOLKSWAGEN vira V.W., Placa com hifen (Ex: ABC-1234). Responda apenas a linha.'
                    
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    resultado = completion.choices[0].message.content.strip()
                    agora = datetime.now()
                    
                    # SALVAR NA PLANILHA (Usando nomes de colunas simples)
                    df_novo = pd.DataFrame([{
                        "Data": agora.strftime("%d/%m/%Y"),
                        "Hora": agora.strftime("%H:%M"),
                        "Dados": resultado,
                        "Placa": resultado.split(' ')[2] if len(resultado.split(' ')) > 2 else ""
                    }])
                    
                    # Tenta ler a planilha. Se a aba chamar "Página1", mude para "Sheet1" se der erro.
                    # DICA: Renomeie a aba na sua planilha para "Dados" para facilitar
                    dados_atuais = conn.read() 
                    df_final = pd.concat([df_novo, dados_atuais], ignore_index=True)
                    conn.update(data=df_final)
                    
                    st.success("✅ Salvo!")
                    st.code(resultado)
                except Exception as e:
                    st.error(f"Erro de Texto/Codec: {e}")

with col2:
    st.subheader("Painel do PC")
    try:
        # Mostra o que está na planilha agora
        df_historico = conn.read()
        if not df_historico.empty:
            st.table(df_historico.head(10))
    except:
        st.info("Sincronizando com a planilha...")
