import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from despesa_voz import (
    DespesaInterpretada,
    interpretar_despesa,
    interpretar_despesa_com_ia,
)


class InterpretarDespesaTest(unittest.TestCase):
    def test_descricao_valor_e_categoria(self):
        despesa = interpretar_despesa("Comprei almoço por 42 reais no cartão")

        self.assertEqual(despesa["descricao"], "Almoço")
        self.assertEqual(despesa["valor"], 42.0)
        self.assertEqual(despesa["categoria"], "Alimentação")

    def test_valor_por_extenso_nao_vai_para_descricao(self):
        despesa = interpretar_despesa("Comprei um lanche de trinta reais")

        self.assertEqual(despesa["descricao"], "Lanche")
        self.assertEqual(despesa["valor"], 30.0)
        self.assertEqual(despesa["categoria"], "Alimentação")

    def test_valor_brasileiro(self):
        despesa = interpretar_despesa("Gastei R$ 1.250,90 em uma viagem")

        self.assertEqual(despesa["descricao"], "Viagem")
        self.assertEqual(despesa["valor"], 1250.90)
        self.assertEqual(despesa["categoria"], "Lazer")

    def test_valor_sem_milhar(self):
        despesa = interpretar_despesa("Comprei um celular por 1250 reais")

        self.assertEqual(despesa["valor"], 1250.0)

    def test_detalhes_opcionais(self):
        despesa = interpretar_despesa(
            "Parcelei um jogo por 300 reais em 3 vezes, foi o Rafael"
        )

        self.assertEqual(despesa["parcelas"], 3)
        self.assertEqual(despesa["responsavel"], "Rafael")
        self.assertEqual(despesa["categoria"], "Lazer")

    def test_parcelas_por_extenso(self):
        despesa = interpretar_despesa("Parcelei um jogo por 90 reais em três vezes")

        self.assertEqual(despesa["parcelas"], 3)
        self.assertEqual(despesa["categoria"], "Lazer")

    def test_resumo_contextual_do_whey(self):
        despesa = interpretar_despesa("Comprei um Whey na academia por 140 reais")

        self.assertEqual(despesa["descricao"], "Whey para dieta")
        self.assertEqual(despesa["valor"], 140.0)
        self.assertEqual(despesa["categoria"], "Alimentação")

    def test_categoria_transporte(self):
        despesa = interpretar_despesa("Gastei 50 reais de gasolina")

        self.assertEqual(despesa["categoria"], "Transporte")

    def test_categoria_casa(self):
        despesa = interpretar_despesa("Paguei 120 reais de energia")

        self.assertEqual(despesa["categoria"], "Casa")

    def test_interpretacao_inteligente_usa_saida_estruturada(self):
        saida = DespesaInterpretada(
            descricao="Jogo",
            valor=180.0,
            categoria="Lazer",
            parcelas=3,
            responsavel=None,
        )
        cliente = Mock()
        cliente.responses.parse.return_value = SimpleNamespace(output_parsed=saida)

        with patch("openai.OpenAI", return_value=cliente):
            despesa = interpretar_despesa_com_ia(
                "Parcelei um jogo de 180 reais em 3 vezes", "chave-de-teste"
            )

        self.assertEqual(despesa["descricao"], "Jogo")
        self.assertEqual(despesa["valor"], 180.0)
        self.assertEqual(despesa["categoria"], "Lazer")
        self.assertEqual(despesa["parcelas"], 3)
        cliente.responses.parse.assert_called_once()


if __name__ == "__main__":
    unittest.main()
