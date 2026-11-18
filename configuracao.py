"""Configuração e limites da investigação."""

from dataclasses import dataclass, fields
import math
from pathlib import Path

PASTA_PROJETO = Path(__file__).resolve().parent
VERSAO = "0.1.0"


class ErroConfiguracao(ValueError):
    """Uma configuração impede o início da investigação."""


@dataclass(frozen=True)
class Configuracao:
    modelo: str = "gemini-3.6-flash"
    max_consultas: int = 5
    max_ferramentas: int = 5
    timeout: float = 30.0
    tempo_total: float = 120.0
    max_entrada: int = 20_000
    max_memoria: int = 10_000
    max_manual: int = 30_000
    max_arquivos: int = 200
    max_itens: int = 2_000
    max_profundidade: int = 10
    max_arquivo: int = 20_000
    max_varredura: int = 1_000_000
    max_linhas: int = 20_000
    max_contexto: int = 80_000
    max_saida: int = 4_096

    def __post_init__(self):
        if not isinstance(self.modelo, str) or not self.modelo.strip():
            raise ErroConfiguracao("O modelo deve ser um texto não vazio.")
        for campo in fields(self):
            if campo.name == "modelo":
                continue
            valor = getattr(self, campo.name)
            tipo = (int, float) if campo.name in {"timeout", "tempo_total"} else int
            if isinstance(valor, bool) or not isinstance(valor, tipo) or not math.isfinite(valor) or valor <= 0:
                raise ErroConfiguracao(f"{campo.name} deve ser um número positivo.")


def ler_texto(caminho: Path, limite: int, descricao: str) -> str:
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            texto = arquivo.read(limite + 1)
    except (OSError, UnicodeError) as falha:
        raise ErroConfiguracao(f"Não foi possível ler {descricao} em UTF-8: {caminho.name}.") from falha
    if len(texto) > limite:
        raise ErroConfiguracao(f"{descricao} ultrapassa {limite} caracteres.")
    return texto
