"""Reprodução explícita de respostas preparadas, sem rede e sem um modelo local."""

import json
from types import SimpleNamespace

from configuracao import PASTA_PROJETO

CASOS = ("media", "tipos", "multiarquivo", "insuficiente")


def pasta_caso(nome):
    if nome not in CASOS:
        raise ValueError("Caso de demonstração desconhecido.")
    return PASTA_PROJETO / "exemplos" / nome


class ClienteDemonstracao:
    simulacao = True

    def __init__(self, nome):
        dados = json.loads((pasta_caso(nome) / "roteiro_demo.json").read_text(encoding="utf-8"))
        self.roteiro = dados
        self.indice = 0
        self.interactions = self

    def create(self, **parametros):
        numero = self.indice
        self.indice += 1
        lotes = self.roteiro["chamadas"]
        if numero < len(lotes) and parametros.get("tools"):
            passos = [
                SimpleNamespace(
                    type="function_call", name=c["nome"], arguments=c["argumentos"],
                    id=f"demo-{numero}-{i}",
                ) for i, c in enumerate(lotes[numero])
            ]
            return SimpleNamespace(id=f"demo-{numero}", status="requires_action", steps=passos, output_text="")
        return SimpleNamespace(
            id=f"demo-{numero}", status="completed", steps=[],
            output_text=json.dumps(self.roteiro["diagnostico"], ensure_ascii=False),
        )

    def close(self):
        pass
