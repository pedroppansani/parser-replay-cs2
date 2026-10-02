# Decisão 19e: Prorrogação é MODELADA: o alvo não é fixo

- **ID:** 19e
- **Status:** vigente
- **Data:** 2026-09-20
- **Resumo:** A prorrogação é modelada: o alvo sobe 4 a cada uma, até 5.

## Texto

19e. **Prorrogação é MODELADA: o alvo não é fixo** (2026-09-20, corrigido
    porque um invariante do corpus pegou). A simplificação antiga ("empate vale
    0,5 e para por ali") estava registrada como limitação aceita, e não era
    aceitável: com o alvo fixo em 13, todo placar a partir de 12-12 era vitória
    para quem chegasse a 13, e a curva de OITO partidas do corpus terminava
    afirmando **100% para o time que PERDEU** em 4 delas (16, 20, 32 e 42 --
    nas outras 4 o time A venceu e o erro apontava para o lado certo por
    acidente). Afirmar certeza sobre o time errado não é simplificar.
    `_alvo_efetivo` sobe o alvo em 4 a cada prorrogação (13 -> 16 -> 19 -> 22) e
    devolve também QUANTAS já começaram; a recursão recebe sempre o alvo do
    FORMATO, nunca o já ajustado -- reaproveitar o ajustado perde a base e a
    conta não sabe mais em que prorrogação está.
    A cadeia é infinita por construção (todo empate abre a próxima), então a
    recursão precisa de fundo: `MAX_PRORROGACOES_MODELADAS` = 5, e ali o estado
    vale 0,5. Não é a simplificação antiga de volta -- lá o corte dava 1,0 para
    um time num estado empatado; aqui dá 0,5 num empate, depois de quatro
    empates seguidos (probabilidade da ordem de 1e-3 de sequer chegar lá).
    CONSEQUÊNCIA MEDIDA, e ela muda a leitura da aba: o maior salto possível num
    round caiu de 0,50 para **0,25**, porque nenhum round leva de 50% a 100%
    sozinho -- sempre há prorrogação depois. Nas 8 partidas de OT o round
    decisivo saiu do OT e voltou para o fim do tempo regulamentar (r23/r24, o
    que leva ao match point ou o que empata em 12-12), e 7 das 8 ficaram com
    `empate_no_topo` -- chegar a 12-11 e devolver para 12-12 movem 0,25 cada.
    Isso é propriedade do formato, não defeito do desempate.
