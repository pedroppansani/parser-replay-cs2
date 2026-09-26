# Material de calibração

Gerado por `py -3.12 -m scripts.material_calibracao`. Cada seção termina com a pergunta que só você responde; as respostas viram constante com data e tamanho de corpus no CLAUDE.md.

## 1. Pisos de função

Gerado por `py -3.12 -m scripts.proposta_pisos`. O rótulo exige **liderar o próprio time** na métrica E passar do piso; o piso barra o líder que não é destacado. Para cada função: a distribuição completa (todos os jogador-partidas e só os líderes), três métodos objetivos -- **maior vazio** entre valores consecutivos, **Otsu** (menor variância dentro das duas classes) e **vale da densidade** (KDE) --, o veredito de concordância e os líderes mais próximos de cada corte. Métodos que concordam = corte real; métodos que discordam = a métrica é um contínuo e o piso é convenção. Os pisos continuam ABSOLUTOS. O que é seu: olhar a fronteira e dizer se aquele jogador jogou a função naquela partida.

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

### Lurker — `off_team_relativo`, piso atual 1.500

429 jogador-partidas profissionais em 43 partidas; 102 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.226      92 ##############################################   <- vazio (todos)
     0.226-0.452      19 ##########
     0.452-0.678      34 #################   <- vale (todos)
     0.678-0.905      19 ##########
     0.905-1.131      27 ##############
     1.131-1.357      44 ######################   <- otsu (todos)
     1.357-1.583      29 ##############   <- atual
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
     1.131-1.357       0    <- vazio (líderes), otsu (líderes)
     1.357-1.583       4 #########   <- atual
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
| atual | 1.500 | 67 de 102 |
| vazio (todos) | 0.142 | 82 de 102 |
| otsu (todos) | 1.261 | 68 de 102 |
| vale (todos) | 0.550 | 78 de 102 |
| vazio (líderes) | 1.284 | 68 de 102 |
| otsu (líderes) | 1.284 | 68 de 102 |
| vale (líderes) | 1.028 | 69 de 102 |

- todos: espalhamento 0.72 amplitude interquartil (1.547) -> **discordam**
- líderes: espalhamento 0.14 amplitude interquartil (1.864) -> **CONCORDAM**, mediana 1.284

**Veredito: corte real em 1.284** (métodos concordam entre líderes). Piso atual 1.500: 67 líderes com rótulo; sugerido: 68.

**Fronteira do corte atual (1.500)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | off_team_relativo |
|---|---|---|---|---|---|
| rótulo | b1t | Natus Vincere | match_10 | dust2 | 1.656 |
| rótulo | makazze | Natus Vincere | match_15 | mirage | 1.612 |
| rótulo | apEX | Team Vitality | match_33 | dust2 | 1.580 |
| rótulo | kyousuke | Falcons | match_20 | mirage | 1.528 |
| rótulo | xertioN | MOUZ | match_50 | inferno | 1.520 |
| — corte 1.500 — | | | | | |
| sem rótulo | Jimpphat | MOUZ | match_41 | inferno | 1.494 |
| sem rótulo | YEKINDAR | FURIA | match_44 | inferno | 1.074 |
| sem rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.983 |
| sem rótulo | Jimpphat | MOUZ | match_51 | nuke | 0.920 |
| sem rótulo | kyxsan | Team Falcons | match_51 | nuke | 0.919 |

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

Gerado por `py -3.12 -m scripts.proposta_grupos`. O KMeans não nomeia (decisão 8): abaixo está o que DEFINE cada grupo e, para cada um, três nomes que se justificam pelos números mostrados. Você escolhe, ajusta ou recusa; o nome vai para `clustering/cluster_names.json`.

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

2268 arremessos em 6 partidas. Os grupos saem por moda (decisão 5); os rótulos foram aplicados PELA ORDEM (mais lento = curto) e estão marcados "(a confirmar)" no código até você responder.

| Grupo | Centro | Arremessos | Exemplo |
|---|---|---|---|
| longo (a confirmar) | 675 u/s | 2066 | iM, flash, match_38 round 20 (0:26), agachado, parado |
| médio (a confirmar) | 443 u/s | 100 | YEKINDAR, he, match_43 round 20 (1:15), em pé, parado |
| curto (a confirmar) | 198 u/s | 102 | SH1R0, he, match_38 round 7 (0:24), agachado, parado |

```
   0-50   u/s |                                                       1  curto (a confirmar)
  50-100  u/s |                                                       1  curto (a confirmar)
 100-150  u/s |                                                       4  curto (a confirmar)
 150-200  u/s | #                                                    43  curto (a confirmar)
 200-250  u/s | #                                                    51  curto (a confirmar)
 250-300  u/s |                                                       1  curto (a confirmar)
 300-350  u/s |                                                       1  médio (a confirmar)
 350-400  u/s |                                                       0  médio (a confirmar)
 400-450  u/s | ##                                                   83  médio (a confirmar)
 450-500  u/s |                                                      14  médio (a confirmar)
 500-550  u/s |                                                       3  médio (a confirmar)
 550-600  u/s |                                                       4  longo (a confirmar)
 600-650  u/s | #                                                    49  longo (a confirmar)
 650-700  u/s | ################################################## 1920  longo (a confirmar)
 700-750  u/s | ##                                                   84  longo (a confirmar)
 750-800  u/s |                                                       8  longo (a confirmar)
 800-850  u/s |                                                       1  longo (a confirmar)
```

**Sua resposta:** curto/médio/longo pela ordem está certo? ____

## 4. Teste do comando de console

Arremesso: **jL**, smoke, **match_38** (de_mirage) round 2, 0:33 do round (tick 9288). Ancoragem com resíduo de 0.02u, em pé, parado.

1. Servidor local no mapa, com:

```
sv_cheats 1; mp_warmup_end; mp_freezetime 0; sv_infinite_ammo 1; sv_grenade_trajectory_prac_pipreview 1
```

2. Com a smoke na mão, sem se mover:

```
setpos -722.82 -2186.60 -179.97; setang -2.27 86.24 0
```

3. Solte com o **botão esquerdo** (arremesso cheio), em pé, parado.

**Certo:** a smoke para em (-655, -1159, -166). O preview da trajetória mostra o ponto antes de você soltar.

**Se errar, me mande:** a saída do `getpos` logo depois do `setpos`; onde a smoke caiu (nome do lugar); e se o erro foi de DISTÂNCIA (curta ou longa demais -> altura ou pitch) ou de LADO (esquerda ou direita -> yaw).

**Sua resposta:** funcionou? ____

## 5. Ângulos de entrada da Nuke, do menos sustentado para o mais

38 ângulos distintos, juntando os 70 que o pipeline deriva partida a partida nas 9 Nuke do corpus (mesmo ângulo em partidas diferentes = mesma região, mesmo lado, yaw a menos de 20°). **19 aparecem numa partida só** -- podem ser hábito de um time naquele dia, não ângulo do mapa. A Nuke é o mapa de partição menos confiável do projeto (os dois sites empilhados na vertical), então é aqui que o julgamento humano mais vale.

Yaw na convenção do CS2: 0° para a direita do radar, 90° para cima, crescendo no sentido anti-horário. O que você confirmar ou corrigir vira `MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`, que tem prioridade sobre o derivado.

| # | região | lado | yaw | direção no radar | partidas | kills | sua resposta |
|---|---|---|---|---|---|---|---|
| 1 | BombsiteA | CT | 90° | cima | 1 | 4 | ____ |
| 2 | BombsiteA | T | 77° | cima | 1 | 4 | ____ |
| 3 | BombsiteB | CT | -100° | baixo | 1 | 4 | ____ |
| 4 | BombsiteB | T | -99° | baixo | 1 | 4 | ____ |
| 5 | Catwalk | CT | -103° | baixo | 1 | 4 | ____ |
| 6 | Garage | CT | 177° | esquerda | 1 | 4 | ____ |
| 7 | Heaven | CT | -118° | esquerda-baixo | 1 | 4 | ____ |
| 8 | Lobby | T | -24° | direita-baixo | 1 | 4 | ____ |
| 9 | LockerRoom | CT | -87° | baixo | 1 | 4 | ____ |
| 10 | Outside | CT | 169° | esquerda | 1 | 4 | ____ |
| 11 | Outside | CT | -163° | esquerda | 1 | 4 | ____ |
| 12 | Rafters | CT | -132° | esquerda-baixo | 1 | 4 | ____ |
| 13 | Ramp | CT | -117° | esquerda-baixo | 1 | 4 | ____ |
| 14 | Ramp | T | -72° | baixo | 1 | 4 | ____ |
| 15 | Tunnels | CT | 98° | cima | 1 | 4 | ____ |
| 16 | Vending | CT | -99° | baixo | 1 | 4 | ____ |
| 17 | BombsiteA | T | 147° | esquerda-cima | 1 | 5 | ____ |
| 18 | Tunnels | T | 82° | cima | 1 | 5 | ____ |
| 19 | Mini | CT | 94° | cima | 1 | 6 | ____ |
| 20 | BombsiteA | T | -83° | baixo | 2 | 8 | ____ |
| 21 | BombsiteB | T | 38° | direita-cima | 2 | 8 | ____ |
| 22 | BombsiteB | T | 100° | cima | 2 | 9 | ____ |
| 23 | BombsiteA | CT | 168° | esquerda | 2 | 10 | ____ |
| 24 | BombsiteA | T | 55° | direita-cima | 2 | 11 | ____ |
| 25 | Control | T | -6° | direita | 2 | 11 | ____ |
| 26 | Ramp | CT | -69° | baixo | 2 | 11 | ____ |
| 27 | BombsiteA | CT | -59° | direita-baixo | 2 | 12 | ____ |
| 28 | BombsiteA | CT | -98° | baixo | 2 | 13 | ____ |
| 29 | Outside | CT | -134° | esquerda-baixo | 2 | 13 | ____ |
| 30 | Outside | T | 90° | cima | 2 | 13 | ____ |
| 31 | Ramp | CT | 161° | esquerda | 2 | 13 | ____ |
| 32 | Ramp | CT | -139° | esquerda-baixo | 3 | 12 | ____ |
| 33 | Ramp | CT | -91° | baixo | 3 | 15 | ____ |
| 34 | Outside | T | 68° | cima | 3 | 16 | ____ |
| 35 | BombsiteB | CT | 96° | cima | 4 | 17 | ____ |
| 36 | Admin | CT | 178° | esquerda | 4 | 18 | ____ |
| 37 | Outside | T | 16° | direita | 4 | 18 | ____ |
| 38 | BombsiteA | CT | -135° | esquerda-baixo | 6 | 32 | ____ |

**Sua resposta:** para cada linha, *confirma*, *descarta* (não é ângulo de verdade) ou *corrige* o yaw.
