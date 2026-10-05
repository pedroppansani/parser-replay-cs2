# Nome do lugar no roteiro da prancheta (fase 8, item 8.5)

**Pergunta.** O roteiro da prancheta quer dizer "TR 1 chega em Palace". De onde vem o nome,
sem inventar, e quanto ele pesa na página?

**Fontes.** O awpy 2.0.2 instalado não tem as áreas de navegação: `~/.awpy` só tem `maps`, e
`NAVS_DIR` (`~/.awpy/navs`) não existe. O que existe é o campo `place` de `ticks.parquet` em
todas as 52 partidas: o nome que o jogo dá ao lugar onde o jogador está, em inglês.

**Método** (`metrics/lugares.py`, `scripts/build_lugares.py --tabela`). Ticks de jogadores vivos
com `place`, um a cada 16 (4 por segundo), em pixel do radar e por andar (corte de
`map_areas.floor_split_z`). Grade de L x L pixels do radar (1024 de lado); cada célula fica com o
lugar mais comum (empate: ordem alfabética). Peso: o JSON compacto que a página carrega (RLE por
linha da grade). Acerto fora da amostra: a grade das partidas de índice par responde pelas de
índice ímpar; célula vazia conta como erro. Escolha: maior acerto (3 casas) entre os L que cabem
em 300 KB (limite do documento da fase 8); empate, o L maior.

**Resultado.**

| mapa | partidas | lado (px) | peso (KB) | acerto fora da amostra | escolhido |
|---|---|---|---|---|---|
| de_ancient | 3 | 4 | 14.7 | 0.937 |  |
| de_ancient | 3 | 8 | 4.6 | 0.964 | sim |
| de_ancient | 3 | 16 | 2.1 | 0.961 |  |
| de_ancient | 3 | 32 | 1.1 | 0.952 |  |
| de_anubis | 5 | 4 | 16.9 | 0.956 |  |
| de_anubis | 5 | 8 | 5.6 | 0.966 | sim |
| de_anubis | 5 | 16 | 2.7 | 0.961 |  |
| de_anubis | 5 | 32 | 1.4 | 0.945 |  |
| de_dust2 | 10 | 4 | 22.6 | 0.969 |  |
| de_dust2 | 10 | 8 | 6.8 | 0.972 | sim |
| de_dust2 | 10 | 16 | 3.0 | 0.962 |  |
| de_dust2 | 10 | 32 | 1.6 | 0.941 |  |
| de_inferno | 6 | 4 | 17.0 | 0.950 |  |
| de_inferno | 6 | 8 | 5.9 | 0.964 | sim |
| de_inferno | 6 | 16 | 2.6 | 0.959 |  |
| de_inferno | 6 | 32 | 1.4 | 0.936 |  |
| de_mirage | 16 | 4 | 14.5 | 0.935 |  |
| de_mirage | 16 | 8 | 5.4 | 0.935 | sim |
| de_mirage | 16 | 16 | 2.5 | 0.926 |  |
| de_mirage | 16 | 32 | 1.3 | 0.895 |  |
| de_nuke | 9 | 4 | 12.8 | 0.936 | sim |
| de_nuke | 9 | 8 | 4.8 | 0.928 |  |
| de_nuke | 9 | 16 | 2.2 | 0.896 |  |
| de_nuke | 9 | 32 | 1.1 | 0.841 |  |
| de_overpass | 2 | 4 | 27.5 | 0.875 |  |
| de_overpass | 2 | 8 | 7.6 | 0.929 |  |
| de_overpass | 2 | 16 | 3.0 | 0.934 | sim |
| de_overpass | 2 | 32 | 1.5 | 0.912 |  |
| de_train | 1 | — | — | sem medida | sem tabela |

O maior acréscimo é o do Nuke, com 12,8 KB, muito abaixo dos 300 KB. O Train tem 1 partida, sem
medida fora da amostra, e fica sem tabela: o roteiro sai sem o nome do lugar. Mapa sem partida no
corpus também fica sem tabela.

**Limites.** O nome é o do jogo, sem tradução. Uma célula na fronteira de dois lugares fica com o
mais visitado, e é por isso que o acerto fica entre 93% e 97%, não em 100%. Um ponto desenhado
onde ninguém pisou no corpus (célula vazia) sai sem nome.
