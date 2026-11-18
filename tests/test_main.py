"""Testes da interface e da inicialização, sem API real."""

from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import main
from configuracao import Configuracao, ErroConfiguracao
from tests.apoio import CasoTemporario, diagnostico, resposta
import json


class TestMain(CasoTemporario):
    def setUp(self):
        super().setUp()
        rede = patch("socket.socket.connect", side_effect=AssertionError("Rede não permitida nos testes."))
        rede.start()
        self.addCleanup(rede.stop)
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()

    def executar(self, argumentos):
        with redirect_stdout(self.stdout), redirect_stderr(self.stderr):
            return main.main(argumentos)

    def test_importacao_nao_le_arquivos_nem_inicia_cliente(self):
        spec = importlib.util.spec_from_file_location("modulo_sem_execucao", main.__file__)
        modulo = importlib.util.module_from_spec(spec)
        with patch("builtins.input", side_effect=AssertionError("Entrada na importação.")), patch.object(
            Path, "read_text", side_effect=AssertionError("Leitura na importação.")
        ), patch.object(main, "criar_cliente", side_effect=AssertionError("API na importação.")):
            spec.loader.exec_module(modulo)
        self.assertTrue(callable(modulo.main))

    def test_recebe_multiplas_linhas_e_eof(self):
        for linhas in (["a", "", "b", " FIM "], ["a", "", "b", EOFError()]):
            with self.subTest(linhas=linhas), patch("builtins.input", side_effect=linhas), redirect_stderr(self.stderr):
                self.assertEqual(main.receber_erro(), "a\n\nb")

    def test_valida_entrada_vazia_e_limite(self):
        for linhas, limite in ((["FIM"], 10), ([" ", "FIM"], 10), (["abc", "FIM"], 2)):
            with self.subTest(linhas=linhas), patch("builtins.input", side_effect=linhas), redirect_stderr(self.stderr):
                with self.assertRaises(ErroConfiguracao):
                    main.receber_erro(limite)
        with patch("builtins.input", side_effect=["abc", "FIM"]), redirect_stderr(self.stderr):
            self.assertEqual(main.receber_erro(3), "abc")

    def test_memoria_nao_e_lida_por_padrao(self):
        self.arquivo("agent.md", "Manual genérico.")
        self.arquivo("memory.md", "HISTORICO QUE NAO DEVE SER ENVIADO")
        with patch.object(main, "PASTA_PROJETO", self.raiz):
            self.assertEqual(main.carregar_contexto(), ("Manual genérico.", ""))

    def test_memoria_opcional_ausente_e_explicita(self):
        self.arquivo("agent.md", "Manual.")
        memoria = self.arquivo("contexto.md", "Contexto.")
        with patch.object(main, "PASTA_PROJETO", self.raiz), redirect_stderr(self.stderr):
            self.assertEqual(main.carregar_contexto(memoria), ("Manual.", "Contexto."))
            self.assertEqual(main.carregar_contexto(self.raiz / "ausente.md"), ("Manual.", ""))
        self.assertIn("continuando sem histórico", self.stderr.getvalue())

    def test_manual_obrigatorio_e_arquivos_limitados(self):
        with patch.object(main, "PASTA_PROJETO", self.raiz):
            with self.assertRaises(ErroConfiguracao):
                main.carregar_contexto()
            self.arquivo("agent.md", " ")
            with self.assertRaises(ErroConfiguracao):
                main.carregar_contexto()
            self.arquivo("agent.md", "manual extenso")
            with self.assertRaises(ErroConfiguracao):
                main.carregar_contexto(config=Configuracao(max_manual=2))

    def test_falta_de_chave_encerra_antes_da_entrada(self):
        with patch.dict(os.environ, {}, clear=True), patch("builtins.input") as entrada:
            codigo = self.executar(["--projeto", str(self.raiz)])
        self.assertEqual(codigo, 2)
        self.assertIn("GEMINI_API_KEY", self.stderr.getvalue())
        entrada.assert_not_called()

    def test_demo_nao_cria_cliente_real_e_exporta_relatorio(self):
        destino = self.raiz / "relatorios" / "demo.md"
        with patch.object(main, "criar_cliente", side_effect=AssertionError("API real.")), patch.dict(os.environ, {}, clear=True):
            codigo = self.executar(["--demo", "media", "--saida", str(destino)])
        self.assertEqual(codigo, 0)
        self.assertIn("SIMULAÇÃO LOCAL", destino.read_text(encoding="utf-8"))
        self.assertIn("calculadora.py:1-2", self.stdout.getvalue())

    def test_todos_os_casos_de_demo(self):
        for nome, esperado in (("media", 0), ("tipos", 0), ("multiarquivo", 0), ("insuficiente", 3)):
            with self.subTest(caso=nome), patch.object(main, "criar_cliente", side_effect=AssertionError("API real.")):
                self.assertEqual(self.executar(["--demo", nome]), esperado)

    def test_executavel_em_outro_diretorio_e_ambiente_sem_chave(self):
        ambiente = {k: v for k, v in os.environ.items() if k not in {"GOOGLE_API_KEY", "GEMINI_API_KEY"}}
        ambiente["PYTHONIOENCODING"] = "utf-8"
        for nome, esperado in (("media", 0), ("tipos", 0), ("multiarquivo", 0), ("insuficiente", 3)):
            with self.subTest(caso=nome):
                processo = subprocess.run(
                    [sys.executable, str(Path(main.__file__).resolve()), "--demo", nome],
                    cwd=self.raiz, env=ambiente, capture_output=True,
                    encoding="utf-8", timeout=20,
                )
                self.assertEqual(processo.returncode, esperado, processo.stderr)
                self.assertIn("SIMULAÇÃO LOCAL", processo.stdout)

    def test_demo_recusa_projeto_externo(self):
        self.assertEqual(self.executar(["--demo", "--projeto", str(self.raiz)]), 2)

    def test_saida_existente_e_extensao_invalida_sao_recusadas(self):
        destino = self.arquivo("existente.md", "Preservar")
        for path in (destino, self.raiz / "codigo.py", self.raiz / ".git" / "relatorio.md"):
            with self.subTest(path=path):
                self.assertEqual(self.executar(["--demo", "--saida", str(path)]), 2)
        self.assertEqual(destino.read_text(encoding="utf-8"), "Preservar")

    def test_configuracoes_invalidas(self):
        for valor in ("0", "-1", "nan", "inf"):
            with self.subTest(valor=valor):
                self.assertEqual(self.executar(["--demo", "--timeout", valor]), 2)
        for valor in ("0", "-1"):
            self.assertEqual(self.executar(["--demo", "--max-consultas", valor]), 2)

    def test_erro_por_arquivo_e_fechamento_do_cliente(self):
        erro = self.arquivo("erro.txt", "Erro de teste.")
        cliente = Mock()
        cliente.interactions.create.return_value = resposta(texto=json.dumps(diagnostico("informacao_insuficiente")))
        with patch.object(main, "obter_chave", return_value="chave-ficticia"), patch.object(
            main, "criar_cliente", return_value=cliente
        ):
            codigo = self.executar(["--projeto", str(self.raiz), "--erro-arquivo", str(erro)])
        self.assertEqual(codigo, 3)
        cliente.close.assert_called_once()
        self.assertIn("Erro de teste.", cliente.interactions.create.call_args.kwargs["input"])

    def test_falha_api_fecha_cliente(self):
        erro = self.arquivo("erro.txt", "Erro.")
        cliente = Mock()
        cliente.interactions.create.side_effect = RuntimeError("NAO MOSTRAR ESTE SEGREDO")
        with patch.object(main, "obter_chave", return_value="ficticia"), patch.object(main, "criar_cliente", return_value=cliente):
            self.assertEqual(self.executar(["--projeto", str(self.raiz), "--erro-arquivo", str(erro)]), 1)
        cliente.close.assert_called_once()
        self.assertNotIn("NAO MOSTRAR", self.stdout.getvalue())

    def test_cancelamento_e_erro_vazio(self):
        with patch.object(main, "obter_chave", return_value="ficticia"), patch("builtins.input", side_effect=KeyboardInterrupt()):
            self.assertEqual(self.executar(["--projeto", str(self.raiz)]), 130)
        erro = self.arquivo("erro.txt", " ")
        with patch.object(main, "obter_chave", return_value="ficticia"):
            self.assertEqual(self.executar(["--projeto", str(self.raiz), "--erro-arquivo", str(erro)]), 2)

    def test_recusa_pasta_inexistente_e_arquivo_de_credenciais_como_erro(self):
        self.assertEqual(self.executar(["--projeto", str(self.raiz / "ausente")]), 2)
        chave = self.arquivo(".env", "NAO LER")
        with patch.object(main, "obter_chave", return_value="ficticia"):
            self.assertEqual(self.executar(["--projeto", str(self.raiz), "--erro-arquivo", str(chave)]), 2)
