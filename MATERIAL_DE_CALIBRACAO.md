# Material de calibração

Gerado por `py -3.12 -m scripts.calibracao.material_calibracao`. Cada seção termina com a pergunta que só você responde; as respostas viram constante com data e tamanho de corpus no CLAUDE.md.

## 1. Pisos de função

Gerado por `py -3.12 -m pesquisa.proposta_pisos`. O rótulo exige **liderar o próprio time** na métrica E passar do piso; o piso barra o líder que não é destacado. Para cada função: a distribuição completa (todos os jogador-partidas e só os líderes), três métodos objetivos -- **maior vazio** entre valores consecutivos, **Otsu** (menor variância dentro das duas classes) e **vale da densidade** (KDE) --, o veredito de concordância e os líderes mais próximos de cada corte. Métodos que concordam = corte real; métodos que discordam = a métrica é um contínuo e o piso é convenção. Os pisos continuam ABSOLUTOS. O que é seu: olhar a fronteira e dizer se aquele jogador jogou a função naquela partida.

### AWPer — `awp_share`, piso atual 0.533

430 jogador-partidas profissionais em 43 partidas; 86 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.056     161 ##############################################
     0.056-0.111      49 ##############
     0.111-0.167      47 #############
     0.167-0.222      31 #########
     0.222-0.278      28 ########
     0.278-0.333       3 #
     0.333-0.389      15 ####
     0.389-0.444       3 #
     0.444-0.500       4 #
     0.500-0.556       0    <- atual, vazio (todos), otsu (todos)
     0.556-0.611       2 #   <- vale (todos)
     0.611-0.667       0 
     0.667-0.722       2 #
     0.722-0.778       1 
     0.778-0.833       2 #
     0.833-0.889       9 ###
     0.889-0.944      17 #####
     0.944-1.000      56 ################
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.667-0.685       1 #
     0.685-0.704       0 
     0.704-0.722       0 
     0.722-0.741       1 #
     0.741-0.759       0 
     0.759-0.778       0 
     0.778-0.796       0 
     0.796-0.815       2 ##
     0.815-0.833       0 
     0.833-0.852       3 ###
     0.852-0.870       1 #
     0.870-0.889       5 ####
     0.889-0.907       9 ########
     0.907-0.926       4 ####
     0.926-0.944       4 ####   <- otsu (líderes), vale (líderes)
     0.944-0.963       3 ###
     0.963-0.981       1 #
     0.981-1.000      52 ##############################################   <- vazio (líderes)
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.533 | 86 de 86 |
| vazio (todos) | 0.533 | 86 de 86 |
| otsu (todos) | 0.533 | 86 de 86 |
| vale (todos) | 0.577 | 86 de 86 |
| vazio (líderes) | 0.982 | 52 de 86 |
| otsu (líderes) | 0.931 | 58 de 86 |
| vale (líderes) | 0.934 | 56 de 86 |

- todos: espalhamento 0.13 amplitude interquartil (0.333) -> **CONCORDAM**, mediana 0.533
- líderes: espalhamento 0.52 amplitude interquartil (0.098) -> **discordam**

**Veredito: corte real em 0.533** (métodos concordam entre todos). Piso atual 0.533: 86 líderes com rótulo; sugerido: 86.

**Fronteira do corte atual (0.533)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | awp_share |
|---|---|---|---|---|---|
| rótulo | ZywOo | Team Vitality | match_35 | inferno | 0.833 |
| rótulo | w0nderful | Natus Vincere | match_40 | nuke | 0.800 |
| rótulo | ZywOo | Team Vitality | match_34 | mirage | 0.800 |
| rótulo | m0NESY | Falcons | match_30 | nuke | 0.727 |
| rótulo | molodoy | FURIA | match_45 | nuke | 0.667 |
| — corte 0.533 — | | | | | |

**Fronteira do corte sugerido (0.533)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | awp_share |
|---|---|---|---|---|---|
| rótulo | ZywOo | Team Vitality | match_35 | inferno | 0.833 |
| rótulo | w0nderful | Natus Vincere | match_40 | nuke | 0.800 |
| rótulo | ZywOo | Team Vitality | match_34 | mirage | 0.800 |
| rótulo | m0NESY | Falcons | match_30 | nuke | 0.727 |
| rótulo | molodoy | FURIA | match_45 | nuke | 0.667 |
| — corte 0.533 — | | | | | |

**Sua resposta:** os jogadores da fronteira jogaram de AWPer naquelas partidas? piso de AWPer = ____

### Abre o round — `first_contact_share`, piso atual 0.320

430 jogador-partidas profissionais em 43 partidas; 103 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.029      13 #########   <- vazio (todos)
     0.029-0.058      20 ##############
     0.058-0.087      23 #################
     0.087-0.116      44 ################################
     0.116-0.146      64 ##############################################
     0.146-0.175      47 ##################################
     0.175-0.204      49 ###################################   <- otsu (todos)
     0.204-0.233      40 #############################
     0.233-0.262      46 #################################
     0.262-0.291      20 ##############
     0.291-0.320      29 #####################   <- atual
     0.320-0.349      12 #########
     0.349-0.378      10 #######
     0.378-0.407       4 ###
     0.407-0.437       5 ####
     0.437-0.466       1 #
     0.466-0.495       0    <- vale (todos)
     0.495-0.524       3 ##
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.206-0.224       9 ########################
     0.224-0.241       6 ################
     0.241-0.259      10 ###########################
     0.259-0.277      11 ##############################
     0.277-0.294      17 ##############################################
     0.294-0.312       7 ###################
     0.312-0.330      11 ##############################   <- atual, otsu (líderes)
     0.330-0.347       7 ###################
     0.347-0.365       8 ######################
     0.365-0.383       5 ##############
     0.383-0.400       3 ########
     0.400-0.418       2 #####
     0.418-0.435       3 ########
     0.435-0.453       0    <- vazio (líderes)
     0.453-0.471       1 ###
     0.471-0.488       0    <- vale (líderes)
     0.488-0.506       2 #####
     0.506-0.524       1 ###
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.320 | 33 de 103 |
| vazio (todos) | 0.021 | 103 de 103 |
| otsu (todos) | 0.197 | 103 de 103 |
| vale (todos) | 0.476 | 3 de 103 |
| vazio (líderes) | 0.447 | 4 de 103 |
| otsu (líderes) | 0.328 | 32 de 103 |
| vale (líderes) | 0.473 | 3 de 103 |

- todos: espalhamento 4.02 amplitude interquartil (0.113) -> **discordam**
- líderes: espalhamento 1.99 amplitude interquartil (0.072) -> **discordam**

**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que a fronteira do piso ATUAL é tudo o que há para julgar.

**Fronteira do corte atual (0.320)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | first_contact_share |
|---|---|---|---|---|---|
| rótulo | donk | Team Spirit | match_36 | mirage | 0.333 |
| rótulo | iM | Natus Vincere | match_36 | mirage | 0.333 |
| rótulo | xertioN | MOUZ | match_33 | dust2 | 0.333 |
| rótulo | flameZ | Vitality | match_27 | nuke | 0.333 |
| rótulo | kyxsan | Falcons | match_31 | train | 0.324 |
| — corte 0.320 — | | | | | |
| sem rótulo | ZywOo | Team Vitality | match_23 | dust2 | 0.318 |
| sem rótulo | zont1x | Team Spirit | match_25 | anubis | 0.316 |
| sem rótulo | zont1x | Team Spirit | match_26 | anubis | 0.316 |
| sem rótulo | ZywOo | Team Vitality | match_48 | dust2 | 0.316 |
| sem rótulo | flameZ | Team Vitality | match_48 | dust2 | 0.316 |

**Sua resposta:** os jogadores da fronteira jogaram de Abre o round naquelas partidas? piso de Abre o round = ____

### Suporte de utility — `enemy_blind_seconds`, piso atual 20.0

430 jogador-partidas profissionais em 43 partidas; 86 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-8.565      61 ################################
     8.565-17.130     88 ##############################################
    17.130-25.695     67 ###################################   <- atual
    25.695-34.260     54 ############################
    34.260-42.825     49 ##########################
    42.825-51.389     35 ##################   <- otsu (todos)
    51.389-59.954     23 ############
    59.954-68.519     14 #######
    68.519-77.084     10 #####
    77.084-85.649      8 ####   <- vazio (todos), vale (todos)
    85.649-94.214     10 #####
    94.214-102.779     3 ##
   102.779-111.344     2 #
   111.344-119.909     0 
   119.909-128.474     2 #
   128.474-137.039     3 ##
   137.039-145.604     0 
   145.604-154.168     1 #
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
    13.578-21.389      4 ##############   <- atual
    21.389-29.199      7 #########################
    29.199-37.010      6 #####################
    37.010-44.821     13 ##############################################
    44.821-52.631     12 ##########################################
    52.631-60.442      7 #########################
    60.442-68.252      6 #####################
    68.252-76.063      6 #####################   <- otsu (líderes)
    76.063-83.873      4 ##############
    83.873-91.684      6 #####################
    91.684-99.494      6 #####################
    99.494-107.305     3 ###########
   107.305-115.116     0    <- vazio (líderes)
   115.116-122.926     1 ####
   122.926-130.737     4 ##############
   130.737-138.547     0 
   138.547-146.358     0 
   146.358-154.168     1 ####
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 20.0 | 82 de 86 |
| vazio (todos) | 82.5 | 21 de 86 |
| otsu (todos) | 47.1 | 49 de 86 |
| vale (todos) | 83.9 | 21 de 86 |
| vazio (líderes) | 113.1 | 6 de 86 |
| otsu (líderes) | 69.9 | 29 de 86 |
| vale (líderes) | sem corte (distribuição unimodal) | — |

- todos: espalhamento 1.19 amplitude interquartil (30.8) -> **discordam**
- líderes: espalhamento 1.06 amplitude interquartil (40.7) -> **discordam**

**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que a fronteira do piso ATUAL é tudo o que há para julgar.

**Fronteira do corte atual (20.0)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | enemy_blind_seconds |
|---|---|---|---|---|---|
| rótulo | sh1ro | Team Spirit | match_11 | anubis | 25.3 |
| rótulo | w0nderful | Natus Vincere | match_10 | dust2 | 25.3 |
| rótulo | donk | Team Spirit | match_40 | nuke | 24.4 |
| rótulo | chopper | Team Spirit | match_26 | anubis | 22.7 |
| rótulo | zont1x | Team Spirit | match_36 | mirage | 22.5 |
| — corte 20.0 — | | | | | |
| sem rótulo | xertioN | MOUZ | match_51 | nuke | 19.4 |
| sem rótulo | torzsi | MOUZ | match_34 | mirage | 18.2 |
| sem rótulo | flameZ | Team Vitality | match_47 | nuke | 17.8 |
| sem rótulo | apEX | Vitality | match_27 | nuke | 13.6 |

**Sua resposta:** os jogadores da fronteira jogaram de Suporte de utility naquelas partidas? piso de Suporte de utility = ____

### Lurker — `off_team_relativo`, piso atual 1.284

429 jogador-partidas profissionais em 43 partidas; 102 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.226      92 ##############################################   <- vazio (todos)
     0.226-0.452      19 ##########
     0.452-0.678      34 #################   <- vale (todos)
     0.678-0.905      19 ##########
     0.905-1.131      27 ##############
     1.131-1.357      44 ######################   <- atual, otsu (todos)
     1.357-1.583      29 ##############
     1.583-1.809      36 ##################
     1.809-2.035      34 #################
     2.035-2.261      40 ####################
     2.261-2.488      18 #########
     2.488-2.714      14 #######
     2.714-2.940       4 ##
     2.940-3.166       9 ####
     3.166-3.392       3 ##
     3.392-3.618       2 #
     3.618-3.844       4 ##
     3.844-4.071       1 
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.000-0.226      20 ##############################################
     0.226-0.452       4 #########
     0.452-0.678       4 #########
     0.678-0.905       2 #####
     0.905-1.131       4 #########   <- vale (líderes)
     1.131-1.357       0    <- atual, vazio (líderes), otsu (líderes)
     1.357-1.583       4 #########
     1.583-1.809       9 #####################
     1.809-2.035       7 ################
     2.035-2.261      15 ##################################
     2.261-2.488      10 #######################
     2.488-2.714       7 ################
     2.714-2.940       2 #####
     2.940-3.166       5 ############
     3.166-3.392       3 #######
     3.392-3.618       2 #####
     3.618-3.844       3 #######
     3.844-4.071       1 ##
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 1.284 | 68 de 102 |
| vazio (todos) | 0.142 | 82 de 102 |
| otsu (todos) | 1.261 | 68 de 102 |
| vale (todos) | 0.550 | 78 de 102 |
| vazio (líderes) | 1.284 | 68 de 102 |
| otsu (líderes) | 1.284 | 68 de 102 |
| vale (líderes) | 1.028 | 69 de 102 |

- todos: espalhamento 0.72 amplitude interquartil (1.547) -> **discordam**
- líderes: espalhamento 0.14 amplitude interquartil (1.864) -> **CONCORDAM**, mediana 1.284

**Veredito: corte real em 1.284** (métodos concordam entre líderes). Piso atual 1.284: 68 líderes com rótulo; sugerido: 68.

**Fronteira do corte atual (1.284)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | off_team_relativo |
|---|---|---|---|---|---|
| rótulo | makazze | Natus Vincere | match_15 | mirage | 1.612 |
| rótulo | apEX | Team Vitality | match_33 | dust2 | 1.580 |
| rótulo | kyousuke | Falcons | match_20 | mirage | 1.528 |
| rótulo | xertioN | MOUZ | match_50 | inferno | 1.520 |
| rótulo | Jimpphat | MOUZ | match_41 | inferno | 1.494 |
| — corte 1.284 — | | | | | |
| sem rótulo | YEKINDAR | FURIA | match_44 | inferno | 1.074 |
| sem rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.983 |
| sem rótulo | Jimpphat | MOUZ | match_51 | nuke | 0.920 |
| sem rótulo | kyxsan | Team Falcons | match_51 | nuke | 0.919 |
| sem rótulo | molodoy | FURIA | match_16 | nuke | 0.733 |

**Fronteira do corte sugerido (1.284)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | off_team_relativo |
|---|---|---|---|---|---|
| rótulo | makazze | Natus Vincere | match_15 | mirage | 1.612 |
| rótulo | apEX | Team Vitality | match_33 | dust2 | 1.580 |
| rótulo | kyousuke | Falcons | match_20 | mirage | 1.528 |
| rótulo | xertioN | MOUZ | match_50 | inferno | 1.520 |
| rótulo | Jimpphat | MOUZ | match_41 | inferno | 1.494 |
| — corte 1.284 — | | | | | |
| sem rótulo | YEKINDAR | FURIA | match_44 | inferno | 1.074 |
| sem rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.983 |
| sem rótulo | Jimpphat | MOUZ | match_51 | nuke | 0.920 |
| sem rótulo | kyxsan | Team Falcons | match_51 | nuke | 0.919 |
| sem rótulo | molodoy | FURIA | match_16 | nuke | 0.733 |

**Sua resposta:** os jogadores da fronteira jogaram de Lurker naquelas partidas? piso de Lurker = ____

### Âncora de bomb — `never_left_share`, piso atual 0.800

410 jogador-partidas profissionais em 43 partidas; 124 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.167-0.213       3 ##
     0.213-0.259       2 #
     0.259-0.306       2 #
     0.306-0.352       3 ##
     0.352-0.398       3 ##
     0.398-0.444      12 ########
     0.444-0.491      12 ########
     0.491-0.537      27 ###################
     0.537-0.583      10 #######
     0.583-0.630      27 ###################
     0.630-0.676      49 ###################################
     0.676-0.722       8 ######   <- otsu (todos)
     0.722-0.769      40 ############################
     0.769-0.815      38 ###########################   <- atual
     0.815-0.861      65 ##############################################
     0.861-0.907      19 #############
     0.907-0.954      43 ##############################
     0.954-1.000      47 #################################   <- vazio (todos)
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.727-0.742       1 #
     0.742-0.758       3 ###
     0.758-0.773       0 
     0.773-0.788       7 #######
     0.788-0.803       2 ##   <- atual
     0.803-0.818       0 
     0.818-0.833       7 #######
     0.833-0.848      13 #############
     0.848-0.864       5 #####
     0.864-0.879       3 ###
     0.879-0.894       4 ####
     0.894-0.909       1 #   <- otsu (líderes)
     0.909-0.924      23 #######################
     0.924-0.939       8 ########
     0.939-0.955       0    <- vale (líderes)
     0.955-0.970       0    <- vazio (líderes)
     0.970-0.985       0 
     0.985-1.000      47 ##############################################
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.800 | 113 de 124 |
| vazio (todos) | 0.967 | 47 de 124 |
| otsu (todos) | 0.707 | 124 de 124 |
| vale (todos) | sem corte (distribuição unimodal) | — |
| vazio (líderes) | 0.967 | 47 de 124 |
| otsu (líderes) | 0.894 | 79 de 124 |
| vale (líderes) | 0.952 | 47 de 124 |

- todos: espalhamento 1.09 amplitude interquartil (0.239) -> **discordam**
- líderes: espalhamento 0.43 amplitude interquartil (0.167) -> **discordam**

**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que a fronteira do piso ATUAL é tudo o que há para julgar.

**Fronteira do corte atual (0.800)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | never_left_share |
|---|---|---|---|---|---|
| rótulo | mezii | Team Vitality | match_46 | overpass | 0.818 |
| rótulo | YEKINDAR | FURIA | match_14 | ancient | 0.818 |
| rótulo | FalleN | FURIA | match_14 | ancient | 0.818 |
| rótulo | yuurih | FURIA | match_20 | mirage | 0.800 |
| rótulo | FalleN | FURIA | match_20 | mirage | 0.800 |
| — corte 0.800 — | | | | | |
| sem rótulo | flameZ | Team Vitality | match_12 | overpass | 0.778 |
| sem rótulo | mezii | Team Vitality | match_12 | overpass | 0.778 |
| sem rótulo | apEX | Team Vitality | match_35 | inferno | 0.778 |
| sem rótulo | flameZ | Team Vitality | match_35 | inferno | 0.778 |
| sem rótulo | ropz | Team Vitality | match_35 | inferno | 0.778 |

**Sua resposta:** os jogadores da fronteira jogaram de Âncora de bomb naquelas partidas? piso de Âncora de bomb = ____

### Segundo homem — `trade_share`, piso atual 0.350

430 jogador-partidas profissionais em 43 partidas; 94 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.056      37 ####################   <- vazio (todos), vale (todos)
     0.056-0.111      55 #############################
     0.111-0.167      70 #####################################
     0.167-0.222      87 ##############################################   <- otsu (todos)
     0.222-0.278      81 ###########################################
     0.278-0.333      40 #####################
     0.333-0.389      35 ###################   <- atual
     0.389-0.444       8 ####
     0.444-0.500       8 ####
     0.500-0.556       5 ###
     0.556-0.611       1 #
     0.611-0.667       1 #
     0.667-0.722       0 
     0.722-0.778       1 #
     0.778-0.833       0 
     0.833-0.889       0 
     0.889-0.944       0 
     0.944-1.000       1 #
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.167-0.213       4 #########
     0.213-0.259      21 ##############################################
     0.259-0.306      14 ###############################
     0.306-0.352      20 ############################################   <- atual
     0.352-0.398      14 ###############################
     0.398-0.444       5 ###########   <- otsu (líderes)
     0.444-0.491       7 ###############
     0.491-0.537       5 ###########
     0.537-0.583       0    <- vazio (líderes), vale (líderes)
     0.583-0.630       2 ####
     0.630-0.676       0 
     0.676-0.722       0 
     0.722-0.769       1 ##
     0.769-0.815       0 
     0.815-0.861       0 
     0.861-0.907       0 
     0.907-0.954       0 
     0.954-1.000       1 ##
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.350 | 36 de 94 |
| vazio (todos) | 0.022 | 94 de 94 |
| otsu (todos) | 0.216 | 90 de 94 |
| vale (todos) | 0.029 | 94 de 94 |
| vazio (líderes) | 0.550 | 4 de 94 |
| otsu (líderes) | 0.403 | 21 de 94 |
| vale (líderes) | 0.571 | 4 de 94 |

- todos: espalhamento 1.39 amplitude interquartil (0.140) -> **discordam**
- líderes: espalhamento 1.37 amplitude interquartil (0.123) -> **discordam**

**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que a fronteira do piso ATUAL é tudo o que há para julgar.

**Fronteira do corte atual (0.350)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | trade_share |
|---|---|---|---|---|---|
| rótulo | yuurih | FURIA | match_46 | overpass | 0.357 |
| rótulo | ropz | Team Vitality | match_46 | overpass | 0.357 |
| rótulo | KSCERATO | FURIA | match_14 | ancient | 0.357 |
| rótulo | xertioN | MOUZ | match_41 | inferno | 0.353 |
| rótulo | NiKo | Team Falcons | match_41 | inferno | 0.350 |
| — corte 0.350 — | | | | | |
| sem rótulo | zont1x | Team Spirit | match_10 | dust2 | 0.333 |
| sem rótulo | KSCERATO | FURIA | match_15 | mirage | 0.333 |
| sem rótulo | molodoy | FURIA | match_15 | mirage | 0.333 |
| sem rótulo | donk | Team Spirit | match_28 | mirage | 0.333 |
| sem rótulo | magixx | Team Spirit | match_28 | mirage | 0.333 |

**Sua resposta:** os jogadores da fronteira jogaram de Segundo homem naquelas partidas? piso de Segundo homem = ____

### Principal fragger — `adr`, piso atual 85.0

430 jogador-partidas profissionais em 43 partidas; 86 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
    19.438-26.170      1 #
    26.170-32.903      3 ##
    32.903-39.635     12 ########
    39.635-46.368     19 ############
    46.368-53.101     34 ######################
    53.101-59.833     47 ###############################
    59.833-66.566     51 ##################################
    66.566-73.299     70 ##############################################
    73.299-80.031     51 ##################################   <- otsu (todos)
    80.031-86.764     58 ######################################   <- atual
    86.764-93.497     25 ################
    93.497-100.229    27 ##################
   100.229-106.962    13 #########
   106.962-113.694     6 ####
   113.694-120.427     6 ####   <- vazio (todos)
   120.427-127.160     3 ##
   127.160-133.892     2 #
   133.892-140.625     2 #
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
    60.842-65.274      1 ###
    65.274-69.707      0 
    69.707-74.139      5 ##############
    74.139-78.572      0    <- vazio (líderes)
    78.572-83.004      7 ###################
    83.004-87.436     17 ##############################################   <- atual
    87.436-91.869      9 ########################
    91.869-96.301     11 ##############################
    96.301-100.734     9 ########################
   100.734-105.166     6 ################   <- otsu (líderes)
   105.166-109.598     6 ################
   109.598-114.031     3 ########
   114.031-118.463     2 #####
   118.463-122.895     4 ###########
   122.895-127.328     2 #####
   127.328-131.760     0 
   131.760-136.193     3 ########
   136.193-140.625     1 ###
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 85.0 | 65 de 86 |
| vazio (todos) | 114.1 | 12 de 86 |
| otsu (todos) | 74.3 | 80 de 86 |
| vale (todos) | sem corte (distribuição unimodal) | — |
| vazio (líderes) | 75.8 | 80 de 86 |
| otsu (líderes) | 102.7 | 23 de 86 |
| vale (líderes) | sem corte (distribuição unimodal) | — |

- todos: espalhamento 1.55 amplitude interquartil (25.7) -> **discordam**
- líderes: espalhamento 1.42 amplitude interquartil (19.0) -> **discordam**

**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que a fronteira do piso ATUAL é tudo o que há para julgar.

**Fronteira do corte atual (85.0)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | adr |
|---|---|---|---|---|---|
| rótulo | jL | Natus Vincere | match_24 | dust2 | 85.8 |
| rótulo | mo0N | magic | match_23 | dust2 | 85.6 |
| rótulo | xertioN | MOUZ | match_41 | inferno | 85.3 |
| rótulo | b1t | Natus Vincere | match_36 | mirage | 85.2 |
| rótulo | jL | Natus Vincere | match_40 | nuke | 85.2 |
| — corte 85.0 — | | | | | |
| sem rótulo | YEKINDAR | FURIA | match_44 | inferno | 84.9 |
| sem rótulo | yuurih | FURIA | match_43 | mirage | 84.8 |
| sem rótulo | yuurih | FURIA | match_46 | overpass | 84.3 |
| sem rótulo | makazze | Natus Vincere | match_22 | mirage | 84.0 |
| sem rótulo | xertioN | MOUZ | match_49 | mirage | 83.9 |

**Sua resposta:** os jogadores da fronteira jogaram de Principal fragger naquelas partidas? piso de Principal fragger = ____

## 2. Nomes dos quatro grupos de estilo

Gerado por `py -3.12 -m pesquisa.proposta_grupos`. O KMeans não nomeia (decisão 8): abaixo está o que DEFINE cada grupo e, para cada um, três nomes que se justificam pelos números mostrados. Você escolhe, ajusta ou recusa; o nome vai para `clustering/cluster_names.json`.

### Antes de nomear: o modelo ainda não foi ajustado no corpus inteiro

O modelo em uso foi ajustado em **11520 jogador-rounds (as 9 partidas de FACEIT)** e aplicado às 52. Reajustado nas 52 (11520 jogador-rounds, sem gravar): índice de Rand ajustado **1.00**, e 100% dos rounds ficam no mesmo grupo. **Os quatro perfis reaparecem** -- são os mesmos quatro jeitos --, mas os NÚMEROS dos grupos trocam, e o maior deles perde parte dos rounds para outro. Por isso os nomes abaixo estão presos ao perfil, não ao número: se o modelo for reajustado, cada nome segue o seu perfil. Reajustar é decisão sua (`py -3.12 -m scripts.fit_global_clusters`); recomendo antes de gravar os nomes.

| perfil | grupo hoje | vira no reajuste | rounds que ficam juntos |
|---|---|---|---|
| mira | 0 | 0 | 1110 de 1110 (100%) |
| junto | 1 | 1 | 4037 de 4037 (100%) |
| longe | 2 | 2 | 3030 de 3030 (100%) |
| roda | 3 | 3 | 3343 de 3343 (100%) |

### Perfil "mira" -- grupo 0 hoje (1110 jogador-rounds, 10% do corpus; CT 565, TR 545)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| mira na altura da cabeça (0-1) **(distingue)** | 0.56 | 0.87 | -2.30 |
| placement da mira (0-100) **(distingue)** | 52.02 | 68.39 | -1.55 |
| maior distância do time no round | 1100.56u | 1238.95u | -0.28 |
| distância média do time | 639.92u | 709.70u | -0.19 |
| tempo até o 1º contato | 42.99s | 47.84s | -0.16 |
| fração do tempo entrando em briga | 0.11 | 0.11 | +0.05 |
| regiões diferentes visitadas | 6.01 | 5.99 | +0.01 |

Mapa mais super-representado: nuke (2.0x a fatia do corpus). **Atenção:** 34% dos rounds deste grupo são em nuke (o corpus tem 17%, 2.0x) -- parte do grupo pode ser efeito do mapa, não estilo.

**Nomes candidatos:**
- **Mira fora da altura** -- mira na altura da cabeça 0.56 contra 0.87 (-2.30 desvio) -- o traço mais forte de todos os grupos
- **Crosshair baixo** -- placement 52 contra 68 (-1.55); o resto do perfil fica perto da média
- **Mira desajustada** -- o grupo é definido só pela mira: posição, tempo e movimento são os da média

**Sua resposta:** perfil "mira" = ____

### Perfil "junto" -- grupo 1 hoje (4037 jogador-rounds, 35% do corpus; CT 1623, TR 2414)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| maior distância do time no round **(distingue)** | 870.86u | 1238.95u | -0.74 |
| tempo até o 1º contato **(distingue)** | 26.80s | 47.84s | -0.69 |
| distância média do time **(distingue)** | 478.12u | 709.70u | -0.64 |
| fração do tempo entrando em briga **(distingue)** | 0.17 | 0.11 | +0.55 |
| regiões diferentes visitadas | 4.90 | 5.99 | -0.46 |
| mira na altura da cabeça (0-1) | 0.92 | 0.87 | +0.35 |
| placement da mira (0-100) | 71.75 | 68.39 | +0.32 |

Mapa mais super-representado: ancient (1.7x a fatia do corpus).

**Nomes candidatos:**
- **Junto e rápido** -- maior distância do time 871u contra 1239u (-0.74) e contato aos 27s (-0.69)
- **Entra em bloco** -- entra em briga +0.55 desvio acima da média, colado no time (-0.64)
- **Execução em grupo** -- 60% dos rounds deste grupo são de TR: é o jeito de executar um bomb junto

**Sua resposta:** perfil "junto" = ____

### Perfil "longe" -- grupo 2 hoje (3030 jogador-rounds, 26% do corpus; CT 2222, TR 808)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| distância média do time **(distingue)** | 1162.43u | 709.70u | +1.25 |
| maior distância do time no round **(distingue)** | 1819.83u | 1238.95u | +1.17 |
| regiões diferentes visitadas | 5.17 | 5.99 | -0.35 |
| placement da mira (0-100) | 71.81 | 68.39 | +0.32 |
| fração do tempo entrando em briga | 0.07 | 0.11 | -0.28 |
| mira na altura da cabeça (0-1) | 0.91 | 0.87 | +0.28 |
| tempo até o 1º contato | 54.14s | 47.84s | +0.21 |

Mapa mais super-representado: dust2 (1.4x a fatia do corpus).

**Nomes candidatos:**
- **Joga isolado** -- distância média do time 1162u contra 710u (+1.25 desvio)
- **Segura longe do time** -- maior distância no round 1820u (+1.17) com poucas regiões visitadas (-0.35): fica parado, longe
- **Posição solitária** -- 73% dos rounds deste grupo são de CT: é o jeito de defender um ponto sozinho

**Sua resposta:** perfil "longe" = ____

### Perfil "roda" -- grupo 3 hoje (3343 jogador-rounds, 29% do corpus; CT 1350, TR 1993)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| regiões diferentes visitadas **(distingue)** | 8.04 | 5.99 | +0.87 |
| tempo até o 1º contato **(distingue)** | 69.16s | 47.84s | +0.69 |
| fração do tempo entrando em briga | 0.05 | 0.11 | -0.43 |
| distância média do time | 602.18u | 709.70u | -0.30 |
| placement da mira (0-100) | 66.68 | 68.39 | -0.16 |
| mira na altura da cabeça (0-1) | 0.88 | 0.87 | +0.09 |
| maior distância do time no round | 1202.90u | 1238.95u | -0.07 |

Mapa mais super-representado: overpass (1.5x a fatia do corpus).

**Nomes candidatos:**
- **Roda o mapa** -- 8.0 regiões por round contra 6.0 (+0.87 desvio)
- **Contato tardio** -- primeiro contato aos 69s contra 48s (+0.69)
- **Joga o relógio** -- chega tarde e evita briga (tempo entrando em briga -0.43 desvio)

**Sua resposta:** perfil "roda" = ____

## 3. Rótulos de força do arremesso

2268 arremessos em 6 partidas. Desde a rota A (decisão 21a) o rótulo é o BOTÃO: a velocidade calculada pela rotina do jogo a até 19 u/s do centro de um dos três botões medidos no gabarito (202.5, 438.7, 675 u/s). As velocidades abaixo são ESTIMATIVAS do modelo; o que é afirmado é o botão.

| Rótulo | Velocidade estimada média | Arremessos | Exemplo |
|---|---|---|---|
| curto | 202 u/s | 88 | ZywOo, he, match_43 round 11 (0:09), em pé, parado |
| médio | 436 u/s | 97 | molodoy, smoke, match_43 round 11 (0:00), em pé, parado |
| longo | 673 u/s | 1931 | jL, flash, match_38 round 7 (0:07), em pé, parado |

Sem rótulo (neutros): 152, por motivo: vetor incoerente com o voo 46; fora da tolerância 38; ambíguo: subindo sem parábola 24; janela 0-5 (sem gabarito) 16; ambíguo: parábola sem pulo limpo 15; janela 14-18 (sem gabarito) 11; ambíguo: queda sem decolagem na janela 2

## 4. Teste do comando de console

Arremesso: **jL**, smoke, **match_38** (de_mirage) round 2, 0:33 do round (tick 9288). Ancoragem com resíduo de 0.12u, em pé, parado.

1. Servidor local no mapa, com:

```
sv_cheats 1; mp_warmup_end; mp_freezetime 0; sv_infinite_ammo 1; sv_grenade_trajectory_prac_pipreview 1
```

2. Com a smoke na mão, sem se mover:

```
setpos -722.82 -2186.60 -179.97; setang -2.99 85.99 0
```

3. Solte com o **botão esquerdo** (arremesso cheio), em pé, parado.

**Certo:** a smoke para em (-655, -1159, -166). O preview da trajetória mostra o ponto antes de você soltar.

**Se errar, me mande:** a saída do `getpos` logo depois do `setpos`; onde a smoke caiu (nome do lugar); e se o erro foi de DISTÂNCIA (curta ou longa demais -> altura ou pitch) ou de LADO (esquerda ou direita -> yaw).

**Sua resposta:** funcionou? ____

## 5. Ângulos de entrada da Nuke, do menos sustentado para o mais

38 ângulos distintos, juntando os 70 que o pipeline deriva partida a partida nas 9 Nuke do corpus (mesmo ângulo em partidas diferentes = mesma região, mesmo lado, yaw a menos de 20°). **19 aparecem numa partida só** -- podem ser hábito de um time naquele dia, não ângulo do mapa. A Nuke é o mapa de partição menos confiável do projeto (os dois sites empilhados na vertical), então é aqui que o julgamento humano mais vale.

Yaw na convenção do CS2: 0° para a direita do radar, 90° para cima, crescendo no sentido anti-horário. O que você confirmar ou corrigir vira `MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`, que tem prioridade sobre o derivado.

Até você revisar: nada entra em `MANUAL_ENTRY_ANGLES`, e o ângulo visto em menos de 2 partidas sai marcado como **baixa confiança** (`MIN_PARTIDAS_ANGULO_CONFIAVEL`).

| # | região | lado | yaw | direção no radar | partidas | kills | confiança do derivado | sua resposta |
|---|---|---|---|---|---|---|---|---|
| 1 | BombsiteA | CT | 90° | cima | 1 | 4 | baixa (1 partida) | ____ |
| 2 | BombsiteA | T | 77° | cima | 1 | 4 | baixa (1 partida) | ____ |
| 3 | BombsiteB | CT | -100° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 4 | BombsiteB | T | -99° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 5 | Catwalk | CT | -103° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 6 | Garage | CT | 177° | esquerda | 1 | 4 | baixa (1 partida) | ____ |
| 7 | Heaven | CT | -118° | esquerda-baixo | 1 | 4 | baixa (1 partida) | ____ |
| 8 | Lobby | T | -24° | direita-baixo | 1 | 4 | baixa (1 partida) | ____ |
| 9 | LockerRoom | CT | -87° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 10 | Outside | CT | 169° | esquerda | 1 | 4 | baixa (1 partida) | ____ |
| 11 | Outside | CT | -163° | esquerda | 1 | 4 | baixa (1 partida) | ____ |
| 12 | Rafters | CT | -132° | esquerda-baixo | 1 | 4 | baixa (1 partida) | ____ |
| 13 | Ramp | CT | -117° | esquerda-baixo | 1 | 4 | baixa (1 partida) | ____ |
| 14 | Ramp | T | -72° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 15 | Tunnels | CT | 98° | cima | 1 | 4 | baixa (1 partida) | ____ |
| 16 | Vending | CT | -99° | baixo | 1 | 4 | baixa (1 partida) | ____ |
| 17 | BombsiteA | T | 147° | esquerda-cima | 1 | 5 | baixa (1 partida) | ____ |
| 18 | Tunnels | T | 82° | cima | 1 | 5 | baixa (1 partida) | ____ |
| 19 | Mini | CT | 94° | cima | 1 | 6 | baixa (1 partida) | ____ |
| 20 | BombsiteA | T | -83° | baixo | 2 | 8 | — | ____ |
| 21 | BombsiteB | T | 38° | direita-cima | 2 | 8 | — | ____ |
| 22 | BombsiteB | T | 100° | cima | 2 | 9 | — | ____ |
| 23 | BombsiteA | CT | 168° | esquerda | 2 | 10 | — | ____ |
| 24 | BombsiteA | T | 55° | direita-cima | 2 | 11 | — | ____ |
| 25 | Control | T | -6° | direita | 2 | 11 | — | ____ |
| 26 | Ramp | CT | -69° | baixo | 2 | 11 | — | ____ |
| 27 | BombsiteA | CT | -59° | direita-baixo | 2 | 12 | — | ____ |
| 28 | BombsiteA | CT | -98° | baixo | 2 | 13 | — | ____ |
| 29 | Outside | CT | -134° | esquerda-baixo | 2 | 13 | — | ____ |
| 30 | Outside | T | 90° | cima | 2 | 13 | — | ____ |
| 31 | Ramp | CT | 161° | esquerda | 2 | 13 | — | ____ |
| 32 | Ramp | CT | -139° | esquerda-baixo | 3 | 12 | — | ____ |
| 33 | Ramp | CT | -91° | baixo | 3 | 15 | — | ____ |
| 34 | Outside | T | 68° | cima | 3 | 16 | — | ____ |
| 35 | BombsiteB | CT | 96° | cima | 4 | 17 | — | ____ |
| 36 | Admin | CT | 178° | esquerda | 4 | 18 | — | ____ |
| 37 | Outside | T | 16° | direita | 4 | 18 | — | ____ |
| 38 | BombsiteA | CT | -135° | esquerda-baixo | 6 | 32 | — | ____ |

**Sua resposta:** para cada linha, *confirma*, *descarta* (não é ângulo de verdade) ou *corrige* o yaw.

<!-- decisivo:inicio -->
## 6. Round decisivo (fase 6)

Gerado por `py -3.12 -m scripts.calibracao.material_decisivo` (regras em `metrics/decisivo_candidatas.py`, diagnóstico em `notas/investigacoes/2026-10-04-piso-do-decisivo.md`).

**As regras candidatas:**
- **A, piso absoluto (a de hoje):** o maior salto da chance de vitória, se passar de 1,5x o round mais barato do formato (12% no MR12).
- **B, proeminência:** o maior salto tem de valer pelo menos k vezes o round típico da partida (a mediana dos saltos dela). Aqui k = 1,68 (a mediana no corpus) só para mostrar; o k de verdade sai das suas respostas.
- **C, virada definitiva:** o round depois do qual o vencedor nunca mais teve menos de 50% de chance, se antes dele esteve abaixo. Sem virada, não há round decisivo.
- **D, combinação:** C quando houve virada; senão, B.
- **Empate no topo** (A, B): o 1º e o 2º maiores saltos que a frase da página escreve com a mesma porcentagem.

As candidatas discordam em 41 das 52 partidas, mais do que as 25 que cabem aqui: entram 21 discordâncias, escolhidas em rodízio pelo tipo de desacordo, e 4 partidas em que as quatro concordam.

| partida | mapa | placar | virada | A | B | C | D |
|---|---|---|---|---|---|---|---|
| match_01 | de_ancient | 13-9 | sim | R19 (empate) | — | R14 | R14 |
| match_02 | de_mirage | 13-9 | sim | R15 (empate) | — | R14 | R14 |
| match_03 | de_anubis | 13-7 | sim | — | R5 (empate) | R4 | R4 |
| match_05 | de_nuke | 4-13 | sim | — | — | R6 | R6 |
| match_06 | de_mirage | 13-5 | não | — | — | — | — |
| match_10 | de_dust2 | 13-1 | não | — | R1 (empate) | — | R1 (empate) |
| match_16 | de_nuke | 13-16 | sim | R24 | R24 | R24 | R24 |
| match_17 | de_dust2 | 13-4 | não | — | R1 (empate) | — | R1 (empate) |
| match_19 | de_inferno | 4-13 | não | — | R1 (empate) | — | R1 (empate) |
| match_20 | de_mirage | 14-16 | sim | R23 (empate) | R23 (empate) | R28 | R28 |
| match_21 | de_nuke | 13-8 | sim | R15 (empate) | — | R14 | R14 |
| match_22 | de_mirage | 7-13 | não | — | R1 (empate) | — | R1 (empate) |
| match_26 | de_anubis | 13-6 | sim | — | — | R6 | R6 |
| match_27 | de_nuke | 5-13 | sim | — | — | R4 | R4 |
| match_28 | de_mirage | 13-10 | sim | R19 (empate) | — | R18 | R18 |
| match_30 | de_nuke | 9-13 | não | R16 | — | — | — |
| match_32 | de_mirage | 16-19 | sim | R23 (empate) | R23 (empate) | R32 | R32 |
| match_34 | de_mirage | 9-13 | não | R21 (empate) | R21 (empate) | — | R21 (empate) |
| match_36 | de_mirage | 8-13 | não | R16 (empate) | — | — | — |
| match_37 | de_dust2 | 16-14 | sim | R24 (empate) | R24 (empate) | R24 | R24 |
| match_40 | de_nuke | 16-14 | sim | R24 (empate) | R24 (empate) | R26 | R26 |
| match_41 | de_inferno | 16-14 | sim | R23 (empate) | R23 (empate) | R16 | R16 |
| match_42 | de_dust2 | 17-19 | sim | R24 (empate) | R24 (empate) | R24 | R24 |
| match_48 | de_dust2 | 13-6 | sim | — | — | R2 | R2 |
| match_51 | de_nuke | 10-13 | não | R21 (empate) | — | — | — |

### match_01 — de_ancient, 13-9 (22 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      0-2    #######.............  34%     8%  vence B
R3      0-3    #####...............  26%     8%  vence B
R4      0-4    ####................  19%     7%  vence B
R5      1-4    #####...............  25%     6%  vence A
R6      2-4    ######..............  32%     7%  vence A
R7      3-4    ########............  41%     8%  vence A
R8      4-4    ##########..........  50%     9%  vence A
R9      5-4    ############........  60%    10%  vence A
R10     5-5    ##########..........  50%    10%  vence B
R11     6-5    ############........  60%    10%  vence A
R12     6-6    ##########..........  50%    10%  vence B
R13     6-7    ########............  39%    11%  vence B
R14     7-7    ##########..........  50%    11%  vence A
R15     8-7    ############........  62%    12%  vence A
R16     9-7    ###############.....  75%    12%  vence A
R17     9-8    #############.......  64%    11%  vence B
R18     9-9    ##########..........  50%    14%  vence B
R19    10-9    #############.......  66%    16%  vence A
R20    11-9    ################....  81%    16%  vence A
R21    12-9    ###################.  94%    12%  vence A
R22    13-9    #################### 100%     6%  vence A
```

Os três maiores saltos:

- **R19** (16%): 9-9 → 10-9, vence o Time A; compra: quem venceu 5.360$, quem perdeu 5.080$; 4K de _AmadeuS; bomba plantada.
- **R20** (16%): 10-9 → 11-9, vence o Time A; compra: quem venceu 5.810$, quem perdeu 4.690$; 3K de rol1ng-; bomba plantada.
- **R18** (14%): 9-8 → 9-9, vence o Time B; compra: quem venceu 4.940$, quem perdeu 5.890$; bomba plantada.

O que cada regra diria:

- **A:** R19 (empate no topo) — maior salto da partida, 16%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,54x o round típico da partida (exigido 1,68x).
- **C:** R14 — virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.
- **D:** R14 — houve virada (regra C): virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_02 — de_mirage, 13-9 (22 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      2-1    ############........  58%     8%  vence B
R4      3-1    #############.......  67%     8%  vence A
R5      3-2    ############........  59%     8%  vence B
R6      4-2    ##############......  68%     9%  vence A
R7      4-3    ############........  59%     8%  vence B
R8      4-4    ##########..........  50%     9%  vence B
R9      4-5    ########............  40%    10%  vence B
R10     4-6    ######..............  30%    10%  vence B
R11     4-7    ####................  21%     9%  vence B
R12     5-7    ######..............  29%     8%  vence A
R13     6-7    ########............  39%    10%  vence A
R14     7-7    ##########..........  50%    11%  vence A
R15     8-7    ############........  62%    12%  vence A
R16     9-7    ###############.....  75%    12%  vence A
R17    10-7    #################...  86%    11%  vence A
R18    10-8    ###############.....  77%     8%  vence B
R19    11-8    ##################..  89%    12%  vence A
R20    12-8    ###################.  97%     8%  vence A
R21    12-9    ###################.  94%     3%  vence B
R22    13-9    #################### 100%     6%  vence A
```

Os três maiores saltos:

- **R15** (12%): 7-7 → 8-7, vence o Time A; compra: quem venceu 4.910$, quem perdeu 4.080$; 3K de donk666.
- **R16** (12%): 8-7 → 9-7, vence o Time A; compra: quem venceu 5.520$, quem perdeu 1.330$; bomba plantada. Frase do round: "Round de economia: o time entrou com 1.330$ de equipamento médio contra 5.520$ do adversário, 4.190$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R19** (12%): 10-8 → 11-8, vence o Time A; compra: quem venceu 4.080$, quem perdeu 5.430$.

O que cada regra diria:

- **A:** R15 (empate no topo) — maior salto da partida, 12%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,43x o round típico da partida (exigido 1,68x).
- **C:** R14 — virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.
- **D:** R14 — houve virada (regra C): virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_03 — de_anubis, 13-7 (20 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      0-2    #######.............  34%     8%  vence B
R3      1-2    ########............  42%     8%  vence A
R4      2-2    ##########..........  50%     8%  vence A
R5      3-2    ############........  59%     9%  vence A
R6      4-2    ##############......  68%     9%  vence A
R7      5-2    ###############.....  76%     8%  vence A
R8      6-2    #################...  83%     7%  vence A
R9      7-2    ##################..  89%     6%  vence A
R10     8-2    ###################.  94%     5%  vence A
R11     9-2    ###################.  97%     3%  vence A
R12    10-2    ####################  99%     2%  vence A
R13    10-3    ####################  98%     1%  vence B
R14    10-4    ###################.  97%     1%  vence B
R15    10-5    ###################.  95%     2%  vence B
R16    11-5    ####################  98%     4%  vence A
R17    11-6    ###################.  96%     2%  vence B
R18    11-7    ###################.  94%     3%  vence B
R19    12-7    ####################  98%     5%  vence A
R20    13-7    #################### 100%     2%  vence A
```

Os três maiores saltos:

- **R5** (9%): 2-2 → 3-2, vence o Time A; compra: quem venceu 5.220$, quem perdeu 1.480$; bomba plantada. Frase do round: "Round de economia: o time entrou com 1.480$ de equipamento médio contra 5.220$ do adversário, 3.740$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R6** (9%): 3-2 → 4-2, vence o Time A; compra: quem venceu 5.060$, quem perdeu 4.840$; bomba plantada.
- **R4** (8%): 1-2 → 2-2, vence o Time A; compra: quem venceu 4.620$, quem perdeu 3.690$; 3K de donk666; bomba plantada.

O que cada regra diria:

- **A:** nenhum round — o maior salto (9%) não passa do piso de 12%.
- **B:** R5 (empate no topo) — o maior salto vale 1,90x o round típico da partida (exigido 1,68x).
- **C:** R4 — virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.
- **D:** R4 — houve virada (regra C): virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_05 — de_nuke, 4-13 (17 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      1-0    ########............  42%     8%  vence A
R2      2-0    #######.............  34%     8%  vence A
R3      3-0    #####...............  26%     8%  vence A
R4      3-1    #######.............  33%     7%  vence B
R5      3-2    ########............  41%     8%  vence B
R6      3-3    ##########..........  50%     9%  vence B
R7      3-4    ############........  59%     9%  vence B
R8      3-5    ##############......  69%     9%  vence B
R9      3-6    ###############.....  77%     9%  vence B
R10     3-7    #################...  85%     8%  vence B
R11     3-8    ##################..  91%     6%  vence B
R12     4-8    #################...  87%     4%  vence A
R13     4-9    ###################.  93%     6%  vence B
R14     4-10   ###################.  97%     4%  vence B
R15     4-11   ####################  99%     2%  vence B
R16     4-12   #################### 100%     1%  vence B
R17     4-13   #################### 100%     0%  vence B
```

Os três maiores saltos:

- **R7** (9%): 3-3 → 3-4, vence o Time B; compra: quem venceu 6.230$, quem perdeu 4.310$; 4K de lilpeepfan-.
- **R8** (9%): 3-4 → 3-5, vence o Time B; compra: quem venceu 6.050$, quem perdeu 1.730$; clutch de lilpeepfan- contra 1; 3K de gwizdakk. Frase do round: "Round de economia: o time entrou com 1.730$ de equipamento médio contra 6.050$ do adversário, 4.320$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R6** (9%): 3-2 → 3-3, vence o Time B; compra: quem venceu 6.190$, quem perdeu 640$. Frase do round: "Round de economia: o time entrou com 640$ de equipamento médio contra 6.190$ do adversário, 5.550$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (9%) não passa do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,21x o round típico da partida (exigido 1,68x).
- **C:** R6 — virada definitiva: o vencedor passou de 41% para 50% e não ficou mais abaixo de 50%.
- **D:** R6 — houve virada (regra C): virada definitiva: o vencedor passou de 41% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_06 — de_mirage, 13-5 (18 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      2-1    ############........  58%     8%  vence B
R4      3-1    #############.......  67%     8%  vence A
R5      4-1    ###############.....  75%     8%  vence A
R6      5-1    ################....  82%     7%  vence A
R7      5-2    ###############.....  76%     6%  vence B
R8      6-2    #################...  83%     7%  vence A
R9      6-3    ###############.....  77%     6%  vence B
R10     7-3    #################...  85%     8%  vence A
R11     8-3    ##################..  91%     6%  vence A
R12     8-4    #################...  87%     4%  vence B
R13     9-4    ###################.  93%     6%  vence A
R14    10-4    ###################.  97%     4%  vence A
R15    10-5    ###################.  95%     2%  vence B
R16    11-5    ####################  98%     4%  vence A
R17    12-5    #################### 100%     2%  vence A
R18    13-5    #################### 100%     0%  vence A
```

Os três maiores saltos:

- **R4** (8%): 2-1 → 3-1, vence o Time A; compra: quem venceu 3.630$, quem perdeu 5.320$; clutch de Etaliqe contra 1.
- **R1** (8%): 0-0 → 1-0, vence o Time A; compra: quem venceu 850$, quem perdeu 850$; 4K de adamS; bomba plantada. Frase do round: "Round de economia: o time entrou com 850$ de equipamento médio contra 850$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R2** (8%): 1-0 → 2-0, vence o Time A; compra: quem venceu 4.130$, quem perdeu 580$; 3K de pradablade. Frase do round: "Round de economia: o time entrou com 580$ de equipamento médio contra 4.130$ do adversário, 3.550$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (8%) não passa do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,38x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** nenhum round — sem virada (regra B): nenhum round se destaca: o maior salto vale 1,38x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_10 — de_dust2, 13-1 (14 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      3-0    ###############.....  74%     8%  vence A
R4      4-0    ################....  81%     7%  vence A
R5      5-0    #################...  87%     6%  vence A
R6      6-0    ##################..  92%     5%  vence A
R7      7-0    ###################.  95%     4%  vence A
R8      8-0    ####################  98%     2%  vence A
R9      9-0    ####################  99%     1%  vence A
R10    10-0    #################### 100%     1%  vence A
R11    10-1    ####################  99%     0%  vence B
R12    11-1    #################### 100%     0%  vence A
R13    12-1    #################### 100%     0%  vence A
R14    13-1    #################### 100%     0%  vence A
```

Os três maiores saltos:

- **R1** (8%): 0-0 → 1-0, vence o Time A; compra: quem venceu 1.050$, quem perdeu 930$; 3K de zont1x; bomba plantada. Frase do round: "Round de economia: o time entrou com 930$ de equipamento médio contra 1.050$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R2** (8%): 1-0 → 2-0, vence o Time A; compra: quem venceu 3.850$, quem perdeu 2.320$; bomba plantada.
- **R3** (8%): 2-0 → 3-0, vence o Time A; compra: quem venceu 4.380$, quem perdeu 790$; bomba plantada. Frase do round: "Round de economia: o time entrou com 790$ de equipamento médio contra 4.380$ do adversário, 3.590$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (8%) não passa do piso de 12%.
- **B:** R1 (empate no topo) — o maior salto vale 2,73x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** R1 (empate no topo) — sem virada (regra B): o maior salto vale 2,73x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_16 — de_nuke, 13-16 (29 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      1-0    ########............  42%     8%  vence A
R2      2-0    #######.............  34%     8%  vence A
R3      3-0    #####...............  26%     8%  vence A
R4      4-0    ####................  19%     7%  vence A
R5      5-0    ###.................  13%     6%  vence A
R6      5-1    ####................  18%     5%  vence B
R7      6-1    ##..................  12%     6%  vence A
R8      7-1    #...................   7%     5%  vence A
R9      8-1    #...................   4%     3%  vence A
R10     8-2    #...................   6%     2%  vence B
R11     9-2    #...................   3%     3%  vence A
R12     9-3    #...................   5%     2%  vence B
R13     9-4    #...................   7%     3%  vence B
R14     9-5    ##..................  11%     4%  vence B
R15     9-6    ###.................  17%     6%  vence B
R16    10-6    ##..................   9%     8%  vence A
R17    10-7    ###.................  14%     5%  vence B
R18    10-8    #####...............  23%     8%  vence B
R19    10-9    #######.............  34%    12%  vence B
R20    10-10   ##########..........  50%    16%  vence B
R21    11-10   ######..............  31%    19%  vence A
R22    12-10   ##..................  12%    19%  vence A
R23    12-11   #####...............  25%    12%  vence B
R24    12-12   ##########..........  50%    25%  vence B
R25    12-13   #############.......  66%    16%  vence B
R26    12-14   ################....  81%    16%  vence B
R27    12-15   ###################.  94%    12%  vence B
R28    13-15   ##################..  88%     6%  vence A
R29    13-16   #################### 100%    12%  vence B
```

Os três maiores saltos:

- **R24** (25%): 12-11 → 12-12, vence o Time B; compra: quem venceu 5.320$, quem perdeu 6.290$; 3K de FalleN; bomba plantada.
- **R21** (19%): 10-10 → 11-10, vence o Time A; compra: quem venceu 5.610$, quem perdeu 5.330$; bomba plantada.
- **R22** (19%): 11-10 → 12-10, vence o Time A; compra: quem venceu 5.570$, quem perdeu 3.460$.

O que cada regra diria:

- **A:** R24 — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R24 — o maior salto vale 3,24x o round típico da partida (exigido 1,68x).
- **C:** R24 — virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.
- **D:** R24 — houve virada (regra C): virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_17 — de_dust2, 13-4 (17 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      3-0    ###############.....  74%     8%  vence A
R4      4-0    ################....  81%     7%  vence A
R5      5-0    #################...  87%     6%  vence A
R6      6-0    ##################..  92%     5%  vence A
R7      7-0    ###################.  95%     4%  vence A
R8      8-0    ####################  98%     2%  vence A
R9      8-1    ###################.  96%     1%  vence B
R10     8-2    ###################.  94%     2%  vence B
R11     9-2    ###################.  97%     3%  vence A
R12    10-2    ####################  99%     2%  vence A
R13    11-2    #################### 100%     1%  vence A
R14    11-3    ####################  99%     0%  vence B
R15    11-4    ####################  99%     0%  vence B
R16    12-4    #################### 100%     1%  vence A
R17    13-4    #################### 100%     0%  vence A
```

Os três maiores saltos:

- **R1** (8%): 0-0 → 1-0, vence o Time A; compra: quem venceu 950$, quem perdeu 890$; clutch de yuurih contra 2; 3K de makazze; bomba plantada. Frase do round: "Round de economia: o time entrou com 890$ de equipamento médio contra 950$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R2** (8%): 1-0 → 2-0, vence o Time A; compra: quem venceu 3.940$, quem perdeu 2.440$; 4K de molodoy; bomba plantada.
- **R3** (8%): 2-0 → 3-0, vence o Time A; compra: quem venceu 4.800$, quem perdeu 600$; bomba plantada. Frase do round: "Round de economia: o time entrou com 600$ de equipamento médio contra 4.800$ do adversário, 4.200$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (8%) não passa do piso de 12%.
- **B:** R1 (empate no topo) — o maior salto vale 3,41x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** R1 (empate no topo) — sem virada (regra B): o maior salto vale 3,41x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_19 — de_inferno, 4-13 (17 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      0-2    #############.......  66%     8%  vence B
R3      0-3    ###############.....  74%     8%  vence B
R4      0-4    ################....  81%     7%  vence B
R5      0-5    #################...  87%     6%  vence B
R6      1-5    ################....  82%     5%  vence A
R7      1-6    ##################..  88%     6%  vence B
R8      1-7    ###################.  93%     5%  vence B
R9      1-8    ###################.  96%     3%  vence B
R10     1-9    ####################  98%     2%  vence B
R11     1-10   ####################  99%     1%  vence B
R12     1-11   #################### 100%     0%  vence B
R13     1-12   #################### 100%     0%  vence B
R14     2-12   #################### 100%     0%  vence A
R15     3-12   #################### 100%     0%  vence A
R16     4-12   #################### 100%     0%  vence A
R17     4-13   #################### 100%     0%  vence B
```

Os três maiores saltos:

- **R1** (8%): 0-0 → 0-1, vence o Time B; compra: quem venceu 850$, quem perdeu 1.280$; 3K de m0NESY; bomba plantada. Frase do round: "Round de economia: o time entrou com 1.280$ de equipamento médio contra 850$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R2** (8%): 0-1 → 0-2, vence o Time B; compra: quem venceu 4.530$, quem perdeu 3.020$.
- **R3** (8%): 0-2 → 0-3, vence o Time B; compra: quem venceu 5.540$, quem perdeu 980$; 3K de kyousuke. Frase do round: "Round de economia: o time entrou com 980$ de equipamento médio contra 5.540$ do adversário, 4.560$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (8%) não passa do piso de 12%.
- **B:** R1 (empate no topo) — o maior salto vale 2,42x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** R1 (empate no topo) — sem virada (regra B): o maior salto vale 2,42x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_20 — de_mirage, 14-16 (30 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      0-2    #############.......  66%     8%  vence B
R3      1-2    ############........  58%     8%  vence A
R4      2-2    ##########..........  50%     8%  vence A
R5      3-2    ########............  41%     9%  vence A
R6      4-2    ######..............  32%     9%  vence A
R7      5-2    #####...............  24%     8%  vence A
R8      6-2    ###.................  17%     7%  vence A
R9      6-3    #####...............  23%     6%  vence B
R10     6-4    ######..............  30%     8%  vence B
R11     6-5    ########............  40%     9%  vence B
R12     6-6    ##########..........  50%    10%  vence B
R13     6-7    ############........  61%    11%  vence B
R14     6-8    ###############.....  73%    11%  vence B
R15     7-8    ############........  62%    10%  vence A
R16     8-8    ##########..........  50%    12%  vence A
R17     9-8    #######.............  36%    14%  vence A
R18     9-9    ##########..........  50%    14%  vence B
R19    10-9    #######.............  34%    16%  vence A
R20    10-10   ##########..........  50%    16%  vence B
R21    11-10   ######..............  31%    19%  vence A
R22    11-11   ##########..........  50%    19%  vence B
R23    11-12   ###############.....  75%    25%  vence B
R24    12-12   ##########..........  50%    25%  vence A
R25    13-12   #######.............  34%    16%  vence A
R26    13-13   ##########..........  50%    16%  vence B
R27    14-13   ######..............  31%    19%  vence A
R28    14-14   ##########..........  50%    19%  vence B
R29    14-15   ###############.....  75%    25%  vence B
R30    14-16   #################### 100%    25%  vence B
```

Os três maiores saltos:

- **R23** (25%): 11-11 → 11-12, vence o Time B; compra: quem venceu 5.760$, quem perdeu 4.950$; clutch de molodoy contra 1; 3K de molodoy; bomba plantada.
- **R24** (25%): 11-12 → 12-12, vence o Time A; compra: quem venceu 2.900$, quem perdeu 5.470$; 3K de TeSeS.
- **R29** (25%): 14-14 → 14-15, vence o Time B; compra: quem venceu 6.520$, quem perdeu 5.600$; bomba plantada.

O que cada regra diria:

- **A:** R23 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R23 (empate no topo) — o maior salto vale 2,12x o round típico da partida (exigido 1,68x).
- **C:** R28 — virada definitiva: o vencedor passou de 31% para 50% e não ficou mais abaixo de 50%.
- **D:** R28 — houve virada (regra C): virada definitiva: o vencedor passou de 31% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_21 — de_nuke, 13-8 (21 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      0-2    #######.............  34%     8%  vence B
R3      0-3    #####...............  26%     8%  vence B
R4      0-4    ####................  19%     7%  vence B
R5      1-4    #####...............  25%     6%  vence A
R6      2-4    ######..............  32%     7%  vence A
R7      3-4    ########............  41%     8%  vence A
R8      4-4    ##########..........  50%     9%  vence A
R9      5-4    ############........  60%    10%  vence A
R10     5-5    ##########..........  50%    10%  vence B
R11     5-6    ########............  40%    10%  vence B
R12     5-7    ######..............  29%    10%  vence B
R13     6-7    ########............  39%    10%  vence A
R14     7-7    ##########..........  50%    11%  vence A
R15     8-7    ############........  62%    12%  vence A
R16     9-7    ###############.....  75%    12%  vence A
R17    10-7    #################...  86%    11%  vence A
R18    11-7    ###################.  94%     8%  vence A
R19    12-7    ####################  98%     5%  vence A
R20    12-8    ###################.  97%     2%  vence B
R21    13-8    #################### 100%     3%  vence A
```

Os três maiores saltos:

- **R15** (12%): 7-7 → 8-7, vence o Time A; compra: quem venceu 5.260$, quem perdeu 4.450$; 3K de XANTARES.
- **R16** (12%): 8-7 → 9-7, vence o Time A; compra: quem venceu 6.130$, quem perdeu 1.380$. Frase do round: "Round de economia: o time entrou com 1.380$ de equipamento médio contra 6.130$ do adversário, 4.750$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R14** (11%): 6-7 → 7-7, vence o Time A; compra: quem venceu 4.330$, quem perdeu 400$. Frase do round: "Round de economia: o time entrou com 400$ de equipamento médio contra 4.330$ do adversário, 3.930$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** R15 (empate no topo) — maior salto da partida, 12%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,47x o round típico da partida (exigido 1,68x).
- **C:** R14 — virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.
- **D:** R14 — houve virada (regra C): virada definitiva: o vencedor passou de 39% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_22 — de_mirage, 7-13 (20 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      0-2    #############.......  66%     8%  vence B
R3      0-3    ###############.....  74%     8%  vence B
R4      0-4    ################....  81%     7%  vence B
R5      0-5    #################...  87%     6%  vence B
R6      0-6    ##################..  92%     5%  vence B
R7      0-7    ###################.  95%     4%  vence B
R8      1-7    ###################.  93%     2%  vence A
R9      1-8    ###################.  96%     3%  vence B
R10     1-9    ####################  98%     2%  vence B
R11     2-9    ###################.  97%     1%  vence A
R12     3-9    ###################.  95%     2%  vence A
R13     3-10   ####################  98%     3%  vence B
R14     3-11   ####################  99%     1%  vence B
R15     3-12   #################### 100%     0%  vence B
R16     4-12   #################### 100%     0%  vence A
R17     5-12   #################### 100%     0%  vence A
R18     6-12   ####################  99%     0%  vence A
R19     7-12   ####################  98%     1%  vence A
R20     7-13   #################### 100%     2%  vence B
```

Os três maiores saltos:

- **R1** (8%): 0-0 → 0-1, vence o Time B; compra: quem venceu 800$, quem perdeu 900$. Frase do round: "Round de economia: o time entrou com 900$ de equipamento médio contra 800$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R2** (8%): 0-1 → 0-2, vence o Time B; compra: quem venceu 4.060$, quem perdeu 400$. Frase do round: "Round de economia: o time entrou com 400$ de equipamento médio contra 4.060$ do adversário, 3.660$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R3** (8%): 0-2 → 0-3, vence o Time B; compra: quem venceu 5.930$, quem perdeu 4.600$; 3K de kyxsan.

O que cada regra diria:

- **A:** nenhum round — o maior salto (8%) não passa do piso de 12%.
- **B:** R1 (empate no topo) — o maior salto vale 3,63x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** R1 (empate no topo) — sem virada (regra B): o maior salto vale 3,63x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_26 — de_anubis, 13-6 (19 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      0-2    #######.............  34%     8%  vence B
R3      0-3    #####...............  26%     8%  vence B
R4      1-3    #######.............  33%     7%  vence A
R5      2-3    ########............  41%     8%  vence A
R6      3-3    ##########..........  50%     9%  vence A
R7      4-3    ############........  59%     9%  vence A
R8      5-3    ##############......  69%     9%  vence A
R9      6-3    ###############.....  77%     9%  vence A
R10     7-3    #################...  85%     8%  vence A
R11     8-3    ##################..  91%     6%  vence A
R12     9-3    ###################.  95%     4%  vence A
R13    10-3    ####################  98%     3%  vence A
R14    11-3    ####################  99%     1%  vence A
R15    12-3    #################### 100%     0%  vence A
R16    12-4    #################### 100%     0%  vence B
R17    12-5    #################### 100%     0%  vence B
R18    12-6    ####################  99%     0%  vence B
R19    13-6    #################### 100%     1%  vence A
```

Os três maiores saltos:

- **R7** (9%): 3-3 → 4-3, vence o Time A; compra: quem venceu 5.510$, quem perdeu 2.640$; 3K de flameZ; bomba plantada.
- **R8** (9%): 4-3 → 5-3, vence o Time A; compra: quem venceu 5.510$, quem perdeu 5.730$; bomba plantada.
- **R6** (9%): 2-3 → 3-3, vence o Time A; compra: quem venceu 5.510$, quem perdeu 5.590$; bomba plantada.

O que cada regra diria:

- **A:** nenhum round — o maior salto (9%) não passa do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,32x o round típico da partida (exigido 1,68x).
- **C:** R6 — virada definitiva: o vencedor passou de 41% para 50% e não ficou mais abaixo de 50%.
- **D:** R6 — houve virada (regra C): virada definitiva: o vencedor passou de 41% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_27 — de_nuke, 5-13 (18 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      1-0    ########............  42%     8%  vence A
R2      1-1    ##########..........  50%     8%  vence B
R3      2-1    ########............  42%     8%  vence A
R4      2-2    ##########..........  50%     8%  vence B
R5      2-3    ############........  59%     9%  vence B
R6      2-4    ##############......  68%     9%  vence B
R7      3-4    ############........  59%     8%  vence A
R8      3-5    ##############......  69%     9%  vence B
R9      3-6    ###############.....  77%     9%  vence B
R10     3-7    #################...  85%     8%  vence B
R11     3-8    ##################..  91%     6%  vence B
R12     3-9    ###################.  95%     4%  vence B
R13     3-10   ####################  98%     3%  vence B
R14     3-11   ####################  99%     1%  vence B
R15     3-12   #################### 100%     0%  vence B
R16     4-12   #################### 100%     0%  vence A
R17     5-12   #################### 100%     0%  vence A
R18     5-13   #################### 100%     0%  vence B
```

Os três maiores saltos:

- **R8** (9%): 3-4 → 3-5, vence o Time B; compra: quem venceu 5.890$, quem perdeu 3.980$.
- **R5** (9%): 2-2 → 2-3, vence o Time B; compra: quem venceu 5.130$, quem perdeu 2.180$; 3K de magixx.
- **R6** (9%): 2-3 → 2-4, vence o Time B; compra: quem venceu 5.420$, quem perdeu 220$; 3K de sh1ro. Frase do round: "Round de economia: o time entrou com 220$ de equipamento médio contra 5.420$ do adversário, 5.200$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."

O que cada regra diria:

- **A:** nenhum round — o maior salto (9%) não passa do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,18x o round típico da partida (exigido 1,68x).
- **C:** R4 — virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.
- **D:** R4 — houve virada (regra C): virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_28 — de_mirage, 13-10 (23 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      0-2    #######.............  34%     8%  vence B
R3      0-3    #####...............  26%     8%  vence B
R4      1-3    #######.............  33%     7%  vence A
R5      1-4    #####...............  25%     8%  vence B
R6      2-4    ######..............  32%     7%  vence A
R7      3-4    ########............  41%     8%  vence A
R8      4-4    ##########..........  50%     9%  vence A
R9      5-4    ############........  60%    10%  vence A
R10     6-4    ##############......  70%    10%  vence A
R11     7-4    ################....  79%     9%  vence A
R12     7-5    ##############......  71%     8%  vence B
R13     7-6    ############........  61%    10%  vence B
R14     7-7    ##########..........  50%    11%  vence B
R15     7-8    ########............  38%    12%  vence B
R16     7-9    #####...............  25%    12%  vence B
R17     8-9    #######.............  36%    11%  vence A
R18     9-9    ##########..........  50%    14%  vence A
R19    10-9    #############.......  66%    16%  vence A
R20    11-9    ################....  81%    16%  vence A
R21    12-9    ###################.  94%    12%  vence A
R22    12-10   ##################..  88%     6%  vence B
R23    13-10   #################### 100%    12%  vence A
```

Os três maiores saltos:

- **R19** (16%): 9-9 → 10-9, vence o Time A; compra: quem venceu 6.300$, quem perdeu 1.840$; 3K de donk. Frase do round: "Round de economia: o time entrou com 1.840$ de equipamento médio contra 6.300$ do adversário, 4.460$ de diferença. Perder aqui é esperado, e o que vale olhar é quanto dano o time conseguiu tirar."
- **R20** (16%): 10-9 → 11-9, vence o Time A; compra: quem venceu 6.180$, quem perdeu 4.440$.
- **R18** (14%): 8-9 → 9-9, vence o Time A; compra: quem venceu 5.410$, quem perdeu 4.910$; 3K de apEX.

O que cada regra diria:

- **A:** R19 (empate no topo) — maior salto da partida, 16%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,62x o round típico da partida (exigido 1,68x).
- **C:** R18 — virada definitiva: o vencedor passou de 36% para 50% e não ficou mais abaixo de 50%.
- **D:** R18 — houve virada (regra C): virada definitiva: o vencedor passou de 36% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_30 — de_nuke, 9-13 (22 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      1-1    ##########..........  50%     8%  vence A
R3      1-2    ############........  58%     8%  vence B
R4      1-3    #############.......  67%     8%  vence B
R5      1-4    ###############.....  75%     8%  vence B
R6      1-5    ################....  82%     7%  vence B
R7      1-6    ##################..  88%     6%  vence B
R8      2-6    #################...  83%     5%  vence A
R9      3-6    ###############.....  77%     6%  vence A
R10     4-6    ##############......  70%     8%  vence A
R11     5-6    ############........  60%     9%  vence A
R12     6-6    ##########..........  50%    10%  vence A
R13     6-7    ############........  61%    11%  vence B
R14     6-8    ###############.....  73%    11%  vence B
R15     7-8    ############........  62%    10%  vence A
R16     7-9    ###############.....  75%    12%  vence B
R17     7-10   #################...  86%    11%  vence B
R18     7-11   ###################.  94%     8%  vence B
R19     8-11   ##################..  89%     5%  vence A
R20     8-12   ###################.  97%     8%  vence B
R21     9-12   ###################.  94%     3%  vence A
R22     9-13   #################### 100%     6%  vence B
```

Os três maiores saltos:

- **R16** (12%): 7-8 → 7-9, vence o Time B; compra: quem venceu 4.160$, quem perdeu 5.860$; clutch de YEKINDAR contra 1; 3K de YEKINDAR; bomba plantada.
- **R13** (11%): 6-6 → 6-7, vence o Time B; compra: quem venceu 870$, quem perdeu 800$; bomba plantada. Frase do round: "Round de economia: o time entrou com 800$ de equipamento médio contra 870$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R14** (11%): 6-7 → 6-8, vence o Time B; compra: quem venceu 3.720$, quem perdeu 2.690$.

O que cada regra diria:

- **A:** R16 — maior salto da partida, 12%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,53x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** nenhum round — sem virada (regra B): nenhum round se destaca: o maior salto vale 1,53x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_32 — de_mirage, 16-19 (35 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      1-0    ########............  42%     8%  vence A
R2      2-0    #######.............  34%     8%  vence A
R3      3-0    #####...............  26%     8%  vence A
R4      4-0    ####................  19%     7%  vence A
R5      4-1    #####...............  25%     6%  vence B
R6      4-2    ######..............  32%     7%  vence B
R7      4-3    ########............  41%     8%  vence B
R8      4-4    ##########..........  50%     9%  vence B
R9      4-5    ############........  60%    10%  vence B
R10     4-6    ##############......  70%    10%  vence B
R11     5-6    ############........  60%     9%  vence A
R12     5-7    ##############......  71%    10%  vence B
R13     6-7    ############........  61%    10%  vence A
R14     7-7    ##########..........  50%    11%  vence A
R15     8-7    ########............  38%    12%  vence A
R16     8-8    ##########..........  50%    12%  vence B
R17     9-8    #######.............  36%    14%  vence A
R18    10-8    #####...............  23%    14%  vence A
R19    10-9    #######.............  34%    12%  vence B
R20    10-10   ##########..........  50%    16%  vence B
R21    10-11   ##############......  69%    19%  vence B
R22    11-11   ##########..........  50%    19%  vence A
R23    11-12   ###############.....  75%    25%  vence B
R24    12-12   ##########..........  50%    25%  vence A
R25    13-12   #######.............  34%    16%  vence A
R26    14-12   ####................  19%    16%  vence A
R27    15-12   #...................   6%    12%  vence A
R28    15-13   ##..................  12%     6%  vence B
R29    15-14   #####...............  25%    12%  vence B
R30    15-15   ##########..........  50%    25%  vence B
R31    16-15   #######.............  34%    16%  vence A
R32    16-16   ##########..........  50%    16%  vence B
R33    16-17   ##############......  69%    19%  vence B
R34    16-18   ##################..  88%    19%  vence B
R35    16-19   #################### 100%    12%  vence B
```

Os três maiores saltos:

- **R23** (25%): 11-11 → 11-12, vence o Time B; compra: quem venceu 5.230$, quem perdeu 5.820$; bomba plantada.
- **R24** (25%): 11-12 → 12-12, vence o Time A; compra: quem venceu 5.150$, quem perdeu 5.630$; 3K de kyxsan.
- **R30** (25%): 15-14 → 15-15, vence o Time B; compra: quem venceu 6.620$, quem perdeu 5.730$; 3K de yuurih.

O que cada regra diria:

- **A:** R23 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R23 (empate no topo) — o maior salto vale 2,03x o round típico da partida (exigido 1,68x).
- **C:** R32 — virada definitiva: o vencedor passou de 34% para 50% e não ficou mais abaixo de 50%.
- **D:** R32 — houve virada (regra C): virada definitiva: o vencedor passou de 34% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_34 — de_mirage, 9-13 (22 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      0-2    #############.......  66%     8%  vence B
R3      1-2    ############........  58%     8%  vence A
R4      1-3    #############.......  67%     8%  vence B
R5      1-4    ###############.....  75%     8%  vence B
R6      1-5    ################....  82%     7%  vence B
R7      1-6    ##################..  88%     6%  vence B
R8      1-7    ###################.  93%     5%  vence B
R9      1-8    ###################.  96%     3%  vence B
R10     2-8    ###################.  94%     2%  vence A
R11     2-9    ###################.  97%     3%  vence B
R12     2-10   ####################  99%     2%  vence B
R13     3-10   ####################  98%     1%  vence A
R14     4-10   ###################.  97%     1%  vence A
R15     5-10   ###################.  95%     2%  vence A
R16     6-10   ##################..  91%     4%  vence A
R17     7-10   #################...  86%     5%  vence A
R18     8-10   ###############.....  77%     8%  vence A
R19     8-11   ##################..  89%    12%  vence B
R20     9-11   ################....  81%     8%  vence A
R21     9-12   ###################.  94%    12%  vence B
R22     9-13   #################### 100%     6%  vence B
```

Os três maiores saltos:

- **R21** (12%): 9-11 → 9-12, vence o Time B; compra: quem venceu 2.450$, quem perdeu 5.380$; clutch de flameZ contra 1; bomba plantada.
- **R19** (12%): 8-10 → 8-11, vence o Time B; compra: quem venceu 4.800$, quem perdeu 6.050$; clutch de mezii contra 2; 3K de mezii; bomba plantada.
- **R4** (8%): 1-2 → 1-3, vence o Time B; compra: quem venceu 5.290$, quem perdeu 5.020$.

O que cada regra diria:

- **A:** R21 (empate no topo) — maior salto da partida, 12%, acima do piso de 12%.
- **B:** R21 (empate no topo) — o maior salto vale 2,03x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** R21 (empate no topo) — sem virada (regra B): o maior salto vale 2,03x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_36 — de_mirage, 8-13 (21 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      0-2    #############.......  66%     8%  vence B
R3      0-3    ###############.....  74%     8%  vence B
R4      1-3    #############.......  67%     7%  vence A
R5      1-4    ###############.....  75%     8%  vence B
R6      1-5    ################....  82%     7%  vence B
R7      1-6    ##################..  88%     6%  vence B
R8      1-7    ###################.  93%     5%  vence B
R9      2-7    ##################..  89%     3%  vence A
R10     2-8    ###################.  94%     5%  vence B
R11     3-8    ##################..  91%     3%  vence A
R12     4-8    #################...  87%     4%  vence A
R13     5-8    ################....  81%     6%  vence A
R14     6-8    ###############.....  73%     8%  vence A
R15     7-8    ############........  62%    10%  vence A
R16     7-9    ###############.....  75%    12%  vence B
R17     7-10   #################...  86%    11%  vence B
R18     8-10   ###############.....  77%     8%  vence A
R19     8-11   ##################..  89%    12%  vence B
R20     8-12   ###################.  97%     8%  vence B
R21     8-13   #################### 100%     3%  vence B
```

Os três maiores saltos:

- **R16** (12%): 7-8 → 7-9, vence o Time B; compra: quem venceu 4.820$, quem perdeu 5.010$; bomba plantada.
- **R19** (12%): 8-10 → 8-11, vence o Time B; compra: quem venceu 1.970$, quem perdeu 5.880$; clutch de sh1ro contra 2; 3K de sh1ro; bomba plantada.
- **R17** (11%): 7-9 → 7-10, vence o Time B; compra: quem venceu 5.060$, quem perdeu 5.000$; bomba plantada.

O que cada regra diria:

- **A:** R16 (empate no topo) — maior salto da partida, 12%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,60x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** nenhum round — sem virada (regra B): nenhum round se destaca: o maior salto vale 1,60x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_37 — de_dust2, 16-14 (30 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      1-1    ##########..........  50%     8%  vence B
R3      2-1    ############........  58%     8%  vence A
R4      3-1    #############.......  67%     8%  vence A
R5      3-2    ############........  59%     8%  vence B
R6      4-2    ##############......  68%     9%  vence A
R7      5-2    ###############.....  76%     8%  vence A
R8      6-2    #################...  83%     7%  vence A
R9      6-3    ###############.....  77%     6%  vence B
R10     6-4    ##############......  70%     8%  vence B
R11     6-5    ############........  60%     9%  vence B
R12     6-6    ##########..........  50%    10%  vence B
R13     6-7    ########............  39%    11%  vence B
R14     7-7    ##########..........  50%    11%  vence A
R15     7-8    ########............  38%    12%  vence B
R16     7-9    #####...............  25%    12%  vence B
R17     7-10   ###.................  14%    11%  vence B
R18     8-10   #####...............  23%     8%  vence A
R19     9-10   #######.............  34%    12%  vence A
R20    10-10   ##########..........  50%    16%  vence A
R21    10-11   ######..............  31%    19%  vence B
R22    10-12   ##..................  12%    19%  vence B
R23    11-12   #####...............  25%    12%  vence A
R24    12-12   ##########..........  50%    25%  vence A
R25    13-12   #############.......  66%    16%  vence A
R26    13-13   ##########..........  50%    16%  vence B
R27    14-13   ##############......  69%    19%  vence A
R28    15-13   ##################..  88%    19%  vence A
R29    15-14   ###############.....  75%    12%  vence B
R30    16-14   #################### 100%    25%  vence A
```

Os três maiores saltos:

- **R24** (25%): 11-12 → 12-12, vence o Time A; compra: quem venceu 4.170$, quem perdeu 2.900$.
- **R30** (25%): 15-14 → 16-14, vence o Time A; compra: quem venceu 5.590$, quem perdeu 6.450$; bomba plantada.
- **R21** (19%): 10-10 → 10-11, vence o Time B; compra: quem venceu 5.370$, quem perdeu 6.310$; clutch de b1t contra 2; 3K de magixx.

O que cada regra diria:

- **A:** R24 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R24 (empate no topo) — o maior salto vale 2,22x o round típico da partida (exigido 1,68x).
- **C:** R24 — virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.
- **D:** R24 — houve virada (regra C): virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_40 — de_nuke, 16-14 (30 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      3-0    ###############.....  74%     8%  vence A
R4      4-0    ################....  81%     7%  vence A
R5      4-1    ###############.....  75%     6%  vence B
R6      4-2    ##############......  68%     7%  vence B
R7      4-3    ############........  59%     8%  vence B
R8      4-4    ##########..........  50%     9%  vence B
R9      4-5    ########............  40%    10%  vence B
R10     4-6    ######..............  30%    10%  vence B
R11     4-7    ####................  21%     9%  vence B
R12     5-7    ######..............  29%     8%  vence A
R13     6-7    ########............  39%    10%  vence A
R14     7-7    ##########..........  50%    11%  vence A
R15     7-8    ########............  38%    12%  vence B
R16     8-8    ##########..........  50%    12%  vence A
R17     8-9    #######.............  36%    14%  vence B
R18     8-10   #####...............  23%    14%  vence B
R19     8-11   ##..................  11%    12%  vence B
R20     9-11   ####................  19%     8%  vence A
R21    10-11   ######..............  31%    12%  vence A
R22    10-12   ##..................  12%    19%  vence B
R23    11-12   #####...............  25%    12%  vence A
R24    12-12   ##########..........  50%    25%  vence A
R25    12-13   #######.............  34%    16%  vence B
R26    13-13   ##########..........  50%    16%  vence A
R27    14-13   ##############......  69%    19%  vence A
R28    14-14   ##########..........  50%    19%  vence B
R29    15-14   ###############.....  75%    25%  vence A
R30    16-14   #################### 100%    25%  vence A
```

Os três maiores saltos:

- **R24** (25%): 11-12 → 12-12, vence o Time A; compra: quem venceu 5.800$, quem perdeu 3.450$.
- **R29** (25%): 14-14 → 15-14, vence o Time A; compra: quem venceu 5.060$, quem perdeu 6.620$; 3K de w0nderful; bomba plantada.
- **R30** (25%): 15-14 → 16-14, vence o Time A; compra: quem venceu 5.160$, quem perdeu 6.170$; bomba plantada.

O que cada regra diria:

- **A:** R24 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R24 (empate no topo) — o maior salto vale 2,17x o round típico da partida (exigido 1,68x).
- **C:** R26 — virada definitiva: o vencedor passou de 34% para 50% e não ficou mais abaixo de 50%.
- **D:** R26 — houve virada (regra C): virada definitiva: o vencedor passou de 34% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_41 — de_inferno, 16-14 (30 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      1-0    ############........  58%     8%  vence A
R2      2-0    #############.......  66%     8%  vence A
R3      3-0    ###############.....  74%     8%  vence A
R4      3-1    #############.......  67%     7%  vence B
R5      3-2    ############........  59%     8%  vence B
R6      3-3    ##########..........  50%     9%  vence B
R7      3-4    ########............  41%     9%  vence B
R8      3-5    ######..............  31%     9%  vence B
R9      4-5    ########............  40%     9%  vence A
R10     4-6    ######..............  30%    10%  vence B
R11     5-6    ########............  40%     9%  vence A
R12     5-7    ######..............  29%    10%  vence B
R13     5-8    ####................  19%    10%  vence B
R14     6-8    #####...............  27%     8%  vence A
R15     7-8    ########............  38%    10%  vence A
R16     8-8    ##########..........  50%    12%  vence A
R17     9-8    #############.......  64%    14%  vence A
R18     9-9    ##########..........  50%    14%  vence B
R19    10-9    #############.......  66%    16%  vence A
R20    10-10   ##########..........  50%    16%  vence B
R21    11-10   ##############......  69%    19%  vence A
R22    11-11   ##########..........  50%    19%  vence B
R23    12-11   ###############.....  75%    25%  vence A
R24    12-12   ##########..........  50%    25%  vence B
R25    13-12   #############.......  66%    16%  vence A
R26    14-12   ################....  81%    16%  vence A
R27    14-13   ##############......  69%    12%  vence B
R28    15-13   ##################..  88%    19%  vence A
R29    15-14   ###############.....  75%    12%  vence B
R30    16-14   #################### 100%    25%  vence A
```

Os três maiores saltos:

- **R23** (25%): 11-11 → 12-11, vence o Time A; compra: quem venceu 5.510$, quem perdeu 4.110$; clutch de xertioN contra 1; 3K de kyousuke; bomba plantada.
- **R24** (25%): 12-11 → 12-12, vence o Time B; compra: quem venceu 2.690$, quem perdeu 5.680$.
- **R30** (25%): 15-14 → 16-14, vence o Time A; compra: quem venceu 5.780$, quem perdeu 6.350$; bomba plantada.

O que cada regra diria:

- **A:** R23 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R23 (empate no topo) — o maior salto vale 2,20x o round típico da partida (exigido 1,68x).
- **C:** R16 — virada definitiva: o vencedor passou de 38% para 50% e não ficou mais abaixo de 50%.
- **D:** R16 — houve virada (regra C): virada definitiva: o vencedor passou de 38% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_42 — de_dust2, 17-19 (36 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      1-0    ########............  42%     8%  vence A
R2      2-0    #######.............  34%     8%  vence A
R3      3-0    #####...............  26%     8%  vence A
R4      4-0    ####................  19%     7%  vence A
R5      4-1    #####...............  25%     6%  vence B
R6      4-2    ######..............  32%     7%  vence B
R7      5-2    #####...............  24%     8%  vence A
R8      6-2    ###.................  17%     7%  vence A
R9      6-3    #####...............  23%     6%  vence B
R10     7-3    ###.................  15%     8%  vence A
R11     7-4    ####................  21%     6%  vence B
R12     7-5    ######..............  29%     8%  vence B
R13     8-5    ####................  19%    10%  vence A
R14     9-5    ##..................  11%     8%  vence A
R15     9-6    ###.................  17%     6%  vence B
R16     9-7    #####...............  25%     8%  vence B
R17     9-8    #######.............  36%    11%  vence B
R18    10-8    #####...............  23%    14%  vence A
R19    10-9    #######.............  34%    12%  vence B
R20    11-9    ####................  19%    16%  vence A
R21    11-10   ######..............  31%    12%  vence B
R22    12-10   ##..................  12%    19%  vence A
R23    12-11   #####...............  25%    12%  vence B
R24    12-12   ##########..........  50%    25%  vence B
R25    12-13   #############.......  66%    16%  vence B
R26    12-14   ################....  81%    16%  vence B
R27    13-14   ##############......  69%    12%  vence A
R28    13-15   ##################..  88%    19%  vence B
R29    14-15   ###############.....  75%    12%  vence A
R30    15-15   ##########..........  50%    25%  vence A
R31    15-16   #############.......  66%    16%  vence B
R32    15-17   ################....  81%    16%  vence B
R33    16-17   ##############......  69%    12%  vence A
R34    17-17   ##########..........  50%    19%  vence A
R35    17-18   ###############.....  75%    25%  vence B
R36    17-19   #################### 100%    25%  vence B
```

Os três maiores saltos:

- **R24** (25%): 12-11 → 12-12, vence o Time B; compra: quem venceu 5.170$, quem perdeu 4.140$; clutch de Jimpphat contra 1; 3K de Jimpphat; bomba plantada.
- **R30** (25%): 14-15 → 15-15, vence o Time A; compra: quem venceu 6.180$, quem perdeu 6.680$; 4K de m0NESY; bomba plantada.
- **R35** (25%): 17-17 → 17-18, vence o Time B; compra: quem venceu 5.550$, quem perdeu 6.070$; bomba plantada.

O que cada regra diria:

- **A:** R24 (empate no topo) — maior salto da partida, 25%, acima do piso de 12%.
- **B:** R24 (empate no topo) — o maior salto vale 2,06x o round típico da partida (exigido 1,68x).
- **C:** R24 — virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.
- **D:** R24 — houve virada (regra C): virada definitiva: o vencedor passou de 25% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_48 — de_dust2, 13-6 (19 rounds)

```
round  placar   chance do vencedor (Time A) depois do round   |ΔP|
R1      0-1    ########............  42%     8%  vence B
R2      1-1    ##########..........  50%     8%  vence A
R3      2-1    ############........  58%     8%  vence A
R4      3-1    #############.......  67%     8%  vence A
R5      3-2    ############........  59%     8%  vence B
R6      4-2    ##############......  68%     9%  vence A
R7      5-2    ###############.....  76%     8%  vence A
R8      6-2    #################...  83%     7%  vence A
R9      6-3    ###############.....  77%     6%  vence B
R10     6-4    ##############......  70%     8%  vence B
R11     7-4    ################....  79%     9%  vence A
R12     7-5    ##############......  71%     8%  vence B
R13     8-5    ################....  81%    10%  vence A
R14     9-5    ##################..  89%     8%  vence A
R15    10-5    ###################.  95%     6%  vence A
R16    11-5    ####################  98%     4%  vence A
R17    12-5    #################### 100%     2%  vence A
R18    12-6    ####################  99%     0%  vence B
R19    13-6    #################### 100%     1%  vence A
```

Os três maiores saltos:

- **R13** (10%): 7-5 → 8-5, vence o Time A; compra: quem venceu 920$, quem perdeu 930$. Frase do round: "Round de economia: o time entrou com 930$ de equipamento médio contra 920$ do adversário. Os dois entraram com equipamento parecido, então a economia não explica a derrota — o round foi decidido no confronto."
- **R11** (9%): 6-4 → 7-4, vence o Time A; compra: quem venceu 5.210$, quem perdeu 6.050$; 3K de flameZ; bomba plantada.
- **R6** (9%): 3-2 → 4-2, vence o Time A; compra: quem venceu 4.770$, quem perdeu 5.360$; bomba plantada.

O que cada regra diria:

- **A:** nenhum round — o maior salto (10%) não passa do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,21x o round típico da partida (exigido 1,68x).
- **C:** R2 — virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.
- **D:** R2 — houve virada (regra C): virada definitiva: o vencedor passou de 42% para 50% e não ficou mais abaixo de 50%.

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

### match_51 — de_nuke, 10-13 (23 rounds)

```
round  placar   chance do vencedor (Time B) depois do round   |ΔP|
R1      0-1    ############........  58%     8%  vence B
R2      1-1    ##########..........  50%     8%  vence A
R3      1-2    ############........  58%     8%  vence B
R4      1-3    #############.......  67%     8%  vence B
R5      1-4    ###############.....  75%     8%  vence B
R6      1-5    ################....  82%     7%  vence B
R7      1-6    ##################..  88%     6%  vence B
R8      1-7    ###################.  93%     5%  vence B
R9      2-7    ##################..  89%     3%  vence A
R10     2-8    ###################.  94%     5%  vence B
R11     3-8    ##################..  91%     3%  vence A
R12     4-8    #################...  87%     4%  vence A
R13     4-9    ###################.  93%     6%  vence B
R14     5-9    ##################..  89%     4%  vence A
R15     6-9    #################...  83%     6%  vence A
R16     7-9    ###############.....  75%     8%  vence A
R17     7-10   #################...  86%    11%  vence B
R18     8-10   ###############.....  77%     8%  vence A
R19     8-11   ##################..  89%    12%  vence B
R20     9-11   ################....  81%     8%  vence A
R21     9-12   ###################.  94%    12%  vence B
R22    10-12   ##################..  88%     6%  vence A
R23    10-13   #################### 100%    12%  vence B
```

Os três maiores saltos:

- **R21** (12%): 9-11 → 9-12, vence o Time B; compra: quem venceu 2.280$, quem perdeu 5.970$; bomba plantada.
- **R23** (12%): 10-12 → 10-13, vence o Time B; compra: quem venceu 2.560$, quem perdeu 5.880$; 3K de Jimpphat; bomba plantada.
- **R19** (12%): 8-10 → 8-11, vence o Time B; compra: quem venceu 4.700$, quem perdeu 6.170$.

O que cada regra diria:

- **A:** R21 (empate no topo) — maior salto da partida, 12%, acima do piso de 12%.
- **B:** nenhum round — nenhum round se destaca: o maior salto vale 1,60x o round típico da partida (exigido 1,68x).
- **C:** nenhum round — sem virada: o vencedor nunca esteve abaixo de 50% de chance.
- **D:** nenhum round — sem virada (regra B): nenhum round se destaca: o maior salto vale 1,60x o round típico da partida (exigido 1,68x).

**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**

Sua resposta: ____

<!-- decisivo:fim -->
