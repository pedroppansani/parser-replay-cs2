# Comandos na prancheta (C1): o leitor, sem interface

O leitor lê uma frase em português e devolve o que ENTENDEU; não aplica nada, não calcula tempo de corrida e não chuta. Arquivos: `dashboard/web/comandos/leitor.js` (puro: sem DOM, rede nem armazenamento), `scripts/comandos_contexto.py` (monta o contexto: pontos do Pedro do mapa, lugares da demo, jogadores, funções, relógio e os TEXTOS das perguntas), `tests/test_comandos_leitor.py` (60 testes, no Chrome do Playwright que o projeto já usa), `pesquisa/comandos_c1_relatorio.py` (gera as tabelas abaixo do próprio leitor) e a decisão 64. A página do site não muda (o leitor ainda não entra em nenhuma página).

## O que ele entende

- **Quem:** "jogador 2", "TR 2", "CT 3", "o 2", "número 2", por extenso de um a cinco ("jogador dois", "tr três"; "um" só depois de jogador, TR ou CT), o nome de uma função da prancheta ("o AWPer", "o lurker") e "ele/ela" (o último citado). Lista de jogadores ("tr 2 e tr 3 jogam flash"). Sem time ("jogador 2") e com os dois times na tática, pergunta de qual time.
- **O quê:** lançar (joga, lança, solta, manda, usa) smoke, flash, molotov (molo, incendiária, fogo), HE (granada, frag); mover (vai, roda, corre, anda, caminha, agacha, entra, sobe, desce, volta, rotaciona: todos valem "vai até"), com "correndo", "andando", "agachado" (sem modo, correndo, marcado como padrão); segurar (segura, fica, holda); esperar (N segundos, até 1:10).
- **Onde:** o ponto do Pedro do mapa (nome, apelido ou nome com qualificação), ou o nome do jogo em inglês (sem diferença de maiúscula, espaço e acento: "BombsiteA", "Bombsite A", "TopOfMid"); o ponto ganha da área de mesmo nome. A letra do bombsite ("na b", "pra A", "site A") só conta depois de preposição, para o artigo "a" não virar bombsite.
- **Quando:** relógio regressivo ("aos 1:20"), "aos N segundos do início", "depois", "em seguida", "ao mesmo tempo". "aos 40 segundos" sozinho pergunta (no relógio ou depois do início). Horário fora do round (3:20) pergunta. "em N segundos" é duração imposta: só avisada. Mesmo jogador, "e roda pra TV" ou "e entra na b": vem depois do anterior sem perguntar o horário.
- **Nome repetido:** o mesmo nome em dois pontos da MESMA área da demo e do MESMO andar (as duas "TV" da Mirage, as duas "Banana" do Inferno) é UM alvo só: o ponto do meio entre eles, sem pergunta. Em áreas ou andares diferentes (o Silo de cima e o de baixo, o "Default" do A e do B) pergunta "qual?" com botões (cada opção diz o andar, a área da demo ou as coordenadas), a não ser que um qualificador resolva sozinho: "default do A", "lixeira do CT", "banco do meio" (A/B, CT, TR ou outro nome; vale o candidato mais perto do lugar citado, com folga de 25%; senão pergunta).
- **Quando não entende:** palavra desconhecida NUNCA vira alvo. O leitor lista o que não entendeu e, para lugar desconhecido, sugere os nomes parecidos como opções que a pessoa escolhe ("caverma" sugere Caverna e Caverna TR; "xyzzy" não sugere nada). Campo que falta (quem, onde, quando, granada) vira pergunta.
- **Aviso, não conta:** o horário fixo de uma ação que vem depois de um deslocamento do mesmo jogador carrega `depende_do_deslocamento`, para a C3 comparar com o tempo de corrida (o leitor só marca).

## As 30 frases (e o que o leitor entendeu em cada uma)

As 15 primeiras são as da C0 (cada uma num mapa onde faz sentido); as 15 seguintes usam os nomes do Pedro. A coluna "o que pergunta" lista o que o leitor ainda precisa saber; "pronto para confirmar" é quando não falta nada.

| # | mapa | frase | o que o leitor entendeu | o que pergunta | avisos |
|---|---|---|---|---|---|
| 1 | Mirage | "jogador 2 joga smoke em window aos 1:30" | jogador 2 (time?): smoke em ?, aos 1:30 (relógio) | De qual time é "jogador 2"? [TR 2 / CT 2]<br>Não achei o lugar "window" neste mapa. Qual destes? |  |
| 2 | Mirage | "TR 2 joga smoke em BombsiteA aos 1:30" | TR 2: smoke em A (BOMBSITE A), aos 1:30 (relógio) | pronto para confirmar |  |
| 3 | Inferno | "o 2 joga molotov na Banana aos 1:20" | jogador 2 (time?): molotov em Banana (BANANA), aos 1:20 (relógio) | De qual time é "o 2"? [TR 2 / CT 2] |  |
| 4 | Mirage | "ct 3 vai pro meio" | CT 3: correndo até Meio (MIDDLE), sem horário | Quando começa "ct 3 vai pro meio"? |  |
| 5 | Mirage | "tr 1 corre até o spawn ct aos 1:00" | TR 1: correndo até CTSpawn, aos 1:00 (relógio) | pronto para confirmar |  |
| 6 | Nuke | "jogador 2 joga uma molotov na rampa e roda pra o meio correndo" | jogador 2 (time?): molotov em ?, sem horário<br>jogador 2 (time?): correndo até ?, depois | De qual time é "jogador 2"? [TR 2 / CT 2]<br>Qual "rampa"? [Rampa · cima · RAMP / Rampa · baixo · RAMP]<br>Quando começa "jogador 2 joga uma molotov na rampa"?<br>Não achei o lugar "meio" neste mapa. Qual destes? |  |
| 7 | Mirage | "awper segura B" | TR 1 [AWPer]: segura B (BOMBSITE B), sem horário | Quando começa "awper segura B"? |  |
| 8 | Mirage | "tr 4 espera 5 segundos e depois vai pra b" | TR 4: espera 5 s, sem horário<br>TR 4: correndo até B (BOMBSITE B), depois | Quando começa "tr 4 espera 5 segundos"? |  |
| 9 | Mirage | "tr 2 e tr 3 jogam flash na b aos 0:50" | TR 2 + TR 3: flash em B (BOMBSITE B), aos 0:50 (relógio) | pronto para confirmar |  |
| 10 | Mirage | "o jogador 2 joga a molotov na caverna aos 1:20 e roda pra tv correndo" | jogador 2 (time?): molotov em Caverna (T RAMP), aos 1:20 (relógio)<br>jogador 2 (time?): correndo até TV (HOUSE), depois | De qual time é "jogador 2"? [TR 2 / CT 2] |  |
| 11 | Mirage | "tr 1 vai até a escada" | TR 1: correndo até ?, sem horário | Não achei o lugar "escada" neste mapa. Qual destes? [Escada TV · SIDE ALLEY / Corredor Escada · BACK ALLEY / Escada Rato · UNDERPASS]<br>Quando começa "tr 1 vai até a escada"? |  |
| 12 | Mirage | "joga uma smoke" | quem?: smoke em ?, sem horário | Quem faz "joga uma smoke"? [TR 1 / TR 2 / TR 3 / TR 4]<br>Em que lugar? ("joga uma smoke")<br>Quando começa "joga uma smoke"? |  |
| 13 | Mirage | "tr 3 joga flash e entra na b" | TR 3: flash em ?, sem horário<br>TR 3: correndo até B (BOMBSITE B), depois | Em que lugar? ("tr 3 joga flash")<br>Quando começa "tr 3 joga flash"? |  |
| 14 | Dust2 | "tr 5 corre pro long depois ele joga uma he aos 1:10" | TR 5: correndo até ?, sem horário<br>TR 5: he em ?, aos 1:10 (relógio) | Não achei o lugar "long" neste mapa. Qual destes? [LONG A / LONG DOORS / OUTSIDE LONG]<br>Quando começa "tr 5 corre pro long"?<br>Em que lugar? ("ele joga uma he aos 1:10") | depende do deslocamento (ação 1) |
| 15 | Mirage | "tr 2 corre pra b em 3 segundos" | TR 2: correndo até B (BOMBSITE B), sem horário, duração pedida 3 s | Quando começa "tr 2 corre pra b em 3 segundos"? | duracao_imposta |
| 16 | Mirage | "tr 2 joga smoke na janela mercado aos 1:30" | TR 2: smoke em Janela Mercado (SHOP), aos 1:30 (relógio) | pronto para confirmar |  |
| 17 | Mirage | "ct 4 vai pro default do A aos 1:50" | CT 4: correndo até Default (BOMBSITE A), aos 1:50 (relógio) | pronto para confirmar |  |
| 18 | Mirage | "ct 3 joga flash na lixeira do ct aos 1:40" | CT 3: flash em Lixeira (CT SPAWN), aos 1:40 (relógio) | pronto para confirmar |  |
| 19 | Mirage | "tr 1 segura banco do meio aos 1:15" | TR 1: segura Banco (MIDDLE), aos 1:15 (relógio) | pronto para confirmar |  |
| 20 | Mirage | "tr 5 anda pra caverna tr aos 1:10" | TR 5: andando até Caverna TR (PALACE ALLEY), aos 1:10 (relógio) | pronto para confirmar |  |
| 21 | Mirage | "o awper agacha na plataforma aos 1:00" | TR 1 [AWPer]: agachado até Plataforma (PALACE ALLEY), aos 1:00 (relógio) | pronto para confirmar |  |
| 22 | Mirage | "tr 2 joga molotov na escada tv e depois vai pra TV" | TR 2: molotov em Escada TV (SIDE ALLEY), sem horário<br>TR 2: correndo até TV (HOUSE), depois | Quando começa "tr 2 joga molotov na escada tv"? |  |
| 23 | Mirage | "tr 3 vai pro tapete a aos 1:05" | TR 3: correndo até Palácio (PALACE INTERIOR), aos 1:05 (relógio) | pronto para confirmar |  |
| 24 | Mirage | "ct 2 segura o mogi aos 1:45" | CT 2: segura Moddii (BOMBSITE B), aos 1:45 (relógio) | pronto para confirmar |  |
| 25 | Mirage | "tr 1 e tr 2 vão pra TV aos 1:35" | TR 1 + TR 2: correndo até TV (HOUSE), aos 1:35 (relógio) | pronto para confirmar |  |
| 26 | Mirage | "tr 4 joga smoke na caixa fogo aos 0:55 e ao mesmo tempo tr 5 joga flash na caixa fogo" | TR 4: smoke em Caixa Fogo (BOMBSITE A), aos 0:55 (relógio)<br>TR 5: flash em Caixa Fogo (BOMBSITE A), ao mesmo tempo | pronto para confirmar |  |
| 27 | Mirage | "ct 1 vai pra base tr em 12 segundos" | CT 1: correndo até Base TR (T SPAWN), sem horário, duração pedida 12 s | Quando começa "ct 1 vai pra base tr em 12 segundos"? | duracao_imposta |
| 28 | Mirage | "tr 2 joga molotov no tetris aos 40 segundos" | TR 2: molotov em Tetris (BOMBSITE A), sem horário | 40 segundos contados como? [40 s no relógio do round (0:40) / 40 s depois do início do round] |  |
| 29 | Mirage | "tr 2 joga molotov no tetris aos 40 segundos do início" | TR 2: molotov em Tetris (BOMBSITE A), aos 40 s do início | pronto para confirmar |  |
| 30 | Nuke | "tr 2 vai pro silo aos 1:00" | TR 2: correndo até ?, aos 1:00 (relógio) | Qual "silo"? [Silo · cima · RAFTERS / Silo · baixo · BOMBSITE B] |  |

## Casos de honestidade (além das 30)

| # | mapa | frase | o que o leitor entendeu | o que pergunta | avisos |
|---|---|---|---|---|---|
| 31 | Mirage | "ct 3 corre pro meio aos 3:20" | CT 3: correndo até Meio (MIDDLE), sem horário | O horário 3:20 não existe no round. |  |
| 32 | Mirage | "tr 2 vai pra xyzzy aos 1:00" | TR 2: correndo até ?, aos 1:00 (relógio) | Não achei o lugar "xyzzy" neste mapa. Qual destes? |  |
| 33 | Mirage | "tr 2 vai pra caverma aos 1:00" | TR 2: correndo até ?, aos 1:00 (relógio) | Não achei o lugar "caverma" neste mapa. Qual destes? [Caverna · T RAMP / Caverna TR · PALACE ALLEY] |  |
| 34 | Mirage | "joga uma bomba na tv" | quem?: granada? em TV (HOUSE), sem horário | Quem faz "joga uma bomba na tv"? [TR 1 / TR 2 / TR 3 / TR 4]<br>Qual granada em "joga uma bomba na tv"? [Smoke / Flash / Molotov / HE]<br>Quando começa "joga uma bomba na tv"? | palavra_sobrando |
| 35 | Mirage | "tr 2 vai pra Bombsite A aos 1:00" | TR 2: correndo até A (BOMBSITE A), aos 1:00 (relógio) | pronto para confirmar |  |
| 36 | Mirage | "tr 2 vai pra BOMBSITEA aos 1:00" | TR 2: correndo até A (BOMBSITE A), aos 1:00 (relógio) | pronto para confirmar |  |
| 37 | Mirage | "tr 2 segura TopOfMid aos 1:00" | TR 2: segura TopofMid, aos 1:00 (relógio) | pronto para confirmar |  |
| 38 | Mirage | "tr 2 joga a molotov na b aos 1:00" | TR 2: molotov em B (BOMBSITE B), aos 1:00 (relógio) | pronto para confirmar |  |
| 39 | Mirage | "tr 2 joga smoke na b aos 1:10 e depois joga flash na b aos 1:30" | TR 2: smoke em B (BOMBSITE B), aos 1:10 (relógio)<br>TR 2: flash em B (BOMBSITE B), aos 1:30 (relógio) | pronto para confirmar, com aviso | ordem_invertida |
| 40 | Mirage | "o lurker vai pra b aos 1:00" | Lurker (quem?): correndo até B (BOMBSITE B), aos 1:00 (relógio) | Não achei "lurker" na tática. Quem é? [TR 1 / TR 2 / TR 3 / TR 4] |  |
| 41 | Mirage | "jogador dois joga smoke na b aos 1:30" | jogador 2 (time?): smoke em B (BOMBSITE B), aos 1:30 (relógio) | De qual time é "jogador dois"? [TR 2 / CT 2] |  |
| 42 | Mirage | "tr um joga um smoke na b aos 1:00" | TR 1: smoke em B (BOMBSITE B), aos 1:00 (relógio) | pronto para confirmar |  |
| 43 | Mirage | "joga um smoke na b aos 1:00" | quem?: smoke em B (BOMBSITE B), aos 1:00 (relógio) | Quem faz "joga um smoke na b aos 1:00"? [TR 1 / TR 2 / TR 3 / TR 4] |  |
| 44 | Mirage | "tr 2 entra na b aos 1:00" | TR 2: correndo até B (BOMBSITE B), aos 1:00 (relógio) | pronto para confirmar |  |
| 45 | Mirage | "tr 2 sobe pro meio aos 1:00" | TR 2: correndo até Meio (MIDDLE), aos 1:00 (relógio) | pronto para confirmar |  |
| 46 | Mirage | "tr 2 desce pra b aos 1:00" | TR 2: correndo até B (BOMBSITE B), aos 1:00 (relógio) | pronto para confirmar |  |
| 47 | Mirage | "tr 2 volta pro spawn ct aos 1:00" | TR 2: correndo até CTSpawn, aos 1:00 (relógio) | pronto para confirmar |  |
| 48 | Mirage | "tr 2 rotaciona pra b aos 1:00" | TR 2: correndo até B (BOMBSITE B), aos 1:00 (relógio) | pronto para confirmar |  |
| 49 | Inferno | "tr 2 vai pra banana aos 1:00" | TR 2: correndo até Banana (BANANA), aos 1:00 (relógio) | pronto para confirmar |  |
| 50 | Mirage | "tr 2 vai pro default aos 1:00" | TR 2: correndo até ?, aos 1:00 (relógio) | Qual "default"? [Default · BOMBSITE B / Default · BOMBSITE A] |  |

## O que o leitor ainda não faz (de propósito ou por limite)

- **Não calcula tempo de corrida, chegada nem granada real** (C3 e C4): só marca `depende_do_deslocamento` e `duracao_imposta`.
- **Número por extenso só de 1 a 5 e só para jogador**; horário por extenso ("um e vinte") não. Granada em lista ("joga flash e smoke na b") e verbo fora da lista ("peeka") não: viram pergunta "o que o jogador faz?".
- **Erro de digitação não é corrigido**: "caverma" só aparece como sugestão. É a regra da C0 (nunca um chute), com o custo de perguntar mais.
- **"window" na Mirage** não é apelido de nada (o Pedro ainda não escolheu acrescentar como apelido do Janelão); o leitor responde "não achei o lugar" e sugere nada.
- **Pontos de mapas ainda não conferidos** (`conferido = não`) entram no contexto por padrão; o parâmetro `so_conferidos` do contexto os tira. Quem usa o leitor na tela (C2) decide.
- **O jogador que muda de andar**: o leitor devolve o andar do ponto no alvo; a regra do Pedro (a peça vai para o andar do ponto; sem amostra, sem estimativa de tempo por causa da troca de andar) fica para a C2 e a C3.
