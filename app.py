import streamlit as st
from groq import Groq
from datetime import datetime
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Faz o painel do PC atualizar sozinho a cada 10 segundos
st_autorefresh(interval=10000, key="datarefresh")

# --- CONEXÃO COM GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO GROQ ---
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("📲 Entrada (Pátio)")
    foto = st.camera_input("Foto")
    audio = st.audio_input("Fale os dados")
    
    if st.button("🚀 Processar e Salvar"):
        if audio:
            with st.spinner("IA Processando..."):
                try:
                    # Transcrição com Whisper
                    transcription = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # Formatação com Llama
                    prompt = f'Formate "{transcription}" como: MARCA MODELO PLACA ANO/. Regras: VOLKSWAGEN=V.W., Placa com hífen (ABC-1234), Ano vazio se nulo. Responda APENAS a linha.'
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    
                    resultado = completion.choices[0].message.content.strip()
                    agora = datetime.now()
                    
                    # SALVAR NA PLANILHA GOOGLE
                    # Lê os dados atuais
                    dados_existentes = conn.read(worksheet="Página1")
                    nova_linha = pd.DataFrame([{
                        "Data": agora.strftime("%d/%m/%Y"),
                        "Hora": agora.strftime("%H:%M"),
                        "Dados": resultado,
                        "Placa": resultado.split(' ')[2] if len(resultado.split(' ')) > 2 else ""
                    }])
                    # Junta e atualiza a planilha
                    dados_atualizados = pd.concat([nova_linha, dados_existentes], ignore_index=True)
                    conn.update(worksheet="Página1", data=dados_atualizados)
                    
                    st.success("✅ Salvo na Planilha e no Painel!")
                    st.code(resultado)
                    if foto: st.image(foto, width=200)
                except Exception as e:
                    st.error(f"Erro: {e}")

with col2:
    st.subheader("📋 Painel do PC (Histórico Real)")
    try:
        # Lê os dados direto da planilha para o PC ver
        df_historico = conn.read(worksheet="Página1")
        if not df_historico.empty:
            st.table(df_historico.head(15)) # Mostra os últimos 15
        else:
            st.info("Nenhum registro encontrado na planilha.")
    except:
        st.warning("Aguardando conexão com a planilha...")

if st.sidebar.button("🗑️ Limpar Histórico (Planilha)"):
    # Limpa mantendo apenas o cabeçalho
    vazio = pd.DataFrame(columns=["Data", "Hora", "Dados", "Placa"])
    conn.update(worksheet="Página1", data=vazio)
    st.rerun()
