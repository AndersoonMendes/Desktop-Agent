# Extensão local para escolher uma imagem do WhatsApp Web

## Fluxo do protótipo

1. O usuário abre `web.whatsapp.com` no Chrome e entra no grupo desejado.
2. O usuário aciona a extensão e clica em **Procurar imagens**.
3. A extensão lê imagens grandes já carregadas na conversa aberta e mostra uma
   galeria dentro da página. A última imagem na ordem do DOM é sugerida como a
   mais recente; o usuário confere o grupo e a prévia.
4. Ao clicar **Salvar imagem selecionada**, o navegador baixa somente aquela
   imagem. A extensão não envia o histórico nem a imagem para outro serviço.
5. O agente usa a pasta de Downloads dedicada como `IMAGE_INBOX`; o usuário
   executa `/imagem-recente` para iniciar o fluxo de revisão já existente.

## Instalação para desenvolvimento

1. No Chrome, abra `chrome://settings/downloads` e escolha uma pasta dedicada,
   por exemplo `Downloads/WhatsAppMusicInbox`. Essa configuração também define
   onde o Chrome salva os outros downloads.
2. Em `chrome://extensions`, habilite **Modo do desenvolvedor** e clique em
   **Carregar sem compactação**.
3. Selecione a pasta do repositório
   `extensions/whatsapp-image-picker`.
4. No WSL, configure `IMAGE_INBOX` para a mesma pasta do Windows, por exemplo:

   ```bash
   export IMAGE_INBOX="/mnt/c/Users/SEU_USUARIO/Downloads/WhatsAppMusicInbox"
   uv run python main.py
   ```

5. Abra o grupo no WhatsApp Web, role até as mensagens mais recentes, clique no
   ícone da extensão e em **Procurar imagens**. Confira o nome do grupo e a
   prévia, selecione a foto desejada e clique em **Salvar imagem selecionada**.
6. No terminal do agente, execute `/imagem-recente` e confirme a imagem listada.

O nome `SEU_USUARIO` deve corresponder à pasta real em `C:\Users` no Windows.
O download precisa terminar antes de chamar `/imagem-recente`.

## Escopo e limitações

- A extensão não inicia sessão, não lê outras abas e não guarda cookies. Ela
  usa as permissões `activeTab` e `scripting`; o script só é injetado quando o
  usuário aciona o popup sobre `web.whatsapp.com`.
- A varredura cobre imagens que já estão carregadas no DOM da conversa aberta.
  Ela não percorre nem baixa o histórico inteiro; role o grupo até o fim para
  que as mensagens recentes sejam carregadas.
- A ordem do DOM é uma heurística para sugerir a imagem mais recente. Por isso,
  a extensão exibe as prévias e exige seleção explícita antes de baixar.
- O WhatsApp Web não oferece um DOM estável para esse uso. Mudanças na interface
  podem fazer a extensão deixar de encontrar imagens ou o nome do grupo.
- O agente ainda não inicia automaticamente a identificação depois do
  download. A integração termina na pasta de entrada e no comando
  `/imagem-recente`.

## Privacidade

O código da extensão é local e não faz requisições a um serviço remoto. A única
imagem baixada é a que o usuário seleciona. O arquivo segue para a pasta de
Downloads configurada no Chrome e depois é lido pelo agente local/Ollama,
conforme a configuração atual do projeto.
