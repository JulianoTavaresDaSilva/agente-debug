"""Interface de terminal do Agente Debug."""

import argparse
from dataclasses import replace
import os
from pathlib import Path
import sys

from agente import investigar, montar_pedido
from cliente_gemini import criar_cliente, obter_chave
from configuracao import Configuracao, ErroConfiguracao, PASTA_PROJETO, VERSAO, ler_texto
from demonstracao import CASOS, ClienteDemonstracao, pasta_caso
from ferramentas import DIRETORIOS_EXCLUIDOS, FerramentasProjeto
from resultado import gerar_markdown, salvar_relatorio


def carregar_contexto(memoria=None, config=None):
    config = config or Configuracao()
    instrucoes = ler_texto(PASTA_PROJETO / "agent.md", config.max_manual, "o manual")
    if not instrucoes.strip():
        raise ErroConfiguracao("O manual agent.md está vazio.")
    historico = ""
    if memoria is not None:
        memoria = Path(memoria)
        if memoria.suffix.lower() != ".md":
            raise ErroConfiguracao("A memória deve ser um arquivo .md.")
        if memoria.exists():
            historico = ler_texto(memoria, config.max_memoria, "a memória")
        else:
            print("Memória não encontrada; continuando sem histórico.", file=sys.stderr)
    return instrucoes, historico


def receber_erro(limite=None):
    limite = Configuracao().max_entrada if limite is None else limite
    print("Cole o erro e o contexto. Termine com FIM em uma linha separada.", file=sys.stderr)
    linhas = []
    tamanho = 0
    while True:
        try:
            linha = input()
        except EOFError:
            break
        if linha.strip() == "FIM":
            break
        tamanho += len(linha) + bool(linhas)
        if tamanho > limite:
            raise ErroConfiguracao(f"O erro ultrapassa {limite} caracteres.")
        linhas.append(linha)
    erro = "\n".join(linhas)
    if not erro.strip():
        raise ErroConfiguracao("Nenhum erro foi informado.")
    return erro


def criar_parser():
    padrao = Configuracao()
    parser = argparse.ArgumentParser(
        description="Investiga bugs Python com Gemini, sem executar ou alterar o código investigado."
    )
    parser.add_argument("--version", action="version", version=f"Agente Debug {VERSAO}")
    parser.add_argument("--projeto", type=Path, help="Raiz autorizada; padrão: casos/ deste repositório.")
    parser.add_argument("--erro-arquivo", type=Path, help="Erro/contexto em .txt, .log ou .md; padrão: terminal.")
    parser.add_argument("--memoria", type=Path, help="Contexto histórico opcional em .md; ignorado por padrão.")
    parser.add_argument("--saida", type=Path, help="Novo arquivo .md para o relatório; não sobrescreve arquivos.")
    parser.add_argument("--modelo", default=os.environ.get("AGENTE_MODELO", padrao.modelo))
    parser.add_argument("--max-consultas", type=int, default=padrao.max_consultas)
    parser.add_argument("--timeout", type=float, default=padrao.timeout, help="Timeout por consulta, em segundos.")
    parser.add_argument("--tempo-total", type=float, default=padrao.tempo_total, help="Orçamento de tempo entre consultas, em segundos.")
    parser.add_argument("--demo", nargs="?", const="media", choices=CASOS, help="Simulação com respostas preparadas; não usa API.")
    return parser


def validar_saida(caminho):
    if caminho is None:
        return
    if caminho.suffix.lower() != ".md" or caminho.exists() or caminho.is_symlink():
        raise ErroConfiguracao("A saída deve ser um arquivo .md novo. Escolha outro nome.")
    if any(p.lower() in DIRETORIOS_EXCLUIDOS for p in caminho.resolve().parts):
        raise ErroConfiguracao("O relatório não pode ser salvo em uma pasta interna excluída.")


def main(argv=None):
    args = criar_parser().parse_args(argv)
    cliente = None
    try:
        config = Configuracao(
            modelo=args.modelo, max_consultas=args.max_consultas,
            timeout=args.timeout, tempo_total=args.tempo_total,
        )
        validar_saida(args.saida)
        if args.demo and (args.projeto is not None or args.erro_arquivo is not None or args.memoria is not None):
            raise ErroConfiguracao("--demo utiliza somente os casos preparados; não combine com projeto, erro ou memória externos.")
        raiz = pasta_caso(args.demo) / "projeto" if args.demo else args.projeto
        ferramentas = FerramentasProjeto(raiz, config)
        instrucoes, memoria = carregar_contexto(args.memoria, config)
        chave = None if args.demo else obter_chave()
        if args.demo:
            config = replace(config, modelo="simulacao-local")
            erro = ler_texto(pasta_caso(args.demo) / "erro.txt", config.max_entrada, "o erro")
        elif args.erro_arquivo:
            if args.erro_arquivo.suffix.lower() not in {".txt", ".log", ".md"} or args.erro_arquivo.name.startswith("."):
                raise ErroConfiguracao("O erro deve estar em um arquivo .txt, .log ou .md não oculto.")
            erro = ler_texto(args.erro_arquivo, config.max_entrada, "o erro")
        else:
            erro = receber_erro(config.max_entrada)
        if not erro.strip():
            raise ErroConfiguracao("Nenhum erro foi informado.")
        cliente = ClienteDemonstracao(args.demo) if args.demo else criar_cliente(config, chave=chave)
        resultado = investigar(cliente, instrucoes, montar_pedido(erro, memoria), ferramentas, config)
        print(gerar_markdown(resultado))
        if args.saida:
            salvar_relatorio(args.saida, resultado)
            print(f"Relatório salvo em {args.saida}", file=sys.stderr)
        return {"analise_produzida": 0, "informacao_insuficiente": 3, "parcial": 4, "falha": 1}[resultado.estado]
    except KeyboardInterrupt:
        print("\nInvestigação cancelada pelo usuário.", file=sys.stderr)
        return 130
    except (ErroConfiguracao, OSError, ValueError, UnicodeError) as falha:
        print(f"Erro: {falha}", file=sys.stderr)
        return 2
    finally:
        if cliente is not None:
            cliente.close()


if __name__ == "__main__":
    raise SystemExit(main())
