import streamlit as st
import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from github import Github
import os
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Pega o token da variável de ambiente
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ Token do GitHub não encontrado. Verifique o arquivo .env.")
# ---------------------------- Configuração GitHub ---------------------------- #
  # Insira seu token pessoal aqui
GITHUB_USER = "Scsant"           # Nome de usuário do GitHub
REPO_NAME = "pedidosMotoristas"  # Nome do repositório
ARQUIVO_GITHUB = "pedidos.json"  # Caminho do arquivo no repositório

# ---------------------------- Funções GitHub ---------------------------- #

# Conectar ao repositório
def conectar_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_user(GITHUB_USER).get_repo(REPO_NAME)
    return repo

# Carregar pedidos direto do GitHub
def carregar_pedidos_github():
    repo = conectar_github()
    contents = repo.get_contents(ARQUIVO_GITHUB)
    return json.loads(contents.decoded_content.decode())

# Salvar pedidos direto no GitHub
def salvar_pedidos_github(pedidos):
    repo = conectar_github()
    contents = repo.get_contents(ARQUIVO_GITHUB)
    repo.update_file(
        contents.path,
        "Atualização de pedidos via Streamlit",
        json.dumps(pedidos, ensure_ascii=False, indent=4),
        contents.sha
    )

# Adicionar novo pedido e salvar no GitHub
def adicionar_pedido_github(pedido):
    pedidos = carregar_pedidos_github()
    pedidos.append(pedido)
    salvar_pedidos_github(pedidos)

# Limpar pedidos no GitHub
def limpar_pedidos_github():
    salvar_pedidos_github([])

# Gerar arquivo Excel
def gerar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

# ---------------------------- Função segura para matrícula ---------------------------- #
def converter_matricula(valor):
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return None

# ---------------------------- Streamlit ---------------------------- #

st.sidebar.title("Menu")
pagina = st.sidebar.selectbox("Escolha uma opção:", ["Área do Motorista", "Área Restrita (Analistas)"])

# ---------------------------- Área do Motorista ---------------------------- #
if pagina == "Área do Motorista":
    st.title("Pedido de Kit Florestal ou Marmita")

    # Carregar dados dos motoristas localmente
    with open('dadosMotoristas.json', 'r', encoding='utf-8') as file:
        dados_motoristas = json.load(file)

    matricula = st.text_input("Digite sua matrícula (sem pontos ou vírgulas):")

    if matricula:
        matricula_formatada = ''.join(filter(str.isdigit, matricula))

        motorista = next(
            (m for m in dados_motoristas if converter_matricula(m['Matrícula']) == int(matricula_formatada)), None
        )

        if motorista:
            st.write(f"**Nome:** {motorista['Nome']}")
            st.write(f"**Frota:** {motorista['Frota']}")
            st.write(f"**Equipe:** {motorista['Equipe']}")

            opcao = st.selectbox("Escolha seu pedido:", ["Kit Florestal", "Marmita"])

            if st.button("Enviar Pedido"):
                pedido = {
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Matrícula": converter_matricula(motorista['Matrícula']),
                    "Nome": motorista['Nome'],
                    "Frota": motorista['Frota'],
                    "Equipe": motorista['Equipe'],
                    "Pedido": opcao
                }

                try:
                    adicionar_pedido_github(pedido)
                    st.success("✅ Pedido registrado com sucesso no GitHub!")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar pedido no GitHub: {e}")
        else:
            st.error("Matrícula não encontrada ou inválida. Verifique se digitou corretamente.")

# ---------------------------- Área Restrita (Analistas) ---------------------------- #
elif pagina == "Área Restrita (Analistas)":
    st.title("Área Restrita - Analistas")

    senha = st.text_input("Digite a senha de acesso:", type="password")
    senha_correta = "analista123"  # Altere conforme necessário

    if senha == senha_correta:
        try:
            pedidos = carregar_pedidos_github()

            if pedidos:
                df = pd.DataFrame(pedidos)
                st.subheader("Pedidos Registrados")
                st.dataframe(df)

                excel_buffer = gerar_excel(df)
                st.download_button("📥 Baixar em Excel", data=excel_buffer, file_name="pedidos.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                if st.button("🗑️ Limpar Pedidos (Após Salvar)"):
                    limpar_pedidos_github()
                    st.success("✅ Pedidos limpos no GitHub com sucesso!")
            else:
                st.info("Nenhum pedido registrado no GitHub.")
        except Exception as e:
            st.error(f"❌ Erro ao acessar o GitHub: {e}")
    elif senha:
        st.error("🔑 Senha incorreta.")
