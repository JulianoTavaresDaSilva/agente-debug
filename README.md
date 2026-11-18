# Agente Debug

Agente de terminal para investigar bugs em projetos Python usando o Gemini. Recebe um erro, consulta arquivos de uma pasta autorizada e produz um diagnóstico com referências a linhas, correção sugerida e passos de verificação.

O projeto explora chamadas de ferramentas (*function calling*), orçamento de investigação, validação de evidências e testes de integração com HTTP simulado, usando Python e o SDK oficial do Google.

**Versão técnica: 0.1.0.** A implementação e as demonstrações offline são testadas localmente. A avaliação de diagnósticos com a API real e a primeira execução do CI no GitHub ainda precisam ser registradas em [Avaliação do MVP](docs/AVALIACAO.md).

## Experimente sem chave de API

Depois de instalar as dependências:

~~~powershell
python main.py --demo media
~~~

O programa consulta os arquivos do exemplo e gera um relatório com respostas previamente preparadas. A saída é marcada como **SIMULAÇÃO LOCAL**: esse modo não utiliza um modelo local nem chama o Gemini.

Outros casos:

~~~powershell
python main.py --demo tipos
python main.py --demo multiarquivo
python main.py --demo insuficiente
~~~

O último caso reconhece informação insuficiente e retorna código de saída 3. Veja um [relatório de demonstração](docs/DEMONSTRACAO.md) e os [critérios de avaliação](docs/AVALIACAO.md).

## Funcionalidades

- Entrada interativa com várias linhas ou leitura do erro por arquivo.
- Seleção da pasta autorizada com --projeto.
- Descoberta de arquivos Python em subpastas, excluindo diretórios internos e ocultos.
- Leitura integral ou por faixa, com caminho e linhas numeradas.
- Validação das referências do diagnóstico contra os trechos efetivamente consultados.
- Memória histórica opcional, selecionada explicitamente.
- Limites de consultas, ferramentas, tempo e volume de contexto.
- Uma tentativa HTTP por consulta, sem repetição ou continuação automáticas do SDK.
- Resultado explícito: análise produzida, informação insuficiente, parcial ou falha.
- Relatório Markdown com criação exclusiva: um arquivo existente nunca é sobrescrito.
- Casos de exemplo, testes locais e workflow de CI para Windows e Linux.

O agente sugere mudanças. Ele não edita nem executa o projeto investigado e não declara que verificou uma correção.

## Instalação

Requisitos: **Python 3.11 ou superior** e acesso à internet para instalar as dependências. A execução real também exige chave do Gemini e acesso ao modelo escolhido.

Na raiz do repositório, usando PowerShell:

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --demo media
~~~

Os comandos usam diretamente o Python do ambiente virtual, sem exigir ativação. Os demais exemplos com python pressupõem um terminal que utilize esse ambiente; no PowerShell, você também pode substituí-lo por .\.venv\Scripts\python.exe.

Em Linux ou macOS:

~~~bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py --demo media
~~~

A versão do SDK foi fixada em 3.3.0, com transporte HTTPX explícito. A atualização inclui a [correção da contagem de tentativas introduzida na versão 3.0](https://github.com/googleapis/python-genai/releases/tag/v3.0.0); o comportamento é conferido por testes de transporte.

## Usar com o Gemini

Obtenha a chave no [Google AI Studio](https://aistudio.google.com/api-keys) e configure-a na sessão atual:

~~~powershell
$env:GEMINI_API_KEY = "SUA_CHAVE_AQUI"
~~~

Em Linux ou macOS:

~~~bash
export GEMINI_API_KEY="SUA_CHAVE_AQUI"
~~~

O SDK também reconhece GOOGLE_API_KEY, que tem prioridade quando ambas estão definidas. [.env.example](.env.example) documenta as variáveis; arquivos .env **não são carregados automaticamente**.

Investigue o exemplo usando a API real:

~~~powershell
.\.venv\Scripts\python.exe main.py --projeto exemplos/media/projeto --erro-arquivo exemplos/media/erro.txt --saida relatorios/media-real.md
~~~

Para investigar seu próprio projeto:

~~~powershell
.\.venv\Scripts\python.exe main.py --projeto "C:\caminho\meu-projeto"
~~~

Cole o erro e o contexto, encerrando com FIM em uma linha separada. O fim da entrada também encerra a coleta. A pasta padrão é [casos/](casos/), relativa ao repositório.

O projeto não configura faturamento, não garante disponibilidade de cota gratuita e não troca para outro modelo ou serviço automaticamente. Confira as condições da sua conta antes de usar a API.

## Opções do terminal

~~~powershell
python main.py --help
python main.py --version
~~~

| Opção | Uso |
| --- | --- |
| --projeto PASTA | Raiz autorizada para as ferramentas. |
| --erro-arquivo ARQUIVO | Erro em UTF-8, com extensão .txt, .log ou .md; padrão: entrada interativa. |
| --memoria ARQUIVO.md | Contexto histórico opcional. Uma memória ausente permite continuar. |
| --saida ARQUIVO.md | Cria um relatório novo; arquivos existentes são recusados antes da consulta. |
| --modelo NOME | Modelo do Gemini; padrão: gemini-3.6-flash ou AGENTE_MODELO. |
| --max-consultas N | Orçamento de consultas, incluindo a conclusão; padrão: 5. |
| --timeout SEGUNDOS | Timeout por consulta; padrão: 30. |
| --tempo-total SEGUNDOS | Orçamento de tempo conferido entre consultas e ferramentas; padrão: 120. |
| --demo [CASO] | Reprodução offline com respostas preparadas; padrão: media. |

O modo de demonstração usa somente os exemplos preparados e não aceita projeto, erro ou memória externos.

## Resultado e relatório

O programa solicita um diagnóstico JSON ao modelo e valida seu formato e suas referências antes de apresentá-lo como análise produzida. Respostas vazias, incompletas ou fora do contrato geram um resultado parcial.

O relatório contém problema, evidências com trechos reais, causa provável, correção sugerida, verificação recomendada e pendências. A validação das referências não comprova que o raciocínio ou a correção estão certos.

| Estado | Código de saída | Significado |
| --- | --- | --- |
| analise_produzida | 0 | Contrato e referências validados; a correção ainda precisa ser verificada. |
| falha | 1 | A consulta falhou ou a API informou falha/cancelamento. |
| Erro de configuração ou entrada | 2 | Chave, pasta, arquivo, argumento ou saída inválidos. |
| informacao_insuficiente | 3 | O diagnóstico reconheceu a falta de contexto. |
| parcial | 4 | Limite atingido, resposta incompleta ou diagnóstico não validado. |
| Cancelamento pelo usuário | 130 | Execução interrompida com Ctrl+C. |

Falhas e limites preservam a lista dos arquivos já consultados. Não há nova consulta extra após esgotar o orçamento.

## Ferramentas e limites

| Ferramenta | Argumentos | Resultado |
| --- | --- | --- |
| listar_arquivos | Nenhum | Caminhos relativos dos arquivos Python e indicador de truncamento. |
| ler_arquivo | caminho; linha_inicio e linha_fim opcionais | Caminho, intervalo efetivamente lido e conteúdo numerado. |

Os valores padrão estão em [configuracao.py](configuracao.py):

- Até cinco consultas e cinco ferramentas por resposta; a última consulta é reservada para conclusão sem novas ferramentas.
- Até 200 arquivos listados, 2.000 entradas examinadas e dez níveis de subpastas.
- Até 20.000 caracteres por leitura, 20.000 linhas e um milhão de caracteres de varredura por leitura.
- Até 80.000 caracteres nos resultados bem-sucedidos das ferramentas por investigação.
- Até 20.000 caracteres de entrada, 10.000 de memória e 30.000 de manual.
- Até 4.096 tokens de saída por consulta.

Limites em caracteres não equivalem a tokens ou valores monetários. O timeout HTTP limita a espera do transporte; o orçamento total é conferido entre operações, sem prometer interromper instantaneamente uma leitura HTTP já em andamento.

## Arquitetura

~~~mermaid
flowchart TD
    CLI[main.py: terminal e configuração] --> CICLO[agente.py: investigação]
    MANUAL[agent.md e memória opcional] --> CICLO
    CICLO --> API[cliente_gemini.py]
    API --> GEMINI[Gemini Interactions API]
    GEMINI --> CICLO
    CICLO --> TOOLS[ferramentas.py: leitura autorizada]
    TOOLS --> CICLO
    CICLO --> SAIDA[resultado.py: contrato e relatório]
~~~

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| [main.py](main.py) | Argumentos, entrada, contexto, criação/fechamento do cliente e código de saída. |
| [agente.py](agente.py) | Ciclo de consultas, continuidade e encerramento. |
| [cliente_gemini.py](cliente_gemini.py) | Credenciais, SDK, timeout e mensagens seguras de falha. |
| [ferramentas.py](ferramentas.py) | Raiz autorizada, descoberta, leitura e orçamento de contexto. |
| [resultado.py](resultado.py) | Validação do diagnóstico e referências; geração do relatório. |
| [configuracao.py](configuracao.py) | Configuração tipada e limites. |
| [demonstracao.py](demonstracao.py) | Cliente de reprodução offline explicitamente identificado. |
| [agent.md](agent.md) | Manual de investigação enviado ao modelo. |
| [exemplos/](exemplos/) | Três bugs conhecidos, um caso insuficiente e correções de referência. |
| [tests/](tests/) | Testes unitários, de arquivos, transporte e fluxo completo com HTTP simulado. |

## Memória e dados

Nenhuma memória é carregada por padrão, inclusive o arquivo legado memory.md. Para usar contexto histórico, copie [memory.example.md](memory.example.md) para memory.local.md, edite-o e passe --memoria memory.local.md.

A memória selecionada é enviada ao modelo e não é atualizada automaticamente. O manual é obrigatório. Código, erro, memória e resultados das ferramentas são enviados à API durante uma investigação real; revise o material que pretende compartilhar.

O ciclo usa store=True e previous_interaction_id para manter a continuidade das interações no provedor. Isso não é um modo de execução local; consulte as políticas e configurações de dados da sua conta.

As ferramentas recusam caminhos externos, arquivos que não sejam Python e pastas ocultas ou excluídas. A listagem não segue links simbólicos. O programa não executa o código consultado. Estas restrições não substituem o isolamento do sistema operacional para diretórios alterados por processos não confiáveis durante a investigação.

Credenciais, ambientes virtuais, caches, memória local e relatórios gerados estão no [.gitignore](.gitignore). Nunca coloque uma chave real no código ou no arquivo de exemplo.

## Testes e CI

~~~powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
~~~

A suíte usa unittest. Não precisa de chave: o cliente é simulado ou o SDK real recebe um httpx.MockTransport. O teste de link simbólico pode ser ignorado quando o Windows não permitir sua criação. A limpeza dos arquivos temporários fica restrita às pastas criadas pelos testes.

O [workflow de testes](.github/workflows/tests.yml) instala as dependências e roda a suíte em Windows e Linux, com Python 3.11 e 3.15, sem configurar segredos de API. Sua primeira execução acontecerá após o envio ao GitHub.

## Portfólio e evolução

O [plano do MVP](docs/PLANO_MVP.md) registra o escopo e o estado das entregas. Os [casos e critérios de avaliação](docs/AVALIACAO.md) distinguem validação local, demonstração preparada e diagnóstico real do modelo.

Interface web, edição e execução automáticas, memória automática, múltiplos agentes e outros provedores ficam fora desta versão.
