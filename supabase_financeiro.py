# ======================================
# 🚀 IMPORTS E CONFIGURAÇÃO
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
from supabase import create_client, Client
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ======================================
# 🔗 CONEXÃO COM SUPABASE
url = "https://zhuqsxfmzubsxgbtfemq.supabase.co"
key = "SUA_ANON_KEY_AQUI"
supabase: Client = create_client(url, key)

# ======================================
# 📌 SCHEMA ESPERADO (para não quebrar com base vazia)
COLUNAS_ESPERADAS = [
    "id", "data_despesa", "categoria", "descricao", "valor",
    "forma_pagamento", "parcelas", "responsavel", "semana"
]

RESPONSAVEIS_FIXOS = ["Rafael", "Nathalia"]
FORMAS_FIXAS = ["Cartão de Crédito", "VR"]  # VR = Ticket/VR

# ======================================
# 📥 CARREGAMENTO DOS DADOS
def carregar_dados():
    if "dados" not in st.session_state:
        res = supabase.table("despesas").select("*").execute()
        df = pd.DataFrame(res.data)

        # ✅ garante colunas mesmo sem linhas
        if df.empty:
            df = pd.DataFrame(columns=COLUNAS_ESPERADAS)
        else:
            # ✅ garante que as colunas existam (caso venha faltando algo)
            for c in COLUNAS_ESPERADAS:
                if c not in df.columns:
                    df[c] = None

        # ✅ tipos e colunas auxiliares (só se tiver data preenchida)
        if "data_despesa" in df.columns and not df.empty:
            df["data_despesa"] = pd.to_datetime(df["data_despesa"], errors="coerce")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
            df["parcelas"] = pd.to_numeric(df["parcelas"], errors="coerce").fillna(1).astype(int)

            # Períodos
            iso = df["data_despesa"].dt.isocalendar()
            df["Ano"] = df["data_despesa"].dt.year
            df["MesRef"] = df["data_despesa"].dt.to_period("M").astype(str)   # YYYY-MM
            df["SemanaRef"] = (df["data_despesa"].dt.year.astype(str) + "-W" +
                               iso.week.astype(int).astype(str).str.zfill(2))

        st.session_state["dados"] = df

    return st.session_state["dados"]


df = carregar_dados()

# ======================================
# 🔧 FUNÇÕES AUXILIARES
def calcular_mes_fatura(data_parcela: pd.Timestamp) -> str:
    # Regra: se dia >= 26, vira fatura do mês seguinte
    if pd.isna(data_parcela):
        return None
    if data_parcela.day >= 26:
        return (data_parcela + pd.DateOffset(months=1)).strftime("%Y-%m")
    return data_parcela.strftime("%Y-%m")

def gerar_df_parcelado(df_base: pd.DataFrame) -> pd.DataFrame:
    if df_base.empty:
        return pd.DataFrame(columns=list(df_base.columns) + ["Numero Parcela", "Data Parcela", "AnoMesFatura", "Valor Parcela"])

    # replica linhas conforme nº de parcelas
    dfp = df_base.loc[df_base.index.repeat(df_base["parcelas"])].reset_index(drop=True)

    # número da parcela dentro do grupo (mesma compra)
    dfp["Numero Parcela"] = dfp.groupby(["data_despesa", "valor", "responsavel", "descricao", "categoria"]).cumcount()

    # data de cada parcela (mes a mes)
    dfp["Data Parcela"] = dfp.apply(
        lambda r: r["data_despesa"] + pd.DateOffset(months=int(r["Numero Parcela"])) if pd.notna(r["data_despesa"]) else pd.NaT,
        axis=1
    )

    dfp["AnoMesFatura"] = dfp["Data Parcela"].apply(calcular_mes_fatura)
    dfp["Valor Parcela"] = dfp["valor"] / dfp["parcelas"]

    # colunas de período da parcela (para gráficos)
    dfp["ParcelaMesRef"] = pd.to_datetime(dfp["Data Parcela"], errors="coerce").dt.to_period("M").astype(str)

    return dfp

df_parcelado = gerar_df_parcelado(df)

# ======================================
# ➕ FORMULÁRIO PARA NOVA DESPESA
with st.expander("➕ Adicionar Nova Despesa"):
    with st.form("form_despesa", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        data_in = c1.date_input("Data da Despesa", datetime.today())
        categoria_in = c2.text_input("Categoria", value="Alimentação")
        descricao_in = c3.text_input("Descrição")

        c4, c5, c6 = st.columns(3)
        valor_in = c4.number_input("Valor (R$)", min_value=0.01, step=0.01, format="%.2f")
        forma_in = c5.selectbox("Forma de Pagamento", FORMAS_FIXAS)
        parcelas_in = c6.number_input("Parcelas", min_value=1, step=1, value=1)

        c7, c8 = st.columns(2)
        resp_in = c7.selectbox("Responsável", RESPONSAVEIS_FIXOS)
        semana_in = c8.number_input("Semana do Ano", min_value=1, max_value=53, value=data_in.isocalendar()[1])

        submit = st.form_submit_button("Adicionar Despesa")

        if submit:
            if not descricao_in.strip():
                st.error("❌ Descrição não pode estar vazia.")
            else:
                nova = {
                    "data_despesa": data_in.strftime("%Y-%m-%d"),
                    "categoria": categoria_in.strip(),
                    "descricao": descricao_in.strip(),
                    "valor": float(valor_in),
                    "forma_pagamento": forma_in,
                    "parcelas": int(parcelas_in),
                    "responsavel": resp_in,
                    "semana": int(semana_in),
                }
                try:
                    supabase.table("despesas").insert(nova).execute()
                    st.success("💾 Despesa adicionada com sucesso!")
                    st.session_state.pop("dados", None)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao adicionar despesa: {e}")

# ======================================
# 🔥 FILTROS GLOBAIS (Responsável, Forma, Data: Semana/Mês/Ano)
st.sidebar.header("🔍 Filtros Globais")

f_resp = st.sidebar.multiselect(
    "Responsável",
    RESPONSAVEIS_FIXOS,
    default=RESPONSAVEIS_FIXOS
)

f_forma = st.sidebar.multiselect(
    "Forma de Pagamento",
    FORMAS_FIXAS,
    default=FORMAS_FIXAS
)

gran = st.sidebar.radio("Período", ["Semana", "Mês", "Ano"], horizontal=True)

# opções do seletor do período (com fallback)
if df.empty or "data_despesa" not in df.columns:
    op_periodo = []
else:
    if gran == "Semana":
        op_periodo = sorted(df["SemanaRef"].dropna().unique(), reverse=True)
    elif gran == "Mês":
        op_periodo = sorted(df["MesRef"].dropna().unique(), reverse=True)
    else:
        op_periodo = sorted(df["Ano"].dropna().unique(), reverse=True)

periodo_sel = st.sidebar.selectbox("Selecione o período", op_periodo) if op_periodo else None

# aplica filtros
df_f = df.copy()
if not df_f.empty:
    df_f = df_f[df_f["responsavel"].isin(f_resp)]
    df_f = df_f[df_f["forma_pagamento"].isin(f_forma)]

    if periodo_sel is not None:
        if gran == "Semana":
            df_f = df_f[df_f["SemanaRef"] == periodo_sel]
        elif gran == "Mês":
            df_f = df_f[df_f["MesRef"] == periodo_sel]
        else:
            df_f = df_f[df_f["Ano"] == periodo_sel]

# para parcelado (filtros compatíveis)
dfp_f = df_parcelado.copy()
if not dfp_f.empty:
    dfp_f = dfp_f[dfp_f["responsavel"].isin(f_resp)]
    dfp_f = dfp_f[dfp_f["forma_pagamento"].isin(f_forma)]

# ======================================
# 📄 PÁGINAS
pagina = st.sidebar.radio("📄 Páginas", ["1) Gasto Total", "2) Parcelamentos", "3) Previsão"])

# ======================================
# 1) GASTO TOTAL
if pagina == "1) Gasto Total":
    st.title("1) Gasto Total")

    if df_f.empty:
        st.warning("Sem dados para os filtros selecionados.")
    else:
        # a) gráfico em barras com gasto total
        # (por responsável no período filtrado; simples e legível)
        total_resp = df_f.groupby("responsavel", as_index=False)["valor"].sum()
        fig = px.bar(total_resp, x="responsavel", y="valor", title="Gasto total (período filtrado)")
        st.plotly_chart(fig, use_container_width=True)

        # b) tabela por categoria
        st.subheader("Gasto por categoria")
        tab_cat = (df_f.groupby("categoria", as_index=False)["valor"]
                   .sum()
                   .sort_values("valor", ascending=False))
        tab_cat["valor"] = tab_cat["valor"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(tab_cat, use_container_width=True)

# ======================================
# 2) PARCELAMENTOS
elif pagina == "2) Parcelamentos":
    st.title("2) Parcelamentos")

    if df_parcelado.empty:
        st.warning("Sem dados de parcelamentos (ou base vazia).")
    else:
        # aqui consideramos parcelas como a distribuição mensal (df_parcelado)
        # a) card com total acumulado de todas as parcelas (dentro dos filtros globais)
        total_parcelas = dfp_f["Valor Parcela"].sum() if not dfp_f.empty else 0.0
        st.metric("Total acumulado de parcelas (filtros atuais)", f"R$ {total_parcelas:,.2f}")

        if dfp_f.empty:
            st.warning("Sem parcelas para os filtros selecionados.")
        else:
            # b) barras por mês até a última parcela
            por_mes = (dfp_f.groupby("ParcelaMesRef", as_index=False)["Valor Parcela"]
                       .sum()
                       .sort_values("ParcelaMesRef"))
            fig2 = px.bar(por_mes, x="ParcelaMesRef", y="Valor Parcela",
                          title="Total a pagar por mês (parcelas) até a última parcela")
            st.plotly_chart(fig2, use_container_width=True)

            # c) tabela por categoria
            st.subheader("Total de parcelas por categoria (filtros atuais)")
            tab_cat_p = (dfp_f.groupby("categoria", as_index=False)["Valor Parcela"]
                         .sum()
                         .sort_values("Valor Parcela", ascending=False))
            tab_cat_p["Valor Parcela"] = tab_cat_p["Valor Parcela"].map(lambda x: f"R$ {x:,.2f}")
            st.dataframe(tab_cat_p, use_container_width=True)

# ======================================
# 3) PREVISÃO
else:
    st.title("3) Previsão (heurística: média dos últimos 3 meses)")

    # salários (ajuste se quiser)
    salarios = {"Rafael": 5600, "Nathalia": 4500}

    if df.empty or "MesRef" not in df.columns:
        st.warning("Sem histórico suficiente para prever.")
    else:
        # últimos 3 meses disponíveis no histórico (base completa, mas respeitando responsável/forma global)
        base_prev = df.copy()
        base_prev = base_prev[base_prev["responsavel"].isin(f_resp)]
        base_prev = base_prev[base_prev["forma_pagamento"].isin(f_forma)]

        meses = sorted(base_prev["MesRef"].dropna().unique())
        if len(meses) < 1:
            st.warning("Sem dados para os filtros selecionados.")
        else:
            ultimos = meses[-3:]  # pega até 3 meses
            hist3 = base_prev[base_prev["MesRef"].isin(ultimos)]

            # a) previsão por categoria = média dos últimos 3 meses
            prev_cat = (hist3.groupby(["MesRef", "categoria"], as_index=False)["valor"].sum())
            media_cat = (prev_cat.groupby("categoria", as_index=False)["valor"].mean()
                         .sort_values("valor", ascending=False))
            media_cat = media_cat.rename(columns={"valor": "Previsão (média 3M)"})

            # define próximo mês (YYYY-MM) a partir do último mês do histórico
            ultimo_mes = pd.Period(meses[-1], freq="M")
            prox_mes = (ultimo_mes + 1).strftime("%Y-%m")

            st.subheader(f"Previsão de gastos por categoria para {prox_mes}")
            tabela_prev = media_cat.copy()
            tabela_prev["Previsão (média 3M)"] = tabela_prev["Previsão (média 3M)"].map(lambda x: f"R$ {x:,.2f}")
            st.dataframe(tabela_prev, use_container_width=True)

            # gráfico da previsão
            figp = px.bar(media_cat, x="categoria", y="Previsão (média 3M)", title=f"Previsão por categoria ({prox_mes})")
            st.plotly_chart(figp, use_container_width=True)

            # b) cálculo dinheiro no próximo mês: salário - gastos previstos - parcelas do próximo mês
            salario_total = sum(salarios.get(r, 0) for r in f_resp)

            # gastos previstos total (média 3M somada)
            gastos_prev_total = media_cat["Previsão (média 3M)"].sum() if not media_cat.empty else 0.0

            # parcelas do próximo mês (somente as parcelas agendadas nesse mês)
            parcelas_prox = 0.0
            if not df_parcelado.empty:
                dfp_prev = df_parcelado.copy()
                dfp_prev = dfp_prev[dfp_prev["responsavel"].isin(f_resp)]
                dfp_prev = dfp_prev[dfp_prev["forma_pagamento"].isin(f_forma)]
                parcelas_prox = dfp_prev[dfp_prev["ParcelaMesRef"] == prox_mes]["Valor Parcela"].sum()

            saldo_prev = salario_total - gastos_prev_total - parcelas_prox

            st.subheader("Estimativa de saldo no próximo mês")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Salário considerado", f"R$ {salario_total:,.2f}")
            c2.metric("Gastos previstos (média 3M)", f"R$ {gastos_prev_total:,.2f}")
            c3.metric("Parcelas do mês", f"R$ {parcelas_prox:,.2f}")
            c4.metric("Saldo estimado", f"R$ {saldo_prev:,.2f}")
