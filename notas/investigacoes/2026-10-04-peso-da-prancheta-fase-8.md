# Peso e velocidade das páginas da prancheta, antes e depois da fase 8

Antes: `main` em 08e1597c. Depois: `fase-8-prancheta-tempo` no item 8.5 (eeaf78ff).
Peso: bytes do HTML gerado por `build_tactics_page.build_html`. Carga: mediana de 5 aberturas
no Chrome (headless, 1300 x 950) até `S.estado` existir.

| mapa | peso antes (KB) | peso depois (KB) | acréscimo (KB) | carga antes (ms) | carga depois (ms) |
|---|---|---|---|---|---|
| de_dust2 | 2921.9 | 2990.7 | 68.9 | 531 | 558 |
| de_mirage | 3861.4 | 3928.8 | 67.4 | 559 | 609 |
| de_nuke | 2399.4 | 2474.3 | 74.9 | 488 | 526 |
| de_train | 979.7 | 1041.6 | 61.9 | 466 | 471 |

O acréscimo é o código da fase 8 (formato 3, linha do tempo, roteiro) mais a tabela de nomes de
lugar do mapa (`data/lugares`, de 3 a 13 KB; o Train não tem). A biblioteca de arremessos
continua sendo quase todo o peso.

**Custo por quadro da reprodução** (mediana de 200 chamadas de `reproduzAte`, Mirage, com a
tática de teste): no relógio, 0,94 ms, incluindo refazer a linha do tempo e o roteiro; por passos,
0,16 ms. Os dois ficam muito abaixo dos 16,7 ms de um quadro a 60 Hz.

A tabela de velocidade de deslocamento medida no corpus está em
`2026-10-04-velocidade-e-voo.md` (rifle 210,6 / 111,8 / 90,4 u/s correndo, andando e agachado;
AWP 197,1 / 104,0 / 82,4), coerente com o jogo: agachado < andando < correndo, e a AWP mais lenta.
