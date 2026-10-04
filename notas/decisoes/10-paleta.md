# Decisão 10: Paleta do dashboard foi validada para daltonismo e contraste

- **ID:** 10
- **Status:** vigente
- **Data:** 2026-09-20
- **Resumo:** Paleta validada para daltonismo e contraste; não trocar cor sem `valida_paleta`.

## Texto

10. **Paleta do dashboard foi validada para daltonismo e contraste.** O scatter
    de clusters é facetado (um painel por cluster) porque nenhuma quarta cor
    passa nos critérios junto das três primeiras no modo escuro. Não troque por
    4 cores num gráfico só.

    Nos gráficos da partida (vantagem e probabilidade de vitória), por pedido
    do Pedro: Time A azul `#2a78d6`, Time B laranja `#eb6834`, round decisivo
    **verde esmeralda escuro `#0b6b4a`** (2026-09-20, no lugar do roxo
    `#4a3aa7`). A linha da diferença de rounds é uma medida só e fica em tinta
    neutra; a cor de cada time está nas áreas e nas bolinhas, e empate é cinza.

    A TROCA CORRIGIU UM DIAGNÓSTICO MEU, e o registro antigo estava errado: ele
    dizia que "esmeralda passava por menos (ΔE 9,2) e com contraste 2,8:1",
    como se a cor tivesse sido reprovada. O que foi reprovado era o esmeralda
    CLARO (`#1baf7a`, o `--aqua` do tema) -- e o defeito era a LUMINÂNCIA, não
    o matiz. Medido de novo com `metrics/paleta.py` (ΔE2000 e dicromacia
    por Viénot 1999), o esmeralda escuro empata com o roxo no critério mais
    duro: pior par para daltônico ΔE **14,5** contra 14,9 do roxo (alvo 8),
    visão normal 40,6 contra 23,1, contraste no branco 6,53:1 contra 8,56:1.
    O piso é esse: `#0f8f63` já cai para ΔE 9,0 e `#1baf7a` reprova no
    contraste. **Não clareie o verde sem rodar o script.**
