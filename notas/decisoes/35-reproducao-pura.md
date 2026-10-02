# Decisão 35: A reprodução da prancheta é FUNÇÃO PURA DO TEMPO

- **ID:** 35
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** A reprodução da prancheta é função pura do tempo.

## Texto

35. **A reprodução da prancheta é FUNÇÃO PURA DO TEMPO** (etapa 3,
    2026-09-26). `estadoNoTempo(estado, t)` (em `tactics.js`, que é quem
    desenha) devolve exatamente o que desenhar; não existe estado de "onde a
    animação estava", então arrastar a barra até t e tocar até t dão o mesmo
    quadro (há teste). O passo k ocupa o intervalo (início_k, início_k +
    duração_k] da linha do tempo: durante ele as peças vão do passo k−1 ao k
    com entrada e saída suaves e giram pelo caminho curto (decisão 34); troca
    de andar não interpola (a peça aparece no andar novo na metade do passo);
    peça que entra ou sai aparece ou some aos poucos; granadas e traços que
    nascem no passo aparecem em ordem de criação, repartindo o passo -- a
    granada risca a linha e depois abre o efeito, o traço se risca ponto a
    ponto --; e o que acabou de viver some no começo do passo seguinte.
    O ponto que o documento deixava ambíguo e foi resolvido assim: "o início
    do passo" é o FIM da transição dele -- em t = fim do intervalo do passo k o
    quadro é exatamente `quadro_do_passo(k)` (teste); em t = 0 as peças já
    estão no lugar e o que nasce no passo 0 ainda vai aparecer.
    Durante a reprodução nada é editável (barra de edição escondida, painel
    `inert`); "Editar" volta ao editor no passo em que parou. Atalhos do
    replay, com a mesma guarda de foco: espaço, setas (passo a passo), [ e ].
