# Decisão 8i: Economia do rating estimada no CORPUS, por arma mais cara + colete

- **ID:** 8i
- **Status:** vigente
- **Data:** 2026-09-19 (entrada no arquivo; o texto não traz data)
- **Resumo:** Economia do rating estimada no corpus, por arma mais cara e colete.

## O que vale hoje

**Empate na classe de equipamento do time: o round é DIVIDIDO entre as classes empatadas**
(decisão do Pedro, 2026-10-02; `metrics/economia.py`, `REGRA_DE_DESEMPATE`). Com dois jogadores de
rifle, dois de pistola e um de SMG, o round conta meio para "rifle" e meio para "pistola". A regra
é determinística, não tem constante escolhida e reproduz o valor esperado do sorteio que existia.

Por que esta e não as outras. A tabela gravada em 2026-09-19 desempatava pela ordem de hash (ao
acaso) e nunca foi regerada; o erro do rating citado até então (0,079) era o de UM sorteio. São 159
empates em 2.304 time-rounds, e a regra do desempate sozinha move o erro do rating contra a HLTV
(deixa uma partida fora, reajustando só os pesos; 430 jogador-partidas; modelo de round de quatro
entradas):

| regra do desempate | erro médio | correlação |
|---|---|---|
| a tabela gravada em 2026-09-19 (um sorteio) | 0,0788 | 0,9659 |
| primeira em ordem alfabética (o código de 2026-09-21 a 2026-10-02) | 0,0827 | 0,9619 |
| classe mais forte | 0,0812 | 0,9634 |
| classe mais fraca | 0,0826 | 0,9619 |
| **empate dividido (em vigor)** | **0,0812** | **0,9635** |
| 12 sorteios ao acaso | 0,0786 a 0,0843 (média 0,081) | |

O arquivo `metrics/economia_reference.json` guarda a regra (`regra_de_desempate`) e o commit que o
gerou (`gerada_por`), e `tests/test_economia_reprodutivel.py` falha se regerar a tabela do corpus
não der exatamente o arquivo gravado.

## Texto

8i. **Economia do rating estimada no CORPUS, por arma mais cara + colete**
   (`metrics/economia.py`, `scripts/fit_economia.py` ->
   `metrics/economia_reference.json`, refazer a cada demo nova). A versão por
   partida tinha ~20 rounds para dezenas de células e mal agia. Classe lida da
   COMPRA no fim do freeze time; colete importa (pistola inicial sem colete
   vence 4-10%, com colete ~50%). Encolhimento em dois níveis: célula com
   colete -> mesma sem colete -> taxa do lado (K = 20). Conferido contra a
   HLTV: rifle x rifle TR 49,4% (HLTV 48%); o "matar pistola inicial 75%" da
   HLTV bate com rifle contra QUALQUER pistola (75,9%), não com pistola inicial
   (96%) -- o grupo deles é mais largo que o nome. Só a taxa entra na
   conversão em peso, então a diferença de nome não a afeta. Efeito, com os
   pesos congelados: erro contra o rating oficial 0,109 -> 0,094.
