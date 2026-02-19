import streamlit as st
from groq import Groq
from datetime import datetime
import pandas as pd
import requests

# CONFIGURAÇÕES DE PÁGINA
st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# CONFIGURAÇÕES DO AIRTABLE (Vindos dos Secrets)
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"  # Confirme se no seu Airtable o nome da aba é este

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Entrada de Dados")
    audio = st.audio_input("Fale a Placa e Modelo")
    
    if st.button("Salvar no Sistema"):
        if audio:
            with st.spinner("Processando..."):
                # 1. Transcrição do Áudio
                transcription = client.audio.transcriptions.create(
                    file=("audio.wav", audio.getvalue()),
                    model="whisper-large-v3-turbo",
                    response_format="text",
                )
                
                # 2. Inteligência para formatar
                prompt = f'Formate "{transcription}" como: MARCA MODELO PLACA ANO. Ex: V.W. CONSTELLATION ABC-1234 2022. Responda APENAS a linha formatada.'
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}]
                )
                resultado = completion.choices[0].message.content.strip()
                
                # 3. Enviar para o Airtable
                url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                agora = datetime.now()
                
                payload = {
                    "records": [{
                        "fields": {
                            "Data": agora.strftime("%d/%m/%Y"),
                            "Hora": agora.strftime("%H:%M"),
                            "Dados": resultado,
                            "Placa": resultado.split(' ')[-2] if '-' in resultado else "Verificar"
                        }
                    }]
                }
                
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    st.success("✅ Salvo com sucesso!")
                else:
                    st.error(f"Erro ao salvar: {response.text}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    res = requests.get(url_get, headers=headers).json()
    
    if "records" in res:
        dados_lista = [r["fields"] for r in res["records"]]
        st.table(pd.DataFrame(dados_lista))
