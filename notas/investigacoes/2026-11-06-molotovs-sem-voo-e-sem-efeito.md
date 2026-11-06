# Molotovs da biblioteca sem voo (148) e sem efeito (162): a causa (cartão 29, L1)

Só investigação: nada no código, nos dados ou na biblioteca mudou. Reproduzível por um script de leitura (`build_lineups.tempos_e_lado` refeito peça a peça sobre o `interim` das partidas).

**Os números batem:** 5.716 molotovs no corpus; 148 sem `voo_s` (e, por consequência, sem `efeito_s`) + 14 com voo mas sem `efeito_s` = 162.

## Os 148 sem voo (o casamento com o fogo da demo não achou o fogo)
| Quantos | Causa |
|---|---|
| 137 | Nenhum fogo (`infernos`) do mesmo jogador no round. |
| 5 | Todo fogo do jogador no round começou ANTES da soltura. |
| 6 | O primeiro fogo depois da soltura começou a mais de 15 s (é de outro arremesso; `MAX_VOO_S`). |

Os 137 abrem assim (cada molotov uma vez, na ordem da checagem):
- **82: uma smoke estava ativa a até 200 u do ponto de queda** quando o molotov caiu (no mesmo round, entre a soltura e 5 s depois). É o comportamento do jogo: o molotov que cai dentro de uma smoke apaga e nunca vira fogo, então a demo não tem fogo para casar. **Causa confirmada pelo dado** (a smoke e o ponto de queda estão na demo).
- **8: há um fogo, mas de OUTRO jogador (ou sem dono casado)**, nascendo ali em até 15 s: o casamento é por quem lançou e o dono não bate (granada trocada entre jogadores, ou o dono do fogo veio nulo). **Atribuição.**
- **47: sem explicação nos dados.** Há fogo de outros jogadores no round, nenhuma smoke perto, e nenhum fogo que o dono e o tempo expliquem. Hipóteses, nenhuma testável com as tabelas que temos: o molotov caiu onde não queima (água, fora do mapa), foi destruído no ar, ou o fogo nasceu e morreu no mesmo instante e a demo não o registrou. **Causa não determinada.**

## Os 14 com voo e sem efeito
O fogo foi casado (o `voo_s` existe), mas o `end_tick` dele vem vazio na demo. No corpus há 17 fogos sem `end_tick`, e **16 deles começaram até 8 s antes do FIM do round**: o fogo ainda ardia quando o round acabou e a entidade saiu com a virada do round, sem evento de fim. **Causa confirmada pelo dado.**

## O que isso diz sobre o uso
- No Reescrever (decisão 59) e na prancheta, esses molotovs ficam de fora das alternativas (o R4 já exige voo e efeito conhecidos), o que é o certo: 82 deles nunca queimaram.
- Corrigir os 8 de atribuição e (talvez) dar um `efeito_s` aos 14 de fim de round (até o fim do round) é possível, mas muda a biblioteca (hash de `biblioteca.arremessos`) e não foi pedido. Os 47 ficam como pendência de causa.
