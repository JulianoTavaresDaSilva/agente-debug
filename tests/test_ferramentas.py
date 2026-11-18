"""Verifica as ferramentas usando arquivos temporários."""

from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

import ferramentas
from configuracao import Configuracao, ErroConfiguracao


class TestFerramentas(unittest.TestCase):
    def setUp(self):
        pasta_testes = Path(__file__).resolve().parent
        self.raiz = pasta_testes / f"_arquivos_{uuid4().hex}"
        self.raiz.mkdir()
        self.addCleanup(self.limpar_arquivos)

        self.casos = self.raiz / "casos"
        self.casos.mkdir()

        pasta_autorizada = patch.object(
            ferramentas, "PASTA_AUTORIZADA", self.casos
        )
        pasta_autorizada.start()
        self.addCleanup(pasta_autorizada.stop)

    def limpar_arquivos(self):
        raiz = self.raiz.resolve()
        pasta_testes = Path(__file__).resolve().parent
        if raiz.parent != pasta_testes or not raiz.name.startswith("_arquivos_"):
            raise ValueError("A limpeza deve ficar restrita à pasta temporária.")
        shutil.rmtree(raiz)

    def criar_arquivo(self, caminho, conteudo="valor = 1\n"):
        arquivo = self.casos / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(conteudo, encoding="utf-8")
        return arquivo

    def test_le_arquivo_utf8_sem_executar_codigo(self):
        conteudo = 'raise RuntimeError("Este código não deve executar.")\n'
        self.criar_arquivo("exemplo.py", conteudo)

        self.assertEqual(ferramentas.ler_arquivo("exemplo.py"), conteudo)

    def test_le_arquivo_em_subpasta_autorizada(self):
        self.criar_arquivo("modulo/exemplo.py", "valor = 42\n")

        self.assertEqual(
            ferramentas.ler_arquivo("modulo/exemplo.py"), "valor = 42\n"
        )

    def test_recusa_caminhos_fora_da_pasta(self):
        arquivo_externo = self.raiz / "fora.py"
        arquivo_externo.write_text("segredo = 1\n", encoding="utf-8")

        for caminho in ("../fora.py", str(arquivo_externo)):
            with self.subTest(caminho=caminho):
                with self.assertRaises(ValueError):
                    ferramentas.ler_arquivo(caminho)

    def test_recusa_pasta_irma_com_nome_parecido(self):
        outra_pasta = self.raiz / "casos_externos"
        outra_pasta.mkdir()
        (outra_pasta / "fora.py").write_text("valor = 1", encoding="utf-8")

        with self.assertRaises(ValueError):
            ferramentas.ler_arquivo("../casos_externos/fora.py")

    def test_recusa_extensao_nao_autorizada(self):
        for nome in ("notas.txt", "sem_extensao"):
            self.criar_arquivo(nome)
            with self.subTest(nome=nome):
                with self.assertRaises(ValueError):
                    ferramentas.ler_arquivo(nome)

    def test_informa_arquivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            ferramentas.ler_arquivo("ausente.py")

    def test_recusa_diretorio_com_extensao_python(self):
        (self.casos / "diretorio.py").mkdir()

        with self.assertRaises(FileNotFoundError):
            ferramentas.ler_arquivo("diretorio.py")

    def test_aceita_exatamente_vinte_mil_caracteres(self):
        conteudo = "á" * 20_000
        self.criar_arquivo("limite.py", conteudo)

        self.assertEqual(ferramentas.ler_arquivo("limite.py"), conteudo)

    def test_recusa_arquivo_acima_do_limite(self):
        self.criar_arquivo("grande.py", "a" * 20_001)

        with self.assertRaises(ValueError):
            ferramentas.ler_arquivo("grande.py")

    def test_informa_conteudo_que_nao_e_utf8(self):
        (self.casos / "invalido.py").write_bytes(b"\xff\xfe\xfa")

        with self.assertRaises(UnicodeError):
            ferramentas.ler_arquivo("invalido.py")

    def test_lista_python_em_subpastas_em_ordem(self):
        for nome in ("zeta.py", "alfa.PY", "beta.py", "notas.txt"):
            self.criar_arquivo(nome)
        self.criar_arquivo("subpasta/oculto.py")
        (self.casos / "diretorio.py").mkdir()

        self.assertEqual(
            ferramentas.listar_arquivos(), ["alfa.PY", "beta.py", "subpasta/oculto.py", "zeta.py"]
        )

    def test_lista_vazia_quando_nao_ha_arquivos(self):
        self.assertEqual(ferramentas.listar_arquivos(), [])

    def test_informa_pasta_autorizada_inexistente(self):
        with patch.object(
            ferramentas, "PASTA_AUTORIZADA", self.raiz / "ausente"
        ):
            with self.assertRaises(ErroConfiguracao):
                ferramentas.listar_arquivos()

    def test_nao_lista_nem_le_diretorios_excluidos(self):
        for pasta in (".git", ".venv", "__pycache__", "node_modules", ".oculta"):
            self.criar_arquivo(f"{pasta}/segredo.py")
            with self.subTest(pasta=pasta):
                retorno = ferramentas.FerramentasProjeto().executar(
                    "ler_arquivo", {"caminho": f"{pasta}/segredo.py"}
                )
                self.assertFalse(retorno["sucesso"])
        self.assertEqual(ferramentas.listar_arquivos(), [])

    def test_devolve_faixa_com_numeracao(self):
        self.criar_arquivo("codigo.py", "a = 1\nb = 2\nc = 3\n")
        sessao = ferramentas.FerramentasProjeto()
        retorno = sessao.executar("ler_arquivo", {
            "caminho": "codigo.py", "linha_inicio": 2, "linha_fim": 3,
        })
        self.assertEqual(retorno["conteudo"], "2: b = 2\n3: c = 3")
        self.assertEqual((retorno["linha_inicio"], retorno["linha_fim"]), (2, 3))
        self.assertEqual(sessao.leituras[0].caminho, "codigo.py")

    def test_recusa_intervalos_invalidos(self):
        self.criar_arquivo("codigo.py")
        sessao = ferramentas.FerramentasProjeto()
        for argumentos in (
            {"linha_inicio": 0}, {"linha_inicio": True}, {"linha_fim": "2"},
            {"linha_inicio": 4, "linha_fim": 2}, {"linha_inicio": None},
            {"linha_inicio": 200}, {"extra": True},
        ):
            with self.subTest(argumentos=argumentos):
                self.assertFalse(sessao.executar(
                    "ler_arquivo", {"caminho": "codigo.py", **argumentos}
                )["sucesso"])

    def test_limita_listagem_e_indica_truncamento(self):
        for i in range(4):
            self.criar_arquivo(f"{i}.py")
        sessao = ferramentas.FerramentasProjeto(config=Configuracao(max_arquivos=2))
        retorno = sessao.listar()
        self.assertEqual(len(retorno["arquivos"]), 2)
        self.assertTrue(retorno["truncado"])

    def test_limita_varredura_e_profundidade(self):
        self.criar_arquivo("a/b/c.py")
        retorno = ferramentas.FerramentasProjeto(config=Configuracao(max_profundidade=1)).listar()
        self.assertTrue(retorno["truncado"])
        self.assertEqual(retorno["arquivos"], [])
        for i in range(4):
            self.criar_arquivo(f"{i}.py")
        retorno = ferramentas.FerramentasProjeto(config=Configuracao(max_itens=2)).listar()
        self.assertTrue(retorno["truncado"])

    def test_limita_contexto_sem_registrar_leitura_nao_enviada(self):
        self.criar_arquivo("codigo.py")
        sessao = ferramentas.FerramentasProjeto(config=Configuracao(max_contexto=10))
        self.assertFalse(sessao.executar("ler_arquivo", {"caminho": "codigo.py"})["sucesso"])
        self.assertTrue(sessao.limite_atingido)
        self.assertEqual(sessao.leituras, [])

    def test_permite_recuperar_leitura_grande_com_faixa_menor(self):
        self.criar_arquivo("codigo.py", "x = 1\n" * 10)
        sessao = ferramentas.FerramentasProjeto(config=Configuracao(max_arquivo=20))
        self.assertFalse(sessao.executar("ler_arquivo", {"caminho": "codigo.py"})["sucesso"])
        self.assertFalse(sessao.limite_atingido)
        self.assertTrue(sessao.executar("ler_arquivo", {
            "caminho": "codigo.py", "linha_inicio": 2, "linha_fim": 3,
        })["sucesso"])

    def test_ferramenta_e_argumentos_nao_permitidos(self):
        sessao = ferramentas.FerramentasProjeto()
        for nome, argumentos in (("executar_codigo", {}), ("listar_arquivos", []), ("listar_arquivos", {"x": 1}), ("ler_arquivo", {})):
            with self.subTest(nome=nome, argumentos=argumentos):
                self.assertFalse(sessao.executar(nome, argumentos)["sucesso"])

    def test_recusa_link_para_arquivo_fora_da_pasta(self):
        arquivo_externo = self.raiz / "fora.py"
        arquivo_externo.write_text("valor = 1\n", encoding="utf-8")
        link = self.casos / "link.py"
        try:
            link.symlink_to(arquivo_externo)
        except (OSError, NotImplementedError) as falha:
            self.skipTest(f"Criação de links simbólicos indisponível: {falha}")

        with self.assertRaises(ValueError):
            ferramentas.ler_arquivo("link.py")
        self.assertNotIn("link.py", ferramentas.listar_arquivos())
