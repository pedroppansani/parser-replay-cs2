# Decisão 22l: Os detalhes estruturais do Rating 2.0/3.0, aplicados um a um e medidos

- **ID:** 22l
- **Status:** vigente
- **Data:** 2026-09-19
- **Resumo:** Escala alinhada, cálculo por lado, kill assistida e morte trocada.

## O que vale hoje

O erro e a correlação atuais estão em `data/processed/numeros_citaveis.json` (bloco `rating`).

## Texto

22l. **Os detalhes estruturais do Rating 2.0/3.0, aplicados um a um e medidos**
    (2026-09-19). Cada etapa foi medida sozinha, com erro de TESTE (deixa uma
    partida fora, 43 partidas / 430 jogador-partidas):
    - sem a regra de corte + vazamentos do fim do round: 0,085 -> 0,086 (igual);
    - **escala alinhada**: a calibração normalizava cada partida pela PRÓPRIA
      média e o site pela média do CORPUS -- pesos ajustados numa escala e
      usados em outra. `componentes_do_corpus` passou a receber a referência:
      0,086 -> 0,083. Custou pouco aqui, mas a diferença entre as escalas
      depende da composição do corpus; tratar como sorte, não como prova;
    - **por lado** (CT e TR normalizados contra a média DAQUELE lado e juntados
      pelos rounds de cada um): 0,083 -> 0,082, e o erro por time ficou mais
      parelho;
    - **kill assistida** (menos de `DANO_PROPRIO_PARA_KILL_LIMPA` = 60 de dano
      próprio na vítima) e **morte trocada** entram como componentes separados:
      0,082 -> **0,079**, correlação 0,966. A regressão dá 0,25 para a kill
      limpa e 0,025 para a assistida -- a kill "roubada" vale quase nada --, e
      0,055 de crédito de volta para a morte trocada. São 20,7% das kills e
      22,4% das mortes. A morte trocada entra como CRÉDITO (e não como
      penalidade menor) porque os pesos são não-negativos: "punir menos" não
      cabe num peso positivo;
    - **forma dos sub-ratings** (dividir pela média x padronizar pelo desvio),
      com os lados separados: 0,0788 x 0,0781, empate técnico. Mantida a
      divisão pela média, que já estava no código.
    Recalibração final: referência de escala + pesos regravados
    (`kills_limpas` 0,251, `kills_assistidas` 0,025, dano 0,268, sobrevivência
    0,127, `mortes_trocadas` 0,055, KAST 0,183, multikills 0,082, Round Swing
    0,490; intercepto -0,399). Os pesos anteriores, nesta escala, dariam 0,107.
