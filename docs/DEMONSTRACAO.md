# Relatório de investigação

> SIMULAÇÃO LOCAL — não é uma resposta real do Gemini

- Estado: **analise_produzida**
- Modelo: `simulacao-local`
- Consultas: 3
- Ferramentas executadas: 2
- Encerramento: Diagnóstico produzido; correção ainda não verificada.

## Problema

Calcular a média de uma lista vazia causa divisão por zero.

## Evidências

### `calculadora.py:1-2`

A função divide pela quantidade de elementos sem tratar uma lista vazia.

````python
def calcular_media(valores):
    return sum(valores) / len(valores)
````


### Arquivos efetivamente consultados

- `calculadora.py:1-6`

## Causa provável

O denominador len(valores) é zero quando a lista está vazia.

## Correção sugerida

Antes da divisão, rejeite a lista vazia com ValueError e uma mensagem clara.

## Verificação sugerida

- Verifique que [2, 4, 6] produz 4.
- Verifique que [] levanta ValueError após a correção.

O agente não alterou o código investigado nem executou seus testes.

## Pendências

- Aplicar a correção e executar os testes no projeto investigado.
