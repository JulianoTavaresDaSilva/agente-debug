"""Investiga um arquivo usando o SDK real sobre transporte HTTP fictício."""

import json
import httpx

from agente import investigar
from cliente_gemini import criar_cliente
from configuracao import Configuracao
from ferramentas import FerramentasProjeto
from tests.apoio import CasoTemporario, diagnostico


class TestPipeline(CasoTemporario):
    def test_sdk_ferramenta_continuacao_e_diagnostico(self):
        self.arquivo("codigo.py")
        requisicoes = []

        def handler(request):
            corpo = json.loads(request.content)
            requisicoes.append(corpo)
            if len(requisicoes) == 1:
                return httpx.Response(200, json={
                    "id": "primeira", "status": "requires_action", "steps": [{
                        "type": "function_call", "id": "ler-1", "name": "ler_arquivo",
                        "arguments": {"caminho": "codigo.py"},
                    }],
                })
            return httpx.Response(200, json={
                "id": "segunda", "status": "completed", "steps": [{
                    "type": "model_output", "content": [{"type": "text", "text": json.dumps(diagnostico())}],
                }],
            })

        with httpx.Client(transport=httpx.MockTransport(handler)) as http:
            cliente = criar_cliente(Configuracao(), chave="chave-ficticia", http_client=http)
            try:
                retorno = investigar(cliente, "Manual fictício", "Erro fictício", FerramentasProjeto(self.raiz))
            finally:
                cliente.close()
        self.assertEqual(retorno.estado, "analise_produzida")
        self.assertEqual(len(requisicoes), 2)
        self.assertEqual(requisicoes[1]["previous_interaction_id"], "primeira")
        self.assertEqual(requisicoes[1]["input"][0]["call_id"], "ler-1")
        self.assertEqual(retorno.leituras[0].conteudo, "valor = 1\n")
