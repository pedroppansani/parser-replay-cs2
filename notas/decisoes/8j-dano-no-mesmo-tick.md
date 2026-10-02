# Decisão 8j: `dmg_health_real` do awpy é recalculado no parsing

- **ID:** 8j
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** `dmg_health_real` é recalculado: vários acertos no tick não passam da vida.

## Texto

8j. **`dmg_health_real` do awpy é recalculado no parsing.** O awpy trava cada
   acerto na vida do INÍCIO do tick; com vários acertos na mesma vítima no mesmo
   tick (balins de escopeta, dois atiradores juntos) a soma passava da vida --
   dois balins de MAG-7 de 79 numa vítima de 100 contavam 158. Correção em
   `parsing.parser.dano_real_no_mesmo_tick` (aplicada no `save_interim`, no
   `load_interim` e nos scripts que leem o parquet direto; idempotente): cada
   acerto travado no que os anteriores do tick deixaram. A base é o dano
   INTEIRO, não a queda de `health` -- a vida é fracionária no jogo, e travar
   pela queda de `health` derrubou o ADR para 131 de 410. Medido contra 410
   ADRs oficiais: 380 -> 401 idênticos no arredondamento, maior diferença 2,74
   -> 0,76. 28 acertos em 22 partidas (584 de dano). Há teste varrendo o interim
   atrás de tick com dano acima da vida.
   LIMITAÇÃO CONHECIDA, investigada: os 9 restantes (listados em
   `tests/test_escada.py`) estão TODOS abaixo do oficial, no máximo 0,76 de ADR
   (27 de dano numa partida inteira). Não é arredondamento, que seria simétrico:
   é fonte de dano que a HLTV conta e nós não. Descartados como explicação: dano
   em companheiro, corte do freeze time, cauda pós-round (só 2 dos 9 têm dano
   pós-round, e esse dano ENTRA no nosso número), arma e tipo de round. Há uma
   concentração fraca em Dust2 (6 de 90 jogadores, 6,7%, contra 0% em Mirage e
   Inferno), pequena demais para sustentar conclusão.
   Reportado ao awpy: https://github.com/pnxenopoulos/awpy/issues/525 (com o caso,
   a detecção genérica e a correção). Se for corrigido lá, a correção local sai.
