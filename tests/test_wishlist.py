import unittest
from copy import deepcopy
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

import streamlit as st
from PIL import Image
from streamlit.testing.v1 import AppTest

from wishlist import BUCKET, LIMITE_FOTO, ErroWishlist, WishlistRepositorio, preparar_foto, validar_item


def foto_png():
    saida = BytesIO()
    Image.new("RGBA", (1800, 900), (0, 120, 255, 80)).save(saida, format="PNG")
    return saida.getvalue()


class BancoFalso:
    def __init__(self):
        self.tabelas = {"despesas": [], "wishlist_itens": []}
        self.arquivos = {}
        self.eventos = []
        self.falhar_gravacao = False
        self.falhar_upload = False
        self.falhar_limpeza = False
        self.falhar_leitura = False
        self.falhar_url = False
        self.storage = SimpleNamespace(from_=self.bucket)

    def bucket(self, nome):
        assert nome == BUCKET
        return self

    def table(self, nome):
        return ConsultaFalsa(self, nome)

    def rpc(self, *_args):
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=0))

    def upload(self, caminho, conteudo, file_options):
        if self.falhar_upload:
            raise RuntimeError("falha de upload")
        self.arquivos[caminho] = conteudo
        self.eventos.append(("upload", caminho))
        assert file_options["content-type"] == "image/jpeg"
        assert file_options["upsert"] == "false"

    def remove(self, caminhos):
        if self.falhar_limpeza:
            raise RuntimeError("falha de limpeza")
        for caminho in caminhos:
            self.eventos.append(("remove", caminho))
            self.arquivos.pop(caminho, None)

    def create_signed_url(self, caminho, duracao):
        if self.falhar_url:
            raise RuntimeError("falha de URL")
        assert duracao == 3600
        return {"signedURL": f"https://example.com/{caminho}?token=temporario"}


class ConsultaFalsa:
    def __init__(self, banco, tabela):
        self.banco, self.tabela = banco, tabela
        self.operacao, self.dados, self.filtro, self.pagina = "select", None, None, None
        self.ordens = []

    def select(self, _colunas):
        return self

    def order(self, coluna, desc=False):
        self.ordens.append((coluna, desc))
        return self

    def range(self, inicio, fim):
        self.pagina = (inicio, fim)
        return self

    def insert(self, dados):
        self.operacao, self.dados = "insert", dados
        return self

    def update(self, dados):
        self.operacao, self.dados = "update", dados
        return self

    def delete(self):
        self.operacao = "delete"
        return self

    def eq(self, coluna, valor):
        self.filtro = (coluna, valor)
        return self

    def execute(self):
        dados = self.banco.tabelas[self.tabela]
        if self.operacao == "select":
            if self.banco.falhar_leitura and self.tabela == "wishlist_itens":
                raise RuntimeError("tabela não existe")
            resultado = deepcopy(dados)
            for coluna, desc in reversed(self.ordens):
                resultado.sort(key=lambda r: r.get(coluna, ""), reverse=desc)
            if self.pagina:
                resultado = resultado[self.pagina[0]:self.pagina[1] + 1]
        else:
            if self.banco.falhar_gravacao:
                raise RuntimeError("falha de gravação")
            self.banco.eventos.append((self.operacao, self.tabela))
            if self.operacao == "insert":
                registro = {"status": "desejado", "criado_em": "2026-10-06T12:00:00Z",
                            "atualizado_em": "2026-10-06T12:00:00Z", "comprado_em": None, **self.dados}
                dados.append(registro)
                resultado = [registro]
            else:
                coluna, valor = self.filtro
                resultado = [r for r in dados if r[coluna] == valor]
                if self.operacao == "update":
                    for registro in resultado:
                        registro.update(self.dados)
                else:
                    self.banco.tabelas[self.tabela] = [r for r in dados if r[coluna] != valor]
        return SimpleNamespace(data=deepcopy(resultado))


class WishlistDadosTest(unittest.TestCase):
    def setUp(self):
        self.banco = BancoFalso()
        self.repo = WishlistRepositorio(self.banco)

    def salvar(self, **opcoes):
        return self.repo.salvar("Cafeteira", 399.90, "Modelo azul", "Rafael", **opcoes)

    def test_valida_campos_e_arredonda_valor_decimal(self):
        self.assertEqual(validar_item("  Café  ", "10.005", "  Modelo  ", "Rafael")["valor"], "10.01")
        for valor in (0, -1, "NaN", "Infinity", "abc", "0.001", "10000000000"):
            with self.subTest(valor=valor), self.assertRaises(ErroWishlist):
                validar_item("Café", valor, "", "Rafael")
        for nome, descricao, responsavel in ((" ", "", "Rafael"), ("x" * 121, "", "Rafael"),
                                              ("Café", "x" * 2001, "Rafael"), ("Café", "", "Outro")):
            with self.subTest(nome=nome), self.assertRaises(ErroWishlist):
                validar_item(nome, 10, descricao, responsavel)

    def test_foto_convertida_com_limites_e_sem_exif(self):
        imagem = Image.new("RGB", (30, 20))
        exif = Image.Exif()
        exif[270] = "metadado privado"
        arquivo = BytesIO()
        imagem.save(arquivo, format="JPEG", exif=exif)
        with Image.open(BytesIO(preparar_foto(arquivo.getvalue()))) as resultado:
            self.assertEqual(len(resultado.getexif()), 0)
        with Image.open(BytesIO(preparar_foto(foto_png()))) as resultado:
            self.assertEqual(resultado.format, "JPEG")
            self.assertEqual(resultado.size, (1600, 800))
        for conteudo in (b"", b"foto falsa", b"x" * (LIMITE_FOTO + 1)):
            with self.assertRaises(ErroWishlist):
                preparar_foto(conteudo)
        with patch("wishlist.Image.open") as abrir:
            abrir.return_value.__enter__.return_value = SimpleNamespace(format="PNG", width=6000, height=5000)
            with self.assertRaisesRegex(ErroWishlist, "25 megapixels"):
                preparar_foto(b"imagem")

    def test_cadastro_sem_foto_edicao_status_e_exclusao(self):
        self.salvar()
        item = self.repo.listar()[0]
        self.assertIsNone(item["foto_path"])
        self.repo.salvar("Nova cafeteira", 450, "", "Nathalia", item=item)
        item = self.repo.listar()[0]
        self.assertEqual(item["nome"], "Nova cafeteira")
        self.repo.mudar_status(item)
        comprado = self.repo.listar()[0]
        self.assertEqual(comprado["status"], "comprado")
        self.assertIsNotNone(comprado["comprado_em"])
        self.repo.mudar_status(comprado)
        self.assertIsNone(self.repo.listar()[0]["comprado_em"])
        self.repo.excluir(comprado)
        self.assertEqual(self.repo.listar(), [])
        self.assertEqual(self.banco.tabelas["despesas"], [])

    def test_troca_e_remocao_da_foto_preservam_ordem(self):
        self.salvar(foto=foto_png())
        item = self.repo.listar()[0]
        antiga = item["foto_path"]
        self.assertTrue(antiga.startswith(item["id"] + "/"))
        self.banco.eventos.clear()
        self.salvar(item=item, foto=foto_png())
        self.assertEqual([acao for acao, _ in self.banco.eventos], ["upload", "update", "remove"])
        self.assertNotIn(antiga, self.banco.arquivos)
        self.salvar(item=self.repo.listar()[0], remover_foto=True)
        self.assertEqual(self.banco.arquivos, {})
        self.assertIsNone(self.repo.listar()[0]["foto_path"])

    def test_falhas_na_gravacao_e_upload_nao_apagam_foto_antiga(self):
        self.salvar(foto=foto_png())
        item = self.repo.listar()[0]
        self.banco.falhar_gravacao = True
        with self.assertRaises(ErroWishlist):
            self.salvar(item=item, foto=foto_png())
        self.assertEqual(list(self.banco.arquivos), [item["foto_path"]])
        self.assertEqual(self.repo.listar()[0], item)
        with self.assertRaises(ErroWishlist):
            self.repo.excluir(item)
        self.assertIn(item["foto_path"], self.banco.arquivos)
        self.banco.falhar_gravacao = False
        self.banco.falhar_upload = True
        with self.assertRaises(ErroWishlist):
            self.salvar(foto=foto_png())
        self.assertEqual(len(self.repo.listar()), 1)

    def test_falha_de_limpeza_informa_caminho_e_url_e_temporaria(self):
        self.salvar(foto=foto_png())
        item = self.repo.listar()[0]
        self.assertIn("token=temporario", self.repo.url_foto(item["foto_path"]))
        self.banco.falhar_limpeza = True
        aviso = self.repo.excluir(item)
        self.assertIn(item["foto_path"], aviso)
        self.assertEqual(self.repo.listar(), [])

    def test_listagem_nao_trunca_mais_de_mil_itens(self):
        self.banco.tabelas["wishlist_itens"] = [{"id": str(uuid4()), "criado_em": "2026-10-06"} for _ in range(1002)]
        self.assertEqual(len(self.repo.listar()), 1002)


class WishlistInterfaceTest(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def app(self):
        return AppTest.from_file(Path(__file__).resolve().parents[1] / "supabase_financeiro.py", default_timeout=30)

    def pagina_wishlist(self, app):
        app.run()
        next(r for r in app.radio if r.label == "Navegação").set_value("♡ Lista de desejos").run()
        self.assertFalse(app.exception)

    def preencher(self, app, nome, valor):
        app.text_input(key="wl_novo_0_nome").input(nome)
        app.number_input(key="wl_novo_0_valor").set_value(valor)
        app.button(key="wl_novo_0_salvar").click().run()

    def test_fluxo_completo_e_filtro_por_responsavel(self):
        banco = BancoFalso()
        with patch("supabase.create_client", return_value=banco), patch("wishlist_ui.create_client", return_value=banco), \
                patch("wishlist_ui.obter_chave_servidor", return_value="chave-de-teste"):
            app = self.app()
            self.pagina_wishlist(app)
            self.preencher(app, "Cafeteira", 399.90)
            self.assertFalse(app.exception)
            self.assertEqual(len(banco.tabelas["wishlist_itens"]), 1)
            self.assertEqual(app.text_input(key="wl_novo_1_nome").value, "")
            item = banco.tabelas["wishlist_itens"][0]
            ident = item["id"]
            app.button(key=f"wl_editar_{ident}").click().run()
            app.text_input(key=f"wl_{ident}_0_nome").input("Cafeteira azul")
            app.button(key=f"wl_{ident}_0_salvar").click().run()
            self.assertEqual(item["nome"], "Cafeteira azul")
            app.sidebar.multiselect[0].set_value(["Nathalia"]).run()
            self.assertEqual(app.metric[0].value, "0")
            self.assertFalse(any("Cafeteira azul" in texto.value for texto in app.markdown))
            app.sidebar.multiselect[0].set_value(["Rafael", "Nathalia"]).run()
            app.button(key=f"wl_status_{ident}").click().run()
            self.assertEqual(item["status"], "comprado")
            self.assertEqual(app.metric[0].value, "0")
            app.selectbox(key="wl_status").set_value("Comprados").run()
            app.checkbox(key=f"wl_confirmar_{ident}").check().run()
            app.button(key=f"wl_excluir_{ident}").click().run()
            self.assertEqual(banco.tabelas["wishlist_itens"], [])
            self.assertEqual(banco.tabelas["despesas"], [])
            self.assertFalse(app.exception)

    def test_camera_conecta_foto_ao_item(self):
        banco = BancoFalso()
        with patch("supabase.create_client", return_value=banco), patch("wishlist_ui.create_client", return_value=banco), \
                patch("wishlist_ui.obter_chave_servidor", return_value="chave-de-teste"), \
                patch("wishlist_ui.st.camera_input", return_value=BytesIO(foto_png())):
            app = self.app()
            self.pagina_wishlist(app)
            app.radio(key="wl_novo_0_origem").set_value("Tirar foto").run()
            self.preencher(app, "Bicicleta", 1200)
            self.assertFalse(app.exception)
            self.assertEqual(len(banco.arquivos), 1)
            self.assertIn(banco.tabelas["wishlist_itens"][0]["foto_path"], banco.arquivos)

    def test_galeria_invalida_nao_quebra_pagina_e_permite_corrigir(self):
        banco = BancoFalso()
        with patch("supabase.create_client", return_value=banco), patch("wishlist_ui.create_client", return_value=banco), \
                patch("wishlist_ui.obter_chave_servidor", return_value="chave-de-teste"), \
                patch("wishlist_ui.st.file_uploader", return_value=BytesIO(b"nao-e-uma-foto")) as upload:
            app = self.app()
            self.pagina_wishlist(app)
            app.radio(key="wl_novo_0_origem").set_value("Enviar imagem").run()
            self.assertFalse(app.exception)
            self.assertTrue(app.error)
            self.preencher(app, "Viagem", 2500)
            self.assertEqual(banco.tabelas["wishlist_itens"], [])
            upload.return_value = BytesIO(foto_png())
            app.button(key="wl_novo_0_salvar").click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(banco.arquivos), 1)

    def test_cancelar_edicao_descarta_alteracoes(self):
        banco = BancoFalso()
        WishlistRepositorio(banco).salvar("Cafeteira", 399.90, "", "Rafael")
        ident = banco.tabelas["wishlist_itens"][0]["id"]
        with patch("supabase.create_client", return_value=banco), patch("wishlist_ui.create_client", return_value=banco), \
                patch("wishlist_ui.obter_chave_servidor", return_value="chave-de-teste"):
            app = self.app()
            self.pagina_wishlist(app)
            app.button(key=f"wl_editar_{ident}").click().run()
            app.text_input(key=f"wl_{ident}_0_nome").input("Alteração descartada")
            app.button(key=f"wl_{ident}_0_cancelar").click().run()
            app.button(key=f"wl_editar_{ident}").click().run()
            self.assertEqual(app.text_input(key=f"wl_{ident}_1_nome").value, "Cafeteira")

    def test_erros_preservam_campos_e_configuracao_faltante_nao_quebra_app(self):
        banco = BancoFalso()
        with patch("supabase.create_client", return_value=banco), patch("wishlist_ui.create_client", return_value=banco), \
                patch("wishlist_ui.obter_chave_servidor", return_value="chave-de-teste"):
            app = self.app()
            self.pagina_wishlist(app)
            self.preencher(app, "Cafeteira", 0)
            self.assertTrue(app.error)
            self.assertEqual(app.text_input(key="wl_novo_0_nome").value, "Cafeteira")
            banco.falhar_gravacao = True
            self.preencher(app, "Cafeteira", 400)
            self.assertTrue(app.error)
            self.assertEqual(app.number_input(key="wl_novo_0_valor").value, 400)
            banco.falhar_leitura = True
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any("migração" in erro.value for erro in app.error))
        with patch("supabase.create_client", return_value=BancoFalso()), \
                patch("wishlist_ui.obter_chave_servidor", return_value=None):
            app = self.app()
            self.pagina_wishlist(app)
            self.assertTrue(any("SUPABASE_WISHLIST_KEY" in aviso.value for aviso in app.info))


if __name__ == "__main__":
    unittest.main()
