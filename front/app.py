"""Streamlit Chatbot App using Custom ADK API"""

import os
import time
import requests
import uuid # Necessário para gerar Session ID
import json # Necessário para tratamento de JSON

import streamlit as st
# REMOVIDO: imports do google.genai não são mais necessários

st.set_page_config(page_title="Chat with DCC Helper", page_icon="♊")

# Título ajustado para refletir a alteração solicitada
st.title("Chat with DCC Helper :D")

st.markdown("Welcome to this simple web application to chat with your custom ADK Agent.")

if st.button('Novo Chat'):
    # Limpa o histórico de mensagens exibido no Streamlit
    st.session_state.messages = [] 
    
    # 1. Gera um novo Session ID único
    new_session_id = "s-" + str(uuid.uuid4())
    st.session_state.session_id = new_session_id
    
    # 2. Prepara a chamada para criar a nova sessão no ADK
    AGENT_API_URL = os.environ.get("AGENT_API_ENDPOINT")
    SESSION_ID = st.session_state.session_id
    APP_NAME = "dcc-helper" 
    USER_ID = "streamlit-user" # ID fixo para todos os usuários do Streamlit
    
    session_api_url = f"{AGENT_API_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    session_payload = {}
    
    
    try:
        # ⚠️ st.info(f"Tentando criar sessão {SESSION_ID} em: {session_api_url}")
        
        session_response = requests.post(session_api_url, json=session_payload, timeout=30)
        
        # O código 409 (Conflict) é aceitável, pois significa que a sessão já foi criada.
        if session_response.status_code == 409:
            st.warning("Sessão já existe no servidor. Reutilizando ID.")
        elif session_response.status_code not in [200, 201]:
            # Levanta erro para outros códigos (e.g., 404 se APP_NAME estiver errado)
            session_response.raise_for_status() 
        else:
            st.success("Sessão criada com sucesso.")
        
        # ... (Lógica de tratamento de sucesso/erro) ...
        
    except requests.exceptions.RequestException as e:
        st.error(f"ERRO DE REDE: Não foi possível conectar à API ADK. Erro: {e}")
        
    # 3. Força a re-execução do script (limpa a tela)
    st.rerun()
    
    
# Importa a fonte do Google Fonts e a aplica ao corpo do aplicativo
# st.markdown(
#     """
#     <style>
#     @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
    
#     html, body, [class*="st-emotion-"] {
#         font-family: 'Roboto', sans-serif;
#     }
#     /* O seletor 'html, body, [class*="st-emotion-"]' garante que a fonte se aplique a todos os elementos Streamlit */
#     </style>
#     """,
#     unsafe_allow_html=True,
# )

st.markdown(
    """
    <style>
    /* Aplica a fonte a todos os elementos body e seus descendentes */
    body, 
    /* Aplica aos elementos gerados pelo Streamlit */
    [class*="st-emotion-"] * { 
        font-family: 'Comic Sans MS', Comic Sans, cursive !important;
    }
    /* Aplica ao título principal */
    h1 {
        font-family: 'Comic Sans MS', Comic Sans, cursive !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------
# 1. Configurar Variáveis de Ambiente e Endpoint ADK
# ----------------------------------------------------------------------

# URL da API do Agente ADK configurada no deploy do Cloud Run
AGENT_API_URL = os.environ.get("AGENT_API_ENDPOINT")

# Nome do seu agente coordenador/raiz no ADK (Ex: coordination_agent)
APP_NAME = "dcc-helper" 
USER_ID = "streamlit-user" # ID fixo para todos os usuários do Streamlit

# Verifica se a URL da API foi configurada
if not AGENT_API_URL:
    st.error("Erro: A variável de ambiente AGENT_API_ENDPOINT não foi definida. Verifique a Célula 10 do notebook.")
    st.stop()


# ----------------------------------------------------------------------
# 2. Gerenciamento de Sessão ADK (Criação de Sessão)
# ----------------------------------------------------------------------

if "session_id" not in st.session_state:
    # 1. Gerar um Session ID único para o usuário atual
    st.session_state["session_id"] = "s-" + str(uuid.uuid4())
    SESSION_ID = st.session_state.session_id
    
    # 2. Tentar criar a sessão no servidor ADK (Endpoint /sessions)
    session_api_url = f"{AGENT_API_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    session_payload = {}
    
    try:
        st.info(f"Tentando criar sessão no agente ADK: {SESSION_ID}...")
        
        # Faz a chamada POST para criar a sessão
        session_response = requests.post(session_api_url, json=session_payload, timeout=30)
        
        # O código 409 (Conflict) é aceitável, pois significa que a sessão já foi criada.
        if session_response.status_code == 409:
            st.warning("Sessão já existe no servidor. Reutilizando ID.")
        elif session_response.status_code not in [200, 201]:
            # Levanta erro para outros códigos (e.g., 404 se APP_NAME estiver errado)
            session_response.raise_for_status() 
        else:
            st.success("Sessão criada com sucesso.")
            
    except requests.exceptions.RequestException as e:
        st.error(f"Falha CRÍTICA ao criar sessão no agente ADK. Verifique a URL e as permissões. Erro: {e}")
        st.stop()


# Inicializar histórico de chat do Streamlit
if "messages" not in st.session_state:
    st.session_state.messages = []

# Exibir mensagens do histórico na tela
for message in st.session_state.messages:
    with st.chat_message(name=message["role"], avatar=message["avatar"]):
        st.markdown(message["content"])


# ----------------------------------------------------------------------
# 3. Refatorar Geração de Resposta (Chamada HTTP POST para /run)
# ----------------------------------------------------------------------

# Função para simular o stream de resposta (para o efeito visual de digitação)
def stream(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.02)


def generate_response(prompt):
    SESSION_ID = st.session_state.session_id
    
    # Definir o payload da requisição para o endpoint /run
    payload = {
        "appName": APP_NAME,
        "userId": USER_ID,
        "sessionId": SESSION_ID,
        "newMessage": {
            "role": "user",
            "parts": [{"text": prompt}]
        }
    }
    
    api_endpoint = AGENT_API_URL + "/run" # Endpoint de execução de query
    
    try:
        # Fazer a Requisição POST
        response = requests.post(api_endpoint, json=payload, timeout=120)
        
        # Levanta uma exceção para códigos de erro HTTP (4xx, 5xx)
        response.raise_for_status() 

        # Linha 113 corrigida: Processamento do JSON
        response_data = response.json()
        
        # O endpoint /run retorna uma lista de eventos ADK.
        if response_data and isinstance(response_data, list):
            # Procura pelo último evento que contenha texto de resposta do modelo
            for event in reversed(response_data):
                if event.get('content') and event['content']['parts'] and event['content']['parts'][0].get('text'):
                    return event['content']['parts'][0]['text']
        
        return "Erro: Formato de resposta do agente não encontrado no JSON retornado."

    except requests.exceptions.HTTPError as e:
        # Captura erros de API (como "Session not found" se a criação falhar)
        details = response.text if response.text else "Sem detalhes."
        return f"Erro de API HTTP: {e} | Detalhes: {details}"
    except Exception as e:
        return f"Erro de conexão: Não foi possível processar a query: {e}"


# ----------------------------------------------------------------------
# 4. Iteração do Chat
# ----------------------------------------------------------------------

# Reage à entrada do usuário
if prompt := st.chat_input("Write a prompt"):
    # 1. Escrever mensagem do usuário
    with st.chat_message(name="user", avatar=None):
        st.write(prompt)
    # 2. Adicionar mensagem do usuário ao histórico do Streamlit
    st.session_state.messages.append(
        {"role": "user", "content": prompt, "avatar": None}
    )

    # 3. Chamar a API ADK e escrever a resposta
    with st.chat_message(name="assistant", avatar="assets/gemini-icon.png"):
        # A generate_response() faz a chamada HTTP
        response_text = generate_response(prompt)
        
        # Usamos st.write_stream para simular o efeito de digitação
        st.write_stream(stream(response_text))
        
    # 4. Adicionar resposta do agente ao histórico do Streamlit
    st.session_state.messages.append(
        {
            "role": "model",
            "content": response_text,
            "avatar": "assets/gemini-icon.png",
        }
    )