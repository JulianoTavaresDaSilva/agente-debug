"""Arquivos temporários e respostas fictícias para os testes locais."""

from pathlib import Path
import shutil
from types import SimpleNamespace
import unittest
from uuid import uuid4


class CasoTemporario(unittest.TestCase):
    def setUp(self):
        self.raiz = Path(__file__).resolve().parent / f"_cli_{uuid4().hex}"
        self.raiz.mkdir()
        self.addCleanup(self.limpar)

    def limpar(self):
        alvo = self.raiz.resolve()
        if alvo.parent != Path(__file__).resolve().parent or not alvo.name.startswith("_cli_"):
            raise ValueError("Pasta temporária fora do escopo de limpeza.")
        shutil.rmtree(alvo)

    def arquivo(self, nome, conteudo="valor = 1\n"):
        caminho = self.raiz / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho


def chamada(nome="ler_arquivo", argumentos=None, identificador="c1"):
    return SimpleNamespace(
        type="function_call", name=nome,
        arguments=argumentos if argumentos is not None else {"caminho": "codigo.py"},
        id=identificador,
    )


def resposta(passos=(), texto="", estado="completed", identificador="r1"):
    return SimpleNamespace(steps=list(passos), output_text=texto, status=estado, id=identificador)


def diagnostico(estado="analise_produzida"):
    return {
        "estado": estado, "problema": "Problema fictício.",
        "causa_provavel": "Causa provável.", "correcao_sugerida": "Correção sugerida.",
        "verificacao": ["Verificação sugerida."],
        "pendencias": ["Contexto adicional."],
        "evidencias": ([{
            "caminho": "codigo.py", "linha_inicio": 1, "linha_fim": 1,
            "observacao": "Referência ao código consultado.",
        }] if estado == "analise_produzida" else []),
    }
