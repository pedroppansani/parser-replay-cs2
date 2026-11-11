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

20 casos correndo em pelo menos 3 partidas. Pares com amostra (depois do alinhamento): Mirage 454 de 5.256 pares de pontos (9%) e 74 de 506 pares de áreas; Dust2 276 de 2.970 (9%) e 70 de áreas;
Nuke 74, Inferno 42, Anubis 43 e Ancient 23 pares de áreas; Overpass (2 partidas) e Train (1) não têm tabela. Os pontos do Pedro só entram nos mapas `conferido = sim` (Mirage e Dust2).

## O fator de desvio saiu, e o estimado virou um piso

O fator (mediana de real ÷ reta) deu 0,91 a 1,02 e quase não mudava o erro, e o Pedro o tirou: o erro foi medido nos pares que já têm tempo real, onde o estimado nunca é usado; o estimado só
aparece nos pares sem amostra, que são os que contornam parede (Mirage Base TR → Meio: 12,0 s real contra 8,0 s em linha reta). Os dois sinais de que as contas mediam coisas diferentes:

- **Distância:** a reta entre os centros dos nós é em mediana 5,4% (Mirage) e 4,2% (Dust2) maior que a distância entre os pontos de maior aproximação que o tempo real mede. Agora a duração é alinhada
  (multiplicada por essa razão; razão fora de 0,8 a 1,25 descarta a viagem). Custo: Mirage 581 → 454 pares de pontos e 91 → 74 de áreas; Dust2 336 → 276 e 88 → 70.
- **Velocidade:** 210,6 u/s é a mediana de quem corre com rifle, não um teto. Velocidade em linha reta entre os pontos de maior aproximação, viagens correndo com reta de 300 u ou mais: Mirage (50.509
  viagens) p50 206, p90 240, p99 248, p99,9 250; Dust2 (21.356) p50 193, p90 237, p99 250, p99,9 250; 45% das viagens da Mirage passam de 211 u/s, e só 0,1% passam de 250. Faca na mão em 27% das viagens da
  Mirage e 20% da Dust2. Por isso "não antes de" usa 250 u/s correndo (e, andando e agachado, a velocidade constante de cada jeito). Teste: em todo par da tabela a mediana real passa da reta a 250 u/s.

## Exemplos

- Mirage Base TR → Meio (pontos): 20 casos em 9 partidas, chega entre 1:18 e 1:17, por volta de 1:17 (cerca de 13 s; saída às 1:30).
- Mirage TSpawn → TopofMid (áreas, na tela "Base TR → Esquina"): 20 casos em 10 partidas, entre 1:22 e 1:21, cerca de 8 s.
- Mirage Caverna → TV: **não passa do mínimo** (12 casos correndo em 5 partidas); desce para as áreas (TRamp → House, 7 casos) e termina em "estimado".
- Dust2 Base TR → Fora do Escuro (pontos): 243 casos em 10 partidas, cerca de 7 s (a faixa cabe num segundo; em relógio, 1:23).
- Nuke Secret → Tunnels (troca de andar, áreas): 35 casos em 9 partidas, mediana 5,4 s; CTSpawn → Tunnels não tem par e a aba pergunta a chegada.

## A ordem do relógio e a peça que ainda anda

Cada comando com horário abre uma cadeia; os sem horário ("depois", "junto", "espera") ficam presos ao comando anterior na escrita; as cadeias andam por horário e, no mesmo horário, na ordem da escrita.
O plano guarda, por peça, a trilha dos pontos que ele mesmo criou; o ponto de partida de um comando é a posição da trilha naquele horário (interpolada em linha reta), depois do último ponto o destino,
antes do primeiro a tática. Se o comando começa no meio de uma corrida do plano, o caminho anterior termina ali e o novo segue dali (um `cria_caminho` só); a chegada que o primeiro comando dizia deixa de aparecer.

## A impressão dos números

`scripts/design/impressao_numeros.py` lê `tempos/<mapa>.js` como `<página>::tempos`. Antes (main) 18.408 linhas; depois 18.470: 62 novas, 0 sumiram. Das novas, 52 são `::tempos` (8 a 10 por mapa) e 10 são
`comandos.velocidade_piso_correndo` (250, uma por página). Mudaram 7 linhas, todas `comandos.areas` (um hash): a estrutura ganhou o campo de texto `exibe` (o nome na tela) e o hash inclui as chaves; nenhum número mudou.
O alinhamento da duração mexe só nas linhas `::tempos`.
