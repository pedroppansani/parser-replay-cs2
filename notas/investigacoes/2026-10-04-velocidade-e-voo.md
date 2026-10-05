# Velocidade de deslocamento e tempo de voo das granadas, medidos no corpus (fase 8, 2026-10-04)

A prancheta do formato 3 calcula o horário em que o jogador chega a cada ponto de um caminho
desenhado sem horário (distância / velocidade) e mostra a granada voando até o destino. Os dois
números saem do corpus, não do manual do jogo. Constantes em `metrics/tactics.py`
(`VELOCIDADE_U_S`, `VOO_*`), injetadas na página pelo build.

## Velocidade (`py -3.12 -m pesquisa.velocidade_no_corpus 12`)

12 partidas profissionais (match_10 a match_22). Movimento livre = janela de 32 ticks (0,5 s) do
mesmo jogador, vivo, no chão (|Δz| ≤ 1 u por tick), mesma arma e mesmo modo, velocidade horizontal
quase constante (CV < 0,05) e acima de 50 u/s. A velocidade da janela é a mediana dela.

| arma | modo | mediana (u/s) | p25 | p75 | janelas |
|---|---|---|---|---|---|
| rifle | correndo | 210,6 | 76,5 | 215,0 | 9.525 |
| rifle | andando | 111,8 | 111,8 | 117,0 | 26.178 |
| AWP | correndo | 197,1 | 193,0 | 200,0 | 1.048 |
| AWP | andando | 104,0 | 104,0 | 104,0 | 1.806 |
| pistola | correndo | 234,0 | 224,3 | 239,8 | 4.182 |
| SMG | correndo | 229,4 | 211,3 | 238,4 | 648 |
| faca | correndo | 250,0 | 247,0 | 250,0 | 22.637 |

Agachado não tem janela estável de 0,5 s (ninguém anda agachado tanto tempo); com janela de 16
ticks: rifle 90,4 e AWP 82,4. Coerência com o jogo: agachado < andando < correndo, a faca bate os
250 do jogo e a AWP sem mira os 200. Sensibilidade (janela 16 ou 64; CV 0,02 ou 0,10): rifle
correndo entre 208,6 e 211,0; AWP correndo entre 194,6 e 199,5.

## Tempo de voo (`py -3.12 -m pesquisa.voo_das_granadas 12`)

Do primeiro tick com o projétil na trajetória até a detonação (`*_detonate`); a molotov, pela vida
do próprio projétil (o `inferno_startburn` traz a entidade do fogo). 4.255 granadas.

| granada | n | mediana (s) | p25 | p75 | correlação com a distância | regra adotada |
|---|---|---|---|---|---|---|
| flash | 1.648 | 1,62 | 1,62 | 1,62 | −0,01 | 1,62 s fixos (pavio) |
| HE | 884 | 1,62 | 1,62 | 1,62 | — | 1,62 s fixos (pavio) |
| smoke | 1.717 | 2,83 | 1,89 | 5,38 | 0,86 | 0,587 + 2,519 s por 1000 u |
| molotov | 1.347 | 1,69 | 1,27 | 2,00 | 0,48 | 1,025 + 0,603 s por 1000 u, teto 2,0 s |

O teto da molotov é o p75 (2,00 s exatos: o pavio dela). A decoy não tem medida própria e usa a
regra da smoke.
