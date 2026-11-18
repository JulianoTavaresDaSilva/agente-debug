# Plano do MVP — Agente Debug

Atualizado após a implementação de 15 de novembro de 2026. Este documento mantém o escopo da revisão inicial e registra o que foi entregue e o que ainda exige validação externa.

## Escopo da versão 0.1.0

Ferramenta de terminal para receber um erro e uma pasta Python autorizada, consultar arquivos sem executá-los ou alterá-los e gerar um diagnóstico com evidências, correção sugerida e verificação recomendada.

O estado "análise produzida" significa que o contrato e as referências foram validados pelo programa. Não significa causa comprovada ou correção verificada.

## Etapas implementadas

### 1. Instalação, configuração e inicialização

- [x] Dependências fixadas em [requirements.txt](../requirements.txt).
- [x] Configuração e limites centralizados em [configuracao.py](../configuracao.py).
- [x] Chave validada antes da entrada interativa.
- [x] Manual obrigatório com mensagem de erro compreensível.
- [x] Memória opcional e desabilitada por padrão.
- [x] Modelo genérico de memória, sem dados pessoais.
- [x] Tratamento de EOF, entrada vazia, limite de entrada e Ctrl+C.
- [x] Comandos documentados para Windows, Linux e macOS.
- [x] Instalação limpa verificada em um segundo ambiente virtual com Python 3.15.

### 2. Comunicação previsível com o Gemini

- [x] SDK atualizado para 3.3.0, que incorpora a correção de contagem de tentativas.
- [x] Verificação da versão validada antes de criar o cliente real.
- [x] Uma tentativa HTTP por consulta e continuação automática desativada.
- [x] Timeout por consulta e orçamento de tempo entre operações.
- [x] Mensagens próprias para autenticação, cota, modelo indisponível, conexão e timeout.
- [x] Testes com o SDK real e transporte HTTP simulado, incluindo contagem de tentativas.
- [x] Nenhuma ativação de faturamento nem troca automática de provedor/modelo.

O orçamento total não interrompe instantaneamente operações HTTP já em andamento. Essa limitação está documentada no README.

### 3. Consulta a uma pasta escolhida pelo usuário

- [x] Argumento --projeto, mantendo casos/ como padrão.
- [x] Descoberta limitada em subpastas, sem seguir links simbólicos na listagem.
- [x] Exclusão de pastas ocultas, ambientes virtuais, Git, caches e node_modules.
- [x] Recusa desses caminhos também na leitura direta.
- [x] Validação de caminhos resolvidos e bloqueio de acessos externos.
- [x] Leitura com caminho, intervalo e linhas numeradas.
- [x] Limites de arquivos, entradas examinadas, profundidade, varredura e contexto.

### 4. Resultado e relatório

- [x] Resultado retornado pelo ciclo com estado, motivo e contadores.
- [x] Distinção entre análise produzida, informação insuficiente, parcial e falha.
- [x] Respostas de falha da API não são tratadas como conclusão normal.
- [x] Validação do contrato JSON e de cada referência contra leituras reais.
- [x] Preservação da lista de leituras e de rascunhos não validados.
- [x] Última consulta reservada para conclusão.
- [x] Entrada do erro por arquivo ou terminal.
- [x] Exportação Markdown sem sobrescrever arquivos.
- [x] Códigos de saída documentados e testes do fluxo completo.

A validação das referências é estrutural. A qualidade da causa e da correção precisa ser avaliada separadamente.

### 5. Exemplos, avaliação e CI

- [x] Três bugs conhecidos e um caso de informação insuficiente.
- [x] Caso que exige relacionar dois arquivos.
- [x] Correções de referência fora da raiz fornecida ao modelo.
- [x] Testes determinísticos das correções de referência.
- [x] Quatro demonstrações offline com indicação explícita de simulação.
- [x] [Relatório de demonstração](DEMONSTRACAO.md) gerado pelo próprio executável.
- [x] [Critérios e procedimento de avaliação online](AVALIACAO.md).
- [x] Workflow de testes para Windows e Linux, com Python 3.11 e 3.15, sem credenciais.
- [ ] Registrar a primeira execução real do workflow após publicar as mudanças.
- [ ] Executar os casos com o Gemini real e registrar a avaliação dos diagnósticos.
- [ ] Criar uma tag de versão depois de conferir os resultados da publicação e da avaliação.

Os testes e as demonstrações locais não consumiram a API. As pendências acima não foram marcadas como concluídas por simulações.

## Arquitetura entregue

| Módulo | Responsabilidade |
| --- | --- |
| [main.py](../main.py) | Terminal, entrada e gerenciamento do cliente. |
| [agente.py](../agente.py) | Ciclo de investigação e encerramento. |
| [cliente_gemini.py](../cliente_gemini.py) | SDK, credenciais e tratamento de falhas. |
| [ferramentas.py](../ferramentas.py) | Descoberta e leitura com restrições e orçamento. |
| [resultado.py](../resultado.py) | Contrato do diagnóstico, referências e relatório. |
| [configuracao.py](../configuracao.py) | Valores padrão e validação da configuração. |
| [demonstracao.py](../demonstracao.py) | Reprodução offline de respostas preparadas. |

## Como conferir a entrega

~~~powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python main.py --demo media
python main.py --demo multiarquivo
~~~

Para investigar com a API, consulte o [README](../README.md) e o [procedimento de avaliação](AVALIACAO.md).

## Fora desta versão

Interface web, autenticação de usuários, banco de dados, RAG, múltiplos agentes ou provedores, suporte a muitas linguagens, edição/execução automática de código e escrita automática de memória. A conversa contínua pode ser avaliada depois; nesta versão, falta de contexto é um resultado explícito.
