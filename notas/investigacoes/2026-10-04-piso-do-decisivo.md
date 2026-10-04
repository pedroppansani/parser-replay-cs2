# Piso do round decisivo: diagnóstico nas 52 partidas (fase 6, passo 6.1, 2026-10-04)

Gerado por `py -3.12 -m pesquisa.diagnostico_decisivo` a partir da curva gravada em cada
`insights.json` (modelo neutro de placar, `metrics/win_probability.py`). Nada mudou na produção.

**Leitura.**

- **O piso quase não acrescenta informação ao placar.** A regra "tem round decisivo se a
  diferença final for de no máximo 4 rounds" acerta 48 das 52 partidas (92%) sem olhar a curva.
  O piso só decide de fato nas diferenças de 4 e 5 (11 partidas). É o que o problema 2 da fase 6
  suspeitava: com o modelo neutro, "ter round decisivo" é quase "terminar apertado".
- **A virada não entra na regra atual.** 34 partidas tiveram virada (o vencedor esteve abaixo de 50%
  de chance em algum momento); 11 delas ficam sem round decisivo hoje.
- **O empate no topo é a regra, não a exceção.** Em 46 de 52 partidas o 1º e o 2º maiores |ΔP|
  ficam a menos de 0,02, e em 36 eles são **exatamente iguais**: no modelo neutro, estados de placar
  simétricos (por exemplo, o mesmo salto em 10-11 e em 11-10) dão o mesmo |ΔP|. Na página, quase
  toda partida com decisivo deveria estar dizendo "empate".

## 1. Por partida (52 partidas; piso 0.121 no MR12)

| partida | formato | placar | maior dif. no jogo | virada | |ΔP| 1º / 2º / 3º | acima do piso | tem decisivo |
|---|---|---|---|---|---|---|---|
| match_08 | MR12 | 11-13 | 7 | sim | 0.250 / 0.188 / 0.125 | 4 | sim |
| match_09 | MR12 | 11-13 | 5 | sim | 0.250 / 0.250 / 0.188 | 5 | sim |
| match_18 | MR12 | 11-13 | 3 | sim | 0.250 / 0.156 / 0.156 | 8 | sim |
| match_20 | MR12 | 14-16 | 4 | sim | 0.250 / 0.250 / 0.250 | 15 | sim |
| match_33 | MR12 | 13-11 | 3 | sim | 0.250 / 0.250 / 0.188 | 7 | sim |
| match_37 | MR12 | 16-14 | 4 | sim | 0.250 / 0.250 / 0.188 | 13 | sim |
| match_39 | MR12 | 13-11 | 5 | sim | 0.250 / 0.250 / 0.188 | 4 | sim |
| match_40 | MR12 | 16-14 | 4 | sim | 0.250 / 0.250 / 0.250 | 14 | sim |
| match_41 | MR12 | 16-14 | 3 | sim | 0.250 / 0.250 / 0.250 | 15 | sim |
| match_42 | MR12 | 17-19 | 4 | sim | 0.250 / 0.250 / 0.250 | 18 | sim |
| match_43 | MR12 | 13-11 | 7 | sim | 0.250 / 0.250 / 0.188 | 4 | sim |
| match_49 | MR12 | 13-11 | 6 | sim | 0.250 / 0.250 / 0.188 | 4 | sim |
| match_12 | MR12 | 13-10 | 6 | sim | 0.137 / 0.137 / 0.125 | 5 | sim |
| match_14 | MR12 | 10-13 | 3 | sim | 0.188 / 0.188 / 0.156 | 8 | sim |
| match_16 | MR12 | 13-16 | 7 | sim | 0.250 / 0.188 / 0.188 | 9 | sim |
| match_28 | MR12 | 13-10 | 3 | sim | 0.156 / 0.156 / 0.137 | 7 | sim |
| match_32 | MR12 | 16-19 | 4 | sim | 0.250 / 0.250 / 0.250 | 19 | sim |
| match_46 | MR12 | 13-10 | 5 | sim | 0.188 / 0.188 / 0.156 | 6 | sim |
| match_51 | MR12 | 10-13 | 6 | não | 0.125 / 0.125 / 0.117 | 2 | sim |
| match_01 | MR12 | 13-9 | 4 | sim | 0.156 / 0.156 / 0.137 | 6 | sim |
| match_02 | MR12 | 13-9 | 4 | sim | 0.123 / 0.123 / 0.117 | 2 | sim |
| match_23 | MR12 | 13-9 | 7 | sim | 0.117 / 0.088 / 0.088 | 0 | não |
| match_30 | MR12 | 9-13 | 5 | não | 0.123 / 0.113 / 0.113 | 1 | sim |
| match_31 | MR12 | 19-15 | 4 | sim | 0.250 / 0.250 / 0.250 | 18 | sim |
| match_34 | MR12 | 9-13 | 8 | não | 0.125 / 0.117 / 0.084 | 1 | sim |
| match_04 | MR12 | 13-8 | 6 | sim | 0.093 / 0.093 / 0.092 | 0 | não |
| match_11 | MR12 | 13-8 | 6 | sim | 0.117 / 0.088 / 0.088 | 0 | não |
| match_21 | MR12 | 13-8 | 5 | sim | 0.123 / 0.123 / 0.113 | 2 | sim |
| match_35 | MR12 | 13-8 | 6 | sim | 0.097 / 0.093 / 0.093 | 0 | não |
| match_36 | MR12 | 8-13 | 6 | não | 0.123 / 0.117 / 0.109 | 1 | sim |
| match_38 | MR12 | 13-8 | 5 | sim | 0.123 / 0.123 / 0.113 | 2 | sim |
| match_44 | MR12 | 13-8 | 5 | não | 0.105 / 0.097 / 0.092 | 0 | não |
| match_03 | MR12 | 13-7 | 8 | sim | 0.088 / 0.088 / 0.084 | 0 | não |
| match_22 | MR12 | 7-13 | 9 | não | 0.081 / 0.081 / 0.077 | 0 | não |
| match_24 | MR12 | 13-7 | 7 | não | 0.081 / 0.081 / 0.080 | 0 | não |
| match_47 | MR12 | 7-13 | 6 | não | 0.082 / 0.082 / 0.081 | 0 | não |
| match_07 | MR12 | 13-6 | 8 | não | 0.093 / 0.093 / 0.088 | 0 | não |
| match_25 | MR12 | 6-13 | 7 | não | 0.103 / 0.082 / 0.081 | 0 | não |
| match_26 | MR12 | 13-6 | 9 | sim | 0.093 / 0.093 / 0.088 | 0 | não |
| match_48 | MR12 | 13-6 | 7 | sim | 0.097 / 0.092 / 0.088 | 0 | não |
| match_50 | MR12 | 13-6 | 7 | sim | 0.105 / 0.105 / 0.098 | 0 | não |
| match_06 | MR12 | 13-5 | 8 | não | 0.084 / 0.081 / 0.081 | 0 | não |
| match_27 | MR12 | 5-13 | 9 | sim | 0.093 / 0.088 / 0.088 | 0 | não |
| match_52 | MR12 | 5-13 | 8 | sim | 0.105 / 0.098 / 0.098 | 0 | não |
| match_05 | MR12 | 4-13 | 9 | sim | 0.093 / 0.093 / 0.088 | 0 | não |
| match_17 | MR12 | 13-4 | 9 | não | 0.081 / 0.081 / 0.077 | 0 | não |
| match_19 | MR12 | 4-13 | 11 | não | 0.081 / 0.081 / 0.077 | 0 | não |
| match_53 | MR12 | 13-4 | 9 | não | 0.093 / 0.087 / 0.084 | 0 | não |
| match_15 | MR12 | 13-3 | 10 | não | 0.084 / 0.084 / 0.081 | 0 | não |
| match_29 | MR12 | 3-13 | 10 | não | 0.081 / 0.081 / 0.077 | 0 | não |
| match_45 | MR12 | 2-13 | 11 | não | 0.081 / 0.081 / 0.077 | 0 | não |
| match_10 | MR12 | 13-1 | 12 | não | 0.081 / 0.081 / 0.077 | 0 | não |

## 2. A diferença final de placar explica 'tem decisivo'?

| diferença final | com decisivo | sem decisivo |
|---|---|---|
| 2 | 12 | 0 |
| 3 | 7 | 0 |
| 4 | 5 | 1 |
| 5 | 3 | 4 |
| 6 | 0 | 4 |
| 7 | 0 | 5 |
| 8 | 0 | 3 |
| 9 | 0 | 4 |
| 10 | 0 | 2 |
| 11 | 0 | 1 |
| 12 | 0 | 1 |

Melhor regra só pelo placar: 'tem decisivo se a diferença final <= 4' acerta 48 de 52 (92%).
Partidas com virada: 34; com decisivo entre elas: 23.

## 3. Empate no topo (limiar atual 0.02)

1º e 2º a menos de 0.02: 46 de 52
diferença 1º-2º: mín 0.0000, p25 0.0000, mediana 0.0000, p75 0.0047, máx 0.0938
empates exatos (mesmo |ΔP| no 1º e no 2º): 36
