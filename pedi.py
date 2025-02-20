import streamlit as st
import json
import pandas as pd
from datetime import datetime
import os
from io import BytesIO

# ---------------------------- Funções ---------------------------- #

# Carregar dados dos motoristas
def carregar_dados_motoristas():
    with open('dadosMotoristas.json', 'r', encoding='utf-8') as file:
        return json.load(file)

# Carregar pedidos
def carregar_pedidos():
    pedidos_file = 'pedidos.json'
    if os.path.exists(pedidos_file):
        with open(pedidos_file, 'r', encoding='utf-8') as file:
            return json.load(file)
    return []

# Salvar pedido no JSON
def salvar_pedido(pedido):
    pedidos = carregar_pedidos()
    pedidos.append(pedido)
    with open('pedidos.json', 'w', encoding='utf-8') as file:
        json.dump(pedidos, file, ensure_ascii=False, indent=4)

# Limpar pedidos
def limpar_pedidos():
    with open('pedidos.json', 'w', encoding='utf-8') as file:
        json.dump([], file, ensure_ascii=False, indent=4)

# Gerar arquivo Excel em memória
def gerar_excel(df):
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    buffer.seek(0)
    return buffer

# ---------------------------- App Streamlit ---------------------------- #

# Sidebar para navegação
st.sidebar.title("Menu")
pagina = st.sidebar.selectbox("Escolha uma opção:", ["Área do Motorista", "Área Restrita (Analistas)"])

# ---------------------------- Área do Motorista ---------------------------- #
if pagina == "Área do Motorista":
    st.title("Pedido de Kit ou Marmita")

    dados_motoristas = carregar_dados_motoristas()

    matricula = st.text_input("Digite sua matrícula (sem pontos ou vírgulas):")

    if matricula:
        # Remover possíveis vírgulas e espaços, e garantir que só números sejam considerados
        matricula_formatada = ''.join(filter(str.isdigit, matricula))

        # Busca do motorista com matrícula formatada
        motorista = next((m for m in dados_motoristas if str(int(m['Matrícula'])).strip() == matricula_formatada), None)

        if motorista:
            st.write(f"**Nome:** {motorista['Nome']}")
            st.write(f"**Frota:** {motorista['Frota']}")
            st.write(f"**Equipe:** {motorista['Equipe']}")

            opcao = st.selectbox("Escolha seu pedido:", ["Kit Florestal", "Marmita"])

            if st.button("Enviar Pedido"):
                pedido = {
                    "Data": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Matrícula": int(motorista['Matrícula']),
                    "Nome": motorista['Nome'],
                    "Frota": motorista['Frota'],
                    "Equipe": motorista['Equipe'],
                    "Pedido": opcao
                }
                salvar_pedido(pedido)
                st.success("Pedido registrado com sucesso!")
        else:
            st.error("Matrícula não encontrada. Verifique se digitou corretamente (somente números).")

# ---------------------------- Área Restrita (Analistas) ---------------------------- #
elif pagina == "Área Restrita (Analistas)":
    st.title("Área Restrita - Analistas")

    senha = st.text_input("Digite a senha de acesso:", type="password")
    senha_correta = "analista123"  # Altere para a senha desejada

    if senha == senha_correta:
        pedidos = carregar_pedidos()

        if pedidos:
            df = pd.DataFrame(pedidos)
            st.subheader("Pedidos Registrados")
            st.dataframe(df)

            # Gerar arquivo Excel para download
            excel_buffer = gerar_excel(df)
            st.download_button("📥 Baixar em Excel", data=excel_buffer, file_name="pedidos.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # Limpar pedidos após salvar
            if st.button("🗑️ Limpar Pedidos (Após Salvar)"):
                limpar_pedidos()
                st.success("Pedidos limpos com sucesso!")
        else:
            st.info("Nenhum pedido registrado.")
    elif senha:  # Se digitou e errou
        st.error("Senha incorreta.")

