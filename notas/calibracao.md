# Pontos de calibração que pertencem ao Pedro

> A lista completa, com o histórico de cada ponto. O `CLAUDE.md` traz a lista curta e aponta para cá.

## Pontos de calibração — pertencem ao Pedro, não ao código

Não "resolva" nenhum destes automaticamente; pergunte.

- Nomes dos clusters (`clustering/cluster_names.json`): **gravados pelo Pedro em
  2026-09-26**, depois de reajustar o modelo nas 52 partidas (11.520
  player-rounds; ARI 1,00 contra o modelo anterior, 100% dos rounds no mesmo
  grupo): 0 "Mira fora da altura", 1 "Entra em bloco", 2 "Segura longe do
  time", 3 "Roda o mapa". A concentração da Nuke em "mira" (34% dos rounds
  contra 17% no corpus) é estilo real: o desvio de mira é mais forte FORA da
  Nuke (-2,47) que dentro (-1,67). Todo reajuste que renumerar os grupos exige
  conferir os nomes de novo (`py -3.12 -m scripts.fit_global_clusters
  --dry-run`).
- Revisar a partição A/Mid/B dos mapas (`MANUAL_PLACE_AREAS` em
  `metrics/map_areas.py`). Rode `py -3.12 -m pesquisa.show_map_areas`. A Nuke é a
  mais frágil: os dois sites ficam empilhados na vertical.
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`).
  Rode `python -m pesquisa.show_derived_angles <match_id>` para ver os derivados.
  Os com `n_kills` baixo (4-5) são os que mais precisam de julgamento humano.
- Janela de trade: **5,0s, calibrada empiricamente** (2026-09-19,
  `py -3.12 -m scripts.calibracao.varre_trade`) contra DOIS gabaritos oficiais -- 310 KASTs
  e as 50 mortes trocadas D(t) da página Detailed stats. A curva é LARGA e
  suave (4,5 a 6,0s ficam todas perto do topo), o que é sinal de regra e não de
  coincidência do corpus. Os dois gabaritos discordam do ótimo: KAST prefere
  5,5s (235 de 310 contra 231), D(t) prefere 5,0s (20 de 50 contra 14); 5,0s é
  o compromisso e é o valor em uso. Também medido e DESCARTADO: limite de
  distância entre o vingador e a morte (900u derruba o KAST para 204, 1500u é
  neutro) e "vingada por qualquer um" em vez de por companheiro (2 a 4 KASTs
  pior em toda a curva). Revisar quando o corpus crescer.
- Limiares: peek/hold (120u / 250u), janela de contato
  (1s), tolerância de pré-fire (25°), permanência mínima para contar rotação
  (15% do round).
- Ratings oficiais da HLTV em `data/reference/hltv_ratings.json`, e demos de
  partidas oficiais para preenchê-lo. Sem isso os pesos do rating continuam
  provisórios.
- Pesos dos seis sub-ratings: **ajustados** contra os ratings oficiais de 43
  partidas (430 jogador-mapas) e gravados em `metrics/rating_weights.json` por
  `fit_rating --fit-pesos --gravar` -- regressão com pesos >= 0 e intercepto
  livre, validada deixando uma partida fora (erro médio 0,111, correlação
  0,921). `PESOS_PROVISORIOS` ficou só como plano B sem o arquivo. Os pesos
  valem para a referência de escala em que foram ajustados: refazer a
  referência exige refazer os pesos (o rating marca `pesos_desatualizados`).
  Os da divisão de crédito do Round Swing (`CREDITO_KILL` e companhia)
  continuam do Pedro.
  `py -3.12 -m scripts.fit_rating --fit-pesos` mostra os pesos ajustados ao
  lado dos atuais, com erro fora da amostra.
- Altura dos olhos em pé medida com tick oficial (63,1-63,8u contra 64) e
  diferença em pé - agachado (16,5 contra 18): manter as constantes ou medir de
  novo com `duck_amount` gravado pelo parser (decisão 21c).
- Força do arremesso: mínimo por grupo absoluto (20) gera 7 grupos no corpus
  inteiro (decisão 21a).
- Limiares do card de destaque (`metrics/match_highlights.py`): piso de evidência
  (0,70), limiar de empate (0,05) e as dispersões do bottom frag (1,5 a 3,0).
- Limiares do round decisivo e do impressionante: o fator do piso de
  decisividade (`FATOR_MINIMO_DECISIVO`, 1,5), a distância que declara empate no
  topo (`LIMIAR_EMPATE_WPA`, 0,02) e **todos os pesos de
  `metrics/round_spectacle.py`** — clutch (26 + 11 por inimigo extra), multikill
  (8 por kill acima de 2), desvantagem (9 por jogador), desarme no limite (20) e
  abertura limpa (12). Os pesos do espetáculo são subjetivos por natureza; o card
  mostra quanto cada componente deu em cada round justamente para recalibrar
  olhando caso concreto. Frequência medida nas 9 partidas: multikill 85x,
  abertura limpa 48x, desvantagem 23x, clutch 19x, desarme no limite 1x.
- Limiares da autópsia de round (`metrics/round_breakdown.py`): equipamento médio
  que caracteriza economia (2000$), diferença de equipamento que torna a economia
  explicativa (1500$) e a cauda pós-round (8s). Registro da medição: dos 56
  rounds abaixo do limiar de eco nas 9 partidas, **18 são round de pistola com os
  dois times igualmente pobres** — ali a economia não explica a derrota, e o
  texto passou a dizer isso em vez de tratar os dois casos igual.
- Limiares dos papéis (`metrics/archetypes.py`): distância máxima para uma morte
  de companheiro contar como "do seu lado" (900u), assinatura de repick (250u de
  percurso, razão 3x), mínimo de tentativas de clutch (3), mínimo de rounds com
  AWP (4), compra abaixo da média do time (-400), fração do time de rifle (60%),
  e o quanto um papel crítico precisa se destacar para virar card (0,85).
- Paleta dos gráficos: `py -3.12 -m metrics.paleta` mede ΔE2000 entre
  todos os pares, em visão normal e em protanopia/deuteranopia, e o contraste
  no branco. Rode antes de trocar qualquer cor de gráfico.
- Distribuição de todo índice de função, antes (9 de FACEIT) e depois (corpus
  inteiro): `py -3.12 -m scripts.calibracao.calibration_report`. Tabela de funções com os
  componentes abertos, por jogador: `py -3.12 -m scripts.calibracao.tabela_funcoes`.
- Pisos do eixo carrega piano <-> baiter (`PISO_CARREGA_PIANO` 0,5 e
  `PISO_BAITER` -0,5) e se o repick exige mais de uma saída e volta
  (`pesquisa/casos_repick.py`).
- Pisos de função (`TRAIT_SPECS` em `metrics/player_roles.py`). Sensibilidade
  medida: lurker (0,40) é estável (±10% muda 1 rótulo), âncora (0,80) é sensível
  só para cima (+10% perde 28% dos rótulos) e **entry (0,32) é sensível dos dois
  lados**. Depois da correção do empate no primeiro contato, 0,32 ficou ACIMA do
  p90 da métrica e só 5 jogadores recebem o rótulo. Recomendação registrada:
  ancorar o piso ao acaso (com 5 jogadores, 1/5 = 0,20) em vez de a um número
  absoluto — 1,5x o acaso = 0,30 dá 10 de 25 times-partida com entry definido. É
  decisão do Pedro.
