"""Verificação determinística das correções de referência, fora do agente."""

import runpy

from configuracao import PASTA_PROJETO
from demonstracao import ClienteDemonstracao, pasta_caso
from agente import investigar
from ferramentas import FerramentasProjeto
from tests.apoio import CasoTemporario


class TestExemplos(CasoTemporario):
    def referencia(self, nome):
        return runpy.run_path(str(pasta_caso(nome) / "referencia.py"))

    def test_media_rejeita_lista_vazia_e_calcula_media(self):
        calcular = self.referencia("media")["calcular_media"]
        self.assertEqual(calcular([2, 4, 6]), 4)
        self.assertEqual(calcular([5]), 5)
        with self.assertRaises(ValueError):
            calcular([])

    def test_taxa_numerica_e_validacao_de_texto_invalido(self):
        calcular = self.referencia("tipos")["adicionar_taxa"]
        self.assertEqual(calcular(100.0, "10"), 110.0)
        self.assertEqual(calcular(100, 10), 110.0)
        with self.assertRaises(ValueError):
            calcular(100, "abc")

    def test_percentual_e_casos_limite(self):
        calcular = self.referencia("multiarquivo")["total_com_desconto"]
        for percentual, esperado in ((0, 100), (10, 90), (100, 0)):
            with self.subTest(percentual=percentual):
                self.assertEqual(calcular(100, percentual), esperado)

    def test_simulacao_multiarquivo_exige_as_duas_leituras(self):
        pasta = pasta_caso("multiarquivo")
        ferramentas = FerramentasProjeto(pasta / "projeto")
        retorno = investigar(ClienteDemonstracao("multiarquivo"), "Manual", "Erro", ferramentas)
        self.assertTrue(retorno.simulacao)
        self.assertEqual(retorno.estado, "analise_produzida")
        self.assertEqual({t.caminho for t in retorno.leituras}, {"app.py", "dominio/descontos.py"})

    def test_referencias_nao_sao_oferecidas_ao_modelo(self):
        for nome in ("media", "tipos", "multiarquivo", "insuficiente"):
            with self.subTest(nome=nome):
                arquivos = FerramentasProjeto(pasta_caso(nome) / "projeto").listar()["arquivos"]
                self.assertNotIn("referencia.py", arquivos)
