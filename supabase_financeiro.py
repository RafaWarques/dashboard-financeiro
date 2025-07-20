# ======================================
# 🚀 IMPORTS E CONFIGURAÇÃO
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
import warnings
import requests  # ✅ NOVO
from bs4 import BeautifulSoup  # ✅ NOVO
import unicodedata
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ======================================
# 🔗 CONEXÃO COM SUPABASE
url = "https://zhuqsxfmzubsxgbtfemq.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodXFzeGZtenVic3hnYnRmZW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5NTc4ODEsImV4cCI6MjA2NTUzMzg4MX0.6iUd7jGQRxN1ZLAvQv57b3QJpLkd4Mdzs43h9uDSfwc"
supabase: Client = create_client(url, key)


# ======================================
# 📥 CARREGAMENTO DOS DADOS
def carregar_dados():
    if 'dados' not in st.session_state:
        res = supabase.table("despesas").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df['data_despesa'] = pd.to_datetime(df['data_despesa'])
            df['Semana'] = df['semana']
            df['Mês'] = df['data_despesa'].dt.strftime('%B')
            df['Ano'] = df['data_despesa'].dt.year
            df['Dia'] = df['data_despesa'].dt.day
            df['Parcelas'] = df['parcelas'].fillna(1).astype(int)
        st.session_state['dados'] = df
    return st.session_state['dados']


df = carregar_dados()


# ======================================
# 🔧 FUNÇÕES AUXILIARES
def calcular_mes_fatura(data):
    if data.day >= 26:
        return (data + pd.DateOffset(months=1)).strftime('%Y-%m')
    return data.strftime('%Y-%m')

# ======================================
# ➕ FORMULÁRIO PARA NOVA DESPESA
with st.expander("➕ Adicionar Nova Despesa"):
    with st.form("form_despesa", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        data = col1.date_input("Data da Despesa", datetime.today())
        categoria = col2.selectbox(
            "Categoria", df['categoria'].dropna().unique() if not df.empty else 
            ["Alimentação", "Saúde", "Transporte", "Lazer", "Farmácia", "Roupas", "Higiene", "Entretenimento"]
        )
        descricao = col3.text_input("Descrição")

        col4, col5, col6 = st.columns(3)
        valor = col4.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
        forma_pagamento = col5.selectbox("Forma de Pagamento", ["VR", "Cartão de Crédito"])  # ✅ Corrigido
        parcelas = col6.number_input("Parcelas", min_value=1, step=1, value=1)

        col7, col8 = st.columns(2)
        responsavel = col7.selectbox(
            "Responsável", df['responsavel'].dropna().unique() if not df.empty else ["Rafael", "Nathalia", "Iris"]
        )
        semana = col8.number_input("Semana do Ano", min_value=1, max_value=53, value=data.isocalendar()[1])

        submit = st.form_submit_button("Adicionar Despesa")

        if submit:
            if descricao.strip() == "":
                st.error("❌ Descrição não pode estar vazia.")
            else:
                nova_despesa = {
                    'data_despesa': data.strftime('%Y-%m-%d'),
                    'categoria': categoria,
                    'descricao': descricao,
                    'valor': valor,
                    'forma_pagamento': forma_pagamento,
                    'parcelas': parcelas,
                    'responsavel': responsavel,
                    'semana': semana
                }
                try:
                    supabase.table("despesas").insert(nova_despesa).execute()
                    st.success("💾 Despesa adicionada com sucesso!")
                    st.session_state.pop('dados', None)  # 🔥 Limpa cache local
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao adicionar despesa: {e}")


# ======================================
# 🧠 DATAFRAME PARCELADO
if not df.empty:
    df_parcelado = df.loc[df.index.repeat(df['Parcelas'])].reset_index(drop=True)
    df_parcelado['Numero Parcela'] = df_parcelado.groupby(
        ['data_despesa', 'valor', 'responsavel']
    ).cumcount()

    df_parcelado['Data Parcela'] = df_parcelado.apply(
        lambda row: row['data_despesa'] + pd.DateOffset(months=row['Numero Parcela']),
        axis=1
    )

    df_parcelado['Ano-Mês Fatura'] = df_parcelado['Data Parcela'].apply(calcular_mes_fatura)
    df_parcelado['Valor Parcela'] = df_parcelado['valor'] / df_parcelado['Parcelas']
else:
    df_parcelado = pd.DataFrame()


# ======================================
# 🔥 FILTRO GLOBAL 🔥
st.sidebar.header("🔍 Filtro Global")
forma_pagamento_filtro = st.sidebar.multiselect(
    "Forma de Pagamento",
    df['forma_pagamento'].dropna().unique(),
    default=df['forma_pagamento'].dropna().unique()
)

df_filtrado = df[df['forma_pagamento'].isin(forma_pagamento_filtro)]

# ======================================
# 📄 PÁGINAS
pagina = st.sidebar.radio("📄 Navegação", [
    "📊 Visão Geral", "👥 Comparativo por Responsável", "💡 Visão Inteligente por Mês", 
    "💳 Renda Comprometida", "🗑️ Deletar Registros", "🛒 Simulação de Compra"
])


# ======================================
# 📊 VISÃO GERAL
if pagina == "📊 Visão Geral":
    st.title("📊 Visão Geral")

    if df_filtrado.empty:
        st.warning("Nenhuma despesa encontrada com os filtros selecionados.")
    else:
        total = df_filtrado['valor'].sum()
        media = df_filtrado['valor'].mean()
        qtd = len(df_filtrado)

        with st.container():
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Gasto", f"R$ {total:,.2f}")
            col2.metric("Média por Despesa", f"R$ {media:,.2f}")
            col3.metric("Nº de Lançamentos", qtd)

        st.subheader("Total por Categoria")
        cat_df = df_filtrado.groupby("categoria")["valor"].sum().reset_index().sort_values("valor", ascending=False)

        for i in range(0, len(cat_df), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(cat_df):
                    row = cat_df.iloc[i + j]
                    cols[j].metric(label=row["categoria"], value=f"R$ {row['valor']:,.2f}")


# ======================================
# 👥 COMPARATIVO POR RESPONSÁVEL
elif pagina == "👥 Comparativo por Responsável":
    st.title("👥 Comparativo por Responsável")

    if df_parcelado.empty:
        st.warning("Nenhuma despesa cadastrada.")
    else:
        meses_fatura = df_parcelado['Ano-Mês Fatura'].drop_duplicates().sort_values(ascending=False)
        mes_ref = st.selectbox("Selecione o Mês da Fatura", meses_fatura)

        df_comp = df_parcelado[
            (df_parcelado['Ano-Mês Fatura'] == mes_ref) &
            (df_parcelado['responsavel'].isin(responsavel_filtro)) &
            (df_parcelado['categoria'].isin(categoria_filtro)) &
            (df_parcelado['forma_pagamento'].isin(forma_pagamento_filtro)) &  # ← isso basta
            (df_parcelado['Data Parcela'] >= pd.to_datetime(data_ini)) &
            (df_parcelado['Data Parcela'] <= pd.to_datetime(data_fim))
        ]


        if df_comp.empty:
            st.warning("Nenhuma despesa encontrada para os filtros selecionados.")
        else:
            df_group = df_comp.groupby(['categoria', 'responsavel'])['Valor Parcela'].sum().reset_index()
            df_pivot = df_group.pivot(index='categoria', columns='responsavel', values='Valor Parcela').fillna(0)

            st.dataframe(df_pivot.style.format("R$ {:,.2f}"), use_container_width=True)

            fig = px.bar(
                df_group, x='categoria', y='Valor Parcela', color='responsavel',
                barmode='group', title="Gastos por Categoria e Responsável"
            )
            st.plotly_chart(fig, use_container_width=True)


# ======================================
# 💡 VISÃO INTELIGENTE POR MÊS
elif pagina == "💡 Visão Inteligente por Mês":
    st.title("💡 Visão Inteligente por Mês")

    if df_parcelado.empty:
        st.warning("Nenhuma despesa cadastrada.")
    else:
        meses_fatura = df_parcelado['Ano-Mês Fatura'].drop_duplicates().sort_values(ascending=False)
        mes_ref = st.selectbox("Selecione o Mês da Fatura", meses_fatura)

        resp_viz = st.multiselect(
            "Filtrar por Responsável", df_parcelado['responsavel'].dropna().unique(),
            default=df_parcelado['responsavel'].dropna().unique()
        )

        # 🔧 Filtro completo com forma de pagamento
        df_final = df_parcelado[
            (df_parcelado['responsavel'].isin(resp_viz)) &
            (df_parcelado['forma_pagamento'].isin(forma_pagamento_filtro)) &
            (df_parcelado['Data Parcela'] >= pd.to_datetime(data_ini)) &
            (df_parcelado['Data Parcela'] <= pd.to_datetime(data_fim))
        ]
        df_mes = df_final[df_final['Ano-Mês Fatura'] == mes_ref]

        if df_mes.empty:
            st.warning("Nenhum lançamento encontrado para o mês selecionado.")
        else:
            total_mes = df_mes['Valor Parcela'].sum()

            col1, col2, col3 = st.columns(3)
            col1.metric("Total no Mês", f"R$ {total_mes:,.2f}")
            col2.metric("Qtd. Lançamentos", len(df_mes))
            col3.metric("Parcelamentos Ativos", df_mes['Numero Parcela'].nunique())

            fig_cat = px.bar(
                df_mes.groupby('categoria')['Valor Parcela'].sum().reset_index(),
                x='categoria', y='Valor Parcela', color='categoria', title='Total por Categoria'
            )
            st.plotly_chart(fig_cat, use_container_width=True)

            df_mes['Data Parcela'] = pd.to_datetime(df_mes['Data Parcela']).dt.strftime('%d/%m/%Y')
            df_mes['Valor Parcela'] = df_mes['Valor Parcela'].map('R$ {:,.2f}'.format)
            st.dataframe(df_mes.sort_values("Data Parcela"), use_container_width=True)
            
# ======================================
# 💳 RENDA COMPROMETIDA
elif pagina == "💳 Renda Comprometida":
    st.title("💳 Renda Comprometida no Cartão")

    salarios = {'Rafael': 5600, 'Nathalia': 4500}

    if df_parcelado.empty:
        st.warning("Nenhuma despesa cadastrada.")
    else:
        meses_fatura = df_parcelado['Ano-Mês Fatura'].drop_duplicates().sort_values(ascending=False)
        mes_ref = st.selectbox("Selecione o Mês da Fatura", meses_fatura)

        df_mes = df_parcelado[
            (df_parcelado['Ano-Mês Fatura'] == mes_ref) &
            (df_parcelado['forma_pagamento'].isin(forma_pagamento_filtro)) &
            (df_parcelado['Data Parcela'] >= pd.to_datetime(data_ini)) &
            (df_parcelado['Data Parcela'] <= pd.to_datetime(data_fim))
        ]

        col1, col2 = st.columns(2)

        for pessoa, col in zip(salarios.keys(), [col1, col2]):
            col.subheader(f"👤 {pessoa}")
            col.markdown(f"**💰 Renda Total:** R$ {salarios[pessoa]:,.2f}")

            df_pessoa = df_mes[df_mes['responsavel'] == pessoa]
            total_gasto = df_pessoa['Valor Parcela'].sum()

            col.markdown(
                f"<span style='color:red; font-size:18px;'>🔻 Total Comprometido: R$ {total_gasto:,.2f}</span>",
                unsafe_allow_html=True
            )

            if df_pessoa.empty:
                col.info("Sem despesas no cartão para este período.")
            else:
                resumo = df_pessoa.groupby('categoria')['Valor Parcela'].sum().reset_index()
                resumo['% da Renda'] = resumo['Valor Parcela'] / salarios[pessoa]
                resumo['Valor Parcela'] = resumo['Valor Parcela'].apply(lambda x: f"R$ {x:,.2f}")
                resumo['% da Renda'] = resumo['% da Renda'].apply(lambda x: f"{x:.1%}")

                col.dataframe(resumo.set_index('categoria'))



# ======================================
# 🗑️ DELETAR REGISTROS
elif pagina == "🗑️ Deletar Registros":
    st.title("🗑️ Deletar Registros de Despesas")

    if df.empty:
        st.warning("Nenhuma despesa cadastrada.")
    else:
        st.info("Selecione os registros que deseja deletar. Os registros mais recentes aparecem primeiro.")

        df_deletar = df.sort_values(by="data_despesa", ascending=False).reset_index(drop=True)
        df_deletar['Data'] = df_deletar['data_despesa'].dt.strftime('%d/%m/%Y')

        df_mostrar = df_deletar[['id', 'Data', 'categoria', 'descricao', 'valor', 'forma_pagamento', 'parcelas', 'responsavel']]

        df_mostrar = df_mostrar.rename(columns={
            'id': 'ID',
            'Data': 'Data',
            'categoria': 'Categoria',
            'descricao': 'Descrição',
            'valor': 'Valor (R$)',
            'forma_pagamento': 'Forma',
            'parcelas': 'Parcelas',
            'responsavel': 'Responsável'
        })

        st.dataframe(df_mostrar, use_container_width=True)

        ids_para_deletar = st.multiselect(
            "Selecione os IDs que deseja deletar:",
            df_mostrar['ID'].tolist()
        )

        if ids_para_deletar:
            st.warning(f"🚨 Você está prestes a deletar {len(ids_para_deletar)} registro(s). Esta ação não pode ser desfeita.")

            if st.button("🚨 Confirmar Deleção"):
                try:
                    for id_deletar in ids_para_deletar:
                        supabase.table('despesas').delete().eq('id', id_deletar).execute()

                    st.success(f"✅ {len(ids_para_deletar)} registro(s) deletado(s) com sucesso!")
                    st.session_state.pop('dados', None)  # 🔥 Limpa cache local
                    st.rerun()

                except Exception as e:
                    st.error(f"❌ Erro ao deletar: {e}")
        else:
            st.info("Selecione um ou mais IDs na lista acima para habilitar a exclusão.")

# ======================================
# 🛒 SIMULAÇÃO DE COMPRA
elif pagina == "🛒 Simulação de Compra":
    st.title("🛒 Simulação de Compra por Produto")

    # Tabela fixa de preços
    dados_precos = [
        {"Produto": "Banana", "Unidade": "kg", "Carrefour": 5.89, "Extra": 4.79, "Pão de Açúcar": 7.98},
        {"Produto": "Iogurte Grego", "Unidade": "unidade", "Carrefour": 2.99, "Extra": 4.09, "Pão de Açúcar": 3.69},
        {"Produto": "Leite em Pó Itambé", "Unidade": "unidade", "Carrefour": 15.99, "Extra": 17.99, "Pão de Açúcar": 18.29},
        {"Produto": "Arroz Camil 1kg", "Unidade": "unidade", "Carrefour": 4.59, "Extra": 5.99, "Pão de Açúcar": 6.49},
        {"Produto": "Papel Higiênico 12 rolos", "Unidade": "unidade", "Carrefour": 30.59, "Extra": 29.99, "Pão de Açúcar": 24.99},
        {"Produto": "Azeite", "Unidade": "unidade", "Carrefour": 34.79, "Extra": 36.99, "Pão de Açúcar": 34.99},
    ]
    df_precos = pd.DataFrame(dados_precos)

    # Produto selecionado
    produto_selecionado = st.selectbox("Selecione o produto:", df_precos["Produto"].unique())

    # Info do produto
    produto_info = df_precos[df_precos["Produto"] == produto_selecionado].iloc[0]
    unidade = produto_info["Unidade"]
    qtde = st.number_input(f"Quantidade desejada ({unidade}):", 
                           min_value=0.0, step=0.5 if unidade == "kg" else 1.0, 
                           value=1.0, format="%.2f")

    # Mostrar os preços nos três mercados
    st.subheader(f"💵 Preços para **{produto_selecionado}**")

    col1, col2, col3 = st.columns(3)
    for col, mercado in zip([col1, col2, col3], ["Carrefour", "Extra", "Pão de Açúcar"]):
        preco_unit = produto_info[mercado]
        total = preco_unit * qtde
        col.markdown(f"### 🛍️ {mercado}")
        col.metric("Preço unitário", f"R$ {preco_unit:.2f}")
        col.metric("Total estimado", f"R$ {total:.2f}")

    # Mostrar tabela (opcional)
    with st.expander("📋 Ver tabela completa de preços"):
        st.dataframe(df_precos.set_index("Produto"))






