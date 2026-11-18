# Avaliação do MVP

## O que foi validado localmente

- Consultas e erros das ferramentas, validação de caminhos e limites.
- Continuidade por ID usando o SDK real com transporte HTTP simulado.
- Uma tentativa HTTP por consulta para 401, 403, 404, 429 e 503.
- Timeout e falha de conexão sem repetição automática.
- Diagnóstico estruturado e recusa de referências a arquivos ou linhas não consultados.
- Exportação Markdown sem sobrescrever arquivos existentes.
- Quatro demonstrações com respostas preparadas e identificação de simulação.
- Correções de referência verificadas por testes determinísticos.
- Instalação em ambiente virtual novo e execução da suíte com Python 3.15: 71 testes, 70 aprovados e um ignorado por privilégio de link simbólico no Windows.

Essas verificações avaliam o software local. Não comprovam a qualidade das respostas reais do Gemini. A validação online e a primeira execução do workflow no GitHub ainda precisam ser registradas.

## Casos e critérios definidos antes da avaliação online

| Caso | Entrada e causa conhecida | Critérios de acerto |
| --- | --- | --- |
| `media` | Média de lista vazia divide por zero. | Citar a divisão por `len(valores)`; propor ValueError para lista vazia; sugerir teste da lista vazia e de uma lista válida. |
| `tipos` | A taxa chega como texto e é somada a um float. | Identificar float + str; converter a taxa numérica de acordo com o comportamento esperado; considerar texto inválido. |
| `multiarquivo` | O chamador passa 10%, mas o módulo usa 10 como fração. | Ler `app.py` e `dominio/descontos.py`; relacionar as duas evidências; propor percentual / 100; verificar descontos 0, 10 e 100. |
| `insuficiente` | Relato genérico sem código nem erro completo. | Retornar `informacao_insuficiente`; pedir traceback, código e comportamento esperado; não inventar causa ou solução verificada. |

Os arquivos investigados estão em `exemplos/<caso>/projeto/`. As correções de referência ficam fora dessa raiz, em `referencia.py`, para que não sejam fornecidas ao modelo. `roteiro_demo.json` contém somente a reprodução offline preparada para a apresentação.

## Reproduzir as simulações

```powershell
python main.py --demo media
python main.py --demo tipos
python main.py --demo multiarquivo
python main.py --demo insuficiente
```

O último comando termina com código 3, que indica informação insuficiente, conforme esperado. Os demais terminam com 0. Nenhum desses comandos chama o Gemini.

## Avaliar com o Gemini real

Depois de instalar as dependências e configurar a chave, execute um caso de cada vez, sem `--demo`:

```powershell
python main.py --projeto exemplos/media/projeto --erro-arquivo exemplos/media/erro.txt --saida relatorios/media-real.md
```

Repita substituindo `media` por `tipos`, `multiarquivo` e `insuficiente`. Essas execuções usam a API e estão sujeitas às cotas e às condições da sua conta. O programa não ativa faturamento e não troca de modelo automaticamente.

Para cada relatório, registre modelo, data, quantidade de consultas, estado, critérios atendidos, erros e limitações. A validação automática confere a estrutura e se as referências foram lidas; a adequação da causa e da correção exige avaliação humana. Não declare acurácia com base apenas nas simulações.

Modelo de registro:

```text
Caso:
Data e modelo:
Estado e número de consultas:
Arquivos relevantes realmente consultados:
Critérios de acerto atendidos:
Critérios não atendidos:
Correção sugerida adequada ao comportamento esperado? Por quê?
Verificação realizada separadamente, por quem e com qual resultado:
Limitações:
```

Somente publique os relatórios revisados, sem credenciais ou dados pessoais. A pasta `relatorios/` é ignorada pelo Git. Uma correção verificada nos exemplos não significa que o agente executa correções ou testes nos projetos que investiga.
