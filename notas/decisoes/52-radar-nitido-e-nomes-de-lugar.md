# Decisão 52: Radar mais nítido, nomes de lugar e peças de outro andar (Fase M)

- **ID:** 52
- **Status:** vigente
- **Data:** 2026-11-03
- **Resumo:** O mapa ganha nitidez só pelo desenho (a mesma imagem do radar, 1.024 x 1.024, com `imageSmoothingQuality = "high"` ao
  reduzir), nomes de lugar discretos que se ligam e desligam, as letras A e B nos bombsites e a peça do outro andar com disco cinza,
  anel do lado, seta e nome em itálico. Registrada ANTES de implementar, com as escolhas do Pedro de 2026-11-03.

## Texto

52. **Radar mais nítido, nomes de lugar e peças de outro andar** (Fase M; pedido e escolhas do Pedro em 2026-11-03).

**Radar mais nítido.** A mesma imagem de hoje (1.024 x 1.024, a maior que o arquivo do jogo tem), sem baixar nada novo. O ganho vem
do desenho: `imageSmoothingQuality = "high"` ao reduzir o radar para o tamanho da tela.

**Variação A (a discreta), com um item da B:**
- **Nomes de lugar:** em caixa alta, sem placa, usando os nomes de lugar que o próprio dado traz (sem inventar e sem traduzir), com
  um controle para ligar e desligar.
- **Bombsites:** só a letra (A e B), discreta.
- **Peça do outro andar** (Nuke, Vertigo, Train): disco cinza com anel na cor do lado, mais seta para cima ou para baixo (▲ ou ▼)
  indicando se está acima ou abaixo.
- **Nome do jogador do outro andar:** aparece, em itálico (este item vem da variação B; na A pura ele não aparecia).

**Regras que valem para tudo:**
- Um nome de lugar só aparece onde não cobre peça, nome de jogador nem bombsite.
- O nome do jogador procura lugar perto da própria peça e, se sair de cima dela, ganha uma linha fina até a peça.
- Nenhum nome de jogador some.
- O mapa continua escuro (os tokens `*-mapa`), e o desenho das peças (o anel duplo, CT e TR) não muda de significado.

**Portão e prova (Fase M):** a prévia em `preview-v2/index.html`; as capturas da Mirage e da Nuke, no Replay e na prancheta, a 1440 e
375 px, nos temas claro e escuro; e o code-review mostrado só na conversa, antes do OK do Pedro. A impressão dos números fica
idêntica. As referências do canvas (`notas/design/referencias/`) são regravadas num commit próprio, com a lista do que mudou.

**Escolhas do Pedro depois do registro (2026-11-03):**
- **Celular:** o botão "Lugares" começa DESLIGADO em telas de até 640 px (a regra "não cobre nada" tira quase todos os nomes numa
  tela pequena). Se a pessoa liga, a escolha fica lembrada; a escolha é guardada por tipo de tela (`mapa:lugares` no computador,
  `mapa:lugares:celular` no celular), então mexer numa não muda a outra. No computador continua começando ligado. As letras A e B
  dos bombsites não dependem do botão.
- **Palavras separadas:** o nome de lugar é escrito com as palavras separadas pelas maiúsculas que o próprio dado usa ("CTSpawn" vira
  "CT SPAWN", "SnipersNest" vira "SNIPERS NEST") e o "of" minúsculo colado entre uma minúscula e uma maiúscula ("TopofMid" vira
  "TOP OF MID", "BackofB" vira "BACK OF B", "BackofA" vira "BACK OF A"). A regra (`metrics/lugares.texto_do_lugar`) muda só esses 3
  nomes entre os 171 das 7 tabelas, e as letras são exatamente as do dado, só com espaço; nenhuma exceção escrita à mão (testes em
  `tests/test_lugares_rotulos.py`).
- **Prancheta:** as peças do outro andar ficam como estão (esmaecidas e editáveis). O visual único para o outro andar fica para o
  design do "Reescrever" (cartão 22), que vai juntar as peças do round real e as editáveis.
- **O botão "Lugares"** fica na legenda do mapa do replay, junto do seletor de andar (a barra de anotações tem os botões visíveis
  fixados por teste, e ela cabe em uma linha); na prancheta, no grupo de zoom da barra.

**Estado:** implementada na branch `fase-m-mapa` (portão do Pedro: prévia, capturas e code-review antes do merge).
