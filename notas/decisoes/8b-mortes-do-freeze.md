# Decisão 8b: Mortes dentro do freeze time não pertencem a round nenhum

- **ID:** 8b
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Mortes e eventos do freeze time e do intervalo não pertencem a round nenhum.

## Texto

8b. **Mortes dentro do freeze time não pertencem a round nenhum.** O demo
   registra mortes entre o `start` e o `freeze_end` — não é warmup (o
   `is_warmup_period` acaba antes do primeiro `start`), é gente se matando no
   tempo parado do pré-partida, e em match_08 o freeze do round 1 dura 93s contra
   20s dos demais. Medido: 11 mortes assim nas 9 partidas, 4 com
   `attacker_steamid == victim_steamid`. Elas produziam DOIS sintomas de uma vez:
   timestamp negativo no timeline e jogador ganhando +1 kill por se matar.
   Exceção decidida pelo Pedro: depois do fim do round que FECHA A METADE (há
   troca de lado em seguida) a morte não conta -- o jogo já foi para o
   intervalo. Caso real: a bomba matou donk (match_24) e ropz (match_26) depois
   do fim do round 12; a HLTV não conta essas mortes e conta as da cauda dos
   outros rounds (6 de 6 conferidos). A sobrevivência do KAST sai da MESMA
   lista de mortes contadas (`basic_metrics.deaths_per_round`), não da vida
   no último tick do round: pelo tick, 71 jogador-rounds apareciam vivos tendo
   morrido (último round da partida, cauda depois do fim), e K-D e KAST se
   contradiziam. O
   filtro é `parsing.kills_do_round_jogado` e precisa ser aplicado em **todo**
   ponto de entrada de kills — `load_interim`, o parse do zero e os scripts que
   leem o parquet direto. A cauda depois do fim do round fica.
   Danos, tiros e cegueiras recebem o MESMO corte do freeze time
   (`parsing.eventos_do_round_jogado`, aplicado em `load_interim` e nos scripts
   que leem direto): medido, 100 danos no freeze time em 9 partidas, sempre em
   blocos de 10 com atacante e vítima do mesmo lado -- restart de round pelo
   servidor. O ADR não era afetado (só soma dano em inimigo), mas o primeiro
   contato ("causou ou sofreu dano") era. A tabela `grenades` fica de fora: as
   linhas dela no freeze time são granada no inventário, com posição nula.
