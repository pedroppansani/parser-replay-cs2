# A fonte de "quem estava vendo quem" (fase 18, item 18.1)

**Pergunta.** Os tipos de erro novos (não trocou, possível bait, perdeu a troca, morreu sozinho) dependem
de saber se o matador estava **visível para o jogador** na janela de troca. Qual fonte o dado permite, na
ordem do pedido: (1) a visibilidade gravada na demo, (2) a linha de visão pelo mapa (awpy 2.0.2, `.tri`),
(3) o campo de visão?

**Resposta.** Linha de visão pelo mapa **e** campo de visão **e** não estar cego, para o corpus inteiro
(`metrics/visao.py`). A visibilidade gravada na demo existe, mas só para 13 das 52 partidas, e serve de
conferência: onde a demo marca visível, a regra adotada também marca em 98% das janelas.

## 1. A visibilidade gravada na demo

- O demoparser2 do projeto (0.42.0) lê `m_bSpottedByMask` como `approximate_spotted_by` (a lista de steamids
  que estão vendo o jogador) e `m_bSpotted` como `spotted`, por tick (`parse_ticks`), em ~2 s por demo.
- **Amostragem:** a máscara muda em degraus de 33 ticks (0,5 s; o passo mais comum entre mudanças na
  match_23: 239 de 606 mudanças são de 33 ticks, 83 de 66). "approximate" é isso.
- **Cobertura:** o interim não guarda a máscara, e só 13 partidas têm a demo inteira no disco (match_10, 11,
  12, 14, 15, 16, 17, 18, 19, 20, 23, 41 e 42; a 12 e a 41 em duas partes). As outras 39 só existem no
  interim. Usar a demo onde ela existe e outra fonte no resto faria a régua do Perfil (por lado e função,
  entre partidas) comparar coisas medidas de jeitos diferentes. Por isso ela fica como **conferência**.
- **Comportamento:** a máscara é conservadora. Na match_23, round 1, o tenzy matou quatro jogadores no Upper
  Tunnel (tick 2833 a 3010) com o ZywOo a ~230 unidades olhando para ele (12 a 20 graus do centro da tela) e
  a máscara do tenzy só tem o ropz entre os ticks 2893 e 2925. A máscara é a do radar: alguém "spota" o
  inimigo com regras próprias do jogo (e com atraso), não "está vendo".

## 2. A linha de visão pelo mapa

- `awpy get tris` (awpy 2.0.2) falha: `https://awpycs.com/17595823/tris.zip` responde 403 (também `maps` e
  `navs`), em 2026-10-15. O mesmo autor publica a colisão dos mapas no repositório `pnxenopoulos/awpy-data`
  (releases do GitHub por versão do cliente; formato `.mesh`). `scripts/visao_malhas.py` baixa a release
  2000932 (14/10/2026, patch 1.41.9.1), confere o sha256 do zip, converte os 8 mapas para `.tri` (o formato
  do awpy 2.0.2) em `~/.awpy/tris/` e grava o sha256 de cada um em `metrics/visao_malhas.json`.
- **Funciona nos 8 mapas** e o resultado é o mesmo do verificador do awpy 2.0.2
  (`pesquisa/visao_custo.py`, 600 segmentos entre posições reais de jogadores por mapa; awpy comparado nas
  duas malhas menores, 300 segmentos cada; `tests/test_visao.py` compara também 600 segmentos numa malha
  sintética e 200 na Mirage):

  | mapa | triângulos | grade (s) | consulta (ms) | awpy 2.0.2: montar (s) | awpy: consulta (ms) | iguais |
  |---|---|---|---|---|---|---|
  | de_ancient | 455.880 | 0,2 | 0,31 | — | — | — |
  | de_anubis | 378.619 | 0,1 | 0,27 | — | — | — |
  | de_dust2 | 239.917 | 0,1 | 0,25 | — | — | — |
  | de_inferno | 547.966 | 0,2 | 0,39 | — | — | — |
  | de_mirage | 73.290 | 0,0 | 0,17 | 3 | 0,8 | 300 de 300 |
  | de_nuke | 89.563 | 0,0 | 0,14 | 5 | 0,7 | 300 de 300 |
  | de_overpass | 243.902 | 0,1 | 0,39 | — | — | — |
  | de_train | 428.865 | 0,2 | 0,52 | — | — | — |

  O verificador do awpy é Python puro numa árvore de objetos; a grade do plano (`metrics.visao.Malha`) faz o
  mesmo teste de Möller–Trumbore, com as mesmas tolerâncias, em numpy. Uma partida inteira custa ~5 s.
- **Limites declarados:** a malha é a do cliente de outubro de 2026, não a da data de cada demo (uma mudança
  de mapa entre as duas muda a linha naquele trecho); portas e objetos que se mexem não estão na colisão
  fixa. A smoke fecha a linha: esfera de 144 unidades (o raio do replay, `RAIO_SMOKE_UNIDADES`) por 20 s
  desde o estouro (`DURACAO_SMOKE_S`; o interim não grava o fim da smoke). O alvo é visível se a linha dos
  olhos do jogador (64 em pé, 46 agachado) até a cabeça OU até o meio do corpo do alvo estiver livre.

## 3. O campo de visão

`MEIO_FOV_GRAUS` = 53,13. O CS2 fixa 90 graus na horizontal de uma tela 4:3 e alarga a horizontal nas
telas largas mantendo a vertical (Hor+): em 16:9, tan(h/2) = tan(45°) × (16/9) / (4/3) = 4/3, h = 106,26
graus. Só a horizontal (o ângulo entre o yaw e a direção até o alvo no plano). Quem joga em 4:3 esticado vê
45 graus de cada lado; 16:9 é o pedido.

## Regra adotada

"Visível para o jogador" num tick = o jogador **não está cego** (flash acima de `EFFECTIVE_BLIND_SECONDS`)
**e** o alvo está **dentro do campo de visão** **e** a **linha de visão está livre** (mapa e smoke). A janela
de troca é conferida de 8 em 8 ticks (`AMOSTRA_VISAO_TICKS`: quatro vezes mais fino que a máscara da demo).

## Conferência contra a demo (`pesquisa/visao_contra_demo.py`)

As 11 partidas com UMA demo no disco; para cada morte por inimigo e cada aliado vivo da vítima, a janela de
troca (até 5 s, cortada na morte de um dos dois e no fim do round): 3.945 janelas.

| | janelas |
|---|---|
| a demo marca o matador visível para o aliado | 469 |
| a regra adotada marca | 781 |
| as duas marcam | 460 (98% das da demo) |
| só a demo | 9 |
| só a regra adotada | 321 (103 delas, 32%, com troca de dano entre os dois na janela) |
| nenhuma das duas | 3.155 (129 com troca de dano: granada ou tiro através de parede) |

Concordância por janela: 91,6% (só linha de visão, sem o campo de visão: 89,1%); por amostra de 8 ticks:
97,7%. Onde a demo diz visível, a regra adotada quase sempre diz também; a diferença é a regra adotada achar
visível onde a máscara do radar não marcou, e em um terço desses casos os dois trocaram dano (então se viam).

## Os cinco lances conferidos (`pesquisa/visao_cinco_lances.py`, match_15, Mirage, round 1)

Conferidos contra a máscara da demo e contra o dano trocado na janela; o link abre o replay 2D do site
naquele instante (`py -3.12 -m scripts.build_site`), onde dá para ver a posição e a direção do olhar.

| # | situação | lance | dado | leitura |
|---|---|---|---|---|
| 1 | as duas fontes: visível | Aleksib (BombsiteA) e YEKINDAR (CTSpawn), depois da morte do iM, 0:39 | 971 u, 0,4° do centro da tela, linha livre; visível nas 9 amostras; 65 ticks marcados pela demo; trocaram dano | bate |
| 2 | as duas: não visível | FalleN (Truck) e makazze (BombsiteA), depois da morte do yuurih, 0:18 | 3.134 u, 41° do centro, linha fechada pelo mapa; 0 de 22 amostras; demo 0 | bate: do Truck não se vê o A |
| 3 | só a regra adotada, com dano | w0nderful (Jungle) e YEKINDAR (CTSpawn), 0:40 | 387 u, 11,6° do centro, linha livre em 3 de 9 amostras; a demo não marca; trocaram dano | a demo deixou de marcar: quem troca dano está se vendo |
| 4 | só a regra adotada, sem dano | w0nderful (Sniper's Nest) e KSCERATO (Middle), depois da morte do Aleksib, 1:07 | 1.016 u, 17° do centro, linha livre em 3 de 8 amostras; a demo não marca; sem dano | a janela do Sniper's Nest dá para o meio: visível pela geometria; a máscara do radar não marcou |
| 5 | a smoke fechou a linha | molodoy (Catwalk) e makazze (BombsiteA), 0:21 | 1.833 u, 0,2° do centro; sem a smoke a linha estaria livre em 1 amostra; com a smoke, 0 de 22; demo 0 | bate: com a smoke do estouro do A, ninguém do Catwalk vê o site |

Os links: `docs/match_15.html#replay?round=1&t=39.1`, `…&t=18.4`, `…&t=39.8`, `…&t=67.3`, `…&t=21.0`.
A conferência foi contra os dados (máscara da demo, dano, posição e olhar no replay 2D), não dentro do jogo.
