import streamlit as st
from groq import Groq
from datetime import datetime
import pandas as pd
import requests

# Configuração da Página
st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# Conectando com as chaves (Secrets)
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1" 

# Inicializa o motor da IA
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.2])

with col1:
    st.subheader("Entrada de Dados")
    
    # Câmera para o pátio
    foto = st.camera_input("Tirar foto do caminhão")
    
    # Microfone para o consultor
    audio = st.audio_input("Fale a Placa e Modelo")
    
    if st.button("Salvar no Sistema"):
        if audio:
            with st.spinner("IA Processando áudio..."):
                try:
                    # 1. Transcreve o áudio para texto
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. IA formata o texto (Marca, Modelo, Placa)
                    prompt = f'Formate "{trans}" como: MARCA MODELO PLACA ANO. Ex: V.W. CONSTELLATION ABC-1234 2022. Responda APENAS a linha limpa, sem aspas.'
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip().replace('"', '').replace("'", "")
                    
                    # 3. Preparação dos dados para o Airtable (Limpando para evitar erros)
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {
                        "Authorization": f"Bearer {AIRTABLE_TOKEN}",
                        "Content-Type": "application/json"
                    }
                    
                    # Tenta extrair a placa (penúltima palavra) ou define como verificar
                    palavras = res_ia.split()
                    placa_extraida = palavras[-2] if len(palavras) >= 2 else "Verificar"

                    payload = {
                        "records": [{
                            "fields": {
                                "Data": str(datetime.now().strftime("%d/%m/%Y")),
                                "Hora": str(datetime.now().strftime("%H:%M")),
                                "Dados": str(res_ia),
                                "Placa": str(placa_extraida)
                            }
                        }]
                    }
                    
                    # 4. Envio Real
                    post_res = requests.post(url, headers=headers, json=payload)
                    
                    if post_res.status_code == 200:
                        st.success(f"✅ Registrado: {res_ia}")
                    else:
                        st.error(f"Erro no Airtable: Verifique se a coluna 'Dados' é do tipo TEXTO.")
                        st.write(post_res.text) # Mostra o erro detalhado se houver
                        
                except Exception as e:
                    st.error(f"Erro técnico na IA: {e}")

with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc"
        headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
        get_res = requests.get(url_get, headers=headers).json()
        
        if "records" in get_res:
            # Transforma os dados do Airtable em uma tabela visual
            dados_lista = [r["fields"] for r in get_res["records"]]
            df = pd.DataFrame(dados_lista)
            if not df.empty:
                # Garante que as colunas apareçam na ordem certa
                colunas_vistas = [c for c in ["Data", "Hora", "Dados", "Placa"] if c in df.columns]
                st.table(df[colunas_vistas])
    except:
        st.info("Sincronizando com a nuvem...")
