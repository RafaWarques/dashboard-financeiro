from __future__ import annotations

import os
import warnings
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client

from despesa_voz import CATEGORIAS_FIXAS, interpretar_despesa, interpretar_despesa_com_ia, transcrever_audio

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Meu Financeiro", page_icon="💰", layout="wide", initial_sidebar_state="collapsed")

CORES = {
    "Alimentação": "#DFFF3F", "Lazer": "#A78BFA", "Higiene": "#22D3EE",
    "Saúde": "#FB7185", "Transporte": "#FB923C", "Casa": "#60A5FA", "Outros": "#A8A29E",
}
RESPONSAVEIS = ["Rafael", "Nathalia"]
COLUNAS = ["id", "data_despesa", "categoria", "descricao", "valor", "forma_pagamento", "parcelas", "responsavel", "semana"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Manrope:wght@600;700;800&display=swap');
html,body,[class*="css"] {font-family:'DM Sans',system-ui,sans-serif}
.stApp {
  background:
    radial-gradient(900px 460px at 22% -8%,rgba(182,58,25,.72),transparent 62%),
    radial-gradient(700px 380px at 92% 2%,rgba(82,13,12,.54),transparent 65%),
    linear-gradient(180deg,#120706 0,#080706 32rem,#080706 100%);
  color:#F7F4EE;
}
.block-container {max-width:1240px;padding-top:1.35rem;padding-bottom:4rem}
[data-testid="stHeader"] {background:transparent}
[data-testid="stSidebar"] {background:#0D0C0A;border-right:1px solid rgba(255,255,255,.08)}
[data-testid="stMetric"] {
  border:1px solid rgba(255,255,255,.09);border-radius:22px;padding:1.1rem 1.2rem;
  background:linear-gradient(145deg,rgba(31,29,26,.94),rgba(13,13,12,.94));
  box-shadow:0 18px 55px rgba(0,0,0,.22),inset 0 1px rgba(255,255,255,.035)
}
[data-testid="stMetricLabel"] {color:#AAA49B}
[data-testid="stMetricValue"] {font-family:'Manrope',sans-serif;font-size:1.65rem;font-weight:800;letter-spacing:-.04em}
[data-testid="stVerticalBlockBorderWrapper"] {
  border-radius:24px;border-color:rgba(255,255,255,.09);
  background:linear-gradient(145deg,rgba(28,26,23,.88),rgba(11,11,10,.94));
  box-shadow:0 20px 65px rgba(0,0,0,.24),inset 0 1px rgba(255,255,255,.035)
}
.app-hero {position:relative;overflow:hidden;padding:1.25rem 0 1.45rem}
.app-hero:after {content:"";position:absolute;width:220px;height:220px;right:4%;top:-90px;border-radius:50%;background:#DFFF3F;filter:blur(100px);opacity:.08;pointer-events:none}
.app-eyebrow {color:#DFFF3F;font:700 .75rem 'Manrope',sans-serif;letter-spacing:.16em}
.app-title {font:800 clamp(2.35rem,6vw,4.6rem)/.98 'Manrope',sans-serif;letter-spacing:-.065em;margin:.38rem 0 .7rem;max-width:760px}
.app-title span {color:#AAA49B}
.app-subtitle,.section-copy {color:#AAA49B;margin-bottom:1rem;font-size:1.02rem}
.section-title,h1,h2,h3,h4 {font-family:'Manrope',sans-serif;letter-spacing:-.035em}
.section-title {font-size:1.42rem;font-weight:800;margin:.2rem 0 .15rem}
.insight {padding:1rem 1.1rem;border-radius:16px;margin:.6rem 0;background:rgba(223,255,63,.07);border-left:3px solid #DFFF3F}
div[data-testid="stRadio"]>div {gap:.45rem;flex-wrap:wrap}
div[data-testid="stRadio"] label {border:1px solid rgba(255,255,255,.1);border-radius:999px;padding:.52rem .95rem;background:rgba(10,9,8,.46);transition:.2s ease}
div[data-testid="stRadio"] label:has(input:checked) {background:#F7F4EE;color:#0A0908;border-color:#F7F4EE}
div[data-testid="stAudioInput"] {padding:1rem;border-radius:18px;background:rgba(0,0,0,.22);border:1px solid rgba(255,255,255,.07)}
div[data-testid="stButton"] button,div[data-testid="stFormSubmitButton"] button {border-radius:14px;font-weight:700;min-height:2.8rem}
div[data-testid="stButton"] button[kind="primary"],div[data-testid="stFormSubmitButton"] button {background:#DFFF3F;color:#0B0A08;border-color:#DFFF3F}
div[data-testid="stButton"] button[kind="primary"]:hover,div[data-testid="stFormSubmitButton"] button:hover {background:#EDFF8A;border-color:#EDFF8A;color:#0B0A08}
[data-testid="stDataFrame"] {border-radius:16px;overflow:hidden}
@media(max-width:700px){
  .block-container{padding:1rem .75rem 3rem}.app-hero{padding-top:.3rem}.app-title{font-size:2.55rem;max-width:330px}
  .app-subtitle{font-size:.94rem;max-width:350px}[data-testid="stMetric"]{padding:.85rem}
  div[data-testid="stRadio"] label{padding:.43rem .7rem;font-size:.88rem}
}
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zhuqsxfmzubsxgbtfemq.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpodXFzeGZtenVic3hnYnRmZW1xIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDk5NTc4ODEsImV4cCI6MjA2NTUzMzg4MX0.6iUd7jGQRxN1ZLAvQv57b3QJpLkd4Mdzs43h9uDSfwc")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def moeda(valor: float) -> str:
    texto = f"{float(valor):,.2f}"
    return f"R$ {texto.replace(',', 'X').replace('.', ',').replace('X', '.')}"


def obter_openai_api_key():
    try:
        chave = st.secrets.get("OPENAI_API_KEY")
    except FileNotFoundError:
        chave = None
    return chave or os.getenv("OPENAI_API_KEY")


def limpar_formulario_voz():
    for chave in ("audio_despesa", "voz_transcricao", "voz_aviso", "form_categoria", "form_descricao", "form_valor", "form_parcelas", "form_responsavel", "form_data", "form_semana"):
        st.session_state.pop(chave, None)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_dados() -> pd.DataFrame:
    return pd.DataFrame(supabase.table("despesas").select("*").execute().data)


def carregar_dados() -> pd.DataFrame:
    base = buscar_dados()
    if base.empty:
        return pd.DataFrame(columns=COLUNAS + ["Ano", "MesRef", "SemanaRef"])
    for coluna in COLUNAS:
        if coluna not in base.columns:
            base[coluna] = None
    base["data_despesa"] = pd.to_datetime(base["data_despesa"], errors="coerce")
    base["valor"] = pd.to_numeric(base["valor"], errors="coerce").fillna(0.0)
    base["parcelas"] = pd.to_numeric(base["parcelas"], errors="coerce").fillna(1).astype(int).clip(lower=1)
    iso = base["data_despesa"].dt.isocalendar()
    base["Ano"] = base["data_despesa"].dt.year
    base["MesRef"] = base["data_despesa"].dt.to_period("M").astype(str)
    base["SemanaRef"] = base["data_despesa"].dt.year.astype("Int64").astype(str) + "-W" + iso.week.astype("Int64").astype(str).str.zfill(2)
    return base


def gerar_parcelas(base: pd.DataFrame) -> pd.DataFrame:
    extras = ["Numero Parcela", "Data Parcela", "Valor Parcela", "ParcelaMesRef"]
    if base.empty:
        return pd.DataFrame(columns=list(base.columns) + extras)
    parcelas = base.loc[base.index.repeat(base["parcelas"])].reset_index(drop=True)
    grupo = ["data_despesa", "valor", "responsavel", "descricao", "categoria"]
    parcelas["Numero Parcela"] = parcelas.groupby(grupo, dropna=False).cumcount() + 1
    parcelas["Data Parcela"] = parcelas.apply(lambda r: r["data_despesa"] + pd.DateOffset(months=int(r["Numero Parcela"]) - 1) if pd.notna(r["data_despesa"]) else pd.NaT, axis=1)
    parcelas["Valor Parcela"] = parcelas["valor"] / parcelas["parcelas"]
    parcelas["ParcelaMesRef"] = parcelas["Data Parcela"].dt.to_period("M").astype(str)
    return parcelas


def estilo_grafico(fig, altura=360):
    fig.update_layout(height=altura, margin=dict(l=8, r=8, t=45, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend_title_text="")
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(148,163,184,.15)")
    return fig


def grafico_vazio(texto="Ainda não há dados neste período"):
    fig = go.Figure()
    fig.add_annotation(text=texto, x=.5, y=.5, showarrow=False, font=dict(color="#94a3b8", size=15))
    fig.update_layout(height=300, xaxis_visible=False, yaxis_visible=False, margin=dict(l=0, r=0, t=10, b=0))
    return fig


df = carregar_dados()
dfp = gerar_parcelas(df)
if st.session_state.pop("limpar_apos_salvar", False):
    limpar_formulario_voz()

st.markdown('''
<div class="app-hero">
  <div class="app-eyebrow">MEU FINANCEIRO</div>
  <div class="app-title">Criado por Rafera.<br><span>Controle e Inteligência pras suas comprinhas.</span></div>
  <div class="app-subtitle">Registre em segundos, entenda seus hábitos e planeje o próximo passo.</div>
</div>
''', unsafe_allow_html=True)
pagina = st.radio("Navegação", ["🏠 Início", "📊 Análises", "💳 Parcelas", "🎯 Planejamento"], horizontal=True, label_visibility="collapsed")

st.sidebar.markdown("## Filtros")
st.sidebar.caption("Afetam as análises e o planejamento.")
f_resp = st.sidebar.multiselect("Responsável", RESPONSAVEIS, default=RESPONSAVEIS)
gran = st.sidebar.radio("Período por", ["Mês", "Semana", "Ano"], horizontal=True)
if df.empty:
    opcoes = []
else:
    coluna = {"Mês": "MesRef", "Semana": "SemanaRef", "Ano": "Ano"}[gran]
    opcoes = sorted(df[coluna].dropna().unique(), reverse=True)
periodo = st.sidebar.selectbox("Período", opcoes) if opcoes else None
st.sidebar.caption("No celular, abra os filtros pelo ícone ›.")

df_resp = df[df["responsavel"].isin(f_resp)].copy() if not df.empty else df.copy()
df_f = df_resp.copy()
if not df_f.empty and periodo is not None:
    coluna = {"Mês": "MesRef", "Semana": "SemanaRef", "Ano": "Ano"}[gran]
    df_f = df_f[df_f[coluna] == periodo]
dfp_f = dfp[dfp["responsavel"].isin(f_resp)].copy() if not dfp.empty else dfp.copy()


def mostrar_resumo():
    if df_f.empty:
        st.info("Seu resumo aparecerá aqui assim que houver despesas neste período.")
        return
    total = df_f["valor"].sum()
    categoria = df_f.groupby("categoria")["valor"].sum().idxmax()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gasto no período", moeda(total))
    col2.metric("Lançamentos", len(df_f))
    col3.metric("Média por compra", moeda(total / len(df_f)))
    col4.metric("Maior categoria", categoria)


def mostrar_cadastro():
    with st.container(border=True):
        st.markdown('<div class="section-title">🎙️ Registrar nova despesa</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-copy">Fale naturalmente: “Comprei um jogo por 150 reais em 3 vezes”.</div>', unsafe_allow_html=True)
        audio = st.audio_input(
            "Toque para gravar sua despesa",
            sample_rate=16000,
            key="audio_despesa",
            help="No primeiro uso, autorize o acesso do navegador ao microfone.",
        )
        st.caption("🔒 O navegador só usa o microfone depois da sua autorização.")
        c1, c2 = st.columns(2)
        interpretar = c1.button("✨ Interpretar gravação", disabled=audio is None, width="stretch", type="primary")
        c2.button("Limpar", on_click=limpar_formulario_voz, width="stretch")

        if interpretar:
            chave = obter_openai_api_key()
            if not chave:
                st.error("Configure OPENAI_API_KEY nos secrets para habilitar a transcrição.")
            else:
                try:
                    with st.spinner("Ouvindo e organizando sua despesa..."):
                        texto = transcrever_audio(audio, chave)
                        try:
                            dados = interpretar_despesa_com_ia(texto, chave)
                            st.session_state.pop("voz_aviso", None)
                        except Exception:
                            dados = interpretar_despesa(texto)
                            st.session_state["voz_aviso"] = "Usei o modo simplificado. Revise os campos."
                    for item in ("form_categoria", "form_descricao", "form_valor", "form_parcelas", "form_responsavel"):
                        st.session_state.pop(item, None)
                    st.session_state["voz_transcricao"] = texto
                    st.session_state["form_descricao"] = dados["descricao"]
                    st.session_state["form_categoria"] = dados["categoria"]
                    if dados["valor"] is not None:
                        st.session_state["form_valor"] = dados["valor"]
                    else:
                        st.session_state["voz_aviso"] = "Não identifiquei o valor; preencha-o manualmente."
                    st.session_state["form_parcelas"] = dados.get("parcelas") or 1
                    if dados.get("responsavel") in RESPONSAVEIS:
                        st.session_state["form_responsavel"] = dados["responsavel"]
                    st.success("Tudo certo. Revise os campos e salve.")
                except Exception as erro:
                    st.error(f"Não foi possível transcrever a gravação: {erro}")

        if st.session_state.get("voz_transcricao"):
            st.info(f'Entendi: “{st.session_state["voz_transcricao"]}”')
        if st.session_state.get("voz_aviso"):
            st.warning(st.session_state["voz_aviso"])
        if st.session_state.get("form_categoria") not in (*CATEGORIAS_FIXAS, None):
            st.session_state["form_categoria"] = "Outros"

        with st.expander("Revisar dados antes de salvar", expanded=bool(st.session_state.get("voz_transcricao"))):
            # A limpeza é feita somente após o salvamento, em limpar_formulario_voz().
            # Usar clear_on_submit junto com o session_state deixava o segundo áudio
            # visualmente preenchido, mas podia enviar os valores padrão do formulário.
            with st.form("form_despesa", clear_on_submit=False):
                c1, c2 = st.columns(2)
                data = c1.date_input("Data da despesa", datetime.today(), key="form_data")
                semana = c2.number_input("Semana do ano", 1, 53, int(data.isocalendar()[1]), key="form_semana")
                c3, c4 = st.columns(2)
                categoria = c3.selectbox("Categoria", CATEGORIAS_FIXAS, key="form_categoria")
                descricao = c4.text_input("Descrição", key="form_descricao", placeholder="Ex.: Almoço")
                c5, c6, c7 = st.columns(3)
                valor = c5.number_input("Valor (R$)", min_value=.01, step=.01, format="%.2f", key="form_valor")
                parcelas = c6.number_input("Parcelas", min_value=1, step=1, value=1, key="form_parcelas")
                responsavel = c7.selectbox("Responsável", RESPONSAVEIS, index=0, key="form_responsavel")
                salvar = st.form_submit_button("Salvar despesa", width="stretch")
                if salvar:
                    descricao_final = (
                        descricao or st.session_state.get("form_descricao", "")
                    ).strip()
                    if not descricao_final:
                        st.error("A descrição não pode estar vazia.")
                    else:
                        supabase.table("despesas").insert({
                            "data_despesa": data.strftime("%Y-%m-%d"), "categoria": categoria,
                            "descricao": descricao_final, "valor": float(valor),
                            "forma_pagamento": "Não informado", "parcelas": int(parcelas),
                            "responsavel": responsavel, "semana": int(semana),
                        }).execute()
                        buscar_dados.clear()
                        st.session_state["limpar_apos_salvar"] = True
                        st.success("Despesa adicionada com sucesso!")
                        st.rerun()


if pagina == "🏠 Início":
    mostrar_cadastro()
    st.markdown("### Visão rápida")
    mostrar_resumo()
    if not df_resp.empty:
        recentes = df_resp.sort_values("data_despesa", ascending=False).head(5).copy()
        recentes["Data"] = recentes["data_despesa"].dt.strftime("%d/%m/%Y")
        recentes["Valor"] = recentes["valor"].map(moeda)
        recentes = recentes.rename(columns={"descricao": "Descrição", "categoria": "Categoria", "responsavel": "Responsável"})
        with st.container(border=True):
            st.markdown("#### Últimos lançamentos")
            st.dataframe(recentes[["Data", "Descrição", "Categoria", "Responsável", "Valor"]], width="stretch", hide_index=True)

elif pagina == "📊 Análises":
    st.markdown("## Painel de gastos")
    st.caption(f"Leitura do período selecionado: {periodo or 'sem período disponível'}")
    mostrar_resumo()
    if df_f.empty:
        st.plotly_chart(grafico_vazio(), width="stretch")
    else:
        por_cat = df_f.groupby("categoria", as_index=False)["valor"].sum().sort_values("valor", ascending=False)
        esquerda, direita = st.columns([1.2, 1])
        barras = px.bar(por_cat.sort_values("valor"), x="valor", y="categoria", orientation="h", color="categoria", color_discrete_map=CORES, title="Onde você mais gastou")
        barras.update_layout(showlegend=False)
        esquerda.plotly_chart(estilo_grafico(barras), width="stretch")
        donut = px.pie(por_cat, names="categoria", values="valor", hole=.66, color="categoria", color_discrete_map=CORES, title="Participação por categoria")
        donut.update_traces(textposition="outside", textinfo="percent+label")
        direita.plotly_chart(estilo_grafico(donut), width="stretch")

        mensal = df_resp.groupby("MesRef", as_index=False)["valor"].sum().sort_values("MesRef").tail(12)
        linha = px.line(mensal, x="MesRef", y="valor", markers=True, title="Evolução dos últimos 12 meses", labels={"MesRef": "Mês", "valor": "Total"})
        linha.update_traces(line_color="#DFFF3F", line_width=4, marker_size=8, fill="tozeroy", fillcolor="rgba(223,255,63,.10)")
        st.plotly_chart(estilo_grafico(linha), width="stretch")

        c1, c2 = st.columns(2)
        maiores = df_f.nlargest(8, "valor")[["descricao", "categoria", "valor"]].copy()
        maiores["valor"] = maiores["valor"].map(moeda)
        maiores.columns = ["Descrição", "Categoria", "Valor"]
        recorrentes = df_f.groupby("descricao", as_index=False).agg(Total=("valor", "sum"), Vezes=("valor", "size")).sort_values(["Vezes", "Total"], ascending=False).head(8)
        recorrentes["Total"] = recorrentes["Total"].map(moeda)
        recorrentes = recorrentes.rename(columns={"descricao": "Descrição"})
        with c1.container(border=True):
            st.markdown("#### Maiores compras")
            st.dataframe(maiores, width="stretch", hide_index=True)
        with c2.container(border=True):
            st.markdown("#### Gastos mais recorrentes")
            st.dataframe(recorrentes, width="stretch", hide_index=True)
        st.download_button("Baixar dados filtrados (.csv)", df_f.to_csv(index=False).encode("utf-8-sig"), "despesas.csv", "text/csv")

elif pagina == "💳 Parcelas":
    st.markdown("## Compromissos parcelados")
    st.caption("Antecipe o que já está comprometido nos próximos meses.")
    mes_atual = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    futuras = dfp_f[dfp_f["ParcelaMesRef"] >= mes_atual].copy() if not dfp_f.empty else dfp_f.copy()
    if futuras.empty:
        st.success("Você não tem parcelas futuras registradas para estes responsáveis.")
        st.plotly_chart(grafico_vazio("Nenhuma parcela futura"), width="stretch")
    else:
        por_mes = futuras.groupby("ParcelaMesRef", as_index=False)["Valor Parcela"].sum().sort_values("ParcelaMesRef")
        c1, c2, c3 = st.columns(3)
        c1.metric("Comprometido no próximo mês", moeda(por_mes.iloc[0]["Valor Parcela"]))
        c2.metric("Total ainda parcelado", moeda(futuras["Valor Parcela"].sum()))
        c3.metric("Compras parceladas ativas", futuras["id"].nunique() if "id" in futuras else len(futuras))
        fig = px.bar(por_mes.head(12), x="ParcelaMesRef", y="Valor Parcela", title="Compromissos nos próximos 12 meses", color_discrete_sequence=["#8b5cf6"])
        st.plotly_chart(estilo_grafico(fig), width="stretch")
        detalhe = futuras.sort_values("Data Parcela").head(30).copy()
        detalhe["Parcela"] = detalhe["Numero Parcela"].astype(str) + "/" + detalhe["parcelas"].astype(str)
        detalhe["Vencimento"] = detalhe["Data Parcela"].dt.strftime("%m/%Y")
        detalhe["Valor"] = detalhe["Valor Parcela"].map(moeda)
        detalhe = detalhe.rename(columns={"descricao": "Descrição", "categoria": "Categoria"})
        st.dataframe(detalhe[["Descrição", "Categoria", "Parcela", "Vencimento", "Valor"]], width="stretch", hide_index=True)

else:
    st.markdown("## Planejamento e próximos passos")
    st.caption("Sugestões baseadas no seu histórico — sem julgamentos e com ações possíveis.")
    if df_resp.empty:
        st.info("Registre algumas despesas para receber recomendações personalizadas.")
    else:
        meses = sorted(df_resp["MesRef"].dropna().unique())
        hist = df_resp[df_resp["MesRef"].isin(meses[-3:])]
        totais = hist.groupby("MesRef")["valor"].sum()
        media = totais.mean() if not totais.empty else 0
        media_cat = hist.groupby(["MesRef", "categoria"], as_index=False)["valor"].sum().groupby("categoria", as_index=False)["valor"].mean()
        prox = (pd.Period(meses[-1], freq="M") + 1).strftime("%Y-%m")
        parcelas_prox = dfp_f[dfp_f["ParcelaMesRef"] == prox]["Valor Parcela"].sum() if not dfp_f.empty else 0
        c1, c2, c3 = st.columns(3)
        c1.metric("Média mensal (3 meses)", moeda(media))
        c2.metric("Previsão base do próximo mês", moeda(media + parcelas_prox))
        c3.metric("Parcelas no próximo mês", moeda(parcelas_prox))

        with st.container(border=True):
            st.markdown("### Seus insights")
            if not media_cat.empty:
                top = media_cat.loc[media_cat["valor"].idxmax()]
                fatia = top["valor"] / media_cat["valor"].sum() * 100
                st.markdown(f'<div class="insight"><b>Comece por {top["categoria"]}.</b> Ela representa cerca de {fatia:.0f}% da sua média recente. Uma redução de 10% liberaria aproximadamente {moeda(top["valor"] * .1)} por mês.</div>', unsafe_allow_html=True)
            if len(totais) > 1 and totais.iloc[-2] > 0:
                var = (totais.iloc[-1] / totais.iloc[-2] - 1) * 100
                direcao = "aumentaram" if var > 0 else "diminuíram"
                acao = "Revise as maiores compras antes de assumir novos compromissos." if var > 10 else "Continue acompanhando semanalmente para manter o controle."
                st.markdown(f'<div class="insight"><b>Ritmo mensal:</b> seus gastos {direcao} {abs(var):.0f}% em relação ao mês anterior. {acao}</div>', unsafe_allow_html=True)
            frequentes = hist.groupby("descricao").agg(total=("valor", "sum"), vezes=("valor", "size")).sort_values("vezes", ascending=False)
            if not frequentes.empty and frequentes.iloc[0]["vezes"] >= 3:
                st.markdown(f'<div class="insight"><b>Pequenos hábitos somam:</b> “{frequentes.index[0]}” apareceu {int(frequentes.iloc[0]["vezes"])} vezes e totalizou {moeda(frequentes.iloc[0]["total"])}. Experimente um limite semanal para esse gasto.</div>', unsafe_allow_html=True)

        st.markdown("### Meta sugerida por categoria")
        st.caption("Ponto de partida: 10% abaixo da média dos últimos três meses. Ajuste à sua realidade.")
        metas = media_cat.sort_values("valor", ascending=False).copy()
        metas["Média atual"] = metas["valor"].map(moeda)
        metas["Meta sugerida"] = (metas["valor"] * .9).map(moeda)
        metas["Economia potencial"] = (metas["valor"] * .1).map(moeda)
        metas = metas.rename(columns={"categoria": "Categoria"})
        st.dataframe(metas[["Categoria", "Média atual", "Meta sugerida", "Economia potencial"]], width="stretch", hide_index=True)

st.caption("Estimativas para apoiar decisões pessoais; não constituem aconselhamento financeiro.")
