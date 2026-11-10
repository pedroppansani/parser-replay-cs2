# Comandos na prancheta (C0b): os callouts do Pedro como dado

Só dado e conferência; nada no site. As 12 imagens do Pedro (material de terceiros) NÃO estão no repositório, nem copiadas nem recortadas: só o nome e a posição que se tirou delas. Scripts em `pesquisa/comandos_c0b_*.py`; a leitura dos nomes, imagem por imagem, em `pesquisa/callouts_br/*.txt` (texto) e o alinhamento em `pesquisa/callouts_br/alinhamento.json`.

## 1. Alinhamento com o radar do projeto

Não coincidem pixel a pixel: cada imagem é **o mesmo radar, com escala própria e deslocamento, sem rotação** (rotação estimada entre −0,11° e +0,15°, escala igual em x e y). A transformação (imagem do Pedro → radar do projeto, 1024 × 1024) foi estimada alinhando o mapa nas duas imagens e refinada por correlação (ECC). Erro que sobra: distância do contorno do radar do projeto até a borda mais próxima na imagem do Pedro (o texto branco ignorado), em px do radar e em unidades do jogo (u):

| imagem | escala | erro mediano / p90 (px) | erro mediano / p90 (u) |
|---|---|---|---|
| ancient | 0,839 | 1,0 / 3,3 | 5 / 16 |
| anubis | 0,930 | 1,0 / 2,9 | 5 / 15 |
| cache | 0,918 | 1,9 / 5,7 | 11 / 32 |
| dust2 | 0,969 | 0,0 / 1,9 | 0 / 8 |
| inferno | 0,885 | 1,0 / 2,3 | 5 / 11 |
| mirage | 0,815 | 1,0 / 2,3 | 5 / 12 |
| overpass | 0,961 | 1,4 / 5,7 | 7 / 30 |
| train | 0,959 | 1,0 / 9,0 | 4 / 37 |
| nuke-cima | 0,911 | 1,0 / 2,9 | 7 / 20 |
| nuke-baixo | **0,534** | 1,0 / 4,6 | 7 / 33 |
| vertigo-cima | 0,690 | 1,0 / 3,8 | 4 / 15 |
| vertigo-baixo | 0,706 | 1,0 / 6,1 | 4 / 25 |

O erro é muito menor que uma área de lugar (~500 u de lado). **Conferido de outro jeito:** as letras vermelhas A e B de cada imagem, convertidas, caem em `BombsiteA` e `BombsiteB` da demo nos 7 mapas com tabela (na Overpass B e na Nuke A encostam também em Water e Rafters). A Nuke de baixo (e a Vertigo de baixo) têm escala própria: o andar de baixo foi enquadrado de outro jeito pelo Pedro, com o zoom do radar do jogo. Conferi a olho a sobreposição (contorno do projeto sobre a imagem do Pedro) na Mirage, na Nuke de baixo e na Vertigo de baixo; nos outros, o erro do contorno e as imagens de conferência. A Train tem o p90 mais alto (9 px, 37 u); a mediana é 4 u.

## 2 a 5. Os pontos

**610 pontos** em `data/reference/callouts_br.csv` (UTF-8 com BOM, `;`, abre no Excel): mapa, andar, nome, apelidos, qualificação, posição vertical (↑/↓), tipo, x, y (unidades do jogo, no andar da imagem), lugar da demo, lugares na borda, nome repetido, texto original, observação, fonte, `conferido = não`.

| mapa | pontos | A/B | nomes que se repetem (pontos) | na borda de 2 lugares | célula sem nome na demo ("mais perto") |
|---|---|---|---|---|---|
| ancient | 48 | 2 | 5 nomes (10) | 6 | 9 |
| anubis | 45 | 2 | 2 (4) | 9 | 1 |
| cache | 58 | 2 | 4 (8) | sem tabela | sem tabela |
| dust2 | 55 | 2 | 5 (10) | 7 | 5 |
| inferno | 68 | 2 | 3 (6) | 11 | 13 |
| mirage | 73 | 2 | 10 (19) | 17 | 6 |
| nuke (cima 41 + baixo 22) | 63 | 2 | 8 (17) | 18 | 9 |
| overpass | 63 | 2 | 2 (4) | 12 | 6 |
| train | 60 | 2 | 2 (4) | sem tabela | sem tabela |
| vertigo (cima 58 + baixo 19) | 77 | 2 | 11 (25) | sem tabela | sem tabela |

**Nomes com "?": 0.** Duas leituras duvidosas foram resolvidas com recorte ampliado ("Buraco/ Escadão" na Anubis, "S1mple" na Inferno e "Simples" na Dust2). Não conferi com o Pedro: o que ficou é a minha leitura. As ressalvas (o que a leitura decidiu) vão na coluna `observacao`: "L" como apelido, "(MF)" como qualificação, "ou Tapete A" como apelido, "(Hell)" como qualificação, "Caixa do Quadrado/Jardim" (a barra pode querer dizer duas caixas), "(Bomb) Antigo" (parênteses no começo) e os rótulos todos entre parênteses (8). Dois "L" na Mirage, um branco grande e um cinza pequeno. Rótulos que o Pedro pôs fora do mapa ou onde ninguém pisou no corpus ficam com o lugar da demo "(mais perto)" (49 pontos).

**Lugar da demo:** a área do `place` da célula do ponto; na borda (outro nome num raio de 12 px do radar, ~60 u) a coluna `lugares_na_borda` diz o outro. **Mapas sem tabela da demo (Cache, Train, Vertigo): 195 pontos sem lugar da demo**; neles os pontos do Pedro são o único alvo.

## 6. `apelido_br` da tabela da C0

Preenchida com os nomes do Pedro que caem dentro de cada lugar da demo (366 nomes em 136 dos 171 lugares), sem apagar o que havia ("A / bomb A / site A" etc. ficou). Os pontos "(mais perto)" não entram (não caem dentro de nenhum). **25 lugares da demo ficaram sem nome do Pedro** (ainda "?"): Ancient MainHall e TopofMid; Anubis Bricks, TunnelStairs, Water; Dust2 ExtendedA, ShortStairs, TRamp, TunnelStairs; Inferno BackAlley, Balcony, Kitchen, Library; Mirage Scaffolding; Nuke Crane, Heaven, Hell, HutRoof, LockerRoom, Roof; Overpass Fountain, SideAlley, Stairs, TStairs, UnderA. Como lugares da demo são grossos e as áreas dos nomes do Pedro nem sempre coincidem com elas, **a coluna mistura nomes de lugares que o Pedro separa** (no Mirage, `BombsiteA` leva "Tetris / Sanduíche / Areia / Caixa Fogo…"): serve para o leitor saber em que área da demo cai cada nome, não para dizer que são o mesmo lugar.

## 7. A prancheta de Train, Vertigo e Cache

A página da prancheta é gerada para todo radar calibrado de mapa `de_*` (`mapas_disponiveis`), então **as três já existem**; Cache e Vertigo aparecem no grupo "Sem partidas no corpus". Têm: radar, botão de andares (Vertigo tem `vertical_sections` e a camada de baixo no JSON), desenho, caminho, granadas com tempo de voo. **Não têm:** (a) tabela de lugares da demo (o roteiro sai sem nome do lugar); (b) biblioteca de arremessos reais em Cache e Vertigo (Train tem 860); (c) tempo de corrida medido (Train tem 1 partida; Cache e Vertigo nenhuma): só "estimado". **O que falta para usar os pontos do Pedro** (nada existe hoje): um canal de dados "pontos nomeados por mapa" na página (a tabela `lugares` só carrega nomes e células da demo); o andar do ponto virar altura (Vertigo corta em Z = 11700, Nuke em −495); e o leitor aceitar o nome do jogo em inglês como alternativa (já decidido). As páginas dos três mapas funcionam hoje sem nada disso.

## 8. As imagens de conferência

12 imagens (`conferencia/<arquivo>-conferencia.png`, 1,2 a 3,1 mil px de lado) em `C:\Users\User\Desktop\Claude outputs\callouts-br\conferencia\`, fora do repositório: o radar DO PROJETO, cada ponto (ciano) com o nome e os apelidos, o contorno laranja das áreas da demo e seus nomes em itálico. Não chamo de "pontos 100% certos": onde dois nomes se encostam o texto sai deslocado com uma linha até o ponto.

## Como o leitor usa os pontos e as áreas (proposta)

- **Ponto do Pedro = alvo.** "vai até Caverna", "molotov em TV": o ponto exato (x, y no andar dele). O nome é achado sem diferença de maiúscula, acento e espaço, pelo nome ou por qualquer apelido; o nome do jogo em inglês continua valendo (decisão do Pedro), caindo na área da demo. Nome repetido no mapa = pergunta "qual?" com botões e o lugar de cada um ("Default: no A ou no B?").
- **Lugar da demo = chave do corpus.** O tempo real vem da demo, que só conhece áreas. Cada ponto traz o lugar da demo em que cai (e a borda), então o leitor sabe de que área medir.
- **Ordem do tempo mostrado:** (1) entre os dois PONTOS, se tiver amostra (abaixo); (2) entre as duas ÁREAS da demo (a faixa da C0); (3) "estimado" (reta ÷ `VELOCIDADE_U_S`), sempre dizendo qual dos três foi.
- **Molotov real:** o destino de cada arremesso da biblioteca ganha o ponto do Pedro mais perto (em vez de o lugar da demo); "molotov na caverna" busca os reais cujo destino cai mais perto de "Caverna" (decisão 3 da C0: o mais perto do jogador e levar até o ponto de lançamento). Cache e Vertigo não têm biblioteca: molotov sem arremesso real, com o aviso.

## O tempo do corpus pode ser medido entre dois pontos do Pedro?

**Pode, com a mesma definição da C0.** Cada jogador vivo, a cada 8 ticks, é "no ponto P" se P é o mais perto e está a até 200 u (`pesquisa/comandos_c0b_pontos.py`; só mapas de um andar, os 3 maiores). Pares com n ≥ 20 casos em ≥ 3 partidas, contra os pares de áreas da demo:

| mapa | pontos | pares possíveis | com amostra (pontos) | % | com amostra (áreas da demo, C0) | % |
|---|---|---|---|---|---|---|
| mirage | 69 | 4.692 | 671 | 14% | 100 de 506 | 20% |
| dust2 | 51 | 2.550 | 329 | 13% | 107 de 552 | 19% |
| inferno | 64 | 4.032 | 240 | 6% | 44 de 552 | 8% |

(Sem os "Default", 69, 51 e 64 pontos.) Em números absolutos há bem mais pares com tempo medido; em fração, um pouco menos. **O par do exemplo do Pedro, Caverna → TV na Mirage, tem 9 casos (6 partidas) até a TV de baixo e 14 (7 partidas) até a outra, mediana 12 a 14 s de saída a chegada, e 15 a 17 s de entrada a entrada: abaixo do mínimo de 20, então hoje sairia "estimado".** Baixar o mínimo para 10 casos dá 1.124 pares na Mirage (24%).

## O que ficou para o Pedro decidir

1. **Mínimo de amostra do tempo entre pontos.** (a) 20 casos e 3 partidas (como na C0); (b) 10 casos e 3 partidas. **Recomendo (a) como regra e mostrar o número de casos de todo jeito**, deixando (b) para depois de ver na tela.
2. **Nome repetido.** (a) sempre perguntar "qual?"; (b) usar o mais perto do jogador e dizer qual. **Recomendo (a)** (nunca um chute).
3. **Os pontos ficam como `conferido = não` até o Pedro conferir as 12 imagens.** Nada na C1 deve valer antes disso.
4. **Andares.** O ponto não tem altura, só o andar da imagem; Nuke e Vertigo precisam de uma regra para o jogador que muda de andar no comando ("vai até Silo" estando em cima). **Recomendo:** o comando diz o andar na tela e o jogador troca de andar no próprio ponto do Pedro.
5. **Os 25 lugares da demo sem nome do Pedro** (lista acima): deixar como estão ("?", só pelo nome em inglês) ou o Pedro completa.
6. **Leituras com ressalva** (coluna `observacao`): "L", "(MF)", "ou Tapete A", "(Hell)", "Caixa do Quadrado/Jardim" e "(Bomb) Antigo": ver se o que li é o que ele quis.

## Limite de reprodução

O script que estimou o alinhamento (busca de escala e deslocamento nas máscaras do mapa, depois ECC do OpenCV) não está no repositório: só o resultado (`pesquisa/callouts_br/alinhamento.json`). A leitura dos nomes é manual (sem OCR), e o centro de cada texto foi ajustado ao bloco de texto mais perto (até 15 px) lendo a imagem do Pedro, que precisa estar na pasta `callouts-br` para `pesquisa.comandos_c0b_callouts` regerar o CSV.

## Decisões do Pedro (2026-11-10) e o que mudou nos dados

1. **Mínimo para o tempo real: 20 casos e 3 partidas.** Abaixo disso, "estimado".
2. **Nome repetido: perguntar "qual?" com botões**, mas aceitar qualificadores que resolvem sozinhos ("default do A", "lixeira do CT", "banco do meio").
3. **Conferência:** Mirage e Dust2 estão conferidas (`conferido = sim` nos 128 pontos dos dois mapas); os outros 8 seguem `não` até o Pedro avisar.
4. **Troca de andar:** a peça vai para o andar do ponto. O tempo vem do corpus, se houver amostra; se não houver, o site diz que não estimou o tempo por causa da troca de andar, em vez de usar a linha reta.
5. **Os 25 lugares da demo sem apelido** ficam só com o nome do jogo em inglês.
6. **Ressalvas:** "L" fica como está (repetido, então pergunta); "(MF)" virou o apelido "MF" do Meio Falso (Mirage, Inferno, Vertigo); "ou Tapete A" é apelido do Palácio; "(Hell)" é apelido do Inferno (Nuke); "Caixa do Quadrado" e "Caixa do Jardim" valem as duas (Ancient); "(Bomb) Antigo" aceita "Bomb Antigo" e "Antigo" (Train); **"Mogi" foi acrescentado como apelido do "Moddii"** na Mirage (a imagem do Pedro diz "Moddii"; "Mogi" não estava nos dados, então não havia o que conferir: entrou por pedido dele). Os ajustes estão em `AJUSTES` de `pesquisa/comandos_c0b_callouts.py`.
