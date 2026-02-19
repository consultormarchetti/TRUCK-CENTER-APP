import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests
import re

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Configurações
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
    
    if st.button("Finalizar Check-in"):
        if audio:
            with st.spinner("Processando..."):
                try:
                    # 1. Transcrição
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. IA - Prompt mais rígido para evitar caracteres especiais
                    prompt = f"""Organize: '{trans}'. 
                    Formato: MARCA MODELO - PLACA. 
                    Serviços: Liste com '*' sem caracteres especiais. 
                    Abrevie: Volkswagen -> V.W., Mercedes -> MB.
                    Placa com hífen: ABC-1234.
                    Responda apenas o texto limpo."""
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip()

                    # 3. Limpeza de Segurança (Remove aspas e caracteres que travam o Airtable)
                    res_ia_safe = res_ia.replace('"', '').replace("'", "").replace("{", "").replace("}", "")
                    
                    # 4. Busca de Placa (Regex Mercosul/Antiga)
                    placa_match = re.search(r'[A-Z]{3}-?\d[A-Z0-9]\d{2}', res_ia_safe.upper())
                    placa_f = placa_match.group(0) if placa_match else "Verificar"
                    if placa_f != "Verificar" and '-' not in placa_f:
                        placa_f = f"{placa_f[:3]}-{placa_f[3:]}"

                    # 5. Fuso Horário
                    agora = datetime.now() - timedelta(hours=3)

                    # 6. Envio para o Airtable
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                    
                    payload = {
                        "records": [{
                            "fields": {
                                "Data": agora.strftime("%d/%m/%Y"),
                                "Hora": agora.strftime("%H:%M"),
                                "Dados": str(res_ia_safe),
                                "Placa": str(placa_f)
                            }
                        }]
                    }
                    
                    resp = requests.post(url, headers=headers, json=payload)
                    
                    if resp.status_code == 200:
                        st.success("✅ Check-in realizado!")
                        if foto:
                            st.info("💡 Para salvar a foto no Airtable, anexe-a diretamente na coluna 'Attachments' da planilha no PC.")
                    else:
                        st.error(f"Erro no banco: {resp.text}")
                        
                except Exception as e:
                    st.error(f"Falha técnica: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        res = requests.get(url_get, headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}).json()
        
        if "records" in res:
            df = pd.DataFrame([r["fields"] for r in res["records"]])
            if not df.empty:
                # Garante que as colunas existam antes de mostrar
                for c in ["Data", "Hora", "Dados", "Placa"]:
                    if c not in df.columns: df[c] = ""
                st.table(df[["Data", "Hora", "Placa", "Dados"]].head(10))
    except:
        st.write("Aguardando novos registros...")
