# Decisão 37: Auditoria, fase 1 (2026-10-02): o que a página afirma vem do dado, e nome de jogador é dado

- **ID:** 37
- **Status:** vigente
- **Data:** 2026-10-02
- **Resumo:** Número de corpus vem de `numeros_citaveis.json`; texto do dado passa por `esc()`; CI testa antes de publicar.

## Texto

37. **Auditoria, fase 1 (2026-10-02): o que a página afirma vem do dado, e
    nome de jogador é dado.**
    - **Rating: `rounds` é o que o jogador JOGOU** (rounds_ct + rounds_t), não o
      total da partida; os subcomponentes por round do caminho sem lado e as
      marcas de amostra fraca usam isso. O corte `MIN_ROUNDS_CONFIAVEL` (30)
      mede amostra absoluta; o da página (`FRACAO_MINIMA_DE_ROUNDS`, 0,75) mede
      quem jogou bem menos que a partida. Impacto no corpus: 0 de 520
      jogador-partidas (ninguém entrou no meio).
    - **A página da partida tem doctype** (modo padrão), `lang`, viewport e
      título por partida gerado no build. No modo antigo as tabelas não
      herdavam fonte e três linhas não ganhavam a altura mínima da linha: as
      regras equivalentes estão no começo do CSS, comentadas. Não as remova
      sem rodar `py -3.12 -m scripts.compara_paginas` (página inteira, aba por
      aba, entre duas revisões; desktop e celular).
    - **Número de corpus não se escreve no template.** Vem de
      `data/processed/numeros_citaveis.json` (`py -3.12 -m
      scripts.numeros_citaveis`), pelo build; há teste estrutural com a lista
      de exceções (exemplos de formato e constantes do replay).
    - **Escape: `MapCore.esc()` é a única função**, aplicada a todo texto do
      dado que entra em `innerHTML`; JSON dentro de `<script>` só por
      `scripts/json_em_script.py`. Texto novo vindo do dado entra com `esc()`
      ou `textContent`.
    - **CI**: `pytest -q` roda antes do build, em toda branch, com o Chromium do
      Playwright (job inteiro em ~3,5 min; 898 testes num clone limpo, os que
      dependem de `data/interim/` pulados). A publicação continua só no main.
    - As imagens do README ficam em `assets/readme/`, regeradas por
      `py -3.12 -m scripts.capturas_readme` (`docs/` é saída e é ignorada).
