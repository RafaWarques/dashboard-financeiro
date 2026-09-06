import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class SupabaseFalso:
    def __init__(self):
        self.dados = []

    def table(self, _nome):
        return ConsultaFalsa(self)


class ConsultaFalsa:
    def __init__(self, cliente):
        self.cliente = cliente
        self.nova_despesa = None

    def select(self, _colunas):
        return self

    def insert(self, nova_despesa):
        self.nova_despesa = nova_despesa
        return self

    def execute(self):
        if self.nova_despesa is not None:
            registro = {"id": len(self.cliente.dados) + 1, **self.nova_despesa}
            self.cliente.dados.append(registro)
            return SimpleNamespace(data=[registro])
        return SimpleNamespace(data=list(self.cliente.dados))


class CadastroRepetidoTest(unittest.TestCase):
    def test_salva_duas_despesas_na_mesma_sessao(self):
        banco = SupabaseFalso()
        with patch("supabase.create_client", return_value=banco):
            caminho_app = Path(__file__).resolve().parents[1] / "supabase_financeiro.py"
            app = AppTest.from_file(caminho_app, default_timeout=30)
            app.run()

            descricao = next(campo for campo in app.text_input if campo.label == "Descrição")
            descricao.input("Primeira compra")
            next(botao for botao in app.button if botao.label == "Salvar despesa").click().run()
            self.assertEqual(len(banco.dados), 1)

            # Representa os campos preenchidos pela interpretação do segundo áudio.
            app.session_state["voz_transcricao"] = "Comprei outro lanche por 25 reais"
            app.session_state["form_descricao"] = "Outro lanche"
            app.session_state["form_categoria"] = "Alimentação"
            app.session_state["form_valor"] = 25.0
            app.session_state["form_parcelas"] = 1
            app.session_state["form_responsavel"] = "Rafael"
            app.run()

            descricao = next(campo for campo in app.text_input if campo.label == "Descrição")
            self.assertEqual(descricao.value, "Outro lanche")
            next(botao for botao in app.button if botao.label == "Salvar despesa").click().run()

            self.assertEqual(len(banco.dados), 2)
            self.assertEqual(banco.dados[1]["descricao"], "Outro lanche")
            self.assertFalse(any("descrição não pode" in erro.value.lower() for erro in app.error))


if __name__ == "__main__":
    unittest.main()
