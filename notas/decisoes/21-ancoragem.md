# Decisão 21: O tick de soltura de uma granada é derivado por ANCORAGEM GEOMÉTRICA, não por atraso fixo de animação

- **ID:** 21
- **Status:** substituída por 21c
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Soltura por ancoragem geométrica.

## O que vale hoje

Onde a demo traz `grenade_thrown`, o tick é o do evento (decisão 21c) e a ancoragem vira validação. A ancoragem continua sendo a FONTE do tick só nas demos sem o evento (FACEIT), e a investigação de 2026-10-02 mostrou que ali ela acerta o tick em 41% ([investigação](../investigacoes/2026-10-02-faceit-tick-pelo-projetil.md)).

## Texto

21. **O tick de soltura de uma granada é derivado por ANCORAGEM GEOMÉTRICA, não
    por atraso fixo de animação.** O `weapon_fire` marca o clique; a granada sai
    da mão depois, e é o ângulo da soltura que importa. Varre-se a janela entre
    o clique e o primeiro sample do projétil e vence o tick cuja geometria
    (olhos + deslocamento na direção da mira) melhor reproduz o ponto observado.

    A separação que faz isso funcionar: o deslocamento da mão age no plano
    HORIZONTAL e a altura dos olhos age só na VERTICAL. O ajuste horizontal
    determina o tick e o deslocamento sem nenhum parâmetro livre por arremesso,
    e a altura cai depois como MEDIÇÃO. É isso que mantém o resíduo honesto como
    medida de confiança.

    Medido em 3.020 arremessos: resíduo mediano 0,51u, 99,9% abaixo do limiar, e
    o atraso da animação sai em 7 ticks (109 ms) em vez de chutado. A altura dos
    olhos derivada dá **64,17u**, o que VALIDA as 64 unidades que o projeto já
    supunha -- e revelou um deslocamento vertical de +3,2u no ponto de
    nascimento da granada, igual em pé e agachado, que ninguém tinha modelado.

    Quando o jogador está parado e a mira quieta, o resíduo é plano na janela e o
    tick fica indeterminado. É inofensivo (a mira varia 0,29° na mediana) mas o
    empate é desfeito pelo tick mais próximo do projétil -- sem isso, 312 dos
    3.020 saíam com soltura ANTES do clique.
