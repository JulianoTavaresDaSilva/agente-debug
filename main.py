import json
from pathlib import Path

from google import genai
from ferramentas import (
    ler_arquivo,
    listar_arquivos,
    DESCRICAO_LER_ARQUIVO,
    DESCRICAO_LISTAR_ARQUIVOS,
)

MODELO = "gemini-3.6-flash"
MAX_RODADAS = 5


def consultar_gemini(client, **parametros):
    try:
        return client.interactions.create(**parametros)

    except Exception as falha:
        print("\nA consulta ao Gemini falhou.")
        print(f"Tipo: {type(falha).__name__}")
        print(f"Mensagem: {falha}")

        resposta_http = getattr(falha, "response", None)

        if resposta_http is None:
            resposta_http = getattr(falha, "raw_response", None)

        cabecalhos = getattr(falha, "headers", None)

        if cabecalhos is None and resposta_http is not None:
            cabecalhos = getattr(resposta_http, "headers", None)

        if cabecalhos is not None:
            espera = cabecalhos.get("retry-after")

            if espera:
                print(f"Retry-After informado pelo servidor: {espera}")
            else:
                print("O servidor não informou Retry-After.")

        if resposta_http is not None:
            try:
                dados = resposta_http.json()

                if isinstance(dados, dict):
                    erro_api = dados.get("error", {})

                    if isinstance(erro_api, dict):
                        detalhes = erro_api.get("details")

                        if detalhes:
                            print("Detalhes adicionais:")
                            print(json.dumps(
                                detalhes,
                                ensure_ascii=False,
                                indent=2
                            ))

            except (ValueError, AttributeError):
                pass

        raise SystemExit(
            "Investigação interrompida; nenhuma repetição automática."
        ) from None


def carregar_contexto() -> tuple[str, str]:
    """Carrega o manual e a memória a partir da pasta do projeto."""
    pasta_projeto = Path(__file__).resolve().parent

    instrucoes = (pasta_projeto / "agent.md").read_text(
        encoding="utf-8"
    )
    print("Manual agent.md carregado.")

    memoria = (pasta_projeto / "memory.md").read_text(
        encoding="utf-8"
    )
    print("Memória memory.md carregada.")

    return instrucoes, memoria


def receber_erro() -> str:
    """Recebe o erro pelo terminal até encontrar uma linha com FIM."""
    print("\nCole o erro e o contexto abaixo.")
    print("Ao terminar, digite FIM em uma linha separada.")

    linhas = []

    while True:
        linha = input()

        if linha.strip() == "FIM":
            break

        linhas.append(linha)

    erro = "\n".join(linhas)

    if not erro.strip():
        raise SystemExit("Nenhum erro foi informado.")

    return erro


def montar_pedido(erro: str, memoria: str) -> str:
    """Monta o pedido com o erro atual e a memória como contexto histórico."""
    return f"""
Use a memória somente como contexto histórico.
Ela pode conter informações desatualizadas.

<memoria>
{memoria}
</memoria>

<erro_atual>
{erro}
</erro_atual>

Investigue o erro seguindo seu manual.
Você dispõe das ferramentas listar_arquivos e ler_arquivo.
Use listar_arquivos quando precisar descobrir os arquivos disponíveis.
Os caminhos recebidos por ler_arquivo são relativos à pasta casos.
"""


def executar_ferramenta(nome: str, argumentos) -> dict:
    """Valida a solicitação e retorna o resultado ou o erro da ferramenta."""
    print(f"\nFerramenta solicitada: {nome}")

    try:
        if argumentos is None:
            argumentos = {}

        if not isinstance(argumentos, dict):
            raise ValueError("Os argumentos devem ser um dicionário.")

        if nome == "listar_arquivos":
            if argumentos:
                raise ValueError(
                    "listar_arquivos não recebe argumentos."
                )

            arquivos = listar_arquivos()
            resultado = {"sucesso": True, "arquivos": arquivos}
            print(f"Arquivos encontrados: {arquivos}")

        elif nome == "ler_arquivo":
            if set(argumentos) != {"caminho"}:
                raise ValueError(
                    "Informe somente o argumento caminho."
                )

            caminho = argumentos["caminho"]

            if not isinstance(caminho, str) or not caminho.strip():
                raise ValueError(
                    "O caminho deve ser um texto não vazio."
                )

            conteudo = ler_arquivo(caminho)
            resultado = {"sucesso": True, "conteudo": conteudo}
            print(f"Arquivo lido: {caminho}")

        else:
            raise ValueError("Ferramenta não permitida.")

    except (OSError, ValueError, UnicodeError) as falha:
        resultado = {"sucesso": False, "erro": str(falha)}
        print(f"Falha na ferramenta: {falha}")

    return resultado


def investigar(client, instrucoes: str, pedido: str) -> None:
    """Coordena as consultas ao Gemini e o ciclo de ferramentas."""
    ferramentas = [
        DESCRICAO_LER_ARQUIVO,
        DESCRICAO_LISTAR_ARQUIVOS,
    ]

    print("\nConsultando o Gemini...")

    resposta = consultar_gemini(
        client,
        model=MODELO,
        system_instruction=instrucoes,
        input=pedido,
        tools=ferramentas
    )

    for rodada in range(1, MAX_RODADAS + 1):
        chamadas = [
            passo
            for passo in (resposta.steps or [])
            if passo.type == "function_call"
        ]

        if not chamadas:
            print("\nAnálise:")
            print(resposta.output_text or "Nenhuma análise textual recebida.")
            break

        if rodada == MAX_RODADAS:
            print("\nLimite de rodadas atingido. Investigação incompleta.")
            break

        if len(chamadas) > 5:
            print("\nQuantidade excessiva de ferramentas solicitadas.")
            break

        resultados = []

        for chamada in chamadas:
            resultado = executar_ferramenta(
                chamada.name, chamada.arguments
            )

            resultados.append({
                "type": "function_result",
                "name": chamada.name,
                "call_id": chamada.id,
                "result": [{
                    "type": "text",
                    "text": json.dumps(resultado, ensure_ascii=False)
                }]
            })

        print("\nDevolvendo os resultados ao Gemini...")

        resposta = consultar_gemini(
            client,
            model=MODELO,
            system_instruction=instrucoes,
            input=resultados,
            tools=ferramentas,
            previous_interaction_id=resposta.id
        )


def main() -> None:
    """Prepara a investigação e garante o fechamento do cliente da API."""
    instrucoes, memoria = carregar_contexto()
    erro = receber_erro()
    pedido = montar_pedido(erro, memoria)

    client = genai.Client()

    try:
        investigar(client, instrucoes, pedido)
    finally:
        client.close()


if __name__ == "__main__":
    main()
