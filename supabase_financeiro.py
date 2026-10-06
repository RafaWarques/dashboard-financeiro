from __future__ import annotations

import os
import warnings
from datetime import date, datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from supabase import Client, create_client

from despesa_voz import CATEGORIAS_FIXAS, interpretar_despesa, interpretar_despesa_com_ia, transcrever_audio
from wishlist_ui import mostrar_wishlist

warnings.filterwarnings("ignore")
st.set_page_config(page_title="Meu Financeiro", page_icon="💰", layout="wide", initial_sidebar_state="collapsed")

CORES = {
    "Alimentação": "#DFFF3F", "Lazer": "#A78BFA", "Higiene": "#22D3EE",
    "Saúde": "#FB7185", "Transporte": "#FB923C", "Casa": "#60A5FA", "Outros": "#A8A29E",
}
RESPONSAVEIS = ["Rafael", "Nathalia"]
COLUNAS = [
    "id", "data_despesa", "categoria", "descricao", "valor",
    "forma_pagamento", "parcelas", "responsavel", "semana",
    "despesa_recorrente_id", "competencia",
]
MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

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


def nome_mes(mes_ref: str) -> str:
    try:
        periodo = pd.Period(mes_ref, freq="M")
        return f"{MESES_PT[periodo.month - 1]} {periodo.year}"
    except Exception:
        return str(mes_ref)


def obter_openai_api_key():
    try:
        chave = st.secrets.get("OPENAI_API_KEY")
    except FileNotFoundError:
        chave = None
    return chave or os.getenv("OPENAI_API_KEY")


def limpar_formulario_voz():
    for chave in ("audio_despesa", "voz_transcricao", "voz_aviso", "form_categoria", "form_descricao", "form_valor", "form_parcelas", "form_responsavel", "form_data", "form_semana", "tipo_lancamento"):
        st.session_state.pop(chave, None)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_dados() -> pd.DataFrame:
    return pd.DataFrame(supabase.table("despesas").select("*").execute().data)


@st.cache_data(ttl=120, show_spinner=False)
def buscar_recorrencias() -> pd.DataFrame:
    resposta = (
        supabase.table("despesas_recorrentes")
        .select("*")
        .order("ativa", desc=True)
        .order("dia_cobranca")
        .execute()
    )
    return pd.DataFrame(resposta.data)


def sincronizar_recorrencias() -> int:
    """Materializa cobranças vencidas sem duplicá-las.

    A função SQL também pode ser executada diariamente pelo Supabase Cron. A chamada
    durante a abertura do app serve como garantia caso o agendamento não esteja ativo.
    """
    try:
        resposta = supabase.rpc(
            "sincronizar_despesas_recorrentes",
            {"p_ate": date.today().isoformat()},
        ).execute()
        st.session_state.pop("erro_sincronizacao_recorrencias", None)
        return int(resposta.data or 0)
    except Exception as erro:
        # Mantém o app antigo funcionando até a migração do Supabase ser aplicada.
        st.session_state["erro_sincronizacao_recorrencias"] = str(erro)
        return 0


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
    grupo = ["id"] if "id" in parcelas.columns else ["data_despesa", "valor", "responsavel", "descricao", "categoria"]
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


novas_recorrencias = sincronizar_recorrencias()
if novas_recorrencias:
    buscar_dados.clear()
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
pagina = st.radio(
    "Navegação",
    ["🏠 Início", "📊 Visão mensal", "🧾 Despesas", "🔁 Fixas e assinaturas", "💳 Parcelas", "♡ Lista de desejos"],
    horizontal=True,
    label_visibility="collapsed",
)

st.sidebar.markdown("## Filtros")
st.sidebar.caption("O responsável selecionado afeta todas as páginas.")
f_resp = st.sidebar.multiselect("Responsável", RESPONSAVEIS, default=RESPONSAVEIS)
st.sidebar.caption("No celular, abra os filtros pelo ícone ›.")

df_resp = df[df["responsavel"].isin(f_resp)].copy() if not df.empty else df.copy()
dfp_f = dfp[dfp["responsavel"].isin(f_resp)].copy() if not dfp.empty else dfp.copy()


def mostrar_resumo():
    mes_atual = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    base_mes = dfp_f[dfp_f["ParcelaMesRef"] == mes_atual].copy() if not dfp_f.empty else dfp_f.copy()
    if base_mes.empty:
        st.info("Seu resumo aparecerá aqui assim que houver despesas neste mês.")
        return
    total = base_mes["Valor Parcela"].sum()
    categoria = base_mes.groupby("categoria")["Valor Parcela"].sum().idxmax()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Impacto neste mês", moeda(total))
    col2.metric("Itens no mês", len(base_mes))
    col3.metric("Média por item", moeda(total / len(base_mes)))
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
            tipo_lancamento = st.radio(
                "Tipo de despesa",
                ["Despesa comum", "Despesa fixa", "Assinatura"],
                index=0,
                horizontal=True,
                key="tipo_lancamento",
                help="Fixas e assinaturas serão lançadas automaticamente todo mês.",
            )
            # A limpeza é feita somente após o salvamento, em limpar_formulario_voz().
            # Usar clear_on_submit junto com o session_state deixava o segundo áudio
            # visualmente preenchido, mas podia enviar os valores padrão do formulário.
            with st.form("form_despesa", clear_on_submit=False):
                c1, c2 = st.columns(2)
                rotulo_data = "Primeira cobrança" if tipo_lancamento != "Despesa comum" else "Data da despesa"
                data = c1.date_input(rotulo_data, datetime.today(), key="form_data")
                if tipo_lancamento == "Despesa comum":
                    semana = c2.number_input("Semana do ano", 1, 53, int(data.isocalendar()[1]), key="form_semana")
                else:
                    semana = int(data.isocalendar()[1])
                    c2.info(f"A cobrança será lançada todo dia {data.day}.")
                c3, c4 = st.columns(2)
                categoria = c3.selectbox("Categoria", CATEGORIAS_FIXAS, key="form_categoria")
                descricao = c4.text_input("Descrição", key="form_descricao", placeholder="Ex.: Almoço")
                if tipo_lancamento == "Despesa comum":
                    c5, c6, c7 = st.columns(3)
                    valor = c5.number_input("Valor (R$)", min_value=.01, step=.01, format="%.2f", key="form_valor")
                    parcelas = c6.number_input("Parcelas", min_value=1, step=1, value=1, key="form_parcelas")
                    responsavel = c7.selectbox("Responsável", RESPONSAVEIS, index=0, key="form_responsavel")
                else:
                    c5, c7 = st.columns(2)
                    valor = c5.number_input("Valor mensal (R$)", min_value=.01, step=.01, format="%.2f", key="form_valor")
                    parcelas = 1
                    responsavel = c7.selectbox("Responsável", RESPONSAVEIS, index=0, key="form_responsavel")
                salvar = st.form_submit_button("Salvar despesa", width="stretch")
                if salvar:
                    descricao_final = (
                        descricao or st.session_state.get("form_descricao", "")
                    ).strip()
                    if not descricao_final:
                        st.error("A descrição não pode estar vazia.")
                    else:
                        if tipo_lancamento == "Despesa comum":
                            supabase.table("despesas").insert({
                                "data_despesa": data.strftime("%Y-%m-%d"), "categoria": categoria,
                                "descricao": descricao_final, "valor": float(valor),
                                "forma_pagamento": "Não informado", "parcelas": int(parcelas),
                                "responsavel": responsavel, "semana": int(semana),
                            }).execute()
                            mensagem = "Despesa adicionada com sucesso!"
                        else:
                            try:
                                supabase.table("despesas_recorrentes").insert({
                                    "tipo": "fixa" if tipo_lancamento == "Despesa fixa" else "assinatura",
                                    "data_inicio": data.strftime("%Y-%m-%d"),
                                    "dia_cobranca": data.day,
                                    "categoria": categoria,
                                    "descricao": descricao_final,
                                    "valor": float(valor),
                                    "forma_pagamento": "Não informado",
                                    "responsavel": responsavel,
                                    "ativa": True,
                                }).execute()
                            except Exception:
                                st.error(
                                    "Não foi possível salvar a recorrência. Confirme se a migração "
                                    "do Supabase indicada no README já foi executada."
                                )
                                return
                            buscar_recorrencias.clear()
                            sincronizar_recorrencias()
                            mensagem = f"{tipo_lancamento} cadastrada com sucesso!"
                        buscar_dados.clear()
                        st.session_state["limpar_apos_salvar"] = True
                        st.success(mensagem)
                        st.rerun()


def mostrar_recorrencias():
    st.markdown("## Despesas fixas e assinaturas")
    st.caption("Veja exatamente o que se repete todos os meses e quanto isso representa no orçamento.")

    try:
        recorrencias = buscar_recorrencias()
    except Exception:
        st.error(
            "A estrutura de recorrências ainda não existe no Supabase. "
            "Execute a migração `supabase/migrations/20260926170000_despesas_recorrentes.sql` "
            "no SQL Editor e recarregue o app."
        )
        return

    if recorrencias.empty:
        st.info("Você ainda não cadastrou despesas fixas ou assinaturas.")
        st.caption("Use o cadastro da página Início e escolha o tipo de despesa antes de salvar.")
        return

    recorrencias["valor"] = pd.to_numeric(recorrencias["valor"], errors="coerce").fillna(0.0)
    recorrencias["ativa"] = recorrencias["ativa"].fillna(False).astype(bool)
    recorrencias["data_inicio"] = pd.to_datetime(recorrencias["data_inicio"], errors="coerce")
    ativas = recorrencias[recorrencias["ativa"]].copy()
    inativas = recorrencias[~recorrencias["ativa"]].copy()

    assinaturas = ativas[ativas["tipo"] == "assinatura"].copy()
    fixas = ativas[ativas["tipo"] == "fixa"].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total recorrente mensal", moeda(ativas["valor"].sum()))
    c2.metric("Assinaturas", moeda(assinaturas["valor"].sum()), f"{len(assinaturas)} ativas")
    c3.metric("Despesas fixas", moeda(fixas["valor"].sum()), f"{len(fixas)} ativas")

    def tabela_ativa(base: pd.DataFrame, nome_coluna: str):
        if base.empty:
            st.info(f"Nenhuma {nome_coluna.lower()} ativa.")
            return
        tabela = base.sort_values(["dia_cobranca", "descricao"]).copy()
        tabela["Início"] = tabela["data_inicio"].dt.strftime("%d/%m/%Y").fillna("—")
        tabela["Cobrança"] = tabela["dia_cobranca"].map(lambda dia: f"Dia {int(dia)}")
        tabela["Valor mensal"] = tabela["valor"].map(moeda)
        tabela = tabela.rename(
            columns={"descricao": nome_coluna, "categoria": "Categoria", "responsavel": "Responsável"}
        )
        tabela = tabela[[nome_coluna, "Categoria", "Responsável", "Início", "Cobrança", "Valor mensal"]]
        total = pd.DataFrame([{nome_coluna: "TOTAL", "Valor mensal": moeda(base["valor"].sum())}])
        st.dataframe(pd.concat([tabela, total], ignore_index=True), width="stretch", hide_index=True)

    aba_assinaturas, aba_fixas = st.tabs(["Assinaturas ativas", "Despesas fixas ativas"])
    with aba_assinaturas:
        tabela_ativa(assinaturas, "Assinatura")
    with aba_fixas:
        tabela_ativa(fixas, "Despesa fixa")

    if not ativas.empty:
        with st.expander("Desativar uma cobrança"):
            opcoes = ativas.sort_values("descricao")["id"].tolist()
            rotulos = {
                item["id"]: f"{item['descricao']} · {moeda(item['valor'])} · dia {int(item['dia_cobranca'])}"
                for _, item in ativas.iterrows()
            }
            recorrencia_id = st.selectbox(
                "Selecione a despesa ou assinatura",
                opcoes,
                format_func=lambda identificador: rotulos[identificador],
            )
            if st.button("Desativar cobrança selecionada", type="primary", width="stretch"):
                (
                    supabase.table("despesas_recorrentes")
                    .update({"ativa": False, "desativada_em": datetime.now().astimezone().isoformat()})
                    .eq("id", recorrencia_id)
                    .execute()
                )
                buscar_recorrencias.clear()
                st.rerun()

    if not inativas.empty:
        with st.expander(f"Ver desativadas ({len(inativas)})"):
            historico = inativas.copy()
            historico["Tipo"] = historico["tipo"].map({"fixa": "Despesa fixa", "assinatura": "Assinatura"})
            historico["Valor"] = historico["valor"].map(moeda)
            historico["Cobrança"] = historico["dia_cobranca"].map(lambda dia: f"Dia {int(dia)}")
            historico = historico.rename(
                columns={"descricao": "Descrição", "categoria": "Categoria", "responsavel": "Responsável"}
            )
            st.dataframe(
                historico[["Descrição", "Tipo", "Categoria", "Responsável", "Cobrança", "Valor"]],
                width="stretch",
                hide_index=True,
            )


def mostrar_despesas_comuns():
    st.markdown("## Despesas comuns")
    st.caption("Filtre os lançamentos e veja quanto cada categoria representa no período.")

    comuns = df_resp[df_resp["despesa_recorrente_id"].isna()].copy() if not df_resp.empty else df_resp.copy()
    if comuns.empty:
        st.info("Ainda não há despesas comuns para os responsáveis selecionados.")
        return

    meses = sorted(comuns["MesRef"].dropna().unique(), reverse=True)
    categorias = sorted(comuns["categoria"].dropna().unique())
    filtro_mes, filtro_categoria = st.columns(2)
    mes = filtro_mes.selectbox("Mês", meses + ["Todos"], format_func=lambda valor: "Todos os meses" if valor == "Todos" else nome_mes(valor))
    categoria = filtro_categoria.selectbox("Categoria", ["Todas"] + categorias)

    filtradas = comuns.copy()
    if mes != "Todos":
        filtradas = filtradas[filtradas["MesRef"] == mes]
    if categoria != "Todas":
        filtradas = filtradas[filtradas["categoria"] == categoria]

    if filtradas.empty:
        st.info("Não há despesas com essa combinação de filtros.")
        return

    total = filtradas["valor"].sum()
    maior_categoria = filtradas.groupby("categoria")["valor"].sum().idxmax()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total filtrado", moeda(total))
    c2.metric("Lançamentos", len(filtradas))
    c3.metric("Média", moeda(total / len(filtradas)))
    c4.metric("Maior categoria", maior_categoria)

    por_categoria = (
        filtradas.groupby("categoria", as_index=False)
        .agg(Lançamentos=("valor", "size"), Total=("valor", "sum"))
        .sort_values("Total", ascending=False)
    )
    por_categoria["Participação"] = (por_categoria["Total"] / total * 100).map(lambda valor: f"{valor:.1f}%")
    por_categoria["Total"] = por_categoria["Total"].map(moeda)
    por_categoria = por_categoria.rename(columns={"categoria": "Categoria"})

    st.markdown("### Total por categoria")
    st.dataframe(por_categoria[["Categoria", "Lançamentos", "Participação", "Total"]], width="stretch", hide_index=True)

    st.markdown("### Lançamentos")
    tabela = filtradas.sort_values(["data_despesa", "descricao"], ascending=[False, True]).copy()
    tabela["Data"] = tabela["data_despesa"].dt.strftime("%d/%m/%Y")
    tabela["Parcelamento"] = tabela["parcelas"].map(lambda qtd: "À vista" if int(qtd) == 1 else f"{int(qtd)}x")
    tabela["Valor"] = tabela["valor"].map(moeda)
    tabela = tabela.rename(columns={"descricao": "Descrição", "categoria": "Categoria", "responsavel": "Responsável"})
    tabela = tabela[["Data", "Descrição", "Categoria", "Responsável", "Parcelamento", "Valor"]]
    linha_total = pd.DataFrame([{"Descrição": "TOTAL", "Valor": moeda(total)}])
    st.dataframe(pd.concat([tabela, linha_total], ignore_index=True), width="stretch", hide_index=True)
    st.download_button(
        "Baixar despesas filtradas (.csv)",
        filtradas.to_csv(index=False).encode("utf-8-sig"),
        "despesas_comuns.csv",
        "text/csv",
    )


def classificar_origem(base: pd.DataFrame) -> pd.DataFrame:
    resultado = base.copy()
    resultado["Origem"] = "Despesa comum"
    recorrente = resultado["despesa_recorrente_id"].notna()
    resultado.loc[recorrente, "Origem"] = "Despesa fixa"
    try:
        regras = buscar_recorrencias()
        ids_assinaturas = {
            str(int(identificador))
            for identificador in regras.loc[regras["tipo"] == "assinatura", "id"].dropna()
        }
        chaves = resultado["despesa_recorrente_id"].map(
            lambda identificador: str(int(identificador)) if pd.notna(identificador) else ""
        )
        resultado.loc[chaves.isin(ids_assinaturas), "Origem"] = "Assinatura"
    except Exception:
        resultado.loc[recorrente, "Origem"] = "Recorrente"
    return resultado


def mostrar_visao_mensal():
    st.markdown("## Visão mensal")
    st.caption("O valor mensal distribui compras parceladas entre os meses e inclui as cobranças recorrentes já lançadas.")

    if dfp_f.empty:
        st.info("Ainda não há lançamentos suficientes para montar a visão mensal.")
        return

    base = classificar_origem(dfp_f)
    meses = sorted(base["ParcelaMesRef"].dropna().unique(), reverse=True)
    mes_atual = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    indice_padrao = meses.index(mes_atual) if mes_atual in meses else 0
    mes = st.selectbox("Mês analisado", meses, index=indice_padrao, format_func=nome_mes)
    mensal = base[base["ParcelaMesRef"] == mes].copy()

    total = mensal["Valor Parcela"].sum()
    comuns = mensal.loc[mensal["Origem"] == "Despesa comum", "Valor Parcela"].sum()
    recorrentes = total - comuns
    mes_anterior = (pd.Period(mes, freq="M") - 1).strftime("%Y-%m")
    total_anterior = base.loc[base["ParcelaMesRef"] == mes_anterior, "Valor Parcela"].sum()
    variacao = ((total / total_anterior) - 1) * 100 if total_anterior else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total do mês", moeda(total))
    c2.metric("Despesas comuns", moeda(comuns))
    c3.metric("Fixas e assinaturas", moeda(recorrentes))
    c4.metric(
        "Variação mensal",
        f"{variacao:+.1f}%" if variacao is not None else "Sem comparação",
        f"vs. {nome_mes(mes_anterior)}" if total_anterior else None,
    )

    if mensal.empty:
        st.plotly_chart(grafico_vazio("Nenhum valor previsto para este mês"), width="stretch")
        return

    por_categoria = mensal.groupby("categoria", as_index=False)["Valor Parcela"].sum().sort_values("Valor Parcela", ascending=False)
    por_origem = mensal.groupby("Origem", as_index=False)["Valor Parcela"].sum().sort_values("Valor Parcela", ascending=False)

    grafico_col, composicao_col = st.columns([1.7, 1])
    barras = px.bar(
        por_categoria.sort_values("Valor Parcela"),
        x="Valor Parcela",
        y="categoria",
        orientation="h",
        color="categoria",
        color_discrete_map=CORES,
        title="Total por categoria",
        labels={"Valor Parcela": "Valor", "categoria": "Categoria"},
        text="Valor Parcela",
    )
    barras.update_traces(texttemplate="R$ %{text:,.2f}", textposition="outside")
    barras.update_layout(showlegend=False)
    grafico_col.plotly_chart(estilo_grafico(barras), width="stretch")

    por_origem["Participação"] = (por_origem["Valor Parcela"] / total * 100).map(lambda valor: f"{valor:.1f}%")
    por_origem["Total"] = por_origem["Valor Parcela"].map(moeda)
    with composicao_col.container(border=True):
        st.markdown("#### Composição do mês")
        st.dataframe(por_origem[["Origem", "Participação", "Total"]], width="stretch", hide_index=True)

    evolucao_base = base[base["ParcelaMesRef"] <= mes].copy()
    ultimos_meses = sorted(evolucao_base["ParcelaMesRef"].dropna().unique())[-12:]
    evolucao = (
        evolucao_base[evolucao_base["ParcelaMesRef"].isin(ultimos_meses)]
        .groupby(["ParcelaMesRef", "Origem"], as_index=False)["Valor Parcela"].sum()
    )
    fig_evolucao = px.bar(
        evolucao,
        x="ParcelaMesRef",
        y="Valor Parcela",
        color="Origem",
        barmode="stack",
        title="Evolução mensal por tipo de despesa",
        labels={"ParcelaMesRef": "Mês", "Valor Parcela": "Total"},
        color_discrete_map={"Despesa comum": "#DFFF3F", "Despesa fixa": "#60A5FA", "Assinatura": "#A78BFA", "Recorrente": "#60A5FA"},
    )
    st.plotly_chart(estilo_grafico(fig_evolucao), width="stretch")

    maior_categoria = por_categoria.iloc[0]
    maior_item = mensal.loc[mensal["Valor Parcela"].idxmax()]
    participacao_recorrente = recorrentes / total * 100 if total else 0
    st.markdown("### Leitura do mês")
    st.markdown(
        f'<div class="insight"><b>{maior_categoria["categoria"]}</b> é a maior categoria, com '
        f'{moeda(maior_categoria["Valor Parcela"])}. O maior item mensal é '
        f'<b>{maior_item["descricao"]}</b>, com {moeda(maior_item["Valor Parcela"])}. '
        f'Fixas e assinaturas representam {participacao_recorrente:.1f}% do total.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Itens que formam o total")
    detalhe = mensal.sort_values(["Valor Parcela", "Data Parcela"], ascending=[False, False]).copy()
    detalhe["Data"] = detalhe["Data Parcela"].dt.strftime("%d/%m/%Y")
    detalhe["Parcela"] = detalhe.apply(
        lambda item: "—" if int(item["parcelas"]) == 1 else f'{int(item["Numero Parcela"])}/{int(item["parcelas"])}',
        axis=1,
    )
    detalhe["Valor no mês"] = detalhe["Valor Parcela"].map(moeda)
    detalhe = detalhe.rename(columns={"descricao": "Descrição", "categoria": "Categoria", "responsavel": "Responsável"})
    detalhe = detalhe[["Data", "Descrição", "Categoria", "Origem", "Responsável", "Parcela", "Valor no mês"]]
    linha_total = pd.DataFrame([{"Descrição": "TOTAL", "Valor no mês": moeda(total)}])
    st.dataframe(pd.concat([detalhe, linha_total], ignore_index=True), width="stretch", hide_index=True)


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

elif pagina == "📊 Visão mensal":
    mostrar_visao_mensal()

elif pagina == "🧾 Despesas":
    mostrar_despesas_comuns()

elif pagina == "🔁 Fixas e assinaturas":
    mostrar_recorrencias()

elif pagina == "♡ Lista de desejos":
    mostrar_wishlist(SUPABASE_URL, f_resp)

else:
    st.markdown("## Compromissos parcelados")
    st.caption("Antecipe o que já está comprometido nos próximos meses.")
    mes_atual = pd.Timestamp.today().to_period("M").strftime("%Y-%m")
    futuras = (
        dfp_f[(dfp_f["parcelas"] > 1) & (dfp_f["ParcelaMesRef"] >= mes_atual)].copy()
        if not dfp_f.empty else dfp_f.copy()
    )
    if futuras.empty:
        st.success("Você não tem parcelas futuras registradas para estes responsáveis.")
        st.plotly_chart(grafico_vazio("Nenhuma parcela futura"), width="stretch")
    else:
        por_mes = futuras.groupby("ParcelaMesRef", as_index=False)["Valor Parcela"].sum().sort_values("ParcelaMesRef")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vencimento em {nome_mes(por_mes.iloc[0]['ParcelaMesRef'])}", moeda(por_mes.iloc[0]["Valor Parcela"]))
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

st.caption("Valores mensais consideram o parcelamento informado e as recorrências já lançadas pelo Supabase.")
