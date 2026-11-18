"""Exercita o SDK real com HTTP simulado, incluindo a contagem de tentativas."""

import os
import unittest
from unittest.mock import patch

import httpx
from google import genai

from cliente_gemini import FalhaConsulta, consultar_gemini, criar_cliente, obter_chave
from configuracao import Configuracao, ErroConfiguracao


class TestClienteGemini(unittest.TestCase):
    def consultar(self, handler):
        transporte = httpx.Client(transport=httpx.MockTransport(handler))
        self.addCleanup(transporte.close)
        cliente = criar_cliente(Configuracao(), chave="chave-ficticia-de-teste", http_client=transporte)
        self.addCleanup(cliente.close)
        return consultar_gemini(
            cliente, model="gemini-3.6-flash", input="Contexto fictício.",
            timeout=1.0, automatic_continuation=False,
        )

    def test_codigos_http_nao_repetem_consulta(self):
        for codigo, mensagem in ((401, "Autenticação"), (403, "Autenticação"), (404, "Modelo"), (429, "Cota"), (503, "indisponível")):
            chamadas = []
            def handler(request):
                chamadas.append(request)
                return httpx.Response(codigo, json={"error": {"code": codigo, "message": "SEGREDO-NAO-EXIBIR"}}, headers={"Retry-After": "3600"})
            with self.subTest(codigo=codigo), patch("time.sleep", side_effect=AssertionError("Repetição indevida.")):
                with self.assertRaises(FalhaConsulta) as falha:
                    self.consultar(handler)
                self.assertEqual(len(chamadas), 1)
                self.assertIn(mensagem, str(falha.exception))
                self.assertNotIn("SEGREDO-NAO-EXIBIR", str(falha.exception))

    def test_timeout_e_conexao_sem_repeticao(self):
        for tipo, mensagem in ((httpx.ReadTimeout, "Tempo limite"), (httpx.ConnectError, "conexão")):
            chamadas = []
            def handler(request):
                chamadas.append(request)
                raise tipo("NAO-EXIBIR", request=request)
            with self.subTest(tipo=tipo), patch("time.sleep", side_effect=AssertionError("Repetição indevida.")):
                with self.assertRaises(FalhaConsulta) as falha:
                    self.consultar(handler)
                self.assertEqual(len(chamadas), 1)
                self.assertIn(mensagem, str(falha.exception))

    def test_resposta_do_sdk_tem_texto_e_estado(self):
        def handler(request):
            self.assertIn("/v1/interactions", str(request.url))
            return httpx.Response(200, json={
                "id": "resposta-teste", "status": "completed",
                "steps": [{"type": "model_output", "content": [{"type": "text", "text": "Resposta fictícia."}]}],
            })
        resultado = self.consultar(handler)
        self.assertEqual(resultado.status, "completed")
        self.assertEqual(resultado.output_text, "Resposta fictícia.")

    def test_chave_ausente_e_precedencia(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ErroConfiguracao):
                obter_chave()
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "google-ficticia", "GEMINI_API_KEY": "gemini-ficticia"}, clear=True):
            self.assertEqual(obter_chave(), "google-ficticia")

    def test_sdk_antigo_e_recusado_antes_de_criar_cliente(self):
        with patch.object(genai, "__version__", "2.31.0"), patch.object(genai, "Client") as criar:
            with self.assertRaises(ErroConfiguracao):
                criar_cliente(Configuracao(), chave="ficticia")
        criar.assert_not_called()
