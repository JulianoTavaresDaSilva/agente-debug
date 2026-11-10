# Memória — Agente Investigador de Bugs

Última atualização: 2026-10-20.

Origem deste registro inicial: decisões e saídas de terminal compartilhadas pelo usuário na conversa de desenvolvimento. Não é um histórico gerado automaticamente pelo agente em execução.

## 1. Estado atual do projeto do agente

| Item | Estado conhecido | Origem |
| --- | --- | --- |
| Identificador do projeto | `agente-debug` | Pasta mostrada no terminal |
| Objetivo | Aprender a construir um agente para investigar bugs e stack traces | Decisão do usuário |
| Implementação | Python, começando com código próprio | Decisão do usuário |
| Interface | Terminal | Código e execução compartilhados |
| Ambiente | Windows; comandos executados no CMD | Saídas de terminal compartilhadas |
| Python | 3.15.0 | Saída de `python --version` e do Python da `.venv` |
| Ambiente virtual | `.venv` criada e utilizada com sucesso no local original | Saídas de terminal compartilhadas |
| Biblioteca | `google-genai` 2.31.0 instalada; importação bem-sucedida | Saídas da instalação e do teste de importação |
| Modelo utilizado | `gemini-3.8-flash` via `client.interactions.create` | Código fornecido e respostas da execução compartilhadas |
| Chave da API | Criada; chamadas autenticadas já tiveram sucesso | Relato do usuário e respostas da execução |
| Faturamento | O usuário relatou a opção “Configurar faturamento” no AI Studio | Relato datado de 2026-10-20; estado atual não inspecionado |
| Restrição de custo | Utilizar somente a cota gratuita, sem ativar faturamento | Decisão do usuário |
| Entrada de erros | `input()` recebe uma mensagem de uma linha | Código e execução compartilhados |
| Instruções atuais confirmadas | A última versão executada com sucesso continha as instruções no próprio `main.py` | Código e execução compartilhados |
| Leitura de `agent.md` | Código proposto; execução dessa versão ainda não confirmada | Etapa de implementação discutida |
| Ferramentas de investigação | Leitura e listagem de arquivos planejadas; implementação ainda não confirmada | Planejamento |
| Memória automática | Leitura e gravação ainda não confirmadas | Planejamento |
| Git | Inicialização de repositório e publicação não confirmadas | Informação ainda ausente |

O caminho observado nas execuções foi `C:\Users\Juliano\agente-debug`. O usuário cogitou mover a pasta para Documentos e informou que pretende abri-la no VS Code. A mudança de caminho e a configuração do editor ainda não foram confirmadas.

## 2. Preferências e hábitos

### Preferências declaradas — 2026-10-20

- Aprender como o agente é construído, compreendendo o funcionamento das partes.
- Usar Python e a API gratuita do Gemini.
- Manter `agent.md` como manual da função do agente.
- Manter `memory.md` para aprendizados, hábitos confirmados e histórico pessoal ou do projeto relevante ao trabalho.

Origem: pedidos e escolhas explícitos do usuário nesta conversa.

### Hábitos confirmados

Nenhum hábito recorrente confirmado até o momento.

## 3. Decisões de implementação

Decisões estabelecidas nesta conversa em 2026-10-20:

- Começar com pequenos exemplos de código Python.
- Disponibilizar ferramentas para listar e ler arquivos dentro de uma pasta autorizada.
- Sugerir correções sem editar código nem executar comandos na primeira versão.
- Adotar inicialmente até cinco rodadas de consulta ao modelo por investigação. Esse limite ainda precisa ser implementado.
- Atualizar a memória ao encerrar uma investigação quando houver informação útil nova e a gravação estiver implementada.
- Adicionar busca externa em documentação somente depois de a investigação local funcionar.

## 4. Histórico resumido do desenvolvimento

### 2026-10-20 — Ambiente preparado

- O usuário criou a pasta `agente-debug` e o ambiente virtual `.venv`.
- Instalou `google-genai` 2.31.0 e confirmou a importação.
- Evidência: saídas de terminal compartilhadas pelo usuário.

### 2026-10-20 — Primeira chamada ao modelo

- Uma execução foi interrompida com `Ctrl+C` enquanto aguardava dados pela conexão; o traceback terminou em `KeyboardInterrupt`.
- Em uma nova execução, o modelo respondeu à pergunta sobre `TypeError`.
- A causa da demora inicial não foi determinada. O sucesso posterior não comprova a causa da demora.
- Evidência: traceback e resposta compartilhados pelo usuário.

### 2026-10-20 — Entrada de erro pelo terminal

- O programa passou a receber o erro usando `input()`.
- O usuário testou `TypeError: unsupported operand type(s) for +: 'int' and 'str'`.
- O modelo retornou significado, possíveis causas, exemplos de correção e informações faltantes.
- Resultado confirmado: o fluxo entrada → chamada à API → exibição da resposta funcionou nesse teste.
- Limite da verificação: não houve leitura de código, aplicação de correção ou teste de um bug real.

## 5. Aprendizados verificados de depuração

Ainda não há caso real com causa e correção verificadas. A análise de `TypeError` foi um teste de comunicação e resposta a uma mensagem de exemplo.

## 6. Investigações de outros projetos

Nenhum projeto externo investigado até o momento.

## 7. Hipóteses e tentativas em aberto

Nenhum diagnóstico ativo. A demora da chamada inicial permanece sem causa identificada e a conexão teve sucesso posteriormente.

## 8. Pendências

- [x] Criar a chave da API, sem registrar seu valor aqui.
- [x] Preparar o ambiente Python no local original do projeto.
- [x] Instalar e importar a biblioteca oficial do Gemini.
- [x] Obter resposta do modelo em uma primeira chamada.
- [x] Receber uma mensagem de erro pelo terminal e obter uma análise.
- [ ] Confirmar o local atual da pasta e a configuração do VS Code.
- [ ] Confirmar a leitura de `agent.md` e seu envio como instrução do sistema.
- [ ] Implementar leitura da memória relevante.
- [ ] Implementar ferramentas de listagem e leitura com validação de caminhos.
- [ ] Implementar o ciclo de ferramentas com limite de etapas.
- [ ] Implementar tratamento de tempo limite, falhas de rede e cotas da API.
- [ ] Implementar a gravação validada da memória sem perder registros existentes.
- [ ] Investigar um pequeno projeto com um bug conhecido e conferir a correção.
