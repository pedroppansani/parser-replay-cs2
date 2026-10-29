# Decisão 51: Tema claro e escuro, escolhido na landing

- **ID:** 51
- **Status:** vigente
- **Data:** 2026-10-29
- **Resumo:** Landing, partida e jogadores saem no claro ou no escuro, o que quem lê escolhe no botão da landing
  (lembrado no navegador; na primeira visita, o tema do aparelho). O escuro é o de antes da v2-5; a prancheta é sempre
  violeta. O tema é aplicado antes da primeira pintura por um arquivo (`tema.js`), sem script inline e sem mudar a CSP.

## Texto

51. **Tema claro e escuro** (Fase T, pedido e escolhas do Pedro em 2026-10-29; revê a parte "tema por página" da nota 48).
Regras:

- Três temas em `tokens.css`: `claro` (o de sempre), `escuro` (o escuro de antes da v2-5, que a moldura do Replay já
  usava desde a v2-7; sem o degradê quente) e `violeta` (o da prancheta desde a v2-5, com nome próprio). O
  `metrics.paleta` mede os três (`TEMAS`), e cada `--apagado` é medido contra os fundos do seu tema; o canvas lê só os
  `*-mapa` e as granadas, iguais em todos.
- `dashboard/web/tema.js` (copiado pelo build ao lado das páginas) entra no `<head>` da landing, da partida e de
  jogadores, síncrono: lê `goatdemo:tema` do `localStorage` (sempre em `try/catch`), cai no `prefers-color-scheme` e põe
  o `data-tema` no `<html>` antes de o corpo existir. A prancheta (`data-tema="violeta"`) não o carrega. O HTML gerado
  continua com `data-tema="claro"`: sem o arquivo (página gerada sozinha), vale o claro.
- O botão fica só na navbar da landing (`design_head.botao_do_tema`, texto do Python): nome "Escuro", `aria-pressed`
  diz se o escuro está ligado; troca na hora e guarda a escolha (o comportamento está no `v2.js`). No celular, só o ícone,
  com o nome lido pelo leitor de tela.
- Os agentes da landing foram aprovados sobre o claro: no escuro eles continuam desenhados com as cores do claro
  (`data-tema="claro"` no próprio agente), num cartão claro arredondado (opção B do Pedro). O desenho não muda.
- A imagem de compartilhamento e o favicon não mudam com o tema.
