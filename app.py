import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests
import base64
import re

st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Configurações de Acesso
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Entrada de Dados")
    foto = st.camera_input("Foto do Veículo/Placa")
    audio = st.audio_input("Fale o Veículo e os Serviços")
    
    if st.button("Finalizar Check-in"):
        if audio:
            with st.spinner("IA Processando dados e imagem..."):
                try:
                    # 1. Áudio -> Texto
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. IA para Formatação Rigorosa
                    prompt = f"""Analise: '{trans}'. 
                    Formate como: MARCA MODELO - PLACA. 
                    Abaixo, liste os serviços com '- '. 
                    Regras de Substituição:
                    - 'Volkswagen' ou 'Volks' vira 'V.W.'
                    - 'Mercedes' ou 'Mercedes-Benz' vira 'M.Benz'
                    - Placas devem ter hífen (ex: ABC-1234 ou ABC-1C34)
                    Responda APENAS o texto formatado."""
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip()
                    
                    # 3. Refino de Placa (Garantia Extra via Código)
                    # Procura padrões ABC1234 ou ABC1C34
                    padrao_placa = re.compile(r'([A-Z]{3})(\d[A-Z0-9]\d{2})')
                    res_ia = padrao_placa.sub(r'\1-\2', res_ia.upper())

                    # 4. Processamento da Foto (Truque Base64)
                    img_str = ""
                    if foto:
                        encoded_string = base64.b64encode(foto.getvalue()).decode()
                        img_str = f"\n\n--- FOTO (BASE64) ---\ndata:image/jpeg;base64,{encoded_string}"

                    # 5. Fuso Horário GMT-3
                    hora_br = datetime.now() - timedelta(hours=3)

                    # 6. Envio para o Airtable
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                    
                    # Extrai a placa formatada para a coluna específica
                    placa_match = re.search(r'[A-Z]{3}-[A-Z0-9]{4}', res_ia)
                    placa_coluna = placa_match.group(0) if placa_match else "Verificar"

                    payload = {
                        "records": [{"fields": {
                            "Data": hora_br.strftime("%d/%m/%Y"),
                            "Hora": hora_br.strftime("%H:%M"),
                            "Dados": res_ia + img_str,
                            "Placa": placa_coluna
                        }}]
                    }
                    
                    post_res = requests.post(url, headers=headers, json=payload)
                    
                    if post_res.status_code == 200:
                        st.success(f"✅ Registro Concluído!")
                    else:
                        st.error(f"Erro no banco de dados: {post_res.text}")
                        
                except Exception as e:
                    st.error(f"Erro técnico: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        res = requests.get(url_get, headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}).json()
        
        if "records" in res:
            records = res["records"]
            dados_para_tabela = []
            for r in records:
                f = r["fields"]
                # Limpa o texto da foto para não poluir a tabela visual
                resumo_dados = f.get("Dados", "").split("--- FOTO")[0]
                dados_para_tabela.append({
                    "Data": f.get("Data"),
                    "Hora": f.get("Hora"),
                    "Serviço/Veículo": resumo_dados,
                    "Placa": f.get("Placa"),
                    "Foto": "📷 SIM" if "--- FOTO" in f.get("Dados", "") else "NÃO"
                })
            
            st.dataframe(pd.DataFrame(dados_para_tabela), use_container_width=True, height=600)
    except:
        st.info("Sincronizando registros...")
