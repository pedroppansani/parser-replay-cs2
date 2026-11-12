# Round swing: o que o Pedro precisa mandar (RS0)

**Antes de tirar qualquer print:** o projeto JÁ tem o Swing oficial de **330 jogadores em 33 partidas** (`data/reference/hltv_componentes.json`, dos seus prints de setembro de 2026) e já compara com ele (correlação 0,903, erro médio 1,71 p.p.; nota principal). Os prints abaixo só ampliam essa conferência. Se quiser, pode pular tudo isto.

## Prints que faltam: 10 partidas profissionais sem Swing oficial
Todas têm o rating oficial no projeto e não têm o Swing. Para cada uma: a página da partida na HLTV, **o mapa certo da série**, na aba/tabela de estatísticas desse mapa que mostra a coluna **Swing** (a mesma de onde saíram os prints das outras 33; se a coluna não existir nessas páginas, avise e pulamos). Um print por mapa, com os 10 jogadores e o número de rounds visíveis.

| # | partida do projeto | mapa | confronto |
|---|---|---|---|
| 1 | match_10 | Dust2 | Spirit × Natus Vincere |
| 2 | match_11 | Anubis | Spirit × Natus Vincere |
| 3 | match_12 | Overpass | Vitality × FURIA |
| 4 | match_14 | Ancient | FURIA × Vitality |
| 5 | match_15 | Mirage | Natus Vincere × FURIA |
| 6 | match_16 | Nuke | Natus Vincere × FURIA |
| 7 | match_17 | Dust2 | FURIA × Natus Vincere |
| 8 | match_18 | Anubis | FURIA × Falcons |
| 9 | match_19 | Inferno | FURIA × Falcons |
| 10 | match_20 | Mirage | Falcons × FURIA |

(O `match_13` não existe no corpus.) As 9 partidas de FACEIT (`match_01` a `match_09`) não servem: a HLTV não publica rating nem swing para FACEIT (decisão 22c).

## Duas perguntas
1. **De que data são os prints que já temos?** O artigo de lançamento é de 20/08/2025 e eu não achei nenhuma atualização de outubro de 2025 (nem a página com esse ajuste). Os prints já transcritos são de setembro de 2026, então já refletem a versão que estava no ar; mas, se você tiver o link da nota de outubro, mande para eu ler e registrar o que mudou.
2. **Prints novos de novo?** Se a HLTV mudou o modelo depois de setembro, o Swing dos prints novos pode não bater com o dos antigos. Nesse caso, tire também UMA partida já transcrita (por exemplo `match_43`, FURIA × Vitality, Mirage) para eu ver se o número dela mudou.

## O que eu faço com eles
Rodo `scripts/escada_validacao.py` (degrau 5) com as 43 partidas e comparo com os números de hoje: correlação por jogador e erro médio em p.p. Não pego nada do site da HLTV; só o que você manda.
