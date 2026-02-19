import streamlit as st
from groq import Groq
from datetime import datetime
import pandas as pd
import requests

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Conectando com o Airtable
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1" 

# Inicializa o cliente Groq
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Entrada de Dados")
    
    # --- CAMMERA DE VOLTA ---
    foto = st.camera_input("Tirar foto do caminhão")
    
    # --- ÁUDIO ---
    audio = st.audio_input("Fale a Placa e Modelo")
    
    if st.button("Salvar no Sistema"):
        if audio:
            with st.spinner("IA Processando..."):
                try:
                    # Transcrição do áudio
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # Inteligência para formatar
                    prompt = f'Formate "{trans}" como: MARCA MODELO PLACA ANO. Ex: V.W. CONSTELLATION ABC-1234 2022. Responda APENAS a linha.'
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip()
                    
                    # Enviar para o Airtable
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                    
                    payload = {
                        "records": [{"fields": {
                            "Data": datetime.now().strftime("%d/%m/%Y"),
                            "Hora": datetime.now().strftime("%H:%M"),
                            "Dados": res_ia,
                            "Placa": res_ia.split(' ')[-2] if '-' in res_ia else "Verificar"
                        }}]
                    }
                    
                    post_res = requests.post(url, headers=headers, json=payload)
                    
                    if post_res.status_code == 200:
                        st.success(f"✅ Salvo: {res_ia}")
                    else:
                        st.error(f"Erro no Airtable: {post_res.text}")
                        
                except Exception as e:
                    # Se cair aqui, a chave Groq provavelmente está errada
                    st.error(f"Erro de Autenticação/IA: Verifique sua Chave Groq nos Secrets.")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
        get_res = requests.get(url_get, headers=headers).json()
        
        if "records" in get_res:
            df = pd.DataFrame([r["fields"] for r in get_res["records"]])
            if not df.empty:
                st.dataframe(df[["Data", "Hora", "Dados", "Placa"]], use_container_width=True)
    except:
        st.info("Sincronizando dados...")
