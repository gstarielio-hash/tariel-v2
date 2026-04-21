# Roteiro de teste no aparelho: chat livre -> PDF

Data de referência: 14 de abril de 2026.

Objetivo: validar no Android real o fluxo completo de chat livre com foto, geração natural de PDF e abertura autenticada do anexo dentro do app do inspetor.

## Pré-requisitos

1. Backend acessível em um host alcançável pelo aparelho.

Host de trabalho para este roteiro:

- `https://tariel-web-free.onrender.com`

Observações importantes:

- `android/.env` local estava apontando para `http://127.0.0.1:8000`; isso só atende dev local e não serve para aparelho físico sem LAN/túnel.
- O fallback antigo `https://tarie-ia.onrender.com` vinha respondendo `503`, então o mobile foi alinhado para usar `https://tariel-web-free.onrender.com` quando não houver override explícito.

2. Variáveis públicas do app ajustadas para o mesmo host:

```bash
cd android
export EXPO_PUBLIC_API_BASE_URL=https://tariel-web-free.onrender.com
export EXPO_PUBLIC_AUTH_WEB_BASE_URL=https://tariel-web-free.onrender.com
```

3. Instalar e abrir o app no aparelho:

```bash
cd android
npm run android:dev
```

Se a intenção for validar um build mais próximo de distribuição:

```bash
cd android
npm run android:preview
```

## Fluxo principal

1. Abrir o app e fazer login no portal do inspetor.
2. Entrar em uma conversa de chat livre.
3. Enviar uma mensagem de contexto simples.
   Exemplo: `Inspeção livre em linha de vida do galpão A.`
4. Tocar no botão de anexo do composer.
5. Escolher `Galeria`.
6. Selecionar uma foto real do aparelho.
7. Confirmar que o rascunho do anexo aparece no composer com preview de imagem.
8. Complementar a mensagem com um texto curto sobre a evidência.
   Exemplo: `Ponto de ancoragem com corrosão aparente e sem placa de identificação.`
9. Enviar a mensagem.
10. Confirmar que a mensagem aparece no chat e que a foto foi absorvida pelo fluxo normal.
11. Enviar um comando natural para o relatório.
   Exemplo: `faça um relatório em pdf com base nisso`
12. Aguardar a resposta da IA.
13. Confirmar que a resposta do assistente contém texto de sucesso e um card de anexo PDF.
14. Tocar no card do PDF.
15. Confirmar que o Android abre o compartilhamento/visualizador do arquivo.
16. Fechar o visualizador e voltar ao chat.
17. Abrir o histórico, reentrar na mesma conversa e confirmar que o anexo PDF continua disponível.
18. Abrir o mesmo PDF novamente a partir do histórico da conversa.

## Variante de câmera

Repetir o fluxo principal trocando a galeria por câmera:

1. Abrir o botão de anexo.
2. Escolher `Câmera`.
3. Conceder a permissão se o Android pedir.
4. Tirar a foto.
5. Confirmar que o preview volta para o composer.
6. Enviar a evidência e repetir o pedido `faça um relatório em pdf`.

## Critérios de aceite

- O anexo de imagem entra no composer sem travar o app.
- O pedido em linguagem natural gera resposta síncrona em JSON com mensagem da IA e um anexo PDF no próprio chat.
- O card do PDF aparece como documento na mensagem da IA.
- O toque no anexo dispara o download autenticado e abre o compartilhamento/visualizador nativo.
- Ao recarregar a conversa pelo histórico, o mesmo PDF continua presente e abrível.
- Nenhum passo depende de rota manual fora do fluxo normal do app.

## Sinais de falha

- Login/bootstrap falha logo no início: base URL errada, host indisponível ou sessão Render fria.
- Foto entra no chat mas o pedido de PDF volta como resposta comum da IA: detecção natural do comando não disparou.
- Resposta da IA aparece sem anexo: o backend não persistiu o PDF na mensagem.
- O card do PDF aparece, mas tocar nele mostra erro de indisponibilidade: URL ausente ou payload do histórico sem `anexos`.
- O card do PDF aparece, mas o arquivo não abre: falha no download autenticado, rede ruim ou problema no `expo-sharing`.

## Evidências para guardar

- Screenshot do rascunho de imagem no composer.
- Screenshot da mensagem da IA com o PDF anexado.
- Screenshot da tela nativa de compartilhamento/visualização do PDF.
- ID do laudo/conversa usada no teste.
- Horário aproximado do teste para cruzar com logs do backend.

## Triagem rápida

Se o app não conectar:

```bash
cd android
cat .env
```

Confirme que o host do aparelho não está em `127.0.0.1`.

Se quiser rodar um smoke auxiliar das superfícies de anexo antes do teste manual:

```bash
cd android
npm run maestro:attachments
```

Esse smoke ajuda a validar galeria, documento e câmera, mas não cobre a geração natural do PDF do chat livre.

Se quiser um smoke semi-automatizado do fluxo `imagem -> pedido natural -> PDF`:

```bash
cd android
npm run maestro:chat-pdf
```

Esse fluxo valida login, abertura do laudo seed, seleção de imagem pela galeria, envio do pedido natural e presença do card do PDF. A abertura final do share sheet ainda deve ser conferida no aparelho, porque depende da UI nativa do Android.
