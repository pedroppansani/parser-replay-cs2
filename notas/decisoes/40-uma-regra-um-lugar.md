# Decisão 40: Regra do jogo usada por vários módulos é definida uma vez

- **ID:** 40
- **Status:** vigente
- **Data:** 2026-10-02
- **Resumo:** Janela de trade e troca de lado em `metrics/constantes.py`; contato em `metrics/contato.py`; "é o AWPer do time" em `player_roles.awpers_do_time`.

## Texto

40. **Regra do jogo usada por vários módulos é definida uma vez** (auditoria, item 4.8,
2026-10-02). A janela de trade de 5 s estava escrita em seis módulos (basic_metrics, archetypes,
player_profile, round_breakdown, structural_roles, rating), o round da troca de lado em quatro
(três deles sem uso), e "contato = causou ou sofreu dano" em dois. Agora:

- `metrics/constantes.py`: `JANELA_DE_TRADE_S`, `HALFTIME_ROUND` (os nomes antigos ficam como
  apelido local);
- `metrics/contato.py`: `primeiro_contato`;
- `metrics/player_roles.awpers_do_time`: quem é o AWPer do time. O empate de função por lado e o
  card de destaque "AWPer" perguntam ali. O índice de AWP do `archetypes` mede como ele jogou com
  a arma e continua existindo, mas não decide mais sozinho quem recebe o card "AWPer".

Conferido arquivo por arquivo no corpus reprocessado: nada mudou, exceto a tabela de candidatos
do destaque em 4 partidas (match_03, 16, 36 e 42), de onde sai o candidato "awper" que não era o
AWPer do time. Nenhum card mudou. `tests/test_uma_regra_um_lugar.py` falha se uma cópia voltar.
