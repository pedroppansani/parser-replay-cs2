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
