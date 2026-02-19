import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests
import re
import unicodedata

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

def limpar_texto(texto):
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ç', 'c').replace('Ç', 'C')

def upload_imagem(foto):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": st.secrets["IMGBB_API_KEY"]}
        files = {"image": foto.getvalue()}
        response = requests.post(url, payload, files=files, timeout=15)
        return response.json()["data"]["url"] if response.status_code == 200 else ""
    except:
        return ""

AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Entrada de Dados")
    # Captura de foto com foco em qualidade
    foto = st.camera_input("Tirar Foto (Foque na Placa/Avaria)")
    audio = st.audio_input("Fale o Veículo, Placa e Serviços")
    
    if st.button("🚀 Finalizar Check-in Total"):
        if audio:
            with st.spinner("Processando dados reais..."):
                try:
                    link_foto = upload_imagem(foto) if foto else ""
                    
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text"
                    )
                    
                    # PROMPT RECALIBRADO: Proibido inventar dados
                    prompt = f"""Transcrissão: '{trans}'. 
                    Instrução: Organize o texto acima de forma profissional. 
                    - Não invente nomes, placas ou serviços que não foram ditos.
                    - Use 'V.W.' para Volkswagen e 'M.Benz' para Mercedes.
                    - Se a placa for dita, coloque-a no formato ABC-1234.
                    - Formato: MARCA MODELO - PLACA (se houver).
                    - Lista de serviços logo abaixo.
                    Responda APENAS com as informações presentes na transcrição."""
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = limpar_texto(compl.choices[0].message.content.strip())
                    
                    # Extração de placa real do áudio
                    placa_match = re.search(r'[A-Z]{3}-?\d[A-Z0-9]\d{2}', res_ia.upper())
                    placa_f = placa_match.group(0) if placa_match else "Verificar"
                    if placa_f != "Verificar" and '-' not in placa_f: 
                        placa_f = f"{placa_f[:3]}-{placa_f[3:]}"

                    agora = datetime.now() - timedelta(hours=3)
                    fields = {
                        "Data": agora.strftime("%d/%m/%Y"),
                        "Hora": agora.strftime("%H:%M"),
                        "Dados": res_ia,
                        "Placa": placa_f
                    }
                    if link_foto: fields["LinkFoto"] = link_foto

                    resp = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}", 
                                  headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}, 
                                  json={"records": [{"fields": fields}]})
                    
                    if resp.status_code == 200:
                        st.success(f"✅ Gravado: {placa_f}")
                    else:
                        st.error("Erro ao gravar no banco.")
                except Exception as e:
                    st.error(f"Erro: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        res = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc&sort[1][field]=Hora&sort[1][direction]=desc", 
                           headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}).json()
        if "records" in res:
            for r in res["records"]:
                f = r["fields"]
                with st.expander(f"🚛 {f.get('Placa', 'S/P')} | {f.get('Data')} {f.get('Hora')}"):
                    st.write(f"**Relatório:**\n{f.get('Dados')}")
                    if f.get("LinkFoto"):
                        st.link_button("🖼️ Ver Foto em Alta", f.get("LinkFoto"))
    except:
        st.write("Sincronizando...")
