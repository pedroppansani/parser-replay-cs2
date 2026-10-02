# Decisão 19a: Impressionante e decisivo são perguntas SEPARADAS, e por isso são dois cards

- **ID:** 19a
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** Decisivo e impressionante são dois cards; o segundo tem pesos expostos.

## Texto

19a. **Impressionante e decisivo são perguntas SEPARADAS, e por isso são dois
    cards.** "Que round mais mudou o resultado" e "que round foi mais
    impressionante de assistir" não são a mesma pergunta: um clutch de 1v3 em
    3-13 é lindo e não decidiu nada; um round banal em 11-11 decidiu muito.
    Somar os dois num score só produz resposta que não serve para nenhuma das
    duas. O impressionante vive em `metrics/round_spectacle.py`, onde **pesos
    relativos são legítimos** porque a pergunta é subjetiva — e ficam todos
    expostos no card, componente por componente, para recalibrar olhando caso
    concreto. Medido: nas 9 partidas os dois rounds coincidem em 1 e divergem em
    8, e os dois casos estão testados.
