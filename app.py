import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import pandas as pd
import requests

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
    audio = st.audio_input("Fale o Veículo e os Serviços")
    
    if st.button("Finalizar Check-in"):
        if audio:
            with st.spinner("IA Processando Veículo e Serviços..."):
                try:
                    # 1. Transcrição do áudio
                    trans = client.audio.transcriptions.create(
                        file=("audio.wav", audio.getvalue()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                    
                    # 2. IA com Padronização de Veículo + Serviços (Conforme imagem_6e6b5f.png)
                    prompt = f'''Analise: "{trans}"
                    Formate exatamente assim:
                    Linha 1: [TIPO] MARCA MODELO PLACA ANO (Regras: Volkswagen=V.W. | Mercedes=M.BENZ | Hífen na placa)
                    Linhas seguintes: Liste cada serviço ou defeito mencionado começando com " - "
                    
                    Exemplo:
                    M.BENZ ATEGO 1719 OLJ-9269
                    - TROCAR OLEO E FILTROS
                    - VERIFICAR FREIO
                    
                    Responda APENAS o texto formatado.'''
                    
                    compl = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    res_ia = compl.choices[0].message.content.strip().replace('"', '')
                    
                    # 3. Horário de Brasília (GMT-3)
                    hora_brasilia = datetime.now() - timedelta(hours=3)
                    placa_f = next((p for p in res_ia.split('\n')[0].split() if '-' in p), "Verificar")

                    # 4. Envio para o Airtable (Sem foto primeiro para pegar o ID)
                    url = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
                    headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}
                    
                    payload = {
                        "records": [{"fields": {
                            "Data": hora_brasilia.strftime("%d/%m/%Y"),
                            "Hora": hora_brasilia.strftime("%H:%M"),
                            "Dados": res_ia,
                            "Placa": placa_f
                        }}]
                    }
                    
                    # Se houver foto, este código precisaria de um serviço de hospedagem temporária (Cloudinary/ImgBB)
                    # Para simplificar agora, focaremos na formatação dos dados.
                    post_res = requests.post(url, headers=headers, json=payload)
                    
                    if post_res.status_code == 200:
                        st.success(f"✅ Check-in realizado com sucesso!")
                        st.text_area("Dados formatados:", res_ia, height=150)
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
            dados_display = []
            for r in res["records"]:
                f = r["fields"]
                # Pega o link da foto se existir
                foto_url = f.get("Foto")[0].get("url") if "Foto" in f else None
                
                dados_display.append({
                    "Data": f.get("Data"),
                    "Hora": f.get("Hora"),
                    "Veículo/Serviços": f.get("Dados"),
                    "Placa": f.get("Placa"),
                    "Ver Foto": f"🔗 [Ver Foto]({foto_url})" if foto_url else "---"
                })
            
            # Usando st.write para renderizar o Markdown do link da foto
            df_final = pd.DataFrame(dados_display)
            st.dataframe(df_final, use_container_width=True)
            
    except:
        st.info("Sincronizando registros...")
