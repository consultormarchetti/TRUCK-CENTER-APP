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
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).replace('ç', 'c').replace('Ç', 'C').upper()

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
    foto = st.camera_input("Tirar Foto do Veículo")
    audio = st.audio_input("Fale o Veículo, Placa e Serviços")
    
    if st.button("🚀 Finalizar Check-in Total"):
        if audio:
            with st.spinner("Gravando dados em MAIÚSCULAS..."):
                try:
                    link_foto = upload_imagem(foto) if foto else ""
                    
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text"
                    )
                    
                    # Prompt focado em MAIÚSCULAS e Placa com Hífen
                    prompt = f"""Transcrição: '{trans}'. 
                    Instrução: Organize em LETRAS MAIÚSCULAS.
                    - Formato: MARCA MODELO - PLACA (COM HÍFEN EX: ABC-1234).
                    - Lista de serviços logo abaixo com '-'.
                    - Proibido inventar serviços.
                    Responda apenas o texto organizado."""
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = limpar_texto(compl.choices[0].message.content.strip())
                    
                    # Extração da placa para o campo específico
                    placa_match = re.search(r'[A-Z]{3}-?\d[A-Z0-9]\d{2}', res_ia)
                    placa_f = placa_match.group(0) if placa_match else "VERIFICAR"
                    if placa_f != "VERIFICAR" and '-' not in placa_f: 
                        placa_f = f"{placa_f[:3]}-{placa_f[3:]}"

                    agora = datetime.now() - timedelta(hours=3)
                    fields = {
                        "Data": agora.strftime("%d/%m/%Y"),
                        "Hora": agora.strftime("%H:%M"),
                        "Dados": res_ia,
                        "Placa": placa_f
                    }
                    if link_foto: fields["LinkFoto"] = link_foto

                    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}", 
                                  headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}, 
                                  json={"records": [{"fields": fields}]})
                    
                    st.success(f"✅ REGISTRADO: {placa_f}")
                    st.rerun()
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
                placa_topo = f.get('Placa', 'S/P').upper()
                with st.expander(f"🚛 {placa_topo} | {f.get('Data')} {f.get('Hora')}"):
                    # Layout com miniatura
                    c_txt, c_img = st.columns([2, 1])
                    with c_txt:
                        st.write(f"**RELATÓRIO:**\n{f.get('Dados')}")
                    with c_img:
                        if f.get("LinkFoto"):
                            st.image(f.get("LinkFoto"), caption="MINIATURA (CLIQUE PARA AMPLIAR)", use_container_width=True)
                            st.link_button("🔍 VER ORIGINAL", f.get("LinkFoto"))
    except:
        st.write("SINCRONIZANDO...")
