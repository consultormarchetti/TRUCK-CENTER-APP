import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
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

# Configurações de API
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("Entrada de Dados")
    foto = st.camera_input("Tirar Foto do Veículo")
    
    # Sistema de áudio duplo
    audio1 = st.audio_input("🎤 Áudio Principal (Veículo/Serviços)")
    audio2 = st.audio_input("🎤 Áudio Complementar (Correções/Extras)")
    
    if st.button("🚀 Finalizar Check-in Total"):
        if audio1:
            with st.spinner("Processando e Cruzando Áudios..."):
                try:
                    link_foto = upload_imagem(foto) if foto else ""
                    
                    # Transcreve áudio 1
                    t1 = client.audio.transcriptions.create(file=("a1.wav", audio1.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                    
                    # Transcreve áudio 2 (se houver)
                    t2 = ""
                    if audio2:
                        t2 = client.audio.transcriptions.create(file=("a2.wav", audio2.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                    
                    # Prompt que prioriza o segundo áudio em caso de conflito
                    prompt = f"""Áudio 1: '{t1}'. 
                    Áudio 2 (Complemento/Correção): '{t2}'.
                    
                    Instrução: Organize tudo em LETRAS MAIÚSCULAS.
                    - Se o Áudio 2 corrigir informações do Áudio 1, use a informação do Áudio 2.
                    - Formato: MARCA MODELO - PLACA (ABC-1234).
                    - Lista de serviços detalhada abaixo.
                    - Proibido inventar dados."""
                    
                    compl = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                    res_ia = limpar_texto(compl.choices[0].message.content.strip())
                    
                    # Extração da placa
                    placa_match = re.search(r'[A-Z]{3}-?\d[A-Z0-9]\d{2}', res_ia)
                    placa_f = placa_match.group(0) if placa_match else "VERIFICAR"
                    if placa_f != "VERIFICAR" and '-' not in placa_f: placa_f = f"{placa_f[:3]}-{placa_f[3:]}"

                    agora = datetime.now() - timedelta(hours=3)
                    fields = {"Data": agora.strftime("%d/%m/%Y"), "Hora": agora.strftime("%H:%M"), "Dados": res_ia, "Placa": placa_f}
                    if link_foto: fields["LinkFoto"] = link_foto

                    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}", 
                                  headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}, 
                                  json={"records": [{"fields": fields}]})
                    
                    st.success(f"✅ REGISTRADO COM SUCESSO!")
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
                rid = r["id"]
                with st.expander(f"🚛 {f.get('Placa', 'S/P')} | {f.get('Data')} {f.get('Hora')}"):
                    c_txt, c_img = st.columns([2, 1])
                    with c_txt:
                        # CAMPOS EDITÁVEIS À MÃO
                        nova_placa = st.text_input("PLACA:", f.get("Placa", ""), key=f"p_{rid}").upper()
                        novo_relatorio = st.text_area("RELATÓRIO DE SERVIÇOS:", f.get("Dados", ""), key=f"d_{rid}").upper()
                        
                        if st.button("💾 SALVAR ALTERAÇÃO MANUAL", key=f"b_{rid}"):
                            update_fields = {"Placa": nova_placa, "Dados": novo_relatorio}
                            patch_resp = requests.patch(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}/{rid}",
                                           headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"},
                                           json={"fields": update_fields})
                            if patch_resp.status_code == 200:
                                st.success("ALTERADO!")
                                st.rerun()
                    with c_img:
                        if f.get("LinkFoto"):
                            st.image(f.get("LinkFoto"), use_container_width=True)
                            st.link_button("🔍 VER ORIGINAL", f.get("LinkFoto"))
    except:
        st.write("SINCRONIZANDO...")
