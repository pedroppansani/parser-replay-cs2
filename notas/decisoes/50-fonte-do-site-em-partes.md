# Decisão 50: Fonte do site em partes, lida só por `le_fonte`

- **ID:** 50
- **Status:** vigente
- **Data:** 2026-10-29
- **Resumo:** O `tactics.js` e o script do `template.html` podem ser divididos em partes, cada uma incluída por uma linha
  `//@inclui <caminho>`. Build, testes e ferramentas leem as duas fontes só por `scripts.fontes_web.le_fonte`, que
  devolve o texto inteiro. Dividir é só mudar de lugar: o site sai igual byte a byte, provado por
  `scripts.design.prova_refatoracao`.

## Texto

50. **Fonte do site em partes** (cartão 9, passos 0 a 3, OK do Pedro em 2026-10-29). O `tactics.js` tinha 4.600 linhas e o
script do `template.html` 2.680, num arquivo só. Regras:

- Uma linha `//@inclui <caminho>` (relativo à pasta da fonte, sozinha na linha, a partir da primeira coluna) é trocada
  pelo conteúdo da parte, tal como está no arquivo. Uma parte não inclui outra.
- O build (`build_web_page`, `build_tactics_page`), os testes e as ferramentas (`compara_paginas`) leem por `le_fonte`,
  nunca pelo `read_text` do arquivo: o que um teste confere continua sendo o texto inteiro.
- Dividir ou juntar partes é só mudança de lugar, sem mudar uma linha de lógica. A prova é
  `py -3.12 -m scripts.design.prova_refatoracao`: o site da base e o do HEAD, gerados em worktrees limpos, iguais em sha256
  arquivo a arquivo, mais a impressão dos números, os 4 quadros do canvas, a `compara_paginas` e a suíte. Qualquer
  diferença reprova.
- `tests/test_fontes_web.py` fixa o sha256 do texto das duas fontes como estava antes da divisão (main `f7bc788a`): é a
  guarda do cartão 9 e sai, com o OK do Pedro, quando o cartão fechar.
- As ferramentas de captura abrem o navegador com rasterização num fio só e sem raster parcial
  (`_comum.ARGS_DETERMINISTICOS`): sem isso, o mesmo arquivo dava de 3 a 132 pixels diferentes em cerca de 1 de cada 3
  aberturas.
