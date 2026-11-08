# Pesquisa: reprodução local de músicas

## O que é permitido e possível

O YouTube oferece downloads offline para assinantes Premium em navegadores e
aplicativos compatíveis, mas esses downloads são gerenciados pelo próprio
YouTube e não ficam disponíveis como arquivos MP3 comuns para outro programa.
O YouTube Music também mantém as músicas offline dentro do aplicativo e exige
reconexão periódica. Referências: [YouTube Premium offline](https://support.google.com/youtube/answer/11977233?hl=pt-BR)
e [YouTube Music offline](https://support.google.com/youtubemusic/answer/6313535?hl=pt-BR).

Os [termos do YouTube](https://www.youtube.com/t/terms) permitem downloads nos
casos oferecidos pelo próprio serviço, autorizados pelo titular ou permitidos
por lei. Portanto, o agente não deve extrair áudio/streams de resultados do
YouTube nem contornar o player, anúncios ou proteções. O aplicativo oficial
também informa que áudio/MP3 não é baixado separadamente pelo app do YouTube.

## Alternativa local viável

É possível tocar automaticamente arquivos de áudio que o usuário já possui ou
obteve de uma fonte que permite o download, por exemplo MP3, M4A, FLAC ou OGG.
O fluxo poderia escanear uma pasta local, comparar nomes de arquivo com as
faixas reconhecidas, pedir confirmação para correspondências ambíguas e usar
um player HTML local para avançar no evento `ended` do áudio.

Essa opção não depende da página do YouTube e não requer uma nova dependência
Python para um primeiro protótipo: o navegador já reproduz os formatos comuns.
Arquivos ausentes ou com nomes ambíguos permaneceriam pendentes; o sistema não
procuraria nem baixaria cópias não autorizadas.

## Caminho recomendado

1. Manter a pesquisa e seleção atuais para vídeos do YouTube.
2. Implementar uma biblioteca local opcional em uma pasta configurável.
3. Fazer correspondência por nome do arquivo, mostrar artista/título e pedir
   confirmação quando houver mais de uma opção.
4. Usar a fila existente para preservar ordem e estado, trocando apenas o
   backend de reprodução entre YouTube incorporado e arquivos locais.

Esta opção ainda não foi implementada; é uma proposta para quando o usuário
tiver uma pasta de arquivos de áudio licenciados ou próprios.
