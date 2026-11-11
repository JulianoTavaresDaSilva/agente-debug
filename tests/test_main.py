"""Verifica o fluxo do agente com respostas simuladas do Gemini."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from google import genai

# Mesmo uma regressão na importação não pode solicitar entrada ou criar a API.
with patch.object(
    genai, "Client", side_effect=AssertionError("API criada na importação.")
), patch(
    "builtins.input", side_effect=AssertionError("Entrada pedida na importação.")
):
    import main as agente


def criar_chamada(nome, argumentos, identificador="chamada-1"):
    return SimpleNamespace(
        type="function_call", name=nome, arguments=argumentos, id=identificador
    )


def criar_resposta(passos=(), texto="Análise simulada.", identificador="resposta-1"):
    return SimpleNamespace(
        steps=list(passos), output_text=texto, id=identificador
    )


class TestMain(unittest.TestCase):
    def setUp(self):
        self.saida = io.StringIO()
        stdout = patch("sys.stdout", self.saida)
        stdout.start()
        self.addCleanup(stdout.stop)

        rede = patch(
            "socket.socket.connect",
            side_effect=AssertionError("Teste tentou abrir uma conexão de rede."),
        )
        rede.start()
        self.addCleanup(rede.stop)

        self.cliente = Mock()
        construtor = patch.object(genai, "Client", return_value=self.cliente)
        self.construtor = construtor.start()
        self.addCleanup(construtor.stop)

    def investigar(self, respostas):
        self.cliente.interactions.create.side_effect = respostas
        agente.investigar(self.cliente, "Manual fictício", "Pedido fictício")

    def executar_main(self):
        with patch.object(
            agente, "carregar_contexto",
            return_value=("Manual fictício", "Memória fictícia"),
        ), patch("builtins.input", side_effect=["Erro de teste", "FIM"]):
            agente.main()

    def test_importacao_nao_inicia_terminal_nem_cliente(self):
        spec = importlib.util.spec_from_file_location(
            "agente_sem_execucao", agente.__file__
        )
        modulo = importlib.util.module_from_spec(spec)
        saida_importacao = io.StringIO()

        with patch(
            "builtins.input", side_effect=AssertionError("Entrada na importação.")
        ) as entrada, patch.object(
            Path, "read_text", side_effect=AssertionError("Leitura na importação.")
        ) as leitura, redirect_stdout(saida_importacao):
            spec.loader.exec_module(modulo)

        self.assertEqual(saida_importacao.getvalue(), "")
        self.construtor.assert_not_called()
        entrada.assert_not_called()
        leitura.assert_not_called()

    def test_recebe_multiplas_linhas_ate_fim(self):
        with patch(
            "builtins.input", side_effect=["linha 1", "", "linha 2", " FIM "]
        ):
            self.assertEqual(agente.receber_erro(), "linha 1\n\nlinha 2")

    def test_recusa_entrada_vazia(self):
        for linhas in (["FIM"], ["   ", "FIM"]):
            with self.subTest(linhas=linhas):
                with patch("builtins.input", side_effect=linhas):
                    with self.assertRaises(SystemExit):
                        agente.receber_erro()

        self.construtor.assert_not_called()

    def test_executa_listagem_sem_argumentos(self):
        with patch.object(
            agente, "listar_arquivos", return_value=["exemplo.py"]
        ) as listar:
            for argumentos in ({}, None):
                with self.subTest(argumentos=argumentos):
                    self.assertEqual(
                        agente.executar_ferramenta("listar_arquivos", argumentos),
                        {"sucesso": True, "arquivos": ["exemplo.py"]},
                    )

        self.assertEqual(listar.call_count, 2)

    def test_executa_leitura_com_caminho(self):
        with patch.object(
            agente, "ler_arquivo", return_value="valor = 42\n"
        ) as ler:
            resultado = agente.executar_ferramenta(
                "ler_arquivo", {"caminho": "exemplo.py"}
            )

        ler.assert_called_once_with("exemplo.py")
        self.assertEqual(
            resultado, {"sucesso": True, "conteudo": "valor = 42\n"}
        )

    def test_recusa_solicitacoes_invalidas_antes_de_executar(self):
        solicitacoes = [
            ("listar_arquivos", {"extra": True}),
            ("ler_arquivo", None),
            ("ler_arquivo", []),
            ("ler_arquivo", "exemplo.py"),
            ("ler_arquivo", {}),
            ("ler_arquivo", {"caminho": 1}),
            ("ler_arquivo", {"caminho": "  "}),
            ("ler_arquivo", {"caminho": "exemplo.py", "extra": True}),
            ("executar_comando", {}),
        ]
        with patch.object(agente, "ler_arquivo") as ler, patch.object(
            agente, "listar_arquivos"
        ) as listar:
            for nome, argumentos in solicitacoes:
                with self.subTest(nome=nome, argumentos=argumentos):
                    resultado = agente.executar_ferramenta(nome, argumentos)
                    self.assertFalse(resultado["sucesso"])
                    self.assertTrue(resultado["erro"])

        ler.assert_not_called()
        listar.assert_not_called()

    def test_converte_falha_da_ferramenta_em_resultado(self):
        for falha in (
            FileNotFoundError("Arquivo ausente."),
            ValueError("Caminho não autorizado."),
            UnicodeError("Codificação inválida."),
        ):
            with self.subTest(falha=type(falha).__name__):
                with patch.object(agente, "ler_arquivo", side_effect=falha):
                    resultado = agente.executar_ferramenta(
                        "ler_arquivo", {"caminho": "exemplo.py"}
                    )
                self.assertEqual(
                    resultado, {"sucesso": False, "erro": str(falha)}
                )

    def test_resposta_textual_encerra_sem_executar_ferramenta(self):
        with patch.object(agente, "executar_ferramenta") as executar:
            self.investigar([criar_resposta(texto="Diagnóstico final.")])

        executar.assert_not_called()
        self.cliente.interactions.create.assert_called_once()
        self.assertIn("Diagnóstico final.", self.saida.getvalue())

    def test_informa_resposta_sem_texto(self):
        self.investigar([criar_resposta(texto=None)])

        self.assertIn("Nenhuma análise textual recebida.", self.saida.getvalue())

    def test_devolve_resultados_em_lote_e_preserva_historico(self):
        primeira = criar_resposta(
            [criar_chamada("listar_arquivos", {}, "listar-1")],
            identificador="resposta-inicial",
        )
        segunda = criar_resposta(
            [
                SimpleNamespace(type="thought"),
                criar_chamada("ler_arquivo", {"caminho": "a.py"}, "ler-a"),
                criar_chamada("ler_arquivo", {"caminho": "b.py"}, "ler-b"),
            ],
            identificador="resposta-leituras",
        )
        with patch.object(
            agente, "listar_arquivos", return_value=["a.py", "b.py"]
        ), patch.object(
            agente, "ler_arquivo", side_effect=["valor = 1", "valor = 2"]
        ):
            self.investigar([primeira, segunda, criar_resposta()])

        consultas = self.cliente.interactions.create.call_args_list
        self.assertEqual(len(consultas), 3)
        self.assertEqual(
            consultas[1].kwargs["previous_interaction_id"], "resposta-inicial"
        )
        self.assertEqual(
            consultas[2].kwargs["previous_interaction_id"], "resposta-leituras"
        )
        self.assertEqual(consultas[0].kwargs["input"], "Pedido fictício")
        for consulta in consultas:
            self.assertEqual(consulta.kwargs["system_instruction"], "Manual fictício")
            self.assertEqual(
                {f["name"] for f in consulta.kwargs["tools"]},
                {"listar_arquivos", "ler_arquivo"},
            )

        listagem = consultas[1].kwargs["input"][0]
        self.assertEqual(listagem["type"], "function_result")
        self.assertEqual(listagem["name"], "listar_arquivos")
        self.assertEqual(listagem["call_id"], "listar-1")
        self.assertEqual(
            json.loads(listagem["result"][0]["text"]),
            {"sucesso": True, "arquivos": ["a.py", "b.py"]},
        )
        leituras = consultas[2].kwargs["input"]
        self.assertEqual([r["call_id"] for r in leituras], ["ler-a", "ler-b"])
        self.assertEqual(
            [json.loads(r["result"][0]["text"])["conteudo"] for r in leituras],
            ["valor = 1", "valor = 2"],
        )

    def test_devolve_erro_de_ferramenta_ao_modelo(self):
        with patch.object(
            agente, "ler_arquivo", side_effect=FileNotFoundError("Arquivo ausente.")
        ):
            self.investigar([
                criar_resposta([
                    criar_chamada("ler_arquivo", {"caminho": "ausente.py"})
                ]),
                criar_resposta(),
            ])

        resultado = self.cliente.interactions.create.call_args.kwargs["input"][0]
        self.assertEqual(
            json.loads(resultado["result"][0]["text"]),
            {"sucesso": False, "erro": "Arquivo ausente."},
        )

    def test_recusa_lote_com_mais_de_cinco_ferramentas(self):
        chamadas = [
            criar_chamada("listar_arquivos", {}, str(i)) for i in range(6)
        ]
        with patch.object(agente, "executar_ferramenta") as executar:
            self.investigar([criar_resposta(chamadas)])

        executar.assert_not_called()
        self.cliente.interactions.create.assert_called_once()
        self.assertIn("Quantidade excessiva", self.saida.getvalue())

    def test_aceita_lote_com_cinco_ferramentas(self):
        chamadas = [
            criar_chamada("listar_arquivos", {}, str(i)) for i in range(5)
        ]
        with patch.object(agente, "listar_arquivos", return_value=[]) as listar:
            self.investigar([criar_resposta(chamadas), criar_resposta()])

        self.assertEqual(listar.call_count, 5)
        self.assertEqual(self.cliente.interactions.create.call_count, 2)

    def test_respeita_limite_de_consultas_e_ferramentas(self):
        respostas = [
            criar_resposta(
                [criar_chamada("listar_arquivos", {}, str(i)) for i in range(5)],
                identificador=f"rodada-{rodada}",
            )
            for rodada in range(agente.MAX_RODADAS)
        ]
        with patch.object(agente, "listar_arquivos", return_value=[]) as listar:
            self.investigar(respostas)

        self.assertEqual(
            self.cliente.interactions.create.call_count, agente.MAX_RODADAS
        )
        self.assertEqual(listar.call_count, (agente.MAX_RODADAS - 1) * 5)
        self.assertIn("Investigação incompleta.", self.saida.getvalue())

    def test_aceita_conclusao_na_ultima_consulta(self):
        respostas = [
            criar_resposta([criar_chamada("listar_arquivos", {})])
            for _ in range(agente.MAX_RODADAS - 1)
        ]
        respostas.append(criar_resposta(texto="Conclusão no limite."))
        with patch.object(agente, "listar_arquivos", return_value=[]):
            self.investigar(respostas)

        self.assertIn("Conclusão no limite.", self.saida.getvalue())
        self.assertNotIn("Investigação incompleta.", self.saida.getvalue())

    def test_main_envia_contexto_e_fecha_cliente(self):
        self.cliente.interactions.create.return_value = criar_resposta()

        self.executar_main()

        parametros = self.cliente.interactions.create.call_args.kwargs
        self.assertEqual(parametros["system_instruction"], "Manual fictício")
        self.assertIn("<memoria>\nMemória fictícia\n</memoria>", parametros["input"])
        self.assertIn("<erro_atual>\nErro de teste\n</erro_atual>", parametros["input"])
        self.cliente.close.assert_called_once_with()

    def test_main_fecha_cliente_quando_a_api_falha(self):
        self.cliente.interactions.create.side_effect = RuntimeError("Falha simulada.")

        with self.assertRaises(SystemExit):
            self.executar_main()

        self.cliente.close.assert_called_once_with()
        self.cliente.interactions.create.assert_called_once()
        self.assertIn("A consulta ao Gemini falhou.", self.saida.getvalue())

    def test_main_fecha_cliente_quando_a_continuacao_falha(self):
        self.cliente.interactions.create.side_effect = [
            criar_resposta([criar_chamada("listar_arquivos", {})]),
            RuntimeError("Falha na continuação."),
        ]
        with patch.object(agente, "listar_arquivos", return_value=[]):
            with self.assertRaises(SystemExit):
                self.executar_main()

        self.cliente.close.assert_called_once_with()
        self.assertEqual(self.cliente.interactions.create.call_count, 2)

    def test_main_nao_cria_cliente_quando_a_entrada_e_vazia(self):
        with patch.object(
            agente, "carregar_contexto", return_value=("Manual", "Memória")
        ), patch("builtins.input", return_value="FIM"):
            with self.assertRaises(SystemExit):
                agente.main()

        self.construtor.assert_not_called()
