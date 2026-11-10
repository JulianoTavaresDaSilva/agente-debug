from pathlib import Path

PASTA_AUTORIZADA = (
    Path(__file__).resolve().parent / "casos"
).resolve()


def ler_arquivo(caminho: str) -> str:
    arquivo = (PASTA_AUTORIZADA / caminho).resolve()

    if not arquivo.is_relative_to(PASTA_AUTORIZADA):
        raise ValueError("O arquivo está fora da pasta autorizada.")

    if arquivo.suffix.lower() != ".py":
        raise ValueError("Somente arquivos .py são permitidos.")

    if not arquivo.is_file():
        raise FileNotFoundError("Arquivo não encontrado.")

    with arquivo.open(encoding="utf-8") as conteudo:
        texto = conteudo.read(20_001)

    if len(texto) > 20_000:
        raise ValueError("O arquivo ultrapassa 20.000 caracteres.")

    return texto

def listar_arquivos() -> list[str]:
    if not PASTA_AUTORIZADA.is_dir():
        raise FileNotFoundError("A pasta autorizada não foi encontrada.")

    arquivos = []

    for arquivo in PASTA_AUTORIZADA.iterdir():
        if not arquivo.is_file():
            continue

        if arquivo.suffix.lower() != ".py":
            continue

        if not arquivo.resolve().is_relative_to(PASTA_AUTORIZADA):
            continue

        arquivos.append(arquivo.name)

    return sorted(arquivos)

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
    "type": "function",
    "name": "listar_arquivos",
    "description": (
        "Lista os nomes dos arquivos Python disponíveis diretamente "
        "na pasta autorizada casos. Não recebe argumentos "
        "e não entra em subpastas."
    ),
    "parameters": {
        "type": "object",
        "properties": {}
    }
}