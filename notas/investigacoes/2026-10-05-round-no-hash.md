# O round inteiro no hash da prancheta (fase 9, item 9.3)

**Pergunta.** O round inteiro (caminho de cada jogador, mortes, granadas e plant) cabe na URL da
prancheta, como o `#instante=` de hoje, dentro de 150 KB (limite do documento da fase 9)? E qual
tolerância usar para simplificar os caminhos?

**Método** (`pesquisa/round_no_hash.py`, regra em `metrics/round_na_prancheta.py`, espelho em
`MapCore.roundParaPrancheta`). Para os 1.181 rounds das 52 partidas, o caminho de cada jogador vivo
sai das amostras do replay (4 por segundo), simplificado com Douglas-Peucker. Tamanho: JSON
compacto, comprimido com zlib nível 6 (o `CompressionStream("deflate")` do navegador usa o mesmo
formato), em base64url sem preenchimento. Erro: em cada amostra de jogador vivo, a distância
entre a posição gravada e a do caminho simplificado no mesmo horário.

A primeira versão usava o Douglas-Peucker só espacial (distância até a reta). Ele chegava a errar
649 u com tolerância de 2 u, porque apaga o vaivém na mesma reta e o tempo parado. A versão
adotada mede a distância **sincronizada no tempo**, até onde o trecho simplificado estaria no mesmo
horário. Com ela, o erro máximo é a própria tolerância:

| tolerância (u) | erro p50 (u) | erro p95 (u) | erro máx (u) | pontos por jogador (mediana / máx) | maior round no hash (KB) | mediana (KB) |
|---|---|---|---|---|---|---|
| 0 | 0.0 | 0.0 | 0.0 | 288 / 630 | 47.5 | 27.1 |
| 2 | 0.0 | 1.4 | 2.0 | 198 / 528 | 38.4 | 21.1 |
| 4 | 0.0 | 3.0 | 4.0 | 164 / 463 | 32.4 | 17.9 |
| 8 | 0.5 | 6.5 | 8.0 | 121 / 375 | 24.8 | 13.8 |
| 16 | 3.3 | 13.0 | 16.0 | 77 / 247 | 16.7 | 9.4 |
| **32** | 7.8 | 24.8 | 32.0 | 46 / 157 | **11.0** | 6.2 |

**Escolha: 32 u.** É a maior tolerância medida cujo erro máximo fica abaixo do que o próprio replay
já não vê entre duas amostras: um jogador correndo de rifle anda 210,6 u/s (velocidade medida no
corpus, fase 8) ÷ 4 amostras por segundo = 52,6 u. O maior round (match_16, round 24) fica com
11,0 KB no hash, menos de um décimo do limite. Até sem simplificar nada ele cabe (47,5 KB). Cada
jogador fica com 46 pontos na mediana, e cada ponto vira uma marca na linha do tempo.

**Limites.** A direção entre dois pontos que ficaram é interpolada. O erro de direção não foi
medido: o documento pede o de posição. A troca de andar sempre vira ponto, porque a prancheta não
interpola entre andares.
