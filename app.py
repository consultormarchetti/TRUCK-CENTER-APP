import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests
import re
import unicodedata

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# --- FUNÇÕES DE LIMPEZA E UPLOAD ---
def limpar_texto(texto):
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ç', 'c').replace('Ç', 'C')

def upload_imagem(foto):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": st.secrets["IMGBB_API_KEY"]}
        files = {"image": foto.getvalue()}
        response = requests.post(url, payload, files=files)
        return response.json()["data"]["url"] if response.status_code == 200 else None
    except:
        return None

# --- CONFIGS ---
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Entrada de Dados")
    foto = st.camera_input("Foto do Veículo")
    audio = st.audio_input("Fale o Veículo e Serviços")
    
    if st.button("🚀 Finalizar Check-in Total"):
        if audio:
            with st.spinner("Sincronizando Voz e Foto..."):
                try:
                    # 1. Processa Foto e Voz
                    link_foto = upload_imagem(foto) if foto else ""
                    trans = client.audio.transcriptions.create(file=("audio.wav", audio.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                    
                    # 2. IA Formata (VW, MB e Placa)
                    prompt = f"Organize: '{trans}'. Formato: MARCA MODELO - PLACA. Abaixo, lista de servicos com '-'. Use V.W. e M.Benz. Placa: ABC-1234. SO TEXTO."
                    compl = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                    res_ia = limpar_texto(compl.choices[0].message.content.strip())
                    
                    # 3. Placa
                    placa_match = re.search(r'[A-Z]{3}-?\d[A-Z0-9]\d{2}', res_ia.upper())
                    placa_f = placa_match.group(0) if placa_match else "Verificar"
                    if placa_f != "Verificar" and '-' not in placa_f: placa_f = f"{placa_f[:3]}-{placa_f[3:]}"

                    # 4. Envio Airtable
                    agora = datetime.now() - timedelta(hours=3)
                    payload = {"records": [{"fields": {
                        "Data": agora.strftime("%d/%m/%Y"),
                        "Hora": agora.strftime("%H:%M"),
                        "Dados": res_ia,
                        "Placa": placa_f,
                        "LinkFoto": link_foto  # Crie uma coluna 'LinkFoto' no Airtable (tipo URL ou Single Text)
                    }}]}
                    
                    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}", 
                                  headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}, 
                                  json=payload)
                    st.success("✅ Check-in enviado com sucesso!")
                except Exception as e:
                    st.error(f"Erro no envio: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        res = requests.get(url_get, headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}).json()
        
        if "records" in res:
            for r in res["records"]:
                f = r["fields"]
                with st.expander(f"🚛 {f.get('Placa', 'S/P')} | {f.get('Data')} {f.get('Hora')}"):
                    st.write(f"**Serviços:**\n{f.get('Dados')}")
                    if f.get("LinkFoto"):
                        st.link_button("🖼️ Ver Foto do Caminhão", f.get("LinkFoto"))
                    else:
                        st.caption("Sem foto anexada")
    except:
        st.info("Buscando novos registros...")
