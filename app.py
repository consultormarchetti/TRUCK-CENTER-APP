import streamlit as st
from groq import Groq
from datetime import datetime, timedelta
import requests
import re
import unicodedata

# 1. Configuração de Página
st.set_page_config(page_title="Truck Center Pro", page_icon="🚛", layout="wide")

# --- FUNÇÕES DE APOIO (PRESERVADAS INTEGRALMENTE) ---
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

# Configurações de API (Secrets) - CORRIGIDO AIRTABLE_TOKEN
AIRTABLE_TOKEN = st.secrets["AIRTABLE_TOKEN"]
BASE_ID = st.secrets["BASE_ID"]
TABLE_NAME = "Table 1"
client = Groq(api_key=st.secrets["GROQ_API_KEY"])

st.title("🚛 Truck Center - Check-in Pro")

col1, col2 = st.columns([1, 1.3])

# --- COLUNA 1: ENTRADA DE DADOS (PÁTIO) ---
with col1:
    st.subheader("Entrada de Dados")
    
    # CONTORNO PARA CÂMERA TRASEIRA: 
    # Usar o uploader de arquivo força o celular a oferecer a 'Câmera Nativa'
    # que sempre abre na lente traseira e com melhor qualidade.
    foto = st.file_uploader("📸 CLIQUE PARA TIRAR FOTO (CÂMERA TRASEIRA)", type=["jpg", "png", "jpeg"])
    
    if foto:
        st.image(foto, caption="Foto capturada", width=200)
    
    # Sistema de áudio duplo para correções e complementos
    audio1 = st.audio_input("🎤 Áudio Principal (Veículo/Serviços)")
    audio2 = st.audio_input("🎤 Áudio Complementar (Correções/Extras)")
    
    if st.button("🚀 Finalizar Check-in Total"):
        if audio1:
            with st.spinner("Sincronizando Voz e Foto..."):
                try:
                    link_foto = upload_imagem(foto) if foto else ""
                    
                    # Transcrições Groq/Whisper
                    t1 = client.audio.transcriptions.create(file=("a1.wav", audio1.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                    t2 = ""
                    if audio2:
                        t2 = client.audio.transcriptions.create(file=("a2.wav", audio2.getvalue()), model="whisper-large-v3-turbo", response_format="text")
                    
                    # PROMPT COMPLETO (REGRAS DE OURO PRESERVADAS E REFORÇADAS)
                    prompt = f"""Áudios: '{t1}' + '{t2}'.
                    
                    Instrução: Organize tudo em LETRAS MAIÚSCULAS.
                    - REGRAS DE MARCAS: 
                      * 'VOLKSWAGEN' ou 'VOLKS' -> 'V.W.'
                      * 'MERCEDES' -> 'M.BENZ'
                      * 'VECO' ou 'IVECO' -> 'IVECO'
                      * 'FRONTI' -> 'NISSAN FRONTIER'
                      * 'ESSE DEZ' -> 'S-10'
                      * 'VECO DEILI' -> 'IVECO DAILY'
                      * 'SPRINTER' -> 'M.BENZ SPRINTER'
                    
                    - REGRA DE KM: Números de quilometragem devem ser 'KM 111.111' (com pontos).
                    - REGRA DE PLACA: Identifique e formate como ABC-1234 (hífen após 3 letras).
                    - Prioridade: O Áudio 2 corrige ou complementa o Áudio 1.
                    - Formato: MARCA MODELO PLACA (sem hífens extras entre eles).
                    - Lista de serviços detalhada abaixo com '-'.
                    - Proibido inventar serviços ou dados não ditos.
                    Responda APENAS o texto organizado em MAIÚSCULAS."""
                    
                    compl = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[{"role": "user", "content": prompt}])
                    res_ia = limpar_texto(compl.choices[0].message.content.strip())
                    
                    # Extração robusta da placa para o campo 'Placa'
                    placa_f = "VERIFICAR"
                    # Busca padrão de placa e garante o hífen no local correto
                    match = re.search(r'([A-Z]{3})(-?)([0-9][A-Z0-9][0-9]{2})', res_ia.upper())
                    if match:
                        placa_f = f"{match.group(1).upper()}-{match.group(3).upper()}"

                    agora = datetime.now() - timedelta(hours=3)
                    fields = {
                        "Data": agora.strftime("%d/%m/%Y"), 
                        "Hora": agora.strftime("%H:%M"), 
                        "Dados": res_ia, 
                        "Placa": placa_f
                    }
                    if link_foto: fields["LinkFoto"] = link_foto

                    # Envio ao Airtable (Correção do Token confirmada)
                    requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}", 
                                  headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}, 
                                  json={"records": [{"fields": fields}]})
                    
                    st.success(f"✅ REGISTRADO: {placa_f}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

# --- COLUNA 2: PAINEL DA RECEPÇÃO (PC) ---
with col2:
    st.subheader("Painel da Recepção (PC)")
    try:
        url_get = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}?sort[0][field]=Data&sort[0][direction]=desc&sort[1][field]=Hora&sort[1][direction]=desc"
        res = requests.get(url_get, headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}).json()
        
        if "records" in res:
            for r in res["records"]:
                f = r["fields"]
                rid = r["id"]
                with st.expander(f"🚛 {f.get('Placa', 'S/P')} | {f.get('Data')} {f.get('Hora')}"):
                    c_txt, c_img = st.columns([2, 1])
                    with c_txt:
                        # CAMPOS EDITÁVEIS
                        nova_placa = st.text_input("PLACA:", f.get("Placa", ""), key=f"p_{rid}").upper()
                        novo_relatorio = st.text_area("RELATÓRIO:", f.get("Dados", ""), key=f"d_{rid}").upper()
                        
                        if st.button("💾 SALVAR ALTERAÇÃO", key=f"b_{rid}"):
                            requests.patch(f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}/{rid}",
                                           headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"},
                                           json={"fields": {"Placa": nova_placa, "Dados": novo_relatorio}})
                            st.rerun()
                    with c_img:
                        if f.get("LinkFoto"):
                            st.image(f.get("LinkFoto"), caption="MINIATURA", use_container_width=True)
                            st.link_button("🔍 VER ORIGINAL", f.get("LinkFoto"))
    except:
        st.write("SINCRONIZANDO DADOS...")
