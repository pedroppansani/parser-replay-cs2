# Comandos na prancheta (fase C0): o que o dado sustenta

Só investigação e proposta. Nada no site, nos dados ou na biblioteca mudou. Os scripts de leitura estão em `pesquisa/comandos_c0_*.py` (viagens, análise, biblioteca, tabela); os logs e os JSON estão em `notas/logs/c0-*` (a pasta não vai para o git). Corpus: 52 partidas, 8 mapas; só 7 têm tabela de lugares (o Train tem 1 partida e fica sem).

## 1. Os nomes de lugar por mapa

Existem duas fontes e são a mesma coisa vista de dois jeitos: o `place` que a demo grava em cada tick e a tabela `data/lugares/<mapa>.json`, feita a partir dele (uma grade de células com o `place` mais comum). Todo `place` do corpus está na tabela (0 ticks fora), então não há nome que a demo tenha e o mapa não tenha.

| mapa | nomes | lado típico da área (u) | menor / maior | nomes com mais de um pedaço separado |
|---|---|---|---|---|
| de_ancient | 18 | 522 | 259 / 924 | 0 |
| de_anubis | 28 | 474 | 200 / 885 | 1 (Canal) |
| de_dust2 | 24 | 495 | 122 / 1119 | 3 (BDoors, ExtendedA, TSpawn) |
| de_inferno | 24 | 468 | 141 / 988 | 2 (Apartments, Bridge) |
| de_mirage | 23 | 504 | 80 / 1010 | 2 (PalaceInterior, Underpass) |
| de_nuke | 29 | 320 | 128 / 1583 | 13, e 2 em dois andares (Ramp, Secret) |
| de_overpass | 25 | 485 | 166 / 1372 | 3 (UnderA, UpperPark, Water) |

"Lado típico" é a raiz da área (cada nome é uma região de ~500 u de lado, ~2,5 s de corrida). Um nome é uma ÁREA, não um ponto. O desenho do mapa já guarda uma âncora por nome (a célula mais funda da região, `metrics.lugares.rotulos`); a âncora fica a 73 a 134 u do ponto típico onde os jogadores realmente estiveram (mediana por mapa), no pior caso 961 u (um nome de vários pedaços na Nuke).

**Qual serve de alvo de "vai até X": o nome da tabela do mapa (a área), com a âncora só para desenhar.** Motivo: é o mesmo nome que o mapa e o replay já mostram, o corpus mede a chegada em ÁREA (entrar no lugar), e a âncora é determinística. O `place` cru não acrescenta nada.

**Dois limites que importam:**
- A tabela é GROSSA: 18 a 29 nomes por mapa. Os callouts que a comunidade usa e que não existem no dado incluem "Window", "Ticket", "Long" na Mirage, etc. **"Caverna" e "TV", do exemplo do Pedro, não existem em nenhum dos 7 mapas.** Comando com nome fora da tabela não tem como funcionar sem uma tabela nova, feita à mão, de pontos ou áreas (decisão aberta 1).
- Nomes de vários pedaços (Nuke: 13 dos 29; TSpawn tem 3 pedaços na Dust2 e 6 na Nuke) fazem "vai pra X" ser ambíguo: o leitor pergunta "qual X?" com botões.

## 2. O caminho (contornar paredes)

- O awpy 2.0.2 TEM o leitor da malha de navegação (`awpy.nav.Nav`, com `find_path`), mas os `navs` não estão nesta máquina (`~/.awpy/navs` não existe) e o download oficial responde 403 (nota 2026-10-15).
- O mesmo autor publica os `.nav` na release 2000932 do `pnxenopoulos/awpy-data` (`navs.zip`, 8,4 MB, os 8 mapas; baixei para uma pasta de rascunho e o sha256 bate com o manifesto da release).
- **O leitor do awpy 2.0.2 NÃO lê esses arquivos:** eles são versão 36 do formato e ele aceita 30 a 35 (`ValueError: Unsupported nav version: 36`). Tentei lê-los com o leitor da versão 35 (pulando 0, 4 ou 8 bytes a mais): falha já na leitura inicial, então o cabeçalho mudou. Isso exigiria um leitor novo (o formato está no ValveResourceFormat), um trabalho próprio com teste contra o `.tri` que o projeto já tem.
- Já existem `~/.awpy/tris` (colisão, sha256 em `metrics/visao_malhas.json`), usados para linha de visão. Daria para derivar caminho deles, mas é projeto maior e não é o que o awpy oferece.
- **Sem malha, o que dá para usar sem inventar:** (a) a reta, como no Reescrever; (b) o tempo real do corpus entre os dois lugares (item 4), que já contém as paredes.
- **Quanto a reta erra:** nas viagens reais correndo sem parar, o caminho andado é 1,15 a 1,27 vezes a reta (mediana por mapa; em pares com 1,4 a 1,5, como Mirage TSpawn→TopofMid). A reta de âncora a âncora a 210 u/s fica ENTRE as duas medidas do corpus na maioria dos mapas, e erra feio onde há andares (Nuke, Outside→BombsiteA: reta 3,3 s contra 5,4 a 8,1 s medidos).

## 3. A velocidade

Já medida e registrada: `metrics/tactics.VELOCIDADE_U_S` (nota 2026-10-04-velocidade-e-voo): rifle 210,6 correndo / 111,8 andando / 90,4 agachado; AWP 197,1 / 104,0 / 82,4. São MEDIDAS do corpus (mediana de janelas de 0,5 s em movimento livre, 12 partidas), coerentes com o jogo (faca 250, AWP sem mira 200), não constantes lidas do jogo. A nota também mediu pistola 234 e SMG 229,4 correndo, que não estão na constante. Para o comando: "corre / anda / agacha" mapeia direto nos 3 modos; a arma segue a regra da prancheta (AWPer com AWP, os outros rifle). Nenhuma velocidade nova a medir; só deixar claro, na tela, que o número é do corpus.

## 4. Os tempos reais de corrida entre dois lugares

Dá para medir, e com amostra grande. `pesquisa/comandos_c0_viagens.py` achou 229.670 viagens (jogador vivo, round valendo, do último tick em A ao primeiro em B, no máximo 25 s). **Atenção à definição:** os nomes são áreas, e quem "parte de A" parte de algum ponto dentro dela. Medi duas pontas: `saída→entrada` (do último tick em A ao primeiro em B, subestima) e `entrada→entrada` (do primeiro tick em A ao primeiro em B, superestima, 1,6 a 1,9 vezes a primeira). O tempo "de um ponto de A" fica entre as duas. Viagem de corrida = sem parada de mais de 1 s abaixo de 40 u/s, andando (shift) em no máximo 10% dos ticks, reta de pelo menos 300 u.

Três pares reais (mediana, p25 a p75 e quantos casos; todas as partidas do mapa):

| mapa | par | casos (partidas) | saída→entrada | entrada→entrada | reta / caminho | reta de âncora a âncora ÷ 210 |
|---|---|---|---|---|---|---|
| Mirage | TSpawn → TopofMid | 560 (16) | 4,9 s (4,8 a 5,0) | 7,2 s | 796 u / 1173 u | 5,0 s |
| Dust2 | CTSpawn → BDoors | 371 (10) | 3,6 s (3,2 a 4,9) | 6,9 s | 771 u / 820 u | 5,9 s |
| Nuke | Outside → BombsiteA | 230 (9) | 5,4 s (4,2 a 5,8) | 8,1 s | 788 u / 1050 u | 3,3 s |

**Aviso de viés:** os pares mais frequentes são os do começo do round (spawn para fora), que são rushes iguais entre si; por isso o p25 a p75 fica tão estreito. Pares de meio de round têm menos casos e mais dispersão.

Quantos pares por mapa têm amostra (pares possíveis = nomes × (nomes − 1)):

| mapa | partidas | possíveis | com n ≥ 5 | n ≥ 10 | n ≥ 20 | n ≥ 30 |
|---|---|---|---|---|---|---|
| de_ancient | 3 | 306 | 102 | 60 | 31 | 23 |
| de_anubis | 5 | 756 | 218 | 117 | 60 | 30 |
| de_dust2 | 10 | 552 | 281 | 192 | 107 | 74 |
| de_inferno | 6 | 552 | 134 | 81 | 44 | 31 |
| de_mirage | 16 | 506 | 266 | 179 | 100 | 75 |
| de_nuke | 9 | 812 | 195 | 113 | 71 | 52 |
| de_overpass | 2 | 600 | 132 | 79 | 39 | 23 |

**Mínimo proposto: n ≥ 20 casos e pelo menos 3 partidas distintas** (Overpass tem só 2 partidas, então sai sem tempo medido). Com n ≥ 20 e 3 partidas há 30 a 107 pares por mapa nos 6 mapas que passam, 8% a 20% dos pares possíveis (Overpass: 0); **o resto cai para o cálculo "estimado"** (reta ÷ velocidade, marcado). O erro da reta contra a mediana medida, nos pares com n ≥ 10: 0,4 a 1,3 s em mediana, e a reta subestima o tempo em 62% a 89% dos pares.

## 5. A molotov real para o comando

Funciona como o R4 (mesmo tipo, mesmo lado, voo e efeito conhecidos, a até 150 u de quem lançou). O destino de cada molotov da biblioteca ganha o nome do lugar mais perto do ponto de queda (a mesma regra da L1, nome da tabela do mapa, sem molotov sem nome em nenhum dos 7 mapas). `pesquisa/comandos_c0_biblioteca.py` mediu, para os 3 destinos de molotov mais comuns de cada mapa e cada lado: quantas molotovs reais, de quantos pontos de lançamento e em que fração de posições reais de jogadores (a cada 4 s nos primeiros 45 s do round) existe uma delas a até 150 u / 400 u.

| mapa | destino | lado | molotovs (voo e efeito) | pontos de lançamento | posições com uma a ≤150 u | a ≤400 u |
|---|---|---|---|---|---|---|
| Mirage | Apartments | CT | 227 | 20 | 33% | 55% |
| Mirage | TRamp | CT | 224 | 15 | 29% | 49% |
| Mirage | Middle | T | 83 | 5 | 16% | 24% |
| Dust2 | UpperTunnel | CT | 191 | 16 | 19% | 28% |
| Dust2 | LongDoors | T | 8 | 3 | 5% | 18% |
| Inferno | Banana | T | 153 | 10 | 30% | 43% |
| Nuke | Squeaky | CT | 123 | 11 | 28% | 65% |
| Nuke | Silo | T | **0** | 0 | 0% | 0% |
| Overpass | Playground | CT | 30 | 1 | 4% | 9% |

(A tabela completa, 3 destinos × 2 lados × 7 mapas, está em `notas/logs/c0-biblioteca.json`.) Leitura: **a molotov real existe quase sempre para o destino (na Mirage, 622 das 1.564 molotovs com voo e efeito vão para os 3 destinos mais comuns), mas o "perto de onde o jogador está" só dá certo em 4% a 35% das posições a 150 u** (9% a 69% a 400 u; faixa das 31 de 42 combinações destino × lado com pelo menos 20 molotovs), e há combinações sem nenhuma (Nuke Silo para os T, Ancient TSideLower para os T). Os lados são desiguais: o mesmo destino é comum para um lado e quase nunca usado pelo outro.

**O que isso muda:** a regra "a até 150 u de onde o jogador está" é boa demais para um comando escrito. Se a pessoa disser "molotov na caverna" com o jogador no spawn, quase nunca haverá um arremesso a 150 u. O comando precisa BUSCAR o arremesso real mais perto do jogador (mesmo lado, voo e efeito conhecidos) e mostrar de onde ele sai ("a molotov real mais perto sai de 380 u daqui; mover o jogador até lá?"), em vez de exigir proximidade. É a decisão aberta 3.

## 6. A gramática da primeira versão

Entrada: português do Brasil, sem acento e sem maiúscula (normalizados), números por extenso ou algarismo. O leitor divide a frase em orações (por "e", vírgula, "depois", "em seguida", "aí"), preenche campos por oração e **nunca chuta**: campo faltando ou ambíguo vira pergunta com botões.

- **Quem:** "jogador 2", "player 2", "TR 2", "CT 3", "o 2", "número 2"; o nome da função que a prancheta já usa ("o AWPer", "o lurker", "o entry", "o IGL"), se houver exatamente uma na tática. "ele" / "depois ele" = o último citado. Sem lado ("jogador 2") e a tática tem os dois lados: pergunta qual.
- **O quê:** lançar (joga, lança, solta, manda, usa) + smoke (smoke, fumaça), flash (flash, flashbang, luz), molotov (molotov, molo, incendiária, fogo), HE (he, granada, frag); mover (vai, roda, corre, anda, caminha, agacha) + até/pra/para/em + lugar; segurar ("segura X", "fica em X", "holda X"); esperar ("espera N s", "espera até 1:10").
- **Onde:** o nome do lugar pela tabela em português (item 8), com apelidos; letra sozinha ("A", "B") = bombsite. Nome com mais de um pedaço = pergunta "qual?".
- **Quando:** "aos 1:20", "no 1:20", "com 1:20" (relógio do round, contagem regressiva, como a prancheta mostra); "aos 40 s" só vale com "do início"/"depois do começo" (senão pergunta: 40 s no relógio ou 40 s depois do começo?); "depois" / "em seguida" = logo que a ação anterior termina; "ao mesmo tempo" / "junto" = mesmo instante da anterior. Sem horário na primeira ação: pergunta.
- **Como:** "correndo", "andando", "agachado"; sem modo = correndo.
- **O que ele faz quando não entende:** mostra a frase com as partes entendidas destacadas, marca a parte não entendida e pergunta ("Não entendi 'rodar pra tv'. Qual destes lugares você quis dizer?" com botões dos lugares do mapa mais parecidos pelo texto, ou "nenhum"). Palavra desconhecida NUNCA é aproximada em silêncio.

15 frases e o que o leitor entenderia:

| # | frase | leitura |
|---|---|---|
| 1 | "jogador 2 joga smoke em window aos 1:30" | **só entende se "window" estiver na tabela** (não está no dado): pergunta "Qual lugar?" |
| 2 | "TR 2 joga smoke em BombsiteA aos 1:30" | TR 2 · smoke em BOMBSITE A · 1:30. Entende tudo. |
| 3 | "o 2 joga molotov na Banana aos 1:20" | falta o lado (Inferno): "TR 2 ou CT 2?" (botões) |
| 4 | "ct 3 vai pro meio" | CT 3 · mover até MIDDLE ("meio"), correndo; falta horário: pergunta "Quando começa?" |
| 5 | "tr 1 corre até o spawn ct aos 1:00" | TR 1 · mover até CT SPAWN · 1:00 · correndo. Entende tudo. |
| 6 | "jogador 2 joga uma molotov na rampa e roda pra o meio correndo" | duas ações: molotov em RAMP (a tabela diz Ramp, mas na Nuke tem 2 pedaços: pergunta "qual rampa?") e depois mover até MIDDLE; falta horário da primeira |
| 7 | "awper segura B" | AWPer (se há um só na tática) · segurar BOMBSITE B; sem horário: pergunta |
| 8 | "tr 4 espera 5 segundos e depois vai pra b" | espera 5 s, depois mover até BOMBSITE B; horário de início: pergunta |
| 9 | "tr 2 e tr 3 jogam flash na b aos 0:50" | DUAS pessoas na mesma ação: duas flashes em BOMBSITE B · 0:50 (mostra as duas, confirma) |
| 10 | "o jogador 2 joga a molotov na caverna aos 1:20 e roda pra tv correndo" (exemplo do Pedro) | "caverna" e "tv" não existem no dado: duas perguntas ("Qual lugar é 'caverna'?"), com os nomes do mapa como botões; a molotov e a corrida só se montam depois de respondidas |
| 11 | "tr 1 vai até a escada" | "escada" bate com STAIRS e LADDER (Mirage): pergunta "STAIRS ou LADDER?" |
| 12 | "joga uma smoke" | falta quem, onde e quando: três perguntas, uma de cada vez |
| 13 | "tr 3 joga flash e entra na b" | flash (onde? pergunta) + "entra" não está no vocabulário: pergunta "mover até BOMBSITE B?" |
| 14 | "tr 5 corre pro long depois ele joga uma he aos 1:10" | "depois ele": TR 5 de novo; ordem diz mover primeiro (tempo vem do corpus), mas a HE vem com horário fixo 1:10 que pode vir antes de chegar: o leitor AVISA o conflito ("a HE sai antes de ele chegar") e pergunta, em vez de aplicar |
| 15 | "tr 2 corre pra b em 3 segundos" | duração imposta: não é velocidade medida; o leitor mostra o tempo calculado ("o corpus leva 5 s; em 3 s não dá correndo") e pede para confirmar ou trocar; **nunca aplica sem o aviso** |

## 7. Onde roda e como é testado

Um módulo JS puro (sem DOM, sem rede), `prancheta/NN-leitor-de-comandos.js`, que recebe texto + a tabela dos nomes + os jogadores da tática e devolve `{ações, perguntas, entendido}`; o texto da tela (rótulos, frases de pergunta) sai do Python como no resto da prancheta (decisão 18). **Teste sem dependência nova:** os testes de navegador do projeto (Playwright com o Chrome do sistema, como `test_annotations_browser.py`) carregam o módulo numa página em branco e chamam `leitor(frase, contexto)` em um único `page.evaluate` com uma tabela de centenas de frases (as 15 acima mais variações), comparando o JSON devolvido; mais testes de página para a aba (C2). Node 24 existe nesta máquina e no runner `ubuntu-24.04`, mas o projeto não usa Node em teste de site (só em `supabase/tests`); como o módulo é puro, daria para testar com Node, mas não vale entrar com uma segunda via. Um teste adicional de honestidade (como o dos "ganha/vence"): o leitor nunca devolve ação sem os campos obrigatórios, nunca aproxima nome fora da tabela e nunca chama tempo estimado de medido.

## 8. A tabela em português

Rascunho em `notas/investigacoes/2026-11-09-comandos-nomes-em-portugues.csv` (uma linha por lugar, 171 linhas, separador `;`, abre no Excel com acento). Colunas: `mapa`, `nome_do_jogo`, `texto_no_mapa`, `traducao_das_palavras` (mecânica, palavra por palavra, sem apelido), `apelido_br`, `pedacos_no_mapa`, `andares`, `ticks_no_corpus`, `status`. **Só preenchi `apelido_br` onde tenho certeza** (letra do bombsite, spawn, meio): são 32 das 171 linhas, as 139 restantes estão com "?" para você completar. No Brasil boa parte dos callouts fica em inglês ("Banana", "Apps", "Long"), então uma tradução literal ("Fosso" para Pit) pode nem ser como se fala; por isso a coluna é sua. Não invento "Caverna" nem "TV": nenhum mapa tem esses nomes no dado.

## O que o dado NÃO sustenta (e o que isso muda)

1. **"Caverna" e "TV"** do exemplo do Pedro: não há esses nomes. Muda o plano: ou uma tabela nova de áreas (decisão 1) ou o exemplo fica fora.
2. **Caminho que contorna parede:** só com leitor novo para o `.nav` v36. Hoje, a reta (com 5% a 23% de erro mediano para menos) ou o tempo do corpus.
3. **O tempo "de um ponto de A até B"** não existe como número único: o corpus mede de borda a borda. O que dá para mostrar é a faixa honesta (saída→entrada a entrada→entrada) ou um valor com aviso do que ele é.
4. **Molotov real perto do jogador:** 4% a 35% das posições a 150 u (9% a 69% a 400 u).
5. **Mapa Train** (1 partida, sem tabela de lugares) e **Overpass/Ancient** (2 e 3 partidas): sem tempo medido com o mínimo proposto; ficam em "estimado".
6. **Tempo de corrida de quem tem granada, escudo ou tiro ao fundo** (arma na mão): o corpus mede com a arma que o jogador tinha; o comando usa rifle ou AWP.

## Decisões abertas

1. **Nomes mais finos que os da demo.** (a) Só os 18 a 29 nomes da demo; (b) uma tabela nova, feita à mão por mapa, de ÁREAS desenhadas por você sobre o radar (apelidos como "Window", "Caverna", "TV" com posição), nomeada à parte da demo. **Recomendo (a) na C1 e (b) como C1b** depois de ver o quanto os nomes da demo servem.
2. **Caminho e tempo.** (a) Tempo do corpus com a faixa e estimado marcado onde não houver; (b) leitor novo do `.nav` v36 para contornar paredes. **Recomendo (a); (b) só se a faixa incomodar.**
3. **Molotov "perto de onde o jogador está".** (a) manter o raio de 150 u (quase nunca acha); (b) buscar o arremesso real mais perto e oferecer mover o jogador até o ponto de lançamento; (c) pôr a molotov sem arremesso real, com aviso. **Recomendo (b), com (c) como fallback explícito.**
4. **O número que o comando mostra de tempo de corrida.** (a) a mediana de saída→entrada; (b) a faixa; (c) o ponto do meio. **Recomendo (b), "entre 4,9 e 7,2 s", com n.**
5. **Horário.** O exemplo do Pedro usa relógio ("aos 1:20"). Aceito só relógio regressivo ou também "aos 20 s do início"? **Recomendo as duas, perguntando quando não houver "do início".**
