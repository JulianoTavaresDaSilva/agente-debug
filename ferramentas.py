"""Ferramentas de leitura com raiz autorizada e orçamento de contexto."""

from dataclasses import dataclass
import json
import os
from pathlib import Path

from configuracao import Configuracao, ErroConfiguracao, PASTA_PROJETO

PASTA_AUTORIZADA = PASTA_PROJETO / "casos"
DIRETORIOS_EXCLUIDOS = {".git", ".venv", "venv", "__pycache__", "node_modules"}


class LimiteConsulta(ValueError):
    """Uma consulta ultrapassaria um limite de leitura ou contexto."""


class LimiteContexto(LimiteConsulta):
    """O orçamento compartilhado da investigação foi esgotado."""


@dataclass(frozen=True)
class TrechoArquivo:
    caminho: str
    linha_inicio: int
    linhas: tuple[str, ...]

    @property
    def linha_fim(self):
        return self.linha_inicio + len(self.linhas) - 1

    @property
    def conteudo(self):
        return "".join(self.linhas)

    def para_modelo(self):
        numerado = "\n".join(
            f"{numero}: {linha.rstrip(chr(10))}"
            for numero, linha in enumerate(self.linhas, self.linha_inicio)
        )
        return {
            "sucesso": True, "caminho": self.caminho,
            "linha_inicio": self.linha_inicio, "linha_fim": self.linha_fim,
            "conteudo": numerado,
        }


def parte_excluida(parte):
    return parte.startswith(".") or parte.lower() in DIRETORIOS_EXCLUIDOS


class FerramentasProjeto:
    def __init__(self, raiz=None, config=None):
        self.config = config or Configuracao()
        self.raiz = Path(raiz if raiz is not None else PASTA_AUTORIZADA).resolve()
        if not self.raiz.is_dir() or parte_excluida(self.raiz.name):
            raise ErroConfiguracao("A pasta do projeto deve existir e ser uma pasta de código autorizada.")
        self.leituras = []
        self.caracteres = 0
        self.limite_atingido = ""

    def validar_caminho(self, caminho):
        if not isinstance(caminho, str) or not caminho.strip():
            raise ValueError("O caminho deve ser um texto não vazio.")
        relativo = Path(caminho)
        if relativo.is_absolute() or any(parte_excluida(p) for p in relativo.parts):
            raise ValueError("Informe um caminho relativo sem pastas ocultas ou excluídas.")
        arquivo = (self.raiz / relativo).resolve()
        if not arquivo.is_relative_to(self.raiz):
            raise ValueError("O arquivo está fora da pasta autorizada.")
        if any(parte_excluida(p) for p in arquivo.relative_to(self.raiz).parts):
            raise ValueError("O arquivo pertence a uma pasta excluída.")
        if arquivo.suffix.lower() != ".py":
            raise ValueError("Somente arquivos .py são permitidos.")
        if not arquivo.is_file():
            raise FileNotFoundError("Arquivo não encontrado.")
        return arquivo

    def listar(self):
        arquivos = []
        visitados = 0
        truncado = False

        def visitar(pasta, profundidade):
            nonlocal visitados, truncado
            entradas = []
            with os.scandir(pasta) as itens:
                for item in itens:
                    visitados += 1
                    if visitados > self.config.max_itens:
                        truncado = True
                        break
                    if not parte_excluida(item.name) and not item.is_symlink():
                        entradas.append(item)
            for item in sorted(entradas, key=lambda e: e.name):
                if len(arquivos) >= self.config.max_arquivos:
                    truncado = True
                    break
                if item.is_dir(follow_symlinks=False):
                    if profundidade < self.config.max_profundidade and visitados <= self.config.max_itens:
                        visitar(Path(item.path), profundidade + 1)
                    else:
                        truncado = True
                elif item.is_file() and Path(item.name).suffix.lower() == ".py":
                    relativo = Path(item.path).relative_to(self.raiz).as_posix()
                    try:
                        self.validar_caminho(relativo)
                    except (OSError, ValueError):
                        continue
                    arquivos.append(relativo)

        visitar(self.raiz, 0)
        return {"sucesso": True, "arquivos": sorted(arquivos), "truncado": truncado}

    def ler(self, caminho, linha_inicio=1, linha_fim=None):
        for nome, valor in (("linha_inicio", linha_inicio), ("linha_fim", linha_fim)):
            if valor is not None and (type(valor) is not int or valor < 1):
                raise ValueError(f"{nome} deve ser um inteiro positivo.")
        if linha_inicio is None or (linha_fim is not None and linha_fim < linha_inicio):
            raise ValueError("Intervalo de linhas inválido.")
        arquivo = self.validar_caminho(caminho)
        linhas = []
        tamanho = varridos = 0
        with arquivo.open(encoding="utf-8") as conteudo:
            for numero in range(1, self.config.max_linhas + 1):
                linha = conteudo.readline(self.config.max_arquivo + 1)
                if not linha:
                    break
                varridos += len(linha)
                if len(linha) > self.config.max_arquivo or varridos > self.config.max_varredura:
                    raise LimiteConsulta("Limite de varredura ou tamanho da linha atingido.")
                if numero >= linha_inicio:
                    tamanho += len(linha)
                    if tamanho > self.config.max_arquivo:
                        raise LimiteConsulta("A leitura ultrapassa o limite de caracteres; solicite uma faixa menor.")
                    linhas.append(linha)
                if numero == linha_fim:
                    break
            else:
                if conteudo.read(1):
                    raise LimiteConsulta("Limite de linhas examinadas atingido.")
        if not linhas:
            raise ValueError("Arquivo vazio ou linha inicial inexistente.")
        return TrechoArquivo(arquivo.relative_to(self.raiz).as_posix(), linha_inicio, tuple(linhas))

    def executar(self, nome, argumentos):
        try:
            if argumentos is None:
                argumentos = {}
            if not isinstance(argumentos, dict):
                raise ValueError("Os argumentos devem ser um dicionário.")
            trecho = None
            if nome == "listar_arquivos":
                if argumentos:
                    raise ValueError("listar_arquivos não recebe argumentos.")
                resultado = self.listar()
            elif nome == "ler_arquivo":
                if "caminho" not in argumentos or set(argumentos) - {"caminho", "linha_inicio", "linha_fim"}:
                    raise ValueError("Informe caminho e, opcionalmente, linha_inicio e linha_fim.")
                trecho = self.ler(**argumentos)
                resultado = trecho.para_modelo()
            else:
                raise ValueError("Ferramenta não permitida.")
            tamanho = len(json.dumps(resultado, ensure_ascii=False))
            if self.caracteres + tamanho > self.config.max_contexto:
                raise LimiteContexto("Limite total de contexto das ferramentas atingido.")
            self.caracteres += tamanho
            if trecho is not None and trecho not in self.leituras:
                self.leituras.append(trecho)
            return resultado
        except LimiteContexto as falha:
            self.limite_atingido = str(falha)
            return {"sucesso": False, "erro": str(falha)}
        except (OSError, ValueError, UnicodeError) as falha:
            return {"sucesso": False, "erro": str(falha)}


def ler_arquivo(caminho: str) -> str:
    """Atalho de leitura integral para uso local."""
    return FerramentasProjeto().ler(caminho).conteudo


def listar_arquivos() -> list[str]:
    """Lista os caminhos Python relativos, incluindo subpastas."""
    return FerramentasProjeto().listar()["arquivos"]


DESCRICAO_LER_ARQUIVO = {
    "type": "function",
    "name": "ler_arquivo",
    "description": (
        "Lê um arquivo Python da pasta autorizada casos. "
        "Recebe o caminho relativo a essa pasta, como calculadora.py. "
        "Não executa o código."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "caminho": {
                "type": "string",
                "description": "Caminho relativo à pasta casos."
            }
        },
        "required": ["caminho"]
    }
}
DESCRICAO_LISTAR_ARQUIVOS = {
    "type": "function", "name": "listar_arquivos",
    "description": "Descobre arquivos Python e subpastas autorizadas, com limites. truncado indica listagem incompleta.",
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}
