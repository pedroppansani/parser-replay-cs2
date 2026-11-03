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

**Estado:** decisão registrada; a implementação ainda não começou.
