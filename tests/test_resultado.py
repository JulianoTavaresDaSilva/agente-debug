"""Contrato e relatório: referências verificáveis e preservação de arquivos."""

import copy
import json

from configuracao import Configuracao, ErroConfiguracao
from ferramentas import TrechoArquivo
from resultado import ResultadoInvestigacao, gerar_markdown, salvar_relatorio, validar_diagnostico
from tests.apoio import CasoTemporario, diagnostico


class TestResultado(CasoTemporario):
    def setUp(self):
        super().setUp()
        self.trecho = TrechoArquivo("codigo.py", 1, ("valor = 1\n",))
        self.dados = diagnostico()

    def test_valida_referencias_e_tipos_do_contrato(self):
        self.assertEqual(validar_diagnostico(json.dumps(self.dados), [self.trecho]), self.dados)
        for campo, valor in (
            ("estado", "solucao_verificada"), ("problema", 1),
            ("verificacao", "executar"), ("pendencias", [None]),
            ("evidencias", []), ("causa_provavel", ""),
        ):
            dados = copy.deepcopy(self.dados)
            dados[campo] = valor
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                validar_diagnostico(json.dumps(dados), [self.trecho])

    def test_insuficiencia_exige_pendencias(self):
        dados = diagnostico("informacao_insuficiente")
        dados["pendencias"] = []
        with self.assertRaises(ValueError):
            validar_diagnostico(json.dumps(dados), [])

    def test_contrato_aceita_bloco_json_mas_nao_campos_extras(self):
        texto = "```json\n" + json.dumps(self.dados) + "\n```"
        self.assertEqual(validar_diagnostico(texto, [self.trecho]), self.dados)
        self.dados["campo_inventado"] = True
        with self.assertRaises(ValueError):
            validar_diagnostico(json.dumps(self.dados), [self.trecho])

    def test_relatorio_inclui_codigo_real_e_marca_simulacao(self):
        resultado = ResultadoInvestigacao(
            "analise_produzida", "Correção sugerida.", "simulacao-local",
            diagnostico=self.dados, leituras=[self.trecho], simulacao=True,
        )
        texto = gerar_markdown(resultado)
        for esperado in ("SIMULAÇÃO LOCAL", "codigo.py:1-1", "valor = 1", "Verificação sugerida", "não alterou"):
            self.assertIn(esperado, texto)
        arquivo = self.raiz / "saida" / "analise.md"
        salvar_relatorio(arquivo, resultado)
        self.assertEqual(arquivo.read_text(encoding="utf-8"), texto)
        with self.assertRaises(FileExistsError):
            salvar_relatorio(arquivo, resultado)
        self.assertEqual(arquivo.read_text(encoding="utf-8"), texto)

    def test_relatorio_parcial_preserva_leituras_e_rascunho(self):
        resultado = ResultadoInvestigacao("parcial", "Limite atingido.", "modelo", leituras=[self.trecho], rascunho="Resposta não validada.")
        texto = gerar_markdown(resultado)
        self.assertIn("codigo.py:1-1", texto)
        self.assertIn("Resposta não validada.", texto)
        self.assertIn("valor = 1", texto)
        self.assertIn("Não determinada.", texto)

    def test_configuracao_rejeita_tipos_e_numeros_invalidos(self):
        for campos in ({"modelo": ""}, {"max_consultas": True}, {"max_entrada": -1}, {"max_linhas": 1.5}, {"timeout": float("nan")}):
            with self.subTest(campos=campos), self.assertRaises(ErroConfiguracao):
                Configuracao(**campos)
