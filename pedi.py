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
ARQUIVO_PEDIDOS = "pedidos.json"  # Arquivo de pedidos
ARQUIVO_MOTORISTAS = "dadosMotoristas.json"  # Arquivo de motoristas

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

def carregar_json_github(arquivo):
    repo = conectar_github()
    contents = repo.get_contents(arquivo)
    return json.loads(contents.decoded_content.decode()), contents

def salvar_json_github(arquivo, dados, contents):
    repo = conectar_github()
    repo.update_file(
        contents.path,
        f"Atualização do arquivo {arquivo} via Streamlit",
        json.dumps(dados, ensure_ascii=False, indent=4),
        contents.sha
    )

def adicionar_motorista_github(novo_motorista):
    motoristas, contents = carregar_json_github(ARQUIVO_MOTORISTAS)
    motoristas.append(novo_motorista)
    salvar_json_github(ARQUIVO_MOTORISTAS, motoristas, contents)

def adicionar_pedido_github(pedido):
    pedidos, contents = carregar_json_github(ARQUIVO_PEDIDOS)
    pedidos.append(pedido)
    salvar_json_github(ARQUIVO_PEDIDOS, pedidos, contents)

def limpar_pedidos_github():
    salvar_json_github(ARQUIVO_PEDIDOS, [], carregar_json_github(ARQUIVO_PEDIDOS)[1])

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

    motoristas, motoristas_contents = carregar_json_github(ARQUIVO_MOTORISTAS)

    matricula = st.text_input("Digite sua matrícula (sem pontos ou vírgulas):")
    turno_selecionado = st.selectbox("Selecione o turno:", turnos_list)
    horario_selecionado = st.selectbox("Selecione o horário (original ou invertido):", horarios_completos)

    if matricula:
        matricula_formatada = ''.join(filter(str.isdigit, matricula))

        motorista = next(
            (m for m in motoristas if converter_matricula(m['Matrícula']) == int(matricula_formatada)), None
        )

        if motorista:
            st.write(f"**Nome:** {motorista['Nome']}")
            st.write(f"**Frota:** {motorista.get('Frota', 'N/A')}")
            st.write(f"**Equipe:** {motorista.get('Equipe', 'N/A')}")

            opcao = st.selectbox("Escolha seu pedido:", ["Kit Florestal", "Marmita"])

            if st.button("Enviar Pedido"):
                pedido = {
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Matrícula": str(int(converter_matricula(motorista['Matrícula']))),
                    "Nome": motorista['Nome'],
                    "Frota": motorista.get('Frota'),
                    "Equipe": motorista.get('Equipe'),
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
            st.warning("🚨 Matrícula não encontrada! Por favor, faça seu cadastro.")
            with st.form("cadastro_motorista"):
                nome = st.text_input("Nome completo:")
                frota = st.text_input("Frota (opcional):", placeholder="Ex: Frota Leste")
                equipe = st.text_input("Equipe (opcional):", placeholder="Ex: BTF5")
                submit_cadastro = st.form_submit_button("Cadastrar")

                if submit_cadastro:
                    if nome.strip():
                        novo_motorista = {
                            "Nome": nome.strip().upper(),
                            "Frota": frota.strip() if frota else None,
                            "Equipe": equipe.strip() if equipe else None,
                            "Matrícula": float(matricula_formatada)
                        }

                        try:
                            adicionar_motorista_github(novo_motorista)
                            st.success("✅ Cadastro realizado com sucesso!")
                        except Exception as e:
                            st.error(f"❌ Erro ao cadastrar motorista no GitHub: {e}")
                    else:
                        st.error("❌ O nome é obrigatório para o cadastro!")

# ---------------------------- Área Restrita (Analistas) ---------------------------- #
elif pagina == "Área Restrita (Analistas)":
    st.title("Área Restrita - Analistas")

    senha = st.text_input("Digite a senha de acesso:", type="password")
    senha_correta = "analista123"

    if senha == senha_correta:
        try:
            pedidos, _ = carregar_json_github(ARQUIVO_PEDIDOS)

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
