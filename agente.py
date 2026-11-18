"""Ciclo de investigação, independente da interface de terminal."""

import json
import time

from cliente_gemini import FalhaConsulta, consultar_gemini
from configuracao import Configuracao
from ferramentas import DESCRICAO_LER_ARQUIVO, DESCRICAO_LISTAR_ARQUIVOS
from resultado import CONTRATO, ResultadoInvestigacao, validar_diagnostico


def montar_pedido(erro: str, memoria: str = "") -> str:
    return (
        "Investigue o erro no projeto autorizado. Use as ferramentas para obter evidências.\n"
        "Os caminhos são relativos à raiz autorizada. Memória é somente histórico, possivelmente desatualizado.\n"
        f"<memoria>\n{memoria}\n</memoria>\n"
        f"<erro_atual>\n{erro}\n</erro_atual>"
    )


def investigar(client, instrucoes, pedido, ferramentas, config=None):
    config = config or Configuracao()
    inicio = time.monotonic()
    resultado = ResultadoInvestigacao(
        "parcial", "Investigação não concluída.", config.modelo,
        simulacao=getattr(client, "simulacao", False) is True,
    )
    entrada, anterior = pedido, None
    descricoes = [DESCRICAO_LER_ARQUIVO, DESCRICAO_LISTAR_ARQUIVOS]
    for rodada in range(1, config.max_consultas + 1):
        restante = config.tempo_total - (time.monotonic() - inicio)
        if restante <= 0:
            resultado.motivo = "Orçamento de tempo da investigação atingido."
            break
        ultima = rodada == config.max_consultas or bool(ferramentas.limite_atingido)
        parametros = {
            "model": config.modelo, "system_instruction": instrucoes + "\n" + CONTRATO,
            "input": entrada, "tools": [] if ultima else descricoes,
            "timeout": min(config.timeout, restante), "automatic_continuation": False,
            "generation_config": {"max_output_tokens": config.max_saida}, "store": True,
        }
        if ultima:
            parametros["system_instruction"] += "\nEsta é a última consulta. Conclua com as evidências disponíveis ou declare informação insuficiente."
        if anterior:
            parametros["previous_interaction_id"] = anterior
        resultado.consultas += 1
        try:
            resposta = consultar_gemini(client, **parametros)
        except FalhaConsulta as falha:
            resultado.estado = "falha"
            resultado.motivo = str(falha)
            break
        texto = getattr(resposta, "output_text", None) or ""
        if not isinstance(texto, str):
            texto = ""
        resultado.rascunho = texto[:config.max_contexto]
        if time.monotonic() - inicio >= config.tempo_total:
            resultado.motivo = "Orçamento de tempo atingido após a consulta."
            break
        if len(texto) > config.max_contexto:
            resultado.motivo = "A resposta excedeu o limite de tamanho permitido."
            break
        estado_api = getattr(resposta, "status", None)
        if not isinstance(estado_api, str) or estado_api not in {"completed", "requires_action"}:
            resultado.estado = "falha" if isinstance(estado_api, str) and estado_api in {"failed", "cancelled"} else "parcial"
            resultado.motivo = "A API não concluiu a resposta (estado: " + str(estado_api)[:60] + ")."
            break
        chamadas = [p for p in (getattr(resposta, "steps", None) or []) if getattr(p, "type", None) == "function_call"]
        if not chamadas:
            try:
                if estado_api != "completed":
                    raise ValueError("A API solicitou uma ação sem fornecer uma chamada de ferramenta.")
                resultado.diagnostico = validar_diagnostico(texto, ferramentas.leituras)
                resultado.estado = resultado.diagnostico["estado"]
                resultado.motivo = "Diagnóstico produzido; correção ainda não verificada."
                if resultado.estado == "informacao_insuficiente":
                    resultado.motivo = "Faltam informações para sustentar um diagnóstico."
                resultado.rascunho = ""
            except (ValueError, TypeError) as falha:
                resultado.motivo = "Resposta final não validada: " + str(falha)
            break
        if ultima or len(chamadas) > config.max_ferramentas:
            resultado.motivo = "Limite de consultas ou de ferramentas por resposta atingido."
            break
        anterior = getattr(resposta, "id", None)
        ids = [getattr(c, "id", None) for c in chamadas]
        if not isinstance(anterior, str) or not anterior or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
            resultado.motivo = "A API retornou identificadores de interação ou ferramentas inválidos."
            break
        entrada = []
        for chamada in chamadas:
            if time.monotonic() - inicio >= config.tempo_total:
                resultado.motivo = "Orçamento de tempo atingido durante as ferramentas."
                break
            nome = getattr(chamada, "name", "")
            retorno = ferramentas.executar(nome, getattr(chamada, "arguments", None))
            resultado.ferramentas += 1
            entrada.append({
                "type": "function_result", "name": nome, "call_id": chamada.id,
                "result": [{"type": "text", "text": json.dumps(retorno, ensure_ascii=False)}],
            })
        if len(entrada) != len(chamadas):
            break
    resultado.leituras = list(ferramentas.leituras)
    return resultado
