# ======================================
# 🚀 IMPORTS E CONFIGURAÇÃO
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client
import warnings
warnings.filterwarnings("ignore")

st.set_page_config(page_title="Controle Financeiro", layout="wide")

# ======================================
# 🔐 SUPABASE (Secrets no Streamlit Cloud)
def get_supabase_credentials():
    # 1) Streamlit Cloud Secrets
    if "https://zhuqsxfmzubsxgbtfemq.supabase.co" in st.secrets and "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodXFzeGZtenVic3hnYnRmZW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5NTc4ODEsImV4cCI6MjA2NTUzMzg4MX0.6iUd7jGQRxN1ZLAvQv57b3QJpLkd4Mdzs43h9uDSfwc" in st.secrets:
        return st.secrets["https://zhuqsxfmzubsxgbtfemq.supabase.co"], st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodXFzeGZtenVic3hnYnRmZW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5NTc4ODEsImV4cCI6MjA2NTUzMzg4MX0.6iUd7jGQRxN1ZLAvQv57b3QJpLkd4Mdzs43h9uDSfwc"]

    # 2) Fallback local via env vars
    url = os.getenv("https://zhuqsxfmzubsxgbtfemq.supabase.co")
    key = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodXFzeGZtenVic3hnYnRmZW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5NTc4ODEsImV4cCI6MjA2NTUzMzg4MX0.6iUd7jGQRxN1ZLAvQv57b3QJpLkd4Mdzs43h9uDSfwc")
    if url and key:
        return url, key

    raise RuntimeError(
        "Credenciais do Supabase não encontradas. Configure SUPABASE_URL e SUPABASE_ANON_KEY em Streamlit Secrets "
        "ou como variáveis de ambiente."
    )

SUPABASE_URL, SUPABASE_ANON_KEY = get_supabase_credentials()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ======================================
# 📌 SCHEMA ESPERADO (evita KeyError quando base estiver vazia)
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
        try:
            res = supabase.table("despesas").select("*").execute()
        except Exception as e:
            st.error("Falha ao consultar a tabela 'despesas' no Supabase.")
            st.exception(e)
            st.stop()

        df = pd.DataFrame(res.data)

        # ✅ garante colunas mesmo sem linhas
        if df.empty:
            df = pd.DataFrame(columns=COLUNAS_ESPERADAS)
        else:
            for c in COLUNAS_ESPERADAS:
                if c not in df.columns:
                    df[c] = None

        # ✅ tipos e colunas auxiliares
        if not df.empty:
            df["data_despesa"] = pd.to_datetime(df["data_despesa"], errors="coerce")
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce").fillna(0.0)
            df["parcelas"] = pd.to_numeric(df["parcelas"], errors="coerce").fillna(1).astype(int)

            iso = df["data_despesa"].dt.isocalendar()
            df["Ano"] = df["data_despesa"].dt.year
            df["MesRef"] = df["data_despesa"].dt.to_period("M").astype(str)  # YYYY-MM
            df["SemanaRef"] = df["data_despesa"].dt.year.astype(str) + "-W" + iso.week.astype(int).astype(str).str.zfill(2)

        st.session_state["dados"] = df

    return st.session_state["dados"]

df = carregar_dados()

# ======================================
# 🔧 FUNÇÕES AUXILIARES
def calcular_mes_fatura(data_parcela: pd.Timestamp) -> str | None:
    if pd.isna(data_parcela):
        return None
    if data_parcela.day >= 26:
        return (data_parcela + pd.DateOffset(months=1)).strftime("%Y-%m")
    return data_parcela.strftime("%Y-%m")

def gerar_df_parcelado(df_base: pd.DataFrame) -> pd.DataFrame:
    if df_base.empty:
        return pd.DataFrame(columns=list(df_base.columns) + ["Numero Parcela", "Data Parcela", "AnoMesFatura", "Valor Parcela", "ParcelaMesRef"])

    dfp = df_base.loc[df_base.index.repeat(df_base["parcelas"])].reset_index(drop=True)

    dfp["Numero Parcela"] = dfp.groupby(
        ["data_despesa", "valor", "responsavel", "descricao", "categoria"]
    ).cumcount()

    dfp["Data Parcela"] = dfp.apply(
        lambda r: r["data_despesa"] + pd.DateOffset(months=int(r["Numero Parcela"])) if pd.notna(r["data_despesa"]) else pd.NaT,
        axis=1
    )

    dfp["AnoMesFatura"] = dfp["Data Parcela"].apply(calcular_mes_fatura)
    dfp["Valor Parcela"] = dfp["valor"] / dfp["parcelas"]
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
        semana_in = c8.number_input("Semana do Ano", min_value=1, max_value=53, value=int(data_in.isocalendar()[1]))

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
                    st.error("❌ Erro ao adicionar despesa.")
                    st.exception(e)

# ======================================
# 🔥 FILTROS GLOBAIS
st.sidebar.header("🔍 Filtros Globais")

f_resp = st.sidebar.multiselect("Responsável", RESPONSAVEIS_FIXOS, default=RESPONSAVEIS_FIXOS)
f_forma = st.sidebar.multiselect("Forma de Pagamento", FORMAS_FIXAS, default=FORMAS_FIXAS)

gran = st.sidebar.radio("Data (granularidade)", ["Semana", "Mês", "Ano"], horizontal=True)

if df.empty:
    op_periodo = []
else:
    if gran == "Semana":
        op_periodo = sorted(df["SemanaRef"].dropna().unique(), reverse=True)
    elif gran == "Mês":
        op_periodo = sorted(df["MesRef"].dropna().unique(), reverse=True)
    else:
        op_periodo = sorted(df["Ano"].dropna().unique(), reverse=True)

periodo_sel = st.sidebar.selectbox("Período", op_periodo) if op_periodo else None

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

dfp_f = df_parcelado.copy()
if not dfp_f.empty:
    dfp_f = dfp_f[dfp_f["responsavel"].isin(f_resp)]
    dfp_f = dfp_f[dfp_f["forma_pagamento"].isin(f_forma)]

# ======================================
# 📄 PÁGINAS
pagina = st.sidebar.radio("📄 Páginas", ["1. Gasto Total", "2. Parcelamentos", "3. Previsão"])

# ======================================
# 1) GASTO TOTAL
if pagina == "1. Gasto Total":
    st.title("Gasto Total")

    if df_f.empty:
        st.warning("Sem dados para os filtros selecionados.")
    else:
        total_resp = df_f.groupby("responsavel", as_index=False)["valor"].sum()
        fig = px.bar(total_resp, x="responsavel", y="valor", title="Gasto total (período filtrado)")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Gasto por categoria")
        tab_cat = df_f.groupby("categoria", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
        tab_cat["valor"] = tab_cat["valor"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(tab_cat, use_container_width=True)

# ======================================
# 2) PARCELAMENTOS
elif pagina == "2. Parcelamentos":
    st.title("Parcelamentos")

    if dfp_f.empty:
        st.warning("Sem parcelas para os filtros selecionados (ou base vazia).")
    else:
        total_parcelas = dfp_f["Valor Parcela"].sum()
        st.metric("Total acumulado de todas as parcelas (filtros atuais)", f"R$ {total_parcelas:,.2f}")

        por_mes = dfp_f.groupby("ParcelaMesRef", as_index=False)["Valor Parcela"].sum().sort_values("ParcelaMesRef")
        fig2 = px.bar(por_mes, x="ParcelaMesRef", y="Valor Parcela",
                      title="Total a pagar por mês (parcelas) até a última parcela")
        st.plotly_chart(fig2, use_container_width=True)

        st.subheader("Total de parcelas por categoria")
        tab_cat_p = dfp_f.groupby("categoria", as_index=False)["Valor Parcela"].sum().sort_values("Valor Parcela", ascending=False)
        tab_cat_p["Valor Parcela"] = tab_cat_p["Valor Parcela"].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(tab_cat_p, use_container_width=True)

# ======================================
# 3) PREVISÃO
else:
    st.title("Previsão (média dos últimos 3 meses)")

    salarios = {"Rafael": 5600, "Nathalia": 4500}

    base_prev = df.copy()
    if base_prev.empty:
        st.warning("Sem histórico para prever.")
        st.stop()

    base_prev = base_prev[base_prev["responsavel"].isin(f_resp)]
    base_prev = base_prev[base_prev["forma_pagamento"].isin(f_forma)]

    meses = sorted(base_prev["MesRef"].dropna().unique())
    if not meses:
        st.warning("Sem histórico suficiente para prever com os filtros atuais.")
        st.stop()

    ultimos = meses[-3:]
    hist3 = base_prev[base_prev["MesRef"].isin(ultimos)]

    prev_cat = hist3.groupby(["MesRef", "categoria"], as_index=False)["valor"].sum()
    media_cat = prev_cat.groupby("categoria", as_index=False)["valor"].mean().sort_values("valor", ascending=False)
    media_cat = media_cat.rename(columns={"valor": "Previsão (média 3M)"})

    ultimo_mes = pd.Period(meses[-1], freq="M")
    prox_mes = (ultimo_mes + 1).strftime("%Y-%m")

    st.subheader(f"Previsão de gastos por categoria para {prox_mes}")
    tabela_prev = media_cat.copy()
    tabela_prev["Previsão (média 3M)"] = tabela_prev["Previsão (média 3M)"].map(lambda x: f"R$ {x:,.2f}")
    st.dataframe(tabela_prev, use_container_width=True)

    figp = px.bar(media_cat, x="categoria", y="Previsão (média 3M)", title=f"Previsão por categoria ({prox_mes})")
    st.plotly_chart(figp, use_container_width=True)

    salario_total = sum(salarios.get(r, 0) for r in f_resp)
    gastos_prev_total = media_cat["Previsão (média 3M)"].sum() if not media_cat.empty else 0.0

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
