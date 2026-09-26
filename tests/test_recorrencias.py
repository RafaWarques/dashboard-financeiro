import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import streamlit as st
from streamlit.testing.v1 import AppTest


class SupabaseFalso:
    def __init__(self):
        self.tabelas = {"despesas": [], "despesas_recorrentes": []}

    def table(self, nome):
        return ConsultaFalsa(self, nome)

    def rpc(self, _nome, _parametros):
        return SimpleNamespace(execute=lambda: SimpleNamespace(data=0))


class ConsultaFalsa:
    def __init__(self, cliente, tabela):
        self.cliente = cliente
        self.tabela = tabela
        self.novo_registro = None
        self.alteracoes = None
        self.filtro = None

    def select(self, _colunas):
        return self

    def order(self, _coluna, **_opcoes):
        return self

    def insert(self, registro):
        self.novo_registro = registro
        return self

    def update(self, alteracoes):
        self.alteracoes = alteracoes
        return self

    def eq(self, coluna, valor):
        self.filtro = (coluna, valor)
        return self

    def execute(self):
        dados = self.cliente.tabelas[self.tabela]
        if self.novo_registro is not None:
            registro = {"id": len(dados) + 1, **self.novo_registro}
            dados.append(registro)
            return SimpleNamespace(data=[registro])
        if self.alteracoes is not None:
            coluna, valor = self.filtro
            alterados = []
            for registro in dados:
                if registro[coluna] == valor:
                    registro.update(self.alteracoes)
                    alterados.append(registro)
            return SimpleNamespace(data=alterados)
        return SimpleNamespace(data=list(dados))


class RecorrenciasTest(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()

    def test_cadastra_assinatura_e_permite_desativar(self):
        banco = SupabaseFalso()
        with patch("supabase.create_client", return_value=banco):
            caminho_app = Path(__file__).resolve().parents[1] / "supabase_financeiro.py"
            app = AppTest.from_file(caminho_app, default_timeout=30)
            app.run()

            tipo = next(campo for campo in app.radio if campo.label == "Tipo de despesa")
            tipo.set_value("Assinatura").run()
            next(campo for campo in app.text_input if campo.label == "Descrição").input("Streaming")
            next(campo for campo in app.number_input if campo.label == "Valor mensal (R$)").set_value(39.90)
            next(botao for botao in app.button if botao.label == "Salvar despesa").click().run()

            self.assertEqual(len(banco.tabelas["despesas_recorrentes"]), 1)
            self.assertEqual(banco.tabelas["despesas_recorrentes"][0]["tipo"], "assinatura")
            self.assertTrue(banco.tabelas["despesas_recorrentes"][0]["ativa"])
            self.assertEqual(banco.tabelas["despesas"], [])

            navegacao = next(campo for campo in app.radio if campo.label == "Navegação")
            navegacao.set_value("🔁 Fixas e assinaturas").run()
            next(
                botao for botao in app.button
                if botao.label == "Desativar cobrança selecionada"
            ).click().run()

            self.assertFalse(banco.tabelas["despesas_recorrentes"][0]["ativa"])

    def test_dashboards_abrem_com_despesas_comuns_e_recorrentes(self):
        hoje = date.today().isoformat()
        banco = SupabaseFalso()
        banco.tabelas["despesas_recorrentes"] = [{
            "id": 1,
            "tipo": "assinatura",
            "data_inicio": hoje,
            "dia_cobranca": date.today().day,
            "categoria": "Lazer",
            "descricao": "Streaming",
            "valor": 39.90,
            "forma_pagamento": "Não informado",
            "responsavel": "Rafael",
            "ativa": True,
            "desativada_em": None,
        }]
        banco.tabelas["despesas"] = [
            {
                "id": 1, "data_despesa": hoje, "categoria": "Casa",
                "descricao": "Mercado", "valor": 180.0,
                "forma_pagamento": "Não informado", "parcelas": 1,
                "responsavel": "Rafael", "semana": 1,
                "despesa_recorrente_id": None, "competencia": None,
            },
            {
                "id": 2, "data_despesa": hoje, "categoria": "Lazer",
                "descricao": "Streaming", "valor": 39.90,
                "forma_pagamento": "Não informado", "parcelas": 1,
                "responsavel": "Rafael", "semana": 1,
                "despesa_recorrente_id": 1, "competencia": hoje[:8] + "01",
            },
            {
                "id": 3, "data_despesa": hoje, "categoria": "Outros",
                "descricao": "Compra parcelada", "valor": 300.0,
                "forma_pagamento": "Não informado", "parcelas": 3,
                "responsavel": "Rafael", "semana": 1,
                "despesa_recorrente_id": None, "competencia": None,
            },
        ]

        with patch("supabase.create_client", return_value=banco):
            caminho_app = Path(__file__).resolve().parents[1] / "supabase_financeiro.py"
            app = AppTest.from_file(caminho_app, default_timeout=30)
            app.run()

            navegacao = next(campo for campo in app.radio if campo.label == "Navegação")
            navegacao.set_value("📊 Visão mensal").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(metrica.label == "Total do mês" for metrica in app.metric))

            navegacao = next(campo for campo in app.radio if campo.label == "Navegação")
            navegacao.set_value("🧾 Despesas").run()
            self.assertFalse(app.exception)
            self.assertTrue(any(metrica.label == "Total filtrado" for metrica in app.metric))


if __name__ == "__main__":
    unittest.main()
