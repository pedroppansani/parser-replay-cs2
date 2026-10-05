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

## Os três grupos de compra (fase 7, 7.2.3)

Eco, força e compra cheia são uma AGREGAÇÃO das classes desta regra, a fonte única de economia do
projeto (resposta 5 do Pedro, 2026-10-05). Não há limiar novo: só a ordem de força dos grupos de
arma que a regra já tem e o colete. Código em `metrics/economia.grupo_de_compra` e
`grupos_de_compra`. A contagem é de time-rounds do corpus (52 partidas, 2.304 time-rounds), com o
empate dividido. O round de pistola é o round 1 e o primeiro depois da troca de lado.

| classe da 8i | grupo | time-rounds | dos quais no round de pistola | vitória |
|---|---|---|---|---|
| pistola_inicial, sem colete | eco | 84,5 | 7,0 | 8% |
| pistola_melhorada, sem colete | eco | 74,0 | 0 | 15% |
| pistola_inicial, com colete | **fora dos três: round de pistola** | 206,7 | 200,5 | 50% |
| pistola_melhorada, com colete | força | 215,7 | 0,5 | 29% |
| smg_shotgun, com colete | força | 86,4 | 0 | 53% |
| rifle_t2, com colete | força | 128,6 | 0 | 61% |
| rifle_t1, sem colete | força | 0,5 | 0 | 0% |
| rifle_t1, com colete | compra cheia | 1.503,8 | 0 | 56% |
| sniper, com colete | compra cheia | 3,8 | 0 | 65% |

(smg_shotgun e rifle_t2 sem colete, e sniper sem colete, não aparecem no corpus; a regra os põe
em força.)

Em palavras:
- **compra cheia** é a arma de primeira linha com colete;
- **eco** é só pistola, sem colete;
- **força** é o resto, a compra parcial: arma intermediária com colete, ou arma boa sem colete.

A pistola inicial com colete é o round de pistola, e não entra em nenhum dos três, porque os dois
times têm a mesma compra limitada. Depois do empate da 8i, 110 dos 2.304 time-rounds ficam divididos
entre dois grupos.

**Para conferir (Pedro):** rifle_t2 com colete (Galil ou FAMAS com colete) está em "força" porque é
a linha intermediária da 8i. Vence 61% dos rounds, mais que a compra cheia (56%), porque costuma
enfrentar time quebrado. Se a leitura de jogo for "Galil com colete é compra cheia", a mudança é só
na linha da tabela acima.

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
