# Decisão 15c: Traço comportamental é comparado DENTRO DA FUNÇÃO estrutural

- **ID:** 15c
- **Status:** vigente
- **Data:** 2026-09-19
- **Resumo:** Traço comportamental é comparado dentro da função estrutural.

## Texto

15c. **Traço comportamental é comparado DENTRO DA FUNÇÃO estrutural.**
    (Decisão do Pedro, 2026-09-19.) A função determina o comportamento
    esperado: jogar de trás e não trocar de perto é o trabalho do AWPer e do
    âncora, não oportunismo. Comparar com a média geral confunde função com
    atitude -- medido, 56% dos rótulos de baiter iam para AWPers, que são 18%
    dos jogador-partidas. O eixo usa `isca_relativa` = isca observada / isca
    ESPERADA da função, e o esperado vem do CORPUS inteiro (1 ou 2 AWPers por
    partida seriam ruído), round a round pelo contexto daquele round -- quem
    puxa AWP em alguns rounds é comparado como AWPer só neles. Medido em 11.520
    player-rounds, mortes de companheiro por perto sem troca, por round:
    suporte 1,02 | trader 0,77 | sem função 0,77 | AWPer 0,70 | entry 0,57 |
    rotativo 0,51 | lurker 0,49 | coringa 0,43 | âncora 0,34. Função com menos
    de MIN_ROUNDS_FUNCAO_NA_REFERENCIA rounds cai na média geral.
    Dependência de ordem, conferida: `structural_roles` é calculado antes dos
    papéis comportamentais (process_demo escreve, build_insights lê).
