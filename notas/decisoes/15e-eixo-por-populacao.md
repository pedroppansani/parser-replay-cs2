# Decisão 15e: O eixo carrega piano <-> baiter compara cada braço com a POPULAÇÃO da própria função

- **ID:** 15e
- **Status:** vigente
- **Data:** 2026-09-24
- **Resumo:** Cada braço do eixo piano/baiter é comparado com a população da função.

## Texto

15e. **O eixo carrega piano <-> baiter compara cada braço com a POPULAÇÃO da
    própria função** (opção (a) do Pedro, 2026-09-24). A isca já era comparada
    dentro da função desde a decisão 15c; agora o SACRIFÍCIO também é, e a
    comparação não é por contexto de round, é por população: o percentil de cada
    braço sai da distribuição dos jogador-partidas que têm a MESMA função
    dominante (`quantis_por_funcao` em `archetype_reference.json`, função com
    menos de `MIN_JOGADOR_PARTIDAS_NA_FUNCAO` = 30 cai na geral). O AWPer é
    comparado com AWPers, sem a função de lado entrar duas vezes.
    POR QUE: medido no corpus, o AWPer paga a conta em 0,071 dos rounds contra
    0,200 da média geral -- três vezes menos, porque o trabalho dele é jogar de
    trás. Contra a régua do elenco inteiro isso o empurrava para a ponta do
    baiter: AWPers eram 16% dos jogador-partidas e **57% dos baiters**.
    TESTE DE ACEITAÇÃO (o que o Pedro pediu): a proporção de AWPers entre os
    baiters tem de cair para perto da fatia deles no corpus. **Caiu de 57% para
    16%**, com a fatia deles em 16%. Distribuição de rótulos por função, antes
    -> depois (carrega piano | baiter): rotativo 40->20 | 7->26; coringa
    41->13 | 6->19; âncora 36->20 | 4->13; AWPer 5->7 | 26->12; entry 5->4 |
    1->1; trader 2->3 | 2->3.
    DUAS TENTATIVAS ERRADAS, registradas porque custaram tempo: (1) normalizar
    pelo esperado da função DO ROUND não move quase nada -- o esperado soma ~3,7
    rounds para todas as funções, porque a função do round é uma mistura e o
    AWPer da partida recebe coringa/rotativo na maioria dos rounds; (2) a
    "função dominante" tirada da moda da função do round saía `sem_funcao` para
    os 520 jogador-partidas, porque os rounds sem função reconhecida são a
    maioria -- eles ficam de fora da moda.
    O valor ABSOLUTO continua na tabela e nos cards ao lado do normalizado
    ("o time colheu em 4 dos 9 rounds em que ele pagou (1,3x o esperado da
    função dele)"), como o Pedro pediu.
