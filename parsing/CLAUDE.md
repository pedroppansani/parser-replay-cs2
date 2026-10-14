# parsing/: o que o parse corta ou corrige

Complementa o `CLAUDE.md` da raiz e não o substitui (lá está a regra de aplicar os filtros daqui
em todo ponto de entrada do interim). Uma regra por linha; (N) = nota em `notas/decisoes/`.

- Mortes, danos, tiros e cegueiras do freeze time (entre `start` e `freeze_end`) não pertencem a
  round nenhum; depois do fim do round que FECHA A METADE a morte também não conta; a cauda depois
  do fim dos outros rounds fica; a tabela `grenades` fica fora do corte (8b)
- A sobrevivência do KAST sai da mesma lista de mortes contadas (`deaths_per_round`), nunca da
  vida no último tick do round (8b)
- `dmg_health_real` é recalculado (`dano_real_no_mesmo_tick`, idempotente): cada acerto travado no
  que os anteriores do mesmo tick deixaram, com base no dano INTEIRO, nunca na queda de `health`;
  se o awpy corrigir (issue 525), a correção local sai (8j)
- Round de faca gravado na demo sai no parse (`remove_round_de_faca`, no `save_interim`) e os
  rounds são renumerados (8f)
- Cegueira sem `player_blind` é reconstruída de `flash_duration`: início é toda mudança para um
  valor positivo; o dono é a flash que detonou no mesmo tick, e duas candidatas indistinguíveis
  deixam a cegueira SEM DONO, nunca um palpite; a tabela leva `origem = "reconstruida"` (8h)
- Rota B (lido): a força é a da granada que saiu (último tick antes do nascimento do projétil),
  nunca a da arma no tick da soltura; botão = o mais próximo da força lida; agachamento parcial não
  é afirmado (21a)
- Gravar um campo novo da demo (como `ducked`) exige subir `VERSAO_DO_PARSER` e só vale para demos
  novas; decida antes, porque a maioria das partidas não tem mais o `.dem` (21c, 27)

## Calibração do Pedro (não resolva sozinho)

- Rota B: força intermediária (0,6141 afirma "médio"), agachamento parcial neutro, custo da tabela
  `movimento`.
