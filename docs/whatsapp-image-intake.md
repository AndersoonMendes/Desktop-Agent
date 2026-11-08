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

O Manifest V3 do Chrome permite declarar acesso por site e permissões opcionais;
uma extensão pode limitar o host solicitado a `web.whatsapp.com`. A API de
downloads do Chrome também permite iniciar e acompanhar o salvamento de um
arquivo, mas exige a permissão `downloads`. Referências: [permissões e host
permissions](https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions)
e [API de downloads](https://developer.chrome.com/docs/extensions/reference/api/downloads/).

### 2. Chrome DevTools Protocol — possível, mas concede acesso amplo

O agente poderia conectar via CDP a um Chrome iniciado explicitamente com uma
porta de depuração local. Isso permite localizar a aba do WhatsApp Web e
interagir com a página existente, mas dá ao processo acesso amplo às abas desse
Chrome e exige encerrar e reiniciar o navegador com configuração especial. Não
é a primeira escolha para este aplicativo.

### 3. Pasta de entrada — disponível agora

O usuário salva a foto do WhatsApp em `images/` (ou configura `IMAGE_INBOX` para
apontar à pasta Downloads); `/imagem-recente` mostra o arquivo mais novo e pede
confirmação antes de iniciar o fluxo atual. Isso não captura mensagens do grupo
automaticamente, mas evita digitar o caminho da imagem.

“Mais novo” aqui significa o arquivo com modificação local mais recente dentro
da pasta configurada, não a imagem mais recente pela data do chat do WhatsApp.

## Próximo protótipo recomendado

Validar uma extensão local com escopo restrito: grupo explicitamente escolhido,
somente a imagem mais recente, confirmação visual e transmissão apenas para
`localhost`. Não ler nem armazenar o histórico completo do grupo.

## Estado

O comando `/imagem-recente` está implementado para arquivos que o usuário salva
na pasta de entrada. A extensão e a integração direta com WhatsApp ainda não
foram implementadas. Um protótipo de extensão local está em
[`chrome-whatsapp-extension.md`](chrome-whatsapp-extension.md). Ele usa a aba
ativa após ação explícita, oferece prévias e salva somente a imagem confirmada
na pasta de Downloads. Não lê o histórico completo nem tem integração
automática com o processo Python.
