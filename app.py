import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests
import base64

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Configurações de API
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Entrada de Dados")
    foto = st.camera_input("Tirar foto do veículo")
    audio = st.audio_input("Fale o tipo, marca, modelo e placa")
    
    if st.button("Finalizar Check-in"):
        if audio:
            with st.spinner("IA Padronizando..."):
                try:
                    # 1. Transcrição do áudio
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. IA com as NOVAS REGRAS de padronização
                    prompt = f'''Analise o texto: "{trans}"
                    Formate como: [TIPO] MARCA MODELO PLACA ANO.
                    REGRAS RÍGIDAS:
                    - Se for Volkswagen ou VW, escreva: V.W.
                    - Se for Mercedes, escreva: M.BENZ
                    - Coloque hífen na placa (ex: GAH-2H67)
                    - Se mencionar Ônibus, Micro, Carreta ou Guindaste, comece com essa palavra.
                    Responda APENAS a linha formatada.'''
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip().replace('"', '')
                    
                    # 3. Horário de Brasília (GMT-3)
                    # O servidor do Streamlit costuma ser UTC, então tiramos 3 horas
                    hora_brasilia = datetime.now() - timedelta(hours=3)
                    
                    # 4. Enviar para o Airtable
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                    
                    # Extração da placa para a coluna individual
                    partes = res_ia.split()
                    placa_f = next((p for p in partes if '-' in p), "Verificar")

                    payload = {
                        "records": [{"fields": {
                            "Data": hora_brasilia.strftime("%d/%m/%Y"),
                            "Hora": hora_brasilia.strftime("%H:%M"),
                            "Dados": res_ia,
                            "Placa": placa_f
                        }}]
                    }
                    
                    post_res = requests.post(url, headers=headers, json=payload)
                    
                    if post_res.status_code == 200:
                        st.success(f"✅ Registrado: {res_ia}")
                    else:
                        st.error(f"Erro no Airtable: {post_res.text}")
                        
                except Exception as e:
                    st.error(f"Erro técnico: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        headers_get = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
        res = requests.get(url_get, headers=headers_get).json()
        
        if "records" in res:
            dados_lista = []
            for r in res["records"]:
                f = r["fields"]
                # Mostra o emoji de câmera se houver anexo na coluna 'Foto'
                tem_foto = "📷" if "Foto" in f else "---"
                dados_lista.append({
                    "Data": f.get("Data"),
                    "Hora": f.get("Hora"),
                    "Veículo": f.get("Dados"),
                    "Placa": f.get("Placa"),
                    "Foto": tem_foto
                })
            st.table(pd.DataFrame(dados_lista))
    except:
        st.info("Sincronizando registros da oficina...")
