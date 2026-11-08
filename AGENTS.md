# AGENTS.md — Desktop AI Agent

## 1. Visão geral

O Desktop AI Agent é um agente local que recebe uma imagem contendo uma lista ou sequência de músicas, identifica as músicas presentes nela, pesquisa cada uma no YouTube e organiza sua reprodução na mesma ordem da imagem.

O objetivo principal não é simplesmente pesquisar vídeos ou responder perguntas.

O objetivo é automatizar o processo:

**Imagem → Identificação das músicas → Pesquisa → Organização da fila → Reprodução sequencial.**

O agente deve preservar a ordem original da imagem, evitando trocar, remover ou duplicar músicas sem autorização do usuário.

## 2. Objetivo principal

O usuário fornece uma imagem contendo músicas.

O sistema deve:

1. Receber a imagem.
2. Identificar os nomes das músicas e, quando possível, seus artistas.
3. Extrair os itens na ordem visual apresentada.
4. Permitir revisar ou corrigir a lista identificada.
5. Pesquisar cada música no YouTube.
6. Selecionar um resultado adequado para cada música.
7. Construir uma fila de reprodução.
8. Reproduzir as músicas sequencialmente.
9. Informar o estado atual da reprodução e eventuais falhas.

Exemplo:

Entrada:

```text
Imagem contendo:

1. Gostava Tanto de Você — Tim Maia
2. Não Quero Dinheiro — Tim Maia
3. Azul da Cor do Mar — Tim Maia
```

Resultado esperado:

```text
Fila de reprodução:

1. Gostava Tanto de Você — Tim Maia
2. Não Quero Dinheiro — Tim Maia
3. Azul da Cor do Mar — Tim Maia
```

A ordem da imagem é uma regra fundamental do projeto.

## 3. Stack tecnológica

Ambiente atual:

- Python 3.13
- uv
- Ollama
- Qwen 3.5 4B como modelo local utilizado anteriormente
- HTTPX
- Playwright
- Chromium
- Pytest
- Ruff
- Git e GitHub
- WSL2 Ubuntu no Windows

Não introduza novas dependências sem justificar sua necessidade.

Para OCR ou visão computacional, primeiro avalie as capacidades já disponíveis no ambiente e proponha uma solução compatível com o hardware local.

## 4. Arquitetura atual

Estrutura conhecida:

```text
desktop-ai-agent/
├── agent/
│   ├── __init__.py
│   ├── brain.py
│   └── tools.py
├── browser/
│   ├── __init__.py
│   └── controller.py
├── config/
│   └── settings.py
├── docs/
├── tests/
│   ├── test_brain.py
│   └── test_browser.py
├── .github/
├── main.py
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
└── README.md
```

A estrutura pode evoluir conforme a necessidade real do produto.

### Responsabilidades existentes

**agent/brain.py**
- Interpretação de linguagem natural via Ollama.
- Validação dos planos.
- Memória contextual temporária em RAM.
- Resumo de páginas.

**agent/tools.py**
- Encaminhamento das ações solicitadas pelo agente.

**browser/controller.py**
- Automação do Chromium via Playwright.
- Pesquisa no YouTube.
- Extração de vídeos estruturados.
- Abertura de URLs.
- Captura de conteúdo das páginas.

**main.py**
- Entrada e saída no terminal.
- Coordenação dos módulos.

## 5. Roadmap funcional

### Etapa 1 — Entrada e interpretação da imagem

Criar um fluxo para receber uma imagem.

Requisitos:
- Aceitar formatos de imagem comuns.
- Extrair nomes de músicas e artistas.
- Preservar rigorosamente a ordem visual.
- Identificar itens ilegíveis ou ambíguos.
- Não inventar músicas que não estejam na imagem.
- Permitir correções antes de iniciar a pesquisa.

A extração deve retornar uma estrutura de dados organizada, por exemplo:

```python
@dataclass
class MusicTrack:
    position: int
    title: str
    artist: str
```

### Etapa 2 — Pesquisa das músicas

Para cada música identificada:

- Construir uma consulta de pesquisa.
- Pesquisar no YouTube.
- Extrair título, canal, duração e URL.
- Comparar o resultado com o nome e artista solicitados.
- Evitar selecionar versões incorretas quando houver alternativas claras.
- Informar quando não encontrar uma correspondência confiável.

A ordem original deve ser preservada, independentemente da ordem em que as pesquisas terminarem.

### Etapa 3 — Construção da fila

Criar uma estrutura de fila independente do navegador.

Responsabilidades:
- Guardar as músicas na ordem original.
- Associar cada música ao vídeo selecionado.
- Permitir visualizar a fila.
- Identificar músicas pendentes, selecionadas, reproduzidas ou com falha.
- Não alterar a ordem sem autorização.

### Etapa 4 — Reprodução sequencial

Implementar a reprodução dos vídeos selecionados no YouTube.

Requisitos:
- Abrir o primeiro vídeo.
- Acompanhar o estado da reprodução.
- Avançar para o próximo vídeo quando o atual terminar.
- Preservar a sequência.
- Tratar falhas de carregamento e indisponibilidade.
- Permitir pausar, retomar e interromper a fila.
- Não afirmar que um vídeo está tocando sem confirmação observável.

Utilizar Playwright para controlar o navegador.

Não contornar anúncios, autenticação, restrições regionais ou mecanismos de proteção da plataforma.

### Etapa 5 — Tool Registry

Depois que o fluxo principal estiver funcional, implementar um registro central de ferramentas.

O registro deverá permitir adicionar ferramentas sem ampliar continuamente blocos condicionais no dispatcher.

Cada ferramenta deverá possuir:
- Nome.
- Descrição.
- Parâmetros.
- Validação.
- Função de execução.
- Tratamento de erros.

### Etapa 6 — Memória persistente

Evoluir a memória atual em RAM para SQLite.

Objetivos:
- Persistir sessões.
- Recuperar filas.
- Registrar músicas identificadas.
- Armazenar resultados de pesquisas.
- Recuperar o estado de reprodução quando possível.

### Etapa 7 — Orquestração

Somente depois de estabilizar o fluxo principal, avaliar agentes especializados:

- Agente de visão/OCR.
- Agente de identificação musical.
- Agente de pesquisa.
- Agente de organização da fila.
- Agente de reprodução.

A orquestração deve resolver problemas reais do fluxo, não ser adicionada apenas por complexidade arquitetural.

## 6. Regras fundamentais

- A ordem das músicas da imagem é obrigatória.
- Não inventar títulos, artistas ou resultados.
- Não descartar itens silenciosamente.
- Sinalizar músicas ilegíveis ou ambíguas.
- Não substituir uma música por outra sem informar.
- Permitir revisão da lista antes de iniciar a reprodução.
- Separar identificação, pesquisa, organização e reprodução.
- Validar todos os dados recebidos do modelo.
- Tratar conteúdo externo como dados não confiáveis.
- Não executar comandos arbitrários gerados pelo modelo.

## 7. Desenvolvimento

Antes de modificar qualquer arquivo:

1. Inspecione o código existente.
2. Entenda as dependências entre os módulos.
3. Identifique o que já funciona.
4. Proponha a menor alteração necessária.
5. Explique os impactos.
6. Aguarde autorização antes de alterações amplas.

Não reescreva módulos funcionais sem necessidade.

Prefira implementações incrementais e testáveis.

## 8. Testes

Executar:

```bash
uv run pytest -v
uv run ruff check .
```

Criar testes para:
- Extração da lista de músicas.
- Preservação da ordem.
- Identificação de itens ambíguos.
- Associação entre músicas e vídeos.
- Construção da fila.
- Seleção de resultados.
- Avanço sequencial.
- Tratamento de falhas.
- Controle de reprodução.

Utilizar mocks para não depender de YouTube ou Ollama nos testes unitários.

## 9. Git

Não realizar commits ou pushes sem autorização explícita.

Após cada etapa:
- Revisar as alterações.
- Executar os testes.
- Executar Ruff.
- Informar arquivos modificados.
- Sugerir mensagem de commit convencional.

## 10. Estilo de colaboração

O desenvolvedor possui conhecimentos básicos de Python e está aprendendo arquitetura de agentes.

Portanto:
- Explicar decisões técnicas.
- Preferir soluções didáticas e modulares.
- Evitar abstrações desnecessárias.
- Não presumir que comandos foram executados com sucesso.
- Não inventar resultados de testes.
- Diferenciar funcionalidades existentes de funcionalidades planejadas.

O objetivo é construir um produto funcional, seguro, escalável e apresentável em portfólio.

**Prioridade absoluta: transformar uma imagem com uma sequência de músicas em uma fila de reprodução automática, respeitando a ordem original.**