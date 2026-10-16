# Decisão 19: Round decisivo é medido por VARIAÇÃO DA PROBABILIDADE DE VITÓRIA, não por soma de pontos

- **ID:** 19
- **Status:** vigente
- **Data:** 2026-09-20
- **Resumo:** Round decisivo é a maior variação da probabilidade de vitória (modelo neutro 0,5).

## Texto

19. **Round decisivo é medido por VARIAÇÃO DA PROBABILIDADE DE VITÓRIA, não
    por soma de pontos.** O esquema antigo somava pesos inventados (ponto sem
    retorno 40, déficit 12 por jogador, clutch 20, multikill 6x, placar apertado
    15, defuse 8) e não havia resposta para "por que clutch vale 20 e defuse vale
    8" — é exatamente o que a decisão 6 chama de chute disfarçado de métrica.

    Agora sai de uma conta só (`metrics/win_probability.py`): programação
    dinâmica sobre os estados de placar até o fim da partida, e o round decisivo
    é o que mais moveu a chance de o time vencer. Três dos componentes antigos
    caem de graça da matemática e **não devem ser reintroduzidos como peso**:
    ponto sem retorno (um round que leva de 40% a 8% tem variação enorme por
    construção), déficit (estado desequilibrado move pouco) e placar apertado
    (11-11 é o pico natural da curva).

    A prorrogação entra na conta desde 2026-09-20 (decisão 19e).

    A probabilidade de ganhar um round isolado é **neutra (0,5)** de propósito:
    alavancagem é propriedade do ESTADO DO PLACAR, não de qual time é melhor.
    Usar a taxa observada na própria partida seria circular — o time que venceu
    teve taxa alta justamente porque venceu. Há um ajuste por lado
    (`PROB_ROUND_CT`) desligado por padrão, para quando houver corpus suficiente.

## A seção da página mudou de forma (2026-10-16)

Na aba Placar, "A chance de vitória, round a round" (a curva da chance de vitória) repetia o desenho de
"A virada em dois atos": a chance depende quase só do placar, e as duas linhas subiam e desciam nos mesmos
rounds. A frase "é a inclinação desta curva que elege o round decisivo" pedia para medir inclinação a olho.

A seção virou **"Quanto cada round pesou"**: uma barra por round com a variação da chance de vitória do
lado A (depois menos antes, a curva que o payload já publica), no mesmo eixo X do gráfico de cima, na cor
do time que ganhou o round; o round decisivo é o publicado (`decisive_round`), com o contorno e o rótulo
no token `--decisivo`; rótulo direto nas três maiores barras (`win_probability.top`); embaixo, os três
cartões desses rounds. Os textos saem de `leitura/peso_dos_rounds.py` (decisão 18). Nenhum número muda: a
soma das barras é a chance final menos a inicial (`tests/test_peso_dos_rounds.py`) e a impressão dos
números fica idêntica. A definição do decisivo não mudou; quando ele empata com outra barra, a frase da
seção diz que o empate vai para o round que veio primeiro (a ordenação de `round_decisivo`).

**Para a especificação de design v2:** a seção mudou de FORMA depois da direção "Sala de demo" (decisão
44), com os tokens e componentes de hoje; a v2 precisa cobrir esta seção (barras, cartões, tabela para
leitor de tela e o destaque sincronizado com o gráfico de cima).
