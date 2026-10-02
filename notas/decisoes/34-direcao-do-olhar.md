# Decisão 34: Direção do olhar: θ = −yaw, e o ângulo interpola pelo caminho mais curto, sem Catmull-Rom

- **ID:** 34
- **Status:** vigente
- **Data:** 2026-09-26
- **Resumo:** θ = −yaw; ângulo interpola linear pelo caminho curto.

## Texto

34. **Direção do olhar: θ = −yaw, e o ângulo interpola pelo caminho mais
    curto, sem Catmull-Rom** (etapa 1, 2026-09-26). No jogo o yaw 0° aponta
    para +X e cresce no anti-horário (decisão 9); o radar inverte o Y, então a
    direção (cos yaw, sin yaw) vira o deslocamento de tela (cos yaw, −sin yaw)
    -- `MapCore.anguloDeTela` é a ÚNICA função com essa conta. Validado no dado
    real: yaw do matador no tick da kill contra a direção da vítima, erro
    mediano 0,46° em 7.685 kills, controle invertido 86,15°; na página, 154 de
    154 kills da match_02 com a ponta a menos de 20°.
    `MapCore.interpolaAngulo` usa delta = ((b − a + 540) % 360) − 180: de 359°
    para 1° são +2°, não −358°. Linear de propósito -- a mira muda por saltos, e
    suavizar inventaria rotação. No replay só interpola com o jogador vivo nos
    dois quadros e sem salto (as guardas do par no `smoothPos`); a reprodução da
    prancheta usa a mesma função. O `d` do replay tem um yaw inteiro por
    quadro, no MESMO índice da posição.
