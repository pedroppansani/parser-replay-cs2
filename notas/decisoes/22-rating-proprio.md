# Decisão 22: O rating é uma REIMPLEMENTAÇÃO da metodologia do Rating 3.0, não o Rating 3.0 da HLTV

- **ID:** 22
- **Status:** vigente
- **Data:** 2026-09-17 (entrada no arquivo; o texto não traz data)
- **Resumo:** O rating é implementação própria da metodologia do Rating 3.0; nunca "o da HLTV".

## O que vale hoje

O texto diz que os pesos são provisórios. Estão AJUSTADOS por regressão contra os ratings oficiais (`metrics/rating_weights.json`, decisão 22l); `PESOS_PROVISORIOS` é só o plano B sem o arquivo.

## Texto

22. **O rating é uma REIMPLEMENTAÇÃO da metodologia do Rating 3.0, não o
    Rating 3.0 da HLTV.** A HLTV publicou a metodologia; os coeficientes e os
    pesos de cada sub-rating são **fechados**. Então este número não é o oficial
    e não pode ser apresentado como se fosse -- em nenhum lugar da interface, do
    código ou do README. O rótulo obrigatório vem no próprio resumo do módulo, e
    há teste que falha se ele deixar de dizer isso.

    O que É honesto afirmar: os seis sub-ratings seguem a metodologia publicada,
    o ajuste de economia usa a única reta que passa pelos dois pontos que a HLTV
    divulgou (rifle x rifle 48% -> 1,10; pistola inicial 75% -> 0,54), e os pesos
    do agregado são provisórios até serem estimados por regressão contra ratings
    oficiais.
