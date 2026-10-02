# Decisão 18: As frases dos cards são geradas em Python, não em JavaScript

- **ID:** 18
- **Status:** vigente
- **Data:** 2026-09-16 (entrada no arquivo; o texto não traz data)
- **Resumo:** Frases dos cards saem do Python; papel sem sustentação devolve vazio.

## Texto

18. **As frases dos cards são geradas em Python, não em JavaScript.** Ficam em
    `scripts/narrative.py` e chegam prontas ao template. O motivo é testabilidade:
    a regra "campo que não existe some da frase" vira teste. Antes disso as três
    frases eram texto fixo escrito para a match_01, e todas as páginas
    renderizavam o placar e os nicks daquela partida. **Papel sem sustentação
    devolve string vazia**, não frase com zeros — "AWP na mão em 0 rounds"
    descreve a ausência do papel como se fosse o papel.
