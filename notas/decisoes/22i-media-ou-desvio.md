# Decisão 22i: Dividir pela média e padronizar pelo desvio dão o MESMO rating aqui

- **ID:** 22i
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Dividir pela média ou padronizar dá o mesmo rating com pesos ajustados.

## O que vale hoje

O defeito de escala citado (calibração por partida, site pelo corpus) foi alinhado na decisão 22l.

## Texto

22i. **Dividir pela média e padronizar pelo desvio dão o MESMO rating aqui.**
    Com agregado linear, pesos ajustados e intercepto livre, x/média e
    (x - média)/desvio são a mesma família de funções: medido, previsões
    idênticas até 1e-15 em validação deixa-uma-partida-fora. A mudança do
    Rating 2.0 para desvio-padrão só pesa com pesos FIXOS. Não "corrija" isso.
    O defeito de forma que existe é outro: `fit_rating.componentes_do_corpus`
    normaliza cada partida pela PRÓPRIA média (não passa a referência), e o site
    aplica os pesos sobre a normalização do CORPUS -- os pesos são ajustados numa
    escala e usados em outra. Medido, custou pouco desta vez (site 0,081 contra
    0,083 dentro da amostra), mas tem que ser alinhado na próxima calibração.
    Onde o resíduo do rating se concentra (430 jogadores, controlando o nível):
    kill com menos de 60 de dano próprio +0,105, morte trocada -0,178, kills de
    CT menos de TR +0,112 -- os três no sentido dos detalhes que a HLTV publicou
    (penalidade da kill "assistida", morte trocada punida menos, cálculo por
    lado), mas juntos explicam só 5,3% da variância do resíduo. O resto é
    espalhado: forma do modelo de probabilidade, não componente.
