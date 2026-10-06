"""Página Streamlit da lista de desejos compartilhada."""
from __future__ import annotations

import os
from decimal import Decimal
from html import escape

import streamlit as st
from supabase import create_client

from wishlist import ErroWishlist, RESPONSAVEIS, WishlistRepositorio, preparar_foto


def moeda(valor):
    return "R$ " + f"{Decimal(str(valor)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def obter_chave_servidor():
    chave = os.getenv("SUPABASE_WISHLIST_KEY")
    if chave:
        return chave
    try:
        return st.secrets.get("SUPABASE_WISHLIST_KEY")
    except FileNotFoundError:
        return None


def concluir(mensagem, aviso=None, formulario=None):
    st.session_state["wl_mensagem"] = mensagem
    st.session_state["wl_aviso"] = aviso
    if formulario:
        # Widgets de foto não aceitam limpeza por atribuição ao session_state.
        # Uma nova versão também limpa todos os campos somente após salvar.
        chave = f"wl_versao_{formulario}"
        st.session_state[chave] = st.session_state.get(chave, 0) + 1
    st.session_state.pop("wl_editar", None)
    st.rerun()


def mostrar_editor(repo, item=None):
    identificador = item["id"] if item else "novo"
    prefixo = f"wl_{identificador}_{st.session_state.get(f'wl_versao_{identificador}', 0)}"
    with st.container(border=True):
        st.subheader("Editar desejo" if item else "Adicionar um desejo")
        nome = st.text_input("Nome do item", value=item["nome"] if item else "",
                             max_chars=120, key=f"{prefixo}_nome", placeholder="Ex.: cafeteira, bicicleta, viagem…")
        c1, c2 = st.columns(2)
        valor = c1.number_input("Valor estimado (R$)", min_value=0.0, max_value=9999999999.99,
                                value=float(item["valor"]) if item else 0.0, step=10.0,
                                format="%.2f", key=f"{prefixo}_valor")
        responsavel = c2.selectbox("Para quem é esse desejo?", RESPONSAVEIS,
                                   index=RESPONSAVEIS.index(item["responsavel"]) if item else 0,
                                   key=f"{prefixo}_responsavel")
        descricao = st.text_area("Descrição", value=item["descricao"] if item else "", max_chars=2000,
                                 placeholder="Modelo, tamanho, onde encontrar ou por que você quer comprar.",
                                 key=f"{prefixo}_descricao")
        possui_foto = bool(item and item.get("foto_path"))
        opcoes = ["Manter foto atual" if possui_foto else "Sem foto", "Tirar foto", "Enviar imagem"]
        if possui_foto:
            opcoes.append("Remover foto")
        origem = st.radio("Foto do item (opcional)", opcoes, horizontal=True, key=f"{prefixo}_origem")
        foto = None
        if origem == "Tirar foto":
            st.caption("Autorize a câmera no navegador. No celular, você também pode enviar uma foto da galeria.")
            foto = st.camera_input("Fotografar o item", key=f"{prefixo}_camera")
        elif origem == "Enviar imagem":
            foto = st.file_uploader("Escolher foto", type=["jpg", "jpeg", "png", "webp"],
                                    key=f"{prefixo}_upload", help="Até 5 MB. Fotos JPG, PNG ou WebP.")
        if foto:
            try:
                st.image(preparar_foto(foto.getvalue()), width=240)
            except ErroWishlist as erro:
                st.error(str(erro))
        c1, c2 = st.columns(2)
        if c1.button("Salvar alterações" if item else "Adicionar à lista", type="primary",
                     width="stretch", key=f"{prefixo}_salvar"):
            try:
                if origem in ("Tirar foto", "Enviar imagem") and foto is None:
                    raise ErroWishlist("Inclua a foto ou selecione a opção sem foto antes de salvar.")
                aviso = repo.salvar(nome, valor, descricao, responsavel, item=item,
                                    foto=foto.getvalue() if foto else None, remover_foto=origem == "Remover foto")
            except ErroWishlist as erro:
                st.error(str(erro))
            else:
                concluir("Desejo atualizado!" if item else "Desejo adicionado à sua lista!", aviso, identificador)
        if item and c2.button("Cancelar edição", width="stretch", key=f"{prefixo}_cancelar"):
            chave_versao = f"wl_versao_{identificador}"
            st.session_state[chave_versao] = st.session_state.get(chave_versao, 0) + 1
            st.session_state.pop("wl_editar", None)
            st.rerun()


def mostrar_wishlist(supabase_url, responsaveis):
    st.markdown("## Lista de desejos")
    st.caption("Guarde suas próximas conquistas: foto, nome, preço e os detalhes que importam.")
    chave = obter_chave_servidor()
    if not chave:
        st.info("Para ativar a lista, configure SUPABASE_WISHLIST_KEY nos secrets do Streamlit "
                "e execute a migração indicada no guia docs/wishlist.md.")
        return
    try:
        # Cliente exclusivo no servidor; nunca substitui a chave anon das despesas.
        repo = WishlistRepositorio(create_client(supabase_url, chave))
        itens = repo.listar()
    except ErroWishlist as erro:
        st.error(str(erro))
        return
    except Exception:
        st.error("Não consegui conectar a lista de desejos. Confira SUPABASE_WISHLIST_KEY e tente novamente.")
        return

    mensagem = st.session_state.pop("wl_mensagem", None)
    aviso = st.session_state.pop("wl_aviso", None)
    if mensagem:
        st.success(mensagem)
    if aviso:
        st.warning(aviso)

    familia = [item for item in itens if item["responsavel"] in responsaveis]
    desejados = [item for item in familia if item["status"] == "desejado"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Desejos na lista", len(desejados))
    c2.metric("Valor dos desejos", moeda(sum((Decimal(str(item["valor"])) for item in desejados), Decimal(0))))
    c3.metric("Conquistas", sum(item["status"] == "comprado" for item in familia))
    st.caption("O resumo considera o filtro de responsável. Desejos e conquistas não entram no total de despesas.")

    with st.expander("＋ Novo desejo", expanded=not itens):
        mostrar_editor(repo)

    c1, c2, c3 = st.columns([2, 1, 1])
    busca = c1.text_input("Buscar na lista", placeholder="Nome ou descrição", key="wl_busca").strip().casefold()
    status = c2.selectbox("Mostrar", ["Desejados", "Comprados", "Todos"], key="wl_status")
    ordem = c3.selectbox("Ordenar", ["Mais recentes", "Menor preço", "Maior preço", "Nome"], key="wl_ordem")
    if st.button("Atualizar lista", key="wl_atualizar"):
        st.rerun()
    visiveis = [item for item in familia
                if (status == "Todos" or item["status"] == ("desejado" if status == "Desejados" else "comprado"))
                and (not busca or busca in f"{item['nome']} {item['descricao']}".casefold())]
    if ordem in ("Menor preço", "Maior preço"):
        visiveis.sort(key=lambda item: Decimal(str(item["valor"])), reverse=ordem == "Maior preço")
    elif ordem == "Nome":
        visiveis.sort(key=lambda item: item["nome"].casefold())

    editando = next((item for item in familia if item["id"] == st.session_state.get("wl_editar")), None)
    if editando:
        mostrar_editor(repo, editando)
    if not visiveis:
        st.info("Sua lista começa com uma ideia. Adicione seu primeiro desejo acima." if not itens
                else "Nenhum item com esses filtros. Ajuste a busca, o status ou os responsáveis.")
        return

    # Uma coluna mantém fotos, texto e ações legíveis também no celular.
    for item in visiveis:
        identificador = item["id"]
        with st.container(border=True):
            if item.get("foto_path"):
                try:
                    st.image(repo.url_foto(item["foto_path"]), width=320)
                except ErroWishlist as erro:
                    st.caption(str(erro))
            st.markdown(f"### {escape(item['nome'])}")
            st.markdown(f"**{moeda(item['valor'])}** · {item['responsavel']} · "
                        f"{'✅ Comprado' if item['status'] == 'comprado' else '♡ Quero comprar'}")
            if item["descricao"]:
                st.text(item["descricao"])
            c1, c2 = st.columns(2)
            if c1.button("Editar", key=f"wl_editar_{identificador}", width="stretch"):
                st.session_state["wl_editar"] = identificador
                st.rerun()
            if c2.button("Voltar para desejos" if item["status"] == "comprado" else "Marcar como comprado",
                         key=f"wl_status_{identificador}", width="stretch"):
                try:
                    repo.mudar_status(item)
                except ErroWishlist as erro:
                    st.error(str(erro))
                else:
                    concluir("Item voltou para a lista de desejos." if item["status"] == "comprado"
                             else "Conquista registrada! Cadastre a compra em Início para contabilizá-la como despesa.")
            with st.expander("Excluir item"):
                confirmado = st.checkbox("Excluir este desejo e sua foto definitivamente",
                                          key=f"wl_confirmar_{identificador}")
                if st.button("Excluir definitivamente", disabled=not confirmado,
                             key=f"wl_excluir_{identificador}"):
                    try:
                        aviso = repo.excluir(item)
                    except ErroWishlist as erro:
                        st.error(str(erro))
                    else:
                        concluir("Item excluído da lista.", aviso)
