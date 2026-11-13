# P1c: nomes de time e de evento (investigação; nenhum nome mudou)

Só leitura. Dados: `data/manifest.json` (nome que a demo gravou, jogadores, mapa, data, caminho da demo), `data/reference/eventos.json`, `scripts/build_web_page.py`. A tabela `nomes.csv` proposta aqui foi **descartada pelo Pedro** (o nome do time vem da demo; os eventos ficam no `eventos.json`): decisão 65.

## O que muda em relação ao pedido
- **As 9 partidas sem time são todas da FACEIT** (match_01 a match_09, todas de 15/09/2026, a data do arquivo .dem, não conferida). São partidas de fila (jogadores que se repetem: donk666 está nas 9, lilpeepfan- em 4), **não há time de verdade**: a demo grava um nome gerado, `team_<nick>`, onde `<nick>` é um jogador do próprio lado em todos os 18 casos. Então a coluna "nome certo" fica "?" para todos; não existe nome real a completar, a menos que o Pedro saiba de algum.
- **"IEM Krakw" já foi consertado na L1** (decisão 63, `data/reference/eventos.json`, cartão 27): a pasta da demo é `iem-krakw-2026`, e o site mostra "IEM Kraków 2026". O único `Krakw` que sobrou no repositório está no `tests/test_eventos.py` (é o identificador da pasta). A tabela de eventos já existe e já tem teste; falta só unir times e eventos num arquivo, se o Pedro quiser.

## 1. Os times das partidas match_01 a match_09
A demo guarda `team_clan_name` por jogador (lido por `scripts/manifest.py`); nas demos da FACEIT vale `team_<nick>`. As demos não estão mais no disco (`existe: false` no manifesto), então não reli nada da demo: tudo vem do manifesto. O site mostra "Time de <primeiro nick em ordem alfabética>" (`metrics/times.nome_do_lado_faceit`, decisão 28), que **não é o mesmo nick** que a demo grava (que seria o do capitão da fila).

| partida | mapa · placar | lado | começou | a demo grava | o site mostra | jogadores |
|---|---|---|---|---|---|---|
| match_01 | ancient · 13-9 | A | TR | `team_t1ltedbot` | Time de _AmadeuS | rol1ng-, Z_o_R_o, donk666, _AmadeuS, t1ltedbot |
| match_01 | ancient · 13-9 | B | CT | `team_HLEB` | Time de 9amaterasu9 | xhx, KREEDZ666, HLEB, 9amaterasu9, s-chilla |
| match_02 | mirage · 13-9 | A | TR | `team_lilpeepfan-` | Time de -olik | donk666, Eleyes, -olik, lilpeepfan-, OG_Pablo_ |
| match_02 | mirage · 13-9 | B | CT | `team_Krimbo` | Time de -h4wkkk | -h4wkkk, Dyshbert, bezimienny, S3NSEYZjE, Krimbo |
| match_03 | anubis · 13-7 | A | TR | `team_lilpeepfan-` | Time de ArmaHan | ArmaHan, publicimage, hally-, donk666, lilpeepfan- |
| match_03 | anubis · 13-7 | B | CT | `team_zecco` | Time de dyrod | zecco, PAiN-M-, dyrod, Unihi, rajkeza |
| match_04 | ancient · 13-8 | A | TR | `team_somehxw` | Time de donk666 | nedorufe, Matthew369, L1nkero, donk666, somehxw |
| match_04 | ancient · 13-8 | B | CT | `team_D0KT0R3N` | Time de borzSE | MolO11, shiFu-, pxd11, D0KT0R3N, borzSE |
| match_05 | nuke · 4-13 | A | TR | `team_Olajida` | Time de chiefkeef19 | chiefkeef19, Olajida, gwizdakk, Dafra1D, f0pa |
| match_05 | nuke · 4-13 | B | CT | `team_lilpeepfan-` | Time de donk666 | donk666, PR--, dorfen, lilpeepfan-, PerdYYY |
| match_06 | mirage · 13-5 | A | TR | `team_xKacpersky` | Time de adamS | adamS, pradablade, xKacpersky, Etaliqe, llorente |
| match_06 | mirage · 13-5 | B | CT | `team_ar1sFLXR` | Time de -_-siNNer | Alperen, -_-siNNer, donk666, regele, ar1sFLXR |
| match_07 | mirage · 13-6 | A | TR | `team_Krabeni` | Time de donk666 | v1w, donk666, stormy, EbuDerdaa, Krabeni |
| match_07 | mirage · 13-6 | B | CT | `team_xKacpersky` | Time de Ajuyep | Ajuyep, xKacpersky, e-girlhuntr, Oller-, s-chilla |
| match_08 | mirage · 11-13 | A | TR | `team_Ahuniwip` | Time de -EsD | -EsD, KENNY-_, PoisonLilies, gwizdakk, Ahuniwip |
| match_08 | mirage · 11-13 | B | CT | `team_lilpeepfan-` | Time de certa1n | lilpeepfan-, donk666, certa1n, Pelle-, endru- |
| match_09 | mirage · 11-13 | A | TR | `team_lemight` | Time de d3bab | d3bab, newnickname7, ELVENIMOUS, wh1temink, lemight |
| match_09 | mirage · 11-13 | B | CT | `team_Magnojezzz` | Time de donk666 | donk666, zzeraj, Magnojezzz, R0Kk-_, tezeuts- |

Arquivo da demo de cada partida (pasta e arquivo têm o mesmo nome; `data/manifest.json`, campo `demos`):

| partida | pasta/arquivo da demo | data (arquivo .dem) |
|---|---|---|
| match_01 | `1-0007ce25-1e02-40fa-9eb0-1bba64c71b12-1-1.dem` | 2026-09-15 16:39 |
| match_02 | `1-07642af7-6568-4661-9aeb-a420adeaad61-1-1.dem` | 2026-09-15 16:40 |
| match_03 | `1-22abf937-659e-4363-9933-cc2a2ae99370-1-1.dem` | 2026-09-15 16:39 |
| match_04 | `1-50a6313e-9399-4821-848e-f3b25a683149-1-1.dem` | 2026-09-15 16:40 |
| match_05 | `1-764e1ec7-1f00-4168-9eed-9741ee3a00e6-1-1.dem` | 2026-09-15 16:40 |
| match_06 | `1-7de2c606-5a1c-4496-9a78-4f9e066aa348-1-1.dem` | 2026-09-15 16:39 |
| match_07 | `1-9be6d5a6-abda-4110-908d-deae67dee533-1-1.dem` | 2026-09-15 16:38 |
| match_08 | `1-a2985358-eb2a-4b11-b891-534de044e54e-1-1.dem` | 2026-09-15 16:40 |
| match_09 | `1-c4169514-a91a-470c-9fa7-11413f06ff45-1-1.dem` | 2026-09-15 16:40 |

## 2. Os nomes de evento (todos do corpus, como aparecem hoje)

| pasta da demo (identificador) | partidas | aparece no site | forma certa proposta |
|---|---|---|---|
| `blast-open-lisbon-2025` | 5 | BLAST Open Lisbon 2025 | BLAST Open Lisbon 2025 (sem mudança; "Kraków" já foi corrigido na L1) |
| `blast-rivals-2025-season-2` | 4 | BLAST Rivals 2025 Season 2 | BLAST Rivals 2025 Season 2 (sem mudança; "Kraków" já foi corrigido na L1) |
| `iem-cologne-major-2026` | 2 | IEM Cologne Major 2026 | IEM Cologne Major 2026 (sem mudança; "Kraków" já foi corrigido na L1) |
| `iem-dallas-2025` | 3 | IEM Dallas 2025 | IEM Dallas 2025 (sem mudança; "Kraków" já foi corrigido na L1) |
| `iem-katowice-2025` | 5 | IEM Katowice 2025 | IEM Katowice 2025 (sem mudança; "Kraków" já foi corrigido na L1) |
| `iem-krakw-2026` | 8 | IEM Kraków 2026 | IEM Kraków 2026 (sem mudança; "Kraków" já foi corrigido na L1) |
| `iem-rio-2026` | 5 | IEM Rio 2026 | IEM Rio 2026 (sem mudança; "Kraków" já foi corrigido na L1) |
| `pgl-cluj-napoca-2026` | 3 | PGL Cluj-Napoca 2026 | PGL Cluj-Napoca 2026 (sem mudança; "Kraków" já foi corrigido na L1) |
| `starladder-budapest-major-2025` | 5 | StarLadder Budapest Major 2025 | StarLadder Budapest Major 2025 (sem mudança; "Kraków" já foi corrigido na L1) |
| `starladder-starseries-fall-2026` | 3 | StarLadder StarSeries Fall 2026 | StarLadder StarSeries Fall 2026 (sem mudança; "Kraków" já foi corrigido na L1) |

Nenhum nome ficou sem acento ou sem letra hoje. Os 9 restantes não têm acento a pôr. Não conferi nada na web (o pedido proíbe): "forma certa" é a que a tabela já tem.

## 3. A tabela proposta (`data/reference/nomes.csv`)
Colunas: `tipo` (time ou evento), `id`, `nome_que_aparece_hoje`, `nome_certo`, `fonte`, `conferido` (começa `não`). Rascunho com as 28 linhas (18 times da FACEIT com `nome_certo = ?`, 10 eventos) em `2026-11-12-p1c-nomes-proposta.csv`. Regra, como nos callouts: **o nome só vale quando `conferido = sim`**; o resto continua como hoje.
- id do time: `match_01:A`. Time profissional não entra (já tem o nome real da demo, e `times_conhecidos.json` só junta variantes: Vitality / Team Vitality).
- Para não ter duas tabelas de evento, `nomes.csv` **substituiria** `data/reference/eventos.json` (o `tests/test_eventos.py` passaria a ler dela). Esse conserto toca teste existente, então precisa do OK do Pedro.
- Decisão a tomar: para a FACEIT, trocar "Time de <primeiro nick em ordem alfabética>" por "Time de <nick que a demo grava>" (o capitão da fila). É dado real da demo, estável, e some a arbitrariedade; mas muda a decisão 28 e os nomes de 9 partidas.

## 4. Onde os nomes aparecem (todos leem do mesmo lugar?)
Sim, para os times: tudo nasce de `scripts/build_web_page._nome_do_lado` (via `cabecalho_da_partida`). Os leitores: a lista de Partidas e os cartões da landing (`build_site._dados_do_card`, `m["lados"]`), o cabeçalho da partida (`PAGINA.cabecalho.lados`, `01-dados-e-comum.js`), o Reescrever (`build_reescrever.py`, `m["lados"]`), o cartão do arremesso real da C4 (`build_site.times_das_partidas` → `biblioteca.partidas_times`), a narrativa (`leitura/narrativa.py`, troca "Time A/B" pelo nome do lado) e o Perfil (agrupa os botões por time, `07-perfil.js`, mesma fonte do cabeçalho). Uma troca em `_nome_do_lado` chega a todos. Para o evento: `build_web_page.nome_do_evento`, lido da landing, das migalhas e do título.

## 5. Efeito na impressão dos números
Nenhum: é só texto (decisão 18) e a impressão não imprime nomes de time nem de evento. Mudar o nome da FACEIT ou ler de `nomes.csv` não muda nenhuma linha dela. Muda: as frases geradas (narrativa, cartão da C4, títulos), os testes que citam "Time de ..." (`tests/test_cabecalho.py`, `test_escape_de_nomes.py`, `test_design_impressao.py`, `test_og.py`) e a imagem OG de cada partida da FACEIT se os nomes mudarem.
