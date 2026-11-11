# C3: o tempo real de corrida na aba Comandos (2026-11-11)

Decisão 64. Código: `metrics/tempos_de_corrida.py` (a conta), `scripts/build_tempos.py` (leitura do corpus e a tabela `data/tempos/<mapa>.json`),
`dashboard/web/prancheta/20-comandos.js` (a aba). Teste: `tests/test_tempos_de_corrida.py` (inclui o recálculo independente) e `tests/test_comandos_tempos.py`.

## Como uma viagem é medida

Um rastro é um jogador vivo em um round valendo (do fim do freeze ao fim do round), uma amostra a cada 8 ticks. Cada tick recebe o nó mais perto (ponto do
Pedro ou âncora de área da demo) se estiver a até 200 u (pontos) ou 250 u (áreas). A viagem de A a B vai do tick de MAIOR APROXIMAÇÃO de A, na última visita a A
antes de B, ao de maior aproximação da primeira visita a B. Usar a borda do raio encurtaria todo tempo em cerca de 2R ÷ velocidade (0,9 a 1,2 s com R = 200 a 250). Descarta: parada
de mais de 1 s abaixo de 40 u/s, buraco no rastro (morte, troca de round), mais de 25 s, caminho andado maior que 1,8 vez a reta. "Correndo" = no máximo 10% dos
ticks andando (shift) e nenhum agachado; a demo grava os dois a cada tick, então a separação é direta e não depende da velocidade. Isso tira de 35 a 65% das viagens
(na exploração, com raio de 150 u, Mirage Caverna→TV: 34 casos em todos os jeitos e 12 correndo; a mediana cai de 18,1 s para 14,4 s).

## O mínimo e a cobertura

20 casos correndo em pelo menos 3 partidas. Pares com amostra: Mirage 581 de 5.256 pares de pontos (11%) e 91 de 506 pares de áreas; Dust2 336 de 2.970 (11%) e 88 de áreas;
Nuke 116, Inferno 52, Anubis 65 e Ancient 28 pares de áreas; Overpass (2 partidas) e Train (1) não têm tabela. Os pontos do Pedro só entram nos mapas `conferido = sim` (Mirage e Dust2).

## O fator de desvio por mapa

Mediana de (tempo real ÷ tempo em linha reta a 210,6 u/s) dos pares com amostra, sem troca de andar e com reta de 300 u ou mais; vale com pelo menos 15 pares. O erro é a mediana de
|tempo real − estimado| nesses pares, em segundos; "validado" deixa cada par de fora do cálculo do fator.

| mapa | fonte | pares | fator | erro da reta | erro com o fator | erro validado |
|---|---|---|---|---|---|---|
| Mirage | pontos | 492 | 0,96 | 0,41 s | 0,36 s | 0,36 s |
| Dust2 | pontos | 278 | 1,02 | 0,32 s | 0,33 s | 0,33 s |
| Nuke | áreas | 94 | 0,97 | 0,42 s | 0,40 s | 0,43 s |
| Inferno | áreas | 52 | 0,94 | 0,53 s | 0,57 s | 0,63 s |
| Anubis | áreas | 65 | 0,91 | 0,45 s | 0,26 s | 0,26 s |
| Ancient | áreas | 28 | 0,93 | 0,49 s | 0,39 s | 0,46 s |
| Overpass, Train | nenhuma | 0 | sem fator (linha reta pura) | | | |

**Leitura honesta:** o fator fica entre 0,91 e 1,02, quase 1, e quase não melhora o erro: com o fator o erro cai em 4 mapas e sobe em 2 (0,01 s na Dust2, 0,04 s no Inferno); validado (par deixado de fora), cai em 3 e sobe em 3. Dois motivos: a mediana é dominada pelos pares curtos
(erro de meio segundo para reta de 2 a 5 s), e os pares com 20 casos correndo são os trajetos populares e diretos (viés de seleção: pares que cercam parede ficam sem amostra). Nos pares longos
(reta de 1.200 u ou mais) o erro da reta sobe para 0,6 a 0,8 s e a direção do erro muda de mapa a mapa; um par como Mirage Base TR → Meio tem 1,5 vez a reta (12,0 s contra 8,0 s).

## Exemplos

- Mirage Base TR → Meio (pontos): 20 casos em 9 partidas, chega entre 1:18 e 1:16, por volta de 1:18 (saída às 1:30).
- Mirage TSpawn → TopofMid (áreas): 20 casos em 10 partidas, entre 1:21 e 1:20.
- Mirage Caverna → TV: **não passa do mínimo** (12 casos correndo em 5 partidas); desce para as áreas (TRamp → House, 7 casos) e termina em "estimado".
- Dust2 Base TR → Fora do Escuro (pontos): 243 casos em 10 partidas, mediana 6,25 s (faixa de 6,12 a 6,50 s; em relógio, tudo cai em 1:24).
- Nuke Secret → Tunnels (troca de andar, áreas): 35 casos em 9 partidas, mediana 5,4 s; CTSpawn → Tunnels não tem par e a aba pergunta a chegada.

## A peça que ainda anda (o caso que ficou da C2)

O plano guarda, por peça, a trilha dos pontos que ele mesmo criou. O ponto de partida de um comando é a posição da trilha naquele horário (interpolada em linha reta entre dois pontos, como a prancheta
toca); depois do último ponto, o destino; antes do primeiro, a tática. Se o comando começa no meio de uma corrida do plano, o caminho anterior termina ali e o novo segue dali (um `cria_caminho` só).
A chegada que o primeiro comando dizia deixa de aparecer, porque a peça não chega mais lá. Limite: o plano lê as frases na ordem em que foram escritas; "joga smoke aos 1:25" escrita antes de "corre aos 1:30" parte da tática, não da corrida.

## A impressão dos números

`scripts/design/impressao_numeros.py` agora lê `tempos/<mapa>.js` como `<página>::tempos`. Antes (main) 18.408 linhas; depois 18.496: 88 linhas novas, todas `::tempos` (14 a 16 por mapa), 0 mudaram, 0 sumiram.
