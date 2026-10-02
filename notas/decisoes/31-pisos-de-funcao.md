# Decisão 31: Registro dos pisos de função

- **ID:** 31
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** Registro dos pisos de função e de onde veio cada um.

## Texto

31. **Registro dos pisos de função** (`metrics/player_roles.py`, TRAIT_SPECS;
    revisão do Pedro em 2026-09-26 sobre 52 partidas, 430 jogador-partidas
    profissionais em 43 partidas, via `scripts/proposta_pisos.py`):
    | função | piso | origem |
    |---|---|---|
    | AWPer (`awp_share`) | 0,533 | corte estatístico (os três métodos concordam) |
    | Lurker (`off_team_relativo`) | 1,284 | corte estatístico (vazio e Otsu entre líderes) |
    | Abre o round (`first_contact_share`) | 0,320 | convenção validada pela fronteira |
    | Suporte de utility (`enemy_blind_seconds`) | 20,0 | convenção validada pela fronteira |
    | Âncora de bomb | 0,800 | convenção validada pela fronteira |
    | Segundo homem (`trade_share`) | 0,350 | convenção validada pela fronteira |
    | Principal fragger (`adr`) | 85,0 | convenção validada pela fronteira |
    "Validada pela fronteira" = os métodos não concordam, e o Pedro conferiu os
    jogadores dos dois lados do corte: ZywOo fora do entry nas duas partidas
    (0,316-0,318); sh1ro e chopper acima do suporte, apEX (13,6) longe abaixo;
    FalleN acima da âncora; ropz e KSCERATO acima do segundo homem, donk fora.
    **Fronteira mais apertada das cinco**: YEKINDAR fica fora do principal
    fragger por 0,1 de ADR (84,9, match_44) -- ruído puro, mas não é evidência
    para mover um piso que é convenção.
    O Lurker é medido por `off_team_relativo` (decisão 29), que SUBSTITUIU a
    taxa absoluta `off_team_share` (escala 0-1, piso antigo 0,40) como métrica
    que define o rótulo; a taxa absoluta continua na tabela só como informação.
