# Decisão 8a: A origem do tempo do timeline é o FIM DO FREEZE TIME (`freeze_end`)

- **ID:** 8a
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** O tempo do timeline conta do fim do freeze; negativo é erro.

## Texto

8a. **A origem do tempo do timeline é o FIM DO FREEZE TIME (`freeze_end`).**
   Declarada em `metrics/round_breakdown.py` e exibida como relógio (`1:09`), não
   como segundos crus com sinal — número sem referência não se audita. Com essa
   origem, **tempo negativo é impossível**: o módulo levanta erro em vez de
   renderizar. Evento depois do fim do round é legítimo (dá pra morrer nos
   segundos seguintes) e sai marcado como pós-round, com tempo positivo.
