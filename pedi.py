import json
import pandas as pd
from datetime import datetime
from io import BytesIO
from github import Github
import os
from dotenv import load_dotenv
import streamlit as st

# ---------------------------- Carregar variáveis do .env ---------------------------- #
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not GITHUB_TOKEN:
    raise ValueError("❌ Token do GitHub não encontrado. Verifique o arquivo .env.")

# ---------------------------- Configuração GitHub ---------------------------- #
GITHUB_USER = "Scsant"           # Nome de usuário do GitHub
REPO_NAME = "pedidosMotoristas"  # Nome do repositório
ARQUIVO_GITHUB = "pedidos.json"  # Caminho do arquivo no repositório

# ---------------------------- Dados fornecidos ---------------------------- #
turno = 'A, B, C'
horario = "06:00 AS 18:00, 08:00 AS 20:00, 10:00 AS 22:00, 12:00 AS 00:00, 14:00 AS 2:00"

turnos_list = [t.strip() for t in turno.split(',')]
horarios_list = [h.strip() for h in horario.split(',')]

# Função para inverter os horários
def inverter_horario(h):
    inicio, _, fim = h.partition(' AS ')
    return f"{fim} AS {inicio}"

horarios_invertidos = [inverter_horario(h) for h in horarios_list]
horarios_completos = horarios_list + horarios_invertidos

# ---------------------------- Funções GitHub ---------------------------- #
def conectar_github():
    g = Github(GITHUB_TOKEN)
    repo = g.get_user(GITHUB_USER).get_repo(REPO_NAME)
    return repo

def carregar_pedidos_github():
    repo = conectar_github()
    contents = repo.get_contents(ARQUIVO_GITHUB)
    return json.loads(contents.decoded_content.decode())

def salvar_pedidos_github(pedidos):
    repo = conectar_github()
    contents = repo.get_contents(ARQUIVO_GITHUB)
    repo.update_file(
        contents.path,
        "Atualização de pedidos via Streamlit",
        json.dumps(pedidos, ensure_ascii=False, indent=4),
        contents.sha
    )

def adicionar_pedido_github(pedido):
    pedidos = carregar_pedidos_github()
    pedidos.append(pedido)
    salvar_pedidos_github(pedidos)

def limpar_pedidos_github():
    salvar_pedidos_github([])

def gerar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

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
    st.title("Pedido de Kit ou Marmita")

    with open('dadosMotoristas.json', 'r', encoding='utf-8') as file:
        dados_motoristas = json.load(file)

    matricula = st.text_input("Digite sua matrícula (sem pontos ou vírgulas):")
    turno_selecionado = st.selectbox("Selecione o turno:", turnos_list)
    horario_selecionado = st.selectbox("Selecione o horário (original ou invertido):", horarios_completos)

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
                    "Turno": turno_selecionado,
                    "Horário": horario_selecionado,
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
    senha_correta = "analista123"

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
