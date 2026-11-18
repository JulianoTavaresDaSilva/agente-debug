"""Verifica o ciclo e a validação do diagnóstico sem rede."""

import json
from unittest.mock import Mock, patch

from agente import investigar
from configuracao import Configuracao
from ferramentas import FerramentasProjeto
from tests.apoio import CasoTemporario, chamada, diagnostico, resposta


class TestAgente(CasoTemporario):
    def setUp(self):
        super().setUp()
        self.arquivo("codigo.py", "valor = 1\nsegunda = 2\n")
        self.config = Configuracao()
        self.ferramentas = FerramentasProjeto(self.raiz, self.config)
        self.cliente = Mock()
        self.cliente.simulacao = False

    def executar(self, respostas, config=None):
        self.cliente.interactions.create.side_effect = respostas
        return investigar(self.cliente, "Manual", "Erro", self.ferramentas, config or self.config)

    def test_le_codigo_e_valida_diagnostico(self):
        resultado = self.executar([
            resposta([chamada()], estado="requires_action"),
            resposta(texto=json.dumps(diagnostico())),
        ])
        self.assertEqual(resultado.estado, "analise_produzida")
        self.assertEqual((resultado.consultas, resultado.ferramentas), (2, 1))
        self.assertEqual(resultado.leituras[0].caminho, "codigo.py")
        consultas = self.cliente.interactions.create.call_args_list
        self.assertEqual(consultas[1].kwargs["previous_interaction_id"], "r1")
        retorno = consultas[1].kwargs["input"][0]
        self.assertEqual(retorno["call_id"], "c1")
        self.assertIn("1: valor = 1", json.loads(retorno["result"][0]["text"])["conteudo"])
        for consulta in consultas:
            self.assertFalse(consulta.kwargs["automatic_continuation"])

    def test_devolve_resultados_em_lote(self):
        resultado = self.executar([
            resposta([chamada(identificador="a"), chamada(identificador="b")]),
            resposta(texto=json.dumps(diagnostico())),
        ])
        self.assertEqual(resultado.ferramentas, 2)
        retorno = self.cliente.interactions.create.call_args.kwargs["input"]
        self.assertEqual([r["call_id"] for r in retorno], ["a", "b"])

    def test_recusa_citacao_de_arquivo_ou_linha_nao_lidos(self):
        for alteracao in ({"caminho": "inventado.py"}, {"linha_fim": 99}, {"linha_inicio": True}):
            dados = diagnostico()
            dados["evidencias"][0].update(alteracao)
            with self.subTest(alteracao=alteracao):
                retorno = self.executar([resposta([chamada()]), resposta(texto=json.dumps(dados))])
                self.assertEqual(retorno.estado, "parcial")
                self.assertTrue(retorno.rascunho)

    def test_nao_confunde_erro_api_com_conclusao(self):
        for estado in ("failed", "cancelled", "incomplete", "budget_exceeded", "queued", None, {"invalido": True}):
            with self.subTest(estado=estado):
                retorno = self.executar([resposta(estado=estado)])
                self.assertIn(retorno.estado, {"falha", "parcial"})
                self.assertIsNone(retorno.diagnostico)

    def test_resposta_vazia_e_json_invalido_sao_parciais(self):
        for texto in ("", "Texto livre.", "{}", "[]"):
            with self.subTest(texto=texto):
                self.assertEqual(self.executar([resposta(texto=texto)]).estado, "parcial")

    def test_informacao_insuficiente_e_explicita(self):
        retorno = self.executar([resposta(texto=json.dumps(diagnostico("informacao_insuficiente")))])
        self.assertEqual(retorno.estado, "informacao_insuficiente")
        self.assertTrue(retorno.diagnostico["pendencias"])

    def test_reserva_ultima_consulta_sem_ferramentas(self):
        config = Configuracao(max_consultas=2)
        resultado = self.executar([resposta([chamada()]), resposta(texto=json.dumps(diagnostico()))], config)
        self.assertEqual(resultado.estado, "analise_produzida")
        self.assertEqual(self.cliente.interactions.create.call_args.kwargs["tools"], [])

    def test_interrompe_pedidos_no_limite_e_preserva_leituras(self):
        config = Configuracao(max_consultas=2)
        resultado = self.executar([resposta([chamada()]), resposta([chamada()])], config)
        self.assertEqual(resultado.estado, "parcial")
        self.assertEqual(len(resultado.leituras), 1)
        self.assertEqual(resultado.ferramentas, 1)

    def test_recusa_excesso_de_ferramentas_antes_de_executar(self):
        retorno = self.executar([resposta([chamada(identificador=str(i)) for i in range(6)])])
        self.assertEqual(retorno.ferramentas, 0)
        self.assertEqual(retorno.estado, "parcial")

    def test_recusa_ids_ausentes_ou_repetidos(self):
        for passos in ([chamada(identificador=None)], [chamada(), chamada()]):
            with self.subTest(passos=passos):
                self.assertEqual(self.executar([resposta(passos)]).ferramentas, 0)

    def test_erro_ferramenta_e_devolvido_sem_falsa_evidencia(self):
        retorno = self.executar([
            resposta([chamada(argumentos={"caminho": "ausente.py"})]),
            resposta(texto=json.dumps(diagnostico("informacao_insuficiente"))),
        ])
        self.assertEqual(retorno.leituras, [])
        resultado = self.cliente.interactions.create.call_args.kwargs["input"][0]
        self.assertFalse(json.loads(resultado["result"][0]["text"])["sucesso"])

    def test_falha_continuacao_preserva_evidencias(self):
        retorno = self.executar([resposta([chamada()]), RuntimeError("falha")])
        self.assertEqual(retorno.estado, "falha")
        self.assertEqual(len(retorno.leituras), 1)

    def test_orcamento_de_tempo_interrompe_sem_api(self):
        with patch("agente.time.monotonic", side_effect=[0, 121]):
            retorno = self.executar([])
        self.assertEqual(retorno.consultas, 0)
        self.assertEqual(retorno.estado, "parcial")

    def test_limite_de_contexto_forca_conclusao(self):
        self.ferramentas = FerramentasProjeto(self.raiz, Configuracao(max_contexto=1))
        retorno = self.executar([
            resposta([chamada()]),
            resposta(texto=json.dumps(diagnostico("informacao_insuficiente"))),
        ])
        self.assertEqual(retorno.leituras, [])
        self.assertEqual(self.cliente.interactions.create.call_args.kwargs["tools"], [])

    def test_resposta_apos_orcamento_e_grande_sao_parciais(self):
        with patch("agente.time.monotonic", side_effect=[0, 0, 121]):
            retorno = self.executar([resposta(texto="resposta tardia")])
        self.assertEqual(retorno.estado, "parcial")
        self.assertEqual(retorno.rascunho, "resposta tardia")
        retorno = self.executar([resposta(texto="x" * 21)], Configuracao(max_contexto=20))
        self.assertEqual(retorno.estado, "parcial")
        self.assertEqual(len(retorno.rascunho), 20)
