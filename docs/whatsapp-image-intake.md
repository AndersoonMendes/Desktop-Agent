# Pesquisa: imagem mais recente de um grupo do WhatsApp

## Pergunta

O agente pode buscar a imagem mais recente em um grupo que já está aberto no
WhatsApp Web do Chrome e enviá-la ao fluxo de identificação de músicas?

## Resultado inicial

É tecnicamente possível automatizar a interface do WhatsApp Web, mas o projeto
hoje não tem acesso à sessão do Chrome do usuário. O Playwright inicia um
navegador isolado; ele não herda a conta que já está conectada no Chrome normal.
Também não existe neste repositório uma integração oficial com o WhatsApp.

A Cloud API do WhatsApp é voltada à conta WhatsApp Business e a webhooks de
mensagens recebidas por essa conta. A Groups API documentada pela Meta não é um
conector geral para ler qualquer grupo pessoal já existente. Portanto, ela não
parece atender ao caso de uma imagem publicada em um grupo comum que já está
aberto no Chrome. Referências: [Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/),
[Groups API](https://developers.facebook.com/docs/whatsapp/cloud-api/groups/) e
[mídia da Cloud API](https://developers.facebook.com/docs/whatsapp/cloud-api/reference/media/).

## Caminhos possíveis

### 1. Chrome extension local — caminho mais integrado

Uma extensão instalada pelo usuário pode operar somente em `web.whatsapp.com`,
usar a aba já autenticada, limitar a busca ao grupo escolhido e oferecer o
comando “Usar imagem mais recente”. A extensão entregaria a imagem baixada ao
agente local, que reutilizaria `AgentBrain.recognize_songs` e a fila existente.

Esse caminho evita copiar cookies ou abrir a base local do WhatsApp. A extensão
dependeria da interface e do DOM interno do WhatsApp Web, que não são uma API
estável: mudanças do site podem exigir manutenção. O primeiro protótipo deve
exigir que o usuário abra o grupo, verificar o nome do grupo na tela e mostrar
uma prévia da imagem selecionada antes de processá-la.

### 2. Chrome DevTools Protocol — possível, mas concede acesso amplo

O agente poderia conectar via CDP a um Chrome iniciado explicitamente com uma
porta de depuração local. Isso permite localizar a aba do WhatsApp Web e
interagir com a página existente, mas dá ao processo acesso amplo às abas desse
Chrome e exige encerrar e reiniciar o navegador com configuração especial. Não
é a primeira escolha para este aplicativo.

### 3. Pasta de entrada — alternativa simples e robusta

O usuário baixa a foto do WhatsApp para `images/`; o agente escolhe a imagem
mais recente dessa pasta e inicia o fluxo atual. Isso não captura mensagens do
grupo automaticamente, mas mantém o processamento desacoplado da interface do
WhatsApp e oferece uma primeira entrega estável.

## Próximo protótipo recomendado

Começar com a pasta `images/` e um comando `/imagem-recente`, que mostra nome,
data e prévia da imagem antes da confirmação. Em paralelo, validar uma extensão
local com escopo restrito: grupo explicitamente escolhido, somente a imagem
mais recente, confirmação visual e transmissão apenas para `localhost`. Não
ler nem armazenar o histórico completo do grupo.

## Estado

Esta é uma avaliação inicial. A extensão e a integração com WhatsApp ainda não
foram implementadas. A implementação automática fica condicionada a validar a
seleção da imagem correta no WhatsApp Web sem depender de acesso ao perfil
inteiro do Chrome.
