import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Dashboard Financeiro", layout="wide")

# ==============================
# 📥 Carregar dados
@st.cache_data
def carregar_dados():
    caminho_arquivo = "C:/Users/RMA704/OneDrive - Maersk Group/2025/Py/Finance/Controle Financeiro.xlsx"
    try:
        df = pd.read_excel(caminho_arquivo)
    except PermissionError:
        st.error(f"❌ O arquivo está aberto ou em uso: {caminho_arquivo}. Feche o arquivo e recarregue.")
        st.stop()

    df['Data da Despesa'] = pd.to_datetime(df['Data da Despesa'])
    df['Semana'] = df['Data da Despesa'].dt.isocalendar().week
    df['Mês'] = df['Data da Despesa'].dt.strftime('%B')
    df['Ano'] = df['Data da Despesa'].dt.year
    df['Parcelas'] = df['Parcelas'].fillna(1).astype(int)
    df['Dia'] = df['Data da Despesa'].dt.day
    return df


df = carregar_dados()

# ==============================
# 🔧 Função para calcular mês da fatura (26 ao dia 25)
def calcular_mes_fatura(data):
    if data.day >= 26:
        mes_fatura = (data + pd.DateOffset(months=1)).strftime('%Y-%m')
    else:
        mes_fatura = data.strftime('%Y-%m')
    return mes_fatura


# ===================================
# 🚀 Formulário para adicionar despesa
with st.expander("➕ Adicionar Nova Despesa"):
    with st.form("form_despesa", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        data = col1.date_input("Data da Despesa", datetime.today())
        categoria = col2.selectbox("Categoria", df['Categoria'].dropna().unique())
        descricao = col3.text_input("Descrição")

        col4, col5, col6 = st.columns(3)
        valor = col4.number_input("Valor (R$)", min_value=0.0, step=0.01, format="%.2f")
        forma_pagamento = col5.selectbox(
            "Forma de Pagamento", 
            ["VR", "Cartão de Crédito"]
        )
        parcelas = col6.number_input("Parcelas", min_value=1, step=1, value=1)

        col7, col8 = st.columns(2)
        responsavel = col7.selectbox("Responsável", df['Responsável'].dropna().unique())
        semana = col8.number_input(
            "Semana do Ano", min_value=1, max_value=53, value=data.isocalendar()[1]
        )

        submit = st.form_submit_button("Adicionar Despesa")

        if submit:
            nova_despesa = pd.DataFrame({
                'Data da Despesa': [pd.to_datetime(data)],
                'Categoria': [categoria],
                'Descrição': [descricao],
                'Valor (R$)': [valor],
                'Forma de Pagamento': [forma_pagamento],
                'Parcelas': [parcelas],
                'Responsável': [responsavel],
                'Semana do Ano': [semana]
            })

            # 🔗 Adiciona no dataframe atual
            df = pd.concat([df, nova_despesa], ignore_index=True)

            # 💾 Salvar no Excel
            caminho_arquivo = "C:/Users/RMA704/OneDrive - Maersk Group/2025/Py/Finance/Controle Financeiro.xlsx"
            try:
                df.to_excel(caminho_arquivo, index=False)
                st.success("💾 Despesa adicionada e salva no Excel com sucesso!")
            except PermissionError:
                st.error("❌ Não foi possível salvar. O arquivo está aberto.")


# ==============================
# 🧠 Gerar dataframe parcelado
df_parcelado = df.copy()
df_parcelado = df_parcelado.loc[df_parcelado.index.repeat(df_parcelado['Parcelas'])].reset_index(drop=True)
df_parcelado['Numero Parcela'] = df_parcelado.groupby(
    ['Data da Despesa', 'Valor (R$)', 'Responsável']
).cumcount()

df_parcelado['Data Parcela'] = df_parcelado.apply(
    lambda row: row['Data da Despesa'] + pd.DateOffset(months=row['Numero Parcela']),
    axis=1
)

df_parcelado['Ano-Mês Fatura'] = df_parcelado['Data Parcela'].apply(calcular_mes_fatura)
df_parcelado['Valor Parcela'] = df_parcelado['Valor (R$)'] / df_parcelado['Parcelas']


# ==============================
# 📄 Páginas do Dashboard
pagina = st.sidebar.radio("Selecionar Página:", [
    "📊 Visão Geral",
    "👥 Comparativo por Responsável",
    "💡 Visão Inteligente por Mês",
    "💳 Renda Comprometida"
])


# ========================================================
# 📊 VISÃO GERAL
if pagina == "📊 Visão Geral":
    st.title("📊 Visão Geral")
    st.sidebar.header("Filtros")
    responsavel = st.sidebar.multiselect("Responsável", df['Responsável'].dropna().unique(), default=df['Responsável'].dropna().unique())
    categorias = st.sidebar.multiselect("Categoria", df['Categoria'].dropna().unique(), default=df['Categoria'].dropna().unique())
    data_ini = st.sidebar.date_input("Data Inicial", df['Data da Despesa'].min())
    data_fim = st.sidebar.date_input("Data Final", df['Data da Despesa'].max())

    filtro = (
        (df['Responsável'].isin(responsavel)) &
        (df['Categoria'].isin(categorias)) &
        (df['Data da Despesa'] >= pd.to_datetime(data_ini)) &
        (df['Data da Despesa'] <= pd.to_datetime(data_fim))
    )
    df_filtrado = df[filtro]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Gasto (R$)", f"R$ {df_filtrado['Valor (R$)'].sum():,.2f}")
    col2.metric("Média por Despesa (R$)", f"R$ {df_filtrado['Valor (R$)'].mean():,.2f}")
    col3.metric("Nº de Lançamentos", len(df_filtrado))

    st.subheader("Total por Categoria")
    cat_df = df_filtrado.groupby("Categoria")["Valor (R$)"].sum().reset_index().sort_values("Valor (R$)", ascending=False)

    for i in range(0, len(cat_df), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(cat_df):
                row = cat_df.iloc[i + j]
                cols[j].metric(label=row["Categoria"], value=f"R$ {row['Valor (R$)']:,.2f}")


# ========================================================
# 👥 COMPARATIVO POR RESPONSÁVEL
elif pagina == "👥 Comparativo por Responsável":
    st.title("👥 Comparativo por Responsável")

    df_comparativo = df.copy()
    df_comparativo['Ano-Mês'] = df_comparativo['Data da Despesa'].apply(calcular_mes_fatura)

    df_comparativo_group = df_comparativo.groupby(['Categoria', 'Responsável'])['Valor (R$)'].sum().reset_index()
    df_pivot = df_comparativo_group.pivot(index='Categoria', columns='Responsável', values='Valor (R$)').fillna(0)

    st.dataframe(df_pivot.style.format("R$ {:,.2f}"), use_container_width=True)

    st.subheader("Comparação Visual")
    fig = px.bar(df_comparativo_group, x='Categoria', y='Valor (R$)', color='Responsável', barmode='group',
                 title="Gastos por Categoria e Responsável")
    st.plotly_chart(fig, use_container_width=True)


# ========================================================
# 💡 VISÃO INTELIGENTE POR MÊS
elif pagina == "💡 Visão Inteligente por Mês":
    st.title("💡 Visão Inteligente por Mês")

    meses_fatura = df_parcelado['Ano-Mês Fatura'].drop_duplicates().sort_values(ascending=False)
    mes_referencia = st.selectbox("Selecione o Mês da Fatura", meses_fatura)

    responsavel_viz = st.multiselect("Filtrar por Responsável (Visão Inteligente)", 
                                     df_parcelado['Responsável'].dropna().unique(), 
                                     default=df_parcelado['Responsável'].dropna().unique())

    df_final = df_parcelado[df_parcelado['Responsável'].isin(responsavel_viz)]
    df_mes = df_final[df_final['Ano-Mês Fatura'] == mes_referencia]

    if df_mes.empty:
        st.warning("Nenhum lançamento encontrado para o mês selecionado.")
    else:
        total_mes = df_mes['Valor Parcela'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Gasto no Mês", f"R$ {total_mes:,.2f}")

        meta = 2000
        df_cartao = df_mes[df_mes['Forma de Pagamento'].str.lower().str.contains("cartão")]
        gastos_cartao = df_cartao.groupby("Responsável")["Valor Parcela"].sum()

        col2.metric("Meta Rafael (Cartão)", f"R$ {meta:,.2f}", delta=f"Usado: R$ {gastos_cartao.get('Rafael', 0):,.2f}")
        col3.metric("Meta Nathalia (Cartão)", f"R$ {meta:,.2f}", delta=f"Usado: R$ {gastos_cartao.get('Nathalia', 0):,.2f}")

        st.metric("Nº de Lançamentos", len(df_mes))

        fig_cat = px.bar(df_mes.groupby('Categoria')['Valor Parcela'].sum().reset_index(),
                         x='Categoria', y='Valor Parcela', color='Categoria', title='Total por Categoria')
        st.plotly_chart(fig_cat, use_container_width=True)

        df_mes['Data Parcela'] = pd.to_datetime(df_mes['Data Parcela']).dt.strftime('%d/%m/%Y')
        df_mes['Valor Parcela'] = df_mes['Valor Parcela'].map('R$ {:,.2f}'.format)
        st.dataframe(df_mes.sort_values("Data Parcela"), use_container_width=True)


# ========================================================
# 💳 RENDA COMPROMETIDA
elif pagina == "💳 Renda Comprometida":
    st.title("💳 Renda Comprometida no Cartão")

    salarios = {
        'Rafael': 5600,
        'Nathalia': 4500
    }

    meses_fatura = df_parcelado['Ano-Mês Fatura'].drop_duplicates().sort_values(ascending=False)
    mes_referencia = st.selectbox("Selecione o Mês da Fatura", meses_fatura)

    df_mes = df_parcelado[
        (df_parcelado['Ano-Mês Fatura'] == mes_referencia) &
        (df_parcelado['Forma de Pagamento'].str.lower().str.contains('cartão'))
    ]

    col1, col2 = st.columns(2)

    for pessoa, col in zip(salarios.keys(), [col1, col2]):
        col.subheader(f"👤 {pessoa}")
        col.markdown(f"**💰 Renda Total:** R$ {salarios[pessoa]:,.2f}")

        df_pessoa = df_mes[df_mes['Responsável'] == pessoa]

        total_gasto = df_pessoa['Valor Parcela'].sum()

        col.markdown(
            f"<span style='color:red; font-size:18px;'>🔻 Total Comprometido: R$ {total_gasto:,.2f}</span>",
            unsafe_allow_html=True
        )

        if df_pessoa.empty:
            col.info("Sem despesas no cartão para este período.")
        else:
            resumo = df_pessoa.groupby('Categoria')['Valor Parcela'].sum().reset_index()
            resumo['% da Renda'] = resumo['Valor Parcela'] / salarios[pessoa]

            resumo['Valor Parcela'] = resumo['Valor Parcela'].apply(lambda x: f"R$ {x:,.2f}")
            resumo['% da Renda'] = resumo['% da Renda'].apply(lambda x: f"{x:.1%}")

            col.dataframe(resumo.set_index('Categoria'))
