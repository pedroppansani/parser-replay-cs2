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

## 7. Erros na aba Perfil

Gerado por `py -3.12 -m scripts.calibracao.erros_do_jogador` (fase 12, decisão 46; definições da fase 18). Os tipos de erro de `metrics/erros.py` sobre as 52 partidas do corpus. Nenhum tipo aparece no site até você confirmar os exemplos: `TIPOS_DE_ERRO_VALIDADOS` começa vazia. Para ver a aba com todos os tipos marcados "em validação": `py -3.12 -m scripts.build_site --mostrar-erros-nao-validados` (gera em `preview/`, fora do git e nunca publicado).

### 7.0 Ocorrências por tipo no corpus

| tipo | candidatos | depois dos filtros | explícito | depende da tática | saiu pelos filtros (motivo: n) |
|---|---|---|---|---|---|
| Não trocou o aliado | 13464 | 66 | 66 | 0 | o matador não ficou visível para ele: 7415; round de economia do time: 2374; round decidido: 969; em duelo próprio: 644; time guardando arma (pós-plant perdido): 560; o matador ficou visível menos de 0,5 s: 500; cego no momento: 428; engajou o matador: 324; sem arma de fogo: 160; depois do fim do round: 24 |
| Possível bait | 13464 | 9 | 9 | 0 | o matador não ficou visível para ele: 7415; round de economia do time: 2374; round decidido: 969; em duelo próprio: 644; time guardando arma (pós-plant perdido): 560; o matador ficou visível menos de 0,5 s: 500; cego no momento: 428; engajou o matador: 324; sem arma de fogo: 160; recuou menos de 64 unidades: 57; depois do fim do round: 24 |
| Perdeu a troca | 2937 | 285 | 285 | 0 | round de economia do time: 851; não engajou o matador: 794; morte trocada: 367; round decidido: 350; time guardando arma (pós-plant perdido): 205; enfrentou dois ou mais ao mesmo tempo: 83; depois do fim do round: 2 |
| Morreu sozinho | 5985 | 1708 | 0 | 1708 | um aliado tinha o matador à vista ou estava perto: 1658; round de economia do time: 1159; time guardando arma (pós-plant perdido): 660; round decidido: 604; sem aliado vivo (1 contra N): 178; depois do fim do round: 18 |
| Primeira morte sem troca | 859 | 691 | 0 | 691 | round de economia do time: 164; time guardando arma (pós-plant perdido): 4 |
| Flash no time | 3091 | 485 | 485 | 0 | abaixo do limiar da partida: 2188; round de economia do time: 207; round decidido: 141; time guardando arma (pós-plant perdido): 54; depois do fim do round: 16 |
| Dano de utilidade no time | 195 | 26 | 26 | 0 | abaixo do limiar da partida: 121; evento sem dano ou sem cegueira: 24; round decidido: 14; round de economia do time: 7; depois do fim do round: 3 |
| Utilidade no bolso | não criado | — | — | — | o inventário na hora da morte não existe no dado (decisão 46) |

**Calibração da fase 18b (decisões do Pedro).** (1) Quem engajou o matador (atirou nele, deu dano ou andou na direção dele com ele visível) conta só em "perdeu a troca" (se morreu); "não trocou" fica para quem viu o matador e não engajou. (2) Bait exige recuo líquido de pelo menos `MIN_RECUO_BAIT` = 64 u (do primeiro tick em que ele vê o matador até o fim da janela, com o matador parado onde estava nesse tick); sair da linha de visão com menos que isso não é bait (o `RECUO_MINIMO` 120 da fase 18 saiu). (3) O matador visível precisa de pelo menos `MIN_TEMPO_VISIVEL` = 0,5 s, somados os ticks visíveis da janela, em "não trocou", no bait e no aliado que tira "morreu sozinho"; nos dois ou mais inimigos de "perdeu a troca", qualquer tick visível conta.

**Mudança da fase 18 (definições do Pedro).** (1) A troca é decidida pelo FATO (o matador morreu por um aliado dentro da janela), nunca pela distância, e toda morte trocada sai de todos os tipos (cada morte do corpus grava se foi trocada e por quem, em `mortes.parquet`). (2) Round decidido fica fora de todos os tipos: a chance de o time vencer o round logo antes do evento acima de 0,95 ou abaixo de 0,05. (3) "Não trocou" exige o matador VISÍVEL para o jogador na janela; "possível bait" é o subconjunto em que ele não engajou (não atirou nele nem deu dano) e recuou mais que `RECUO_MINIMO` ou saiu da linha de visão andando (o critério "atrás do aliado" saiu). (4) "Perdeu a troca" exige ter ido trocar (atirou, deu dano ou andou na direção do matador com ele visível) e sai com dois ou mais inimigos visíveis ao mesmo tempo. (5) "Morreu isolado" virou "morreu sozinho": nenhum aliado vivo com o matador à vista na janela nem a até `DIST_TROCA`. (6) A situação conta os vivos pelas mortes: antes vinha das posições gravadas só nos ticks das kills, e uma flash ou granada antes da primeira morte do round saía "0 contra 0". (7) Um evento com 0 de dano ou de cegueira não é ocorrência (o 0 vem do próprio jogo: o `player_hurt` do aliado na borda da explosão). "Candidatos" agora inclui os casos registrados com o motivo de ficar de fora (por exemplo, todo aliado vivo de quem morreu sem troca em "não trocou").

**Mudança da fase 15 (decisão 46).** "Flash no time" e "dano de utilidade no time" eram somas da partida (CT e TR juntos); passam a ser POR LADO, com o mesmo limiar (`SEG_CEGUEIRA_ALIADO` 27 s e `DANO_UTILIDADE_ALIADO` 20) aplicado a cada lado.

#### Antes (fase 18) -> depois (fase 18b)

"Antes" são as ocorrências da fase 18 (commit `b3efc9da`), "depois" as de agora. Uma ocorrência antiga "segue" se a mesma (partida, round, tick, jogador e, nos tipos de troca, o aliado) ainda passa nos filtros; se não, saiu com o motivo do filtro novo. "Entraram" são as novas que não existiam. "Situação corrigida": das que seguem, quantas mudaram de "N contra M".

| tipo | antes | depois | seguem | saíram | por qual motivo (n) | entraram | situação corrigida |
|---|---|---|---|---|---|---|---|
| Não trocou o aliado | 890 | 66 | 66 | 824 | o matador ficou visível menos de 0,5 s: 500; engajou o matador: 324 | 0 | 0 |
| Possível bait | 229 | 9 | 7 | 222 | o matador ficou visível menos de 0,5 s: 167; recuou menos de 64 unidades: 30; engajou o matador: 25 | 2 | 0 |
| Perdeu a troca | 282 | 285 | 282 | 0 | — | 3 | 0 |
| Morreu sozinho | 1537 | 1708 | 1537 | 0 | — | 171 | 0 |
| Primeira morte sem troca | 691 | 691 | 691 | 0 | — | 0 | 0 |
| Flash no time | 485 | 485 | 485 | 0 | — | 0 | 0 |
| Dano de utilidade no time | 26 | 26 | 26 | 0 | — | 0 | 0 |

#### Os números da calibração da fase 18b

- "Possível bait" que sobram: 9; recuo líquido deles: mediana 81 u, quartis 76 e 144 u (mínimo 65, máximo 370).
- "Não trocou" que sobram: 66.
- Casos que saíram SÓ pelo tempo mínimo de visão (as ocorrências com o mínimo valendo qualquer amostra visível menos as de agora, com as outras regras iguais): Não trocou o aliado 224; Possível bait 20; Perdeu a troca 0; Morreu sozinho -171; Primeira morte sem troca 0; Flash no time 0; Dano de utilidade no time 0.
  Em "morreu sozinho" o número é negativo: com o mínimo, um aliado que viu o matador por menos de 0,5 s não tira mais o caso, e a morte volta a ser "morreu sozinho".

#### Enfrentou dois ou mais ao mesmo tempo (informação, não é erro)

Foi trocar (engajou o matador), morreu sem matá-lo e tinha dois ou mais inimigos visíveis ao mesmo tempo na janela: 83 casos que saíram de "perdeu a troca" por esse motivo (240 contando os que já tinham saído antes por outro filtro, como o round decidido). Não é tipo de erro e não aparece no Perfil.

Ordem dos níveis (a primeira regra que se aplica decide): 1) round de eco ou pistola do time, time guardando arma (evento depois do plant num round que o time perdeu), depois do fim do round ou round decidido: fora; 2) morreu sozinho sendo lurker: depende; 3) primeira morte sem troca sendo entry: depende; 4) morreu sozinho ou primeira morte do AWPer no duelo de abertura: depende; 5) função só tendência: o motivo diz que a função não é firme; 6) não trocou, possível bait, perdeu a troca, flash no time e dano de utilidade no time: explícito (os dois primeiros só existem com o matador visível); 7) o resto: depende. Por isso "morreu sozinho" e "primeira morte sem troca" saem sempre como "depende da tática" (só o motivo muda).

### 7.1 As constantes

Valor proposto, origem, histograma no corpus e quantas ocorrências (depois dos filtros) cada tipo teria no valor mais baixo e no mais alto da faixa. As outras constantes ficam no valor proposto em cada varredura. As da fase 18 são `MEIO_FOV_GRAUS`, `LIMIAR_ROUND_GANHO`/`LIMIAR_ROUND_PERDIDO` e `CONE_DO_TIRO_GRAUS`; as da calibração da fase 18b, `MIN_RECUO_BAIT` (no lugar do `RECUO_MINIMO`) e `MIN_TEMPO_VISIVEL`.

#### `DIST_TROCA` = 600 unidades

Origem: o raio de apoio do projeto (RAIO_COMPANHEIRO = 600 do perfil e das funções: "o alcance em que uma troca ainda acontece"). Fase 18: só entra em "morreu sozinho" (um aliado a até isto não deixa a morte ser "sozinho"); nos outros tipos a distância é contexto. O histograma é a distância de cada aliado vivo a quem morreu, na hora da morte, no mesmo andar.

Mediana 976,24, p75 1605,72, p90 2296,45, p95 2697,48, p99 3368,48.

```
        0-100        446 #######
      100-200       1050 #################
      200-300       1028 #################
      300-400       1051 #################
      400-500        996 ################
      500-600        977 ################
      600-700        950 ################   <- proposto
      700-800        969 ################
      800-1000      1784 ##############################
     1000-1200      1566 ##########################
     1200-1500      2081 ##################################
     1500-2000      2415 ########################################
     2000-3000      2231 #####################################
  >= 3000            496 ########
  (18040 valores, em unidades)
```

| tipo | DIST_TROCA = 400 | proposto (600) | DIST_TROCA = 800 |
|---|---|---|---|
| Não trocou o aliado | 66 | 66 | 66 |
| Possível bait | 9 | 9 | 9 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 2135 | 1708 | 1318 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `S_DUELO` = 2 s

Origem: tempo de um duelo de rifle (reação de ~0,25 s mais 0,3 a 1 s para matar), com folga. O histograma é, para cada aliado vivo de quem morreu, o tempo desde o último dano que ele deu ou levou de um inimigo antes da morte.

Mediana 8,23, p75 26,47, p90 49,92, p95 65,31, p99 86,33.

```
        0-0.5        785 ###########
      0.5-1          383 #####
        1-1.5        325 ####
      1.5-2          308 ####
        2-2.5        287 ####   <- proposto
      2.5-3          233 ###
        3-4          429 ######
        4-5          362 #####
        5-7          550 #######
        7-10         616 ########
       10-15         660 #########
  >= 15             2971 ########################################
  (7909 valores, em s)
```

| tipo | S_DUELO = 1 | proposto (2) | S_DUELO = 4 |
|---|---|---|---|
| Não trocou o aliado | 69 | 66 | 61 |
| Possível bait | 10 | 9 | 7 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `SEG_CEGUEIRA_ALIADO` = 27 s

Origem: o percentil 90 da soma de cegueira imposta ao próprio time por jogador-partida no corpus (fase 12). O histograma é a soma por jogador-LADO (a regra desde a fase 15).

Mediana 3,34, p75 8,19, p90 15,01, p95 20,76, p99 30,77.

```
        0-0.01       248 ########################################
     0.01-2          195 ###############################
        2-4          122 ####################
        4-6          123 ####################
        6-8           84 ##############
        8-10          80 #############
       10-12          40 ######
       12-15          42 #######
       15-20          43 #######
       20-30          49 ########   <- proposto
  >= 30               14 ##
  (1040 valores, em s)
```

| tipo | SEG_CEGUEIRA_ALIADO = 5 | proposto (27) | SEG_CEGUEIRA_ALIADO = 20 |
|---|---|---|---|
| Não trocou o aliado | 66 | 66 | 66 |
| Possível bait | 9 | 9 | 9 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 1979 | 485 | 728 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `SEG_CEGUEIRA_ALIADO_UMA` = 4,8 s

Origem: o percentil 90 da cegueira nos aliados por flash no corpus (uma flash cheia cega de 2 a 5 s; perto do topo é a flash que estourou na cara do aliado). O histograma é a cegueira nos aliados por flash.

Mediana 1,66, p75 3,19, p90 4,77, p95 5,84, p99 8,55.

```
        0-0.5        294 ##################
      0.5-1          668 ########################################
        1-1.5        292 #################
      1.5-2          329 ####################
        2-2.5        165 ##########
      2.5-3          168 ##########
        3-3.5        173 ##########
      3.5-4          122 #######
        4-5          227 ##############   <- proposto
  >= 5               235 ##############
  (2673 valores, em s)
```

| tipo | SEG_CEGUEIRA_ALIADO_UMA = 2 | proposto (4,8) | SEG_CEGUEIRA_ALIADO_UMA = 4 |
|---|---|---|---|
| Não trocou o aliado | 66 | 66 | 66 |
| Possível bait | 9 | 9 | 9 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 1198 | 485 | 659 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `DANO_UTILIDADE_ALIADO` = 20 de dano

Origem: o percentil 95 do dano de HE e molotov no próprio time por jogador-partida no corpus (fase 12). O histograma é a soma por jogador-lado.

Mediana 0,00, p75 0,00, p90 2,00, p95 9,00, p99 26,00.

```
        0-0.01       909 ########################################
     0.01-10          83 ####
       10-25          35 ##   <- proposto
       25-40           9 
       40-50           4 
       50-60           0 
       60-80           0 
       80-100          0 
      100-150          0 
  >= 150               0 
  (1040 valores, em de dano)
```

| tipo | DANO_UTILIDADE_ALIADO = 25 | proposto (20) | DANO_UTILIDADE_ALIADO = 100 |
|---|---|---|---|
| Não trocou o aliado | 66 | 66 | 66 |
| Possível bait | 9 | 9 | 9 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 15 | 26 | 0 |

#### `MIN_RECUO_BAIT` = 64 unidades

Origem: a decisão do Pedro na fase 18b (64 u: o passo de lado do jiggle não é bait). O recuo é o deslocamento LÍQUIDO do jogador para longe do matador (parado onde estava na primeira amostra visível), da primeira amostra visível até o fim da janela. Substitui o `RECUO_MINIMO` 120 da fase 18 (o máximo, e o bait também por "saiu da linha de visão"). O mesmo valor, ao contrário, é o "andou na direção dele" de "perdeu a troca". O histograma é o recuo em "não trocou".

Mediana -2,60, p75 18,60, p90 70,20, p95 95,30, p99 179,80.

```
     -500--128         0 
     -128--64          0 
      -64--32         13 #######################
      -32-0           23 ########################################
        0-32          15 ##########################
       32-64           6 ##########
       64-96           6 ##########   <- proposto
       96-128          0 
      128-200          2 ###
      200-300          0 
      300-500          1 ##
  >= 500               0 
  (66 valores, em unidades)
```

| tipo | MIN_RECUO_BAIT = 32 | proposto (64) | MIN_RECUO_BAIT = 128 |
|---|---|---|---|
| Não trocou o aliado | 66 | 66 | 66 |
| Possível bait | 15 | 9 | 3 |
| Perdeu a troca | 291 | 285 | 280 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `MIN_TEMPO_VISIVEL` = 0,5 s

Origem: a decisão do Pedro na fase 18b (0,5 s), SOMANDO as amostras visíveis da janela (não precisa ser contínuo: o peek repetido também dá chance de troca). Vale para o matador visível em "não trocou" e no bait e para o aliado que tira "morreu sozinho"; não vale para os dois ou mais inimigos de "perdeu a troca". O histograma é o tempo visível em "não trocou" (os que passaram e os que saíram só por isso).

Mediana 0,25, p75 0,38, p90 0,50, p95 0,77, p99 1,75.

```
        0-0.125      160 ########################################
    0.125-0.25        67 #################
     0.25-0.375      153 ######################################
    0.375-0.5        120 ##############################
      0.5-0.75        31 ########   <- proposto
     0.75-1           13 ###
        1-1.5         13 ###
      1.5-2            6 ##
        2-3            0 
        3-5            3 #
  >= 5                 0 
  (566 valores, em s)
```

| tipo | MIN_TEMPO_VISIVEL = 0,25 | proposto (0,5) | MIN_TEMPO_VISIVEL = 1 |
|---|---|---|---|
| Não trocou o aliado | 160 | 66 | 22 |
| Possível bait | 17 | 9 | 3 |
| Perdeu a troca | 285 | 285 | 285 |
| Morreu sozinho | 1619 | 1708 | 1793 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `MEIO_FOV_GRAUS` = 53,13 graus

Origem: a metade do campo de visão horizontal do CS2 em 16:9: 90 graus numa tela 4:3, alargados na tela larga mantendo a vertical (Hor+), dão 106,26 graus (tan(h/2) = 4/3). 45 é quem joga em 4:3. O histograma é, para cada aliado vivo de quem morreu, o menor ângulo entre o olhar dele e o matador nas amostras da janela com a linha de visão livre.

Mediana 0,43, p75 1,67, p90 10,33, p95 37,10, p99 123,79.

```
        0-5         3612 ########################################
        5-10         190 ##
       10-20         130 #
       20-30          58 #
       30-40          36 
       40-45          17 
       45-50          13 
       50-53.13        6 
    53.13-55           7    <- proposto
       55-60          11 
       60-75          36 
       75-90          26 
       90-120         39 
      120-180         51 #
  >= 180               0 
  (4232 valores, em graus)
```

| tipo | MEIO_FOV_GRAUS = 45 | proposto (53,13) | MEIO_FOV_GRAUS = 60 |
|---|---|---|---|
| Não trocou o aliado | 65 | 66 | 70 |
| Possível bait | 9 | 9 | 9 |
| Perdeu a troca | 286 | 285 | 285 |
| Morreu sozinho | 1709 | 1708 | 1707 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `LIMIAR_ROUND_GANHO / LIMIAR_ROUND_PERDIDO` = 0,95 / 0,05

Origem: os valores propostos pelo Pedro na fase 18 (0,95 e 0,05), simétricos: a chance já de 19 contra 1. O histograma é a chance de o time do jogador vencer o round logo antes da morte do aliado, em "não trocou" (o modelo de round do rating). Na varredura, os dois limiares andam juntos (0,90 e 0,10; 0,98 e 0,02).

Mediana 0,97, p75 0,99, p90 1,00, p95 1,00, p99 1,00.

```
        0-0.02        16 #
     0.02-0.05       101 #########
     0.05-0.1          2 
      0.1-0.2          6 #
      0.2-0.3          2 
      0.3-0.4          6 #
      0.4-0.5         10 #
      0.5-0.6         10 #
      0.6-0.7          8 #
      0.7-0.8         11 #
      0.8-0.9          8 #
      0.9-0.95         3 
     0.95-0.98       428 ########################################   <- proposto
  >= 0.98            424 ########################################
  (1035 valores, em chance de vitória do round)
```

| tipo | LIMIAR_ROUND_GANHO / LIMIAR_ROUND_PERDIDO = 0,9 | proposto (0,95) | LIMIAR_ROUND_GANHO / LIMIAR_ROUND_PERDIDO = 0,98 |
|---|---|---|---|
| Não trocou o aliado | 61 | 66 | 69 |
| Possível bait | 8 | 9 | 9 |
| Perdeu a troca | 243 | 285 | 330 |
| Morreu sozinho | 1503 | 1708 | 1845 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 418 | 485 | 505 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `CONE_DO_TIRO_GRAUS` = 6 graus

Origem: o percentil 99 do ângulo horizontal entre a mira e a vítima nos tiros que ACERTARAM um inimigo no corpus, arredondado para cima: um tiro que erra perto do alvo ainda é um tiro nele. O histograma é esse ângulo.

Mediana 0,52, p75 1,05, p90 1,92, p95 2,75, p99 5,66.

```
        0-0.5      11422 ########################################
      0.5-1         5817 ####################
        1-1.5       2644 #########
      1.5-2         1427 #####
        2-3         1212 ####
        3-4          439 ##
        4-5          216 #
        5-6          126 
        6-8           81    <- proposto
        8-10          38 
       10-15          36 
  >= 15               44 
  (23502 valores, em graus)
```

| tipo | CONE_DO_TIRO_GRAUS = 3 | proposto (6) | CONE_DO_TIRO_GRAUS = 10 |
|---|---|---|---|
| Não trocou o aliado | 70 | 66 | 61 |
| Possível bait | 10 | 9 | 9 |
| Perdeu a troca | 271 | 285 | 293 |
| Morreu sozinho | 1708 | 1708 | 1708 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 485 | 485 | 485 |
| Dano de utilidade no time | 26 | 26 | 26 |

#### `MIN_GRANADAS_NO_BOLSO`: não criada

O tipo "Utilidade no bolso" exige o inventário na hora da morte. O parser lê o inventário só no fim do freeze time (`PROPS_DA_COMPRA` em `parsing/parser.py`, a tabela `compra`); na hora da morte não há o que ler. Pela regra do pedido, o tipo não foi criado e nada foi estimado (decisão 46).

### 7.1b Quantos pontos a melhorar cada jogador teria

Uma ocorrência só vira "ponto a melhorar" quando a contagem do jogador num lado fica ACIMA do percentil 90 da referência (os jogador-lados do corpus com a mesma função no mesmo lado; com menos de 20 deles, todos os jogador-lados daquele lado) e tem pelo menos 2 ocorrências. Um jogador-lado é um jogador numa partida, num dos lados (1040 no corpus). A tela mostra no máximo 3 por jogador; as contagens abaixo são as brutas, sem esse corte.

#### Distribuição da contagem por jogador-lado, por tipo e lado

| tipo | lado | jogador-lados | média | mediana | p75 | p90 | máximo | com 0 |
|---|---|---|---|---|---|---|---|---|
| Não trocou o aliado | CT | 520 | 0,05 | 0,0 | 0,0 | 0,0 | 2 | 95% |
| Não trocou o aliado | TR | 520 | 0,07 | 0,0 | 0,0 | 0,0 | 3 | 94% |
| Possível bait | CT | 520 | 0,00 | 0,0 | 0,0 | 0,0 | 1 | 100% |
| Possível bait | TR | 520 | 0,01 | 0,0 | 0,0 | 0,0 | 1 | 99% |
| Perdeu a troca | CT | 520 | 0,19 | 0,0 | 0,0 | 1,0 | 4 | 83% |
| Perdeu a troca | TR | 520 | 0,36 | 0,0 | 1,0 | 1,0 | 3 | 72% |
| Morreu sozinho | CT | 520 | 2,00 | 2,0 | 3,0 | 4,0 | 7 | 15% |
| Morreu sozinho | TR | 520 | 1,28 | 1,0 | 2,0 | 3,0 | 6 | 29% |
| Primeira morte sem troca | CT | 520 | 0,54 | 0,0 | 1,0 | 2,0 | 4 | 59% |
| Primeira morte sem troca | TR | 520 | 0,78 | 1,0 | 1,0 | 2,0 | 6 | 50% |
| Flash no time | CT | 520 | 0,29 | 0,0 | 0,0 | 1,0 | 15 | 87% |
| Flash no time | TR | 520 | 0,64 | 0,0 | 0,0 | 1,0 | 21 | 77% |
| Dano de utilidade no time | CT | 520 | 0,03 | 0,0 | 0,0 | 0,0 | 2 | 98% |
| Dano de utilidade no time | TR | 520 | 0,02 | 0,0 | 0,0 | 0,0 | 2 | 98% |

#### Pontos a melhorar por jogador-partida, por percentil

| percentil | jogador-partidas | com pelo menos 1 | % | média | com 0 | com 1 | com 2 | com 3 ou mais |
|---|---|---|---|---|---|---|---|---|
| 50 | 520 | 378 | 73% | 1,24 | 142 | 191 | 126 | 61 |
| 75 | 520 | 282 | 54% | 0,78 | 238 | 183 | 80 | 19 |
| 90 (em uso) | 520 | 171 | 33% | 0,41 | 349 | 135 | 29 | 7 |

Pares (tipo, lado) que viram ponto a melhorar, por tipo:

| tipo | p50 | p75 | p90 |
|---|---|---|---|
| Não trocou o aliado | 7 | 7 | 7 |
| Possível bait | 0 | 0 | 0 |
| Perdeu a troca | 44 | 44 | 44 |
| Morreu sozinho | 370 | 152 | 56 |
| Primeira morte sem troca | 157 | 139 | 52 |
| Flash no time | 61 | 61 | 51 |
| Dano de utilidade no time | 4 | 4 | 4 |

#### O efeito de `DIST_TROCA` em "morreu sozinho"

Fase 18: `DIST_TROCA` só entra em "morreu sozinho" (nos outros tipos a troca é decidida pelo fato e a distância é contexto). Cada linha recalcula as ocorrências do corpus com outro `DIST_TROCA` (o atual está marcado) e refaz a referência com elas. Ponto a melhorar com o percentil 90. O valor da constante NÃO muda agora: depende da sua calibração.

| `DIST_TROCA` | tipo | ocorrências no corpus | média por jogador-lado | jogador-partidas com pelo menos 1 ponto a melhorar | % |
|---|---|---|---|---|---|
| 400 | Morreu sozinho | 2135 | 2,05 | 76 | 15% |
| 600 (atual) | Morreu sozinho | 1708 | 1,64 | 53 | 10% |
| 800 | Morreu sozinho | 1318 | 1,27 | 76 | 15% |

### 7.2 Dez exemplos por tipo

Sorteados com semente fixa (20261013), no máximo 2 por partida, só entre as ocorrências que passaram nos filtros, e FIXADOS em `scripts/calibracao/exemplos_fixados.json`: rodar de novo mantém todo exemplo que ainda é ocorrência; o que deixar de ser é trocado e marcado "(substituído em <data>: <motivo>)". Os exemplos da fase 17 não valem mais (as definições mudaram na fase 18) e foram sorteados de novo; na calibração da fase 18b, os que deixaram de ser ocorrência foram trocados (a marca diz quando e por quê), e um tipo abaixo de `MIN_CASOS_PARA_VALIDAR` não tem exemplos de validação. O relógio é o tempo decorrido desde o fim do freeze time. O link abre o replay naquele round, 3 s antes do instante (gere o site com `py -3.12 -m scripts.build_site`). Distâncias em unidades do jogo, no mesmo andar; "—" quando não se aplica ou estão em andares diferentes. "Visível" é a linha de visão pelo mapa (com as smokes) dentro do campo de visão e sem estar cego (`metrics/visao.py`). A chance de vitória é a do time do jogador vencer o ROUND logo antes do evento (modelo de round do rating). ΔWPA em pontos de chance de vitória da partida, pela estimativa do modelo (negativo = o time perdeu chance).

**Regra de publicação:** o tipo só aparece no site com pelo menos 8 dos 10 confirmados: "sim" quando o nível é explícito, ou "depende da tática" quando o nível é depende.

#### Não trocou o aliado

Frase de como melhorar: "Jogue a uma distância de troca do parceiro e mirando o mesmo ponto que ele. Se ele cair, o matador está exposto por alguns segundos: é a sua janela."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? | recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_02 | 7 | 0:35 | donk666 | -olik | Dyshbert | 934 | 1080 | 4 contra 5 | 54% | sim (1,8 s) | não atirou; dano 0 | -43; saiu da linha de visão | — | não | -4,2 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_51 R8 Spinx) | [abrir](docs/match_02.html#replay?round=7&t=34.67) | sim / não / depende da tática |
| 2 | match_04 | 21 | 0:17 | MolO11 | pxd11 | L1nkero | 137 | 1091 | 4 contra 5 | 47% | sim (0,5 s) | não atirou; dano 0 | 144; saiu da linha de visão | — | não | -1,5 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_12 R22 FalleN) | [abrir](docs/match_04.html#replay?round=21&t=17.27) | sim / não / depende da tática |
| 3 | match_10 | 11 | 1:32 | donk | zont1x | w0nderful | 62 | 1100 | 4 contra 5 | 33% | sim (0,5 s) | não atirou; dano 0 | -6 | — | não | -0,1 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_19 R9 molodoy) | [abrir](docs/match_10.html#replay?round=11&t=92.03) | sim / não / depende da tática |
| 4 | match_14 | 20 | 1:29 | ropz | apEX | molodoy | 860 | 1294 | 4 contra 3 | 78% | sim (0,7 s) | não atirou; dano 0 | -0 | — | não | -7,4 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_48 R15 torzsi) | [abrir](docs/match_14.html#replay?round=20&t=89.3) | sim / não / depende da tática |
| 5 | match_31 | 31 | 1:43 | molodoy | YEKINDAR | m0NESY | 349 | 1065 | 2 contra 1 | 88% | sim (0,6 s) | não atirou; dano 0 | 15; saiu da linha de visão | — | não | -10,7 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_40 R28 magixx) | [abrir](docs/match_31.html#replay?round=31&t=103.23) | sim / não / depende da tática |
| 6 | match_32 | 28 | 0:52 | NiKo | kyxsan | YEKINDAR | 598 | 978 | 3 contra 5 | 11% | sim (0,7 s) | não atirou; dano 0 | -44 | — | não | -1,0 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: engajou o matador; era match_30 R18 FalleN) | [abrir](docs/match_32.html#replay?round=28&t=51.86) | sim / não / depende da tática |
| 7 | match_32 | 34 | 1:11 | YEKINDAR | molodoy | NiKo | 556 | 675 | 3 contra 2 | 93% | sim (3,1 s) | não atirou; dano 0 | 4 | — | não | -5,3 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: engajou o matador; era match_19 R14 FalleN) | [abrir](docs/match_32.html#replay?round=34&t=71.02) | sim / não / depende da tática |
| 8 | match_47 | 10 | 1:15 | ropz | apEX | xertioN | 407 | 516 | 5 contra 3 | 76% | sim (0,6 s) | não atirou; dano 0 | -40 | — | não | -1,9 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: o matador ficou visível menos de 0,5 s; era match_39 R6 b1t) | [abrir](docs/match_47.html#replay?round=10&t=75.09) | sim / não / depende da tática |
| 9 | match_50 | 4 | 1:21 | kyousuke | kyxsan | torzsi | 321 | 1023 | 4 contra 3 | 76% | sim (0,8 s) | não atirou; dano 0 | -2; saiu da linha de visão | — | não | -4,1 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca (substituído em 2026-10-16: engajou o matador; era match_53 R2 mezii) | [abrir](docs/match_50.html#replay?round=4&t=80.95) | sim / não / depende da tática |
| 10 | match_52 | 11 | 1:23 | mezii | ropz | Mzinho | 838 | 987 | 5 contra 4 | 75% | sim (0,7 s) | não atirou; dano 0 | 9 | — | não | -3,9 | explícito | o aliado morreu, o matador ficou visível para ele e saiu vivo da janela de troca | [abrir](docs/match_52.html#replay?round=11&t=83.14) | sim / não / depende da tática |

#### Possível bait: amostra insuficiente (9 casos), só para conferir a definição

Com menos de 10 casos no corpus (`MIN_CASOS_PARA_VALIDAR`, contados dos dados), o tipo não entra na validação nem em `TIPOS_DE_ERRO_VALIDADOS`: não dá para sortear os 10 exemplos da regra dos 8 de 10. Ele continua calculado e gravado e volta à validação normal quando o corpus tiver casos suficientes. Estes são TODOS os casos (não são exemplos fixados): a pergunta é se a definição pega o que você chamaria de bait.

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? | recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_04 | 21 | 0:17 | MolO11 | pxd11 | L1nkero | 137 | 1091 | 4 contra 5 | 47% | sim (0,5 s) | não atirou; dano 0 | 144; saiu da linha de visão | — | não | -1,5 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_04.html#replay?round=21&t=17.27) | sim / não / depende da tática |
| 2 | match_06 | 17 | 0:21 | Alperen | ar1sFLXR | Etaliqe | 1314 | 1211 | 2 contra 4 | 7% | sim (1,1 s) | não atirou; dano 0 | 180; saiu da linha de visão | — | não | -0,2 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_06.html#replay?round=17&t=20.86) | sim / não / depende da tática |
| 3 | match_22 | 6 | 0:25 | iM | w0nderful | kyxsan | 459 | 252 | 3 contra 4 | 17% | sim (0,9 s) | não atirou; dano 0 | 76 | — | não | -1,1 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_22.html#replay?round=6&t=25.12) | sim / não / depende da tática |
| 4 | match_26 | 6 | 0:37 | donk | chopper | apEX | 594 | 302 | 5 contra 5 | 43% | sim (1,8 s) | não atirou; dano 0 | 70; saiu da linha de visão | — | não | -3,6 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_26.html#replay?round=6&t=36.58) | sim / não / depende da tática |
| 5 | match_32 | 9 | 0:17 | NiKo | TeSeS | molodoy | 369 | 1168 | 5 contra 5 | 33% | sim (0,5 s) | não atirou; dano 0 | 81 | — | não | -3,4 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_32.html#replay?round=9&t=16.64) | sim / não / depende da tática |
| 6 | match_34 | 21 | 1:05 | mezii | apEX | Spinx | 548 | 1115 | 4 contra 3 | 71% | sim (0,8 s) | não atirou; dano 0 | 65; saiu da linha de visão | — | não | -6,4 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_34.html#replay?round=21&t=65.3) | sim / não / depende da tática |
| 7 | match_39 | 17 | 1:10 | magixx | chopper | Aleksib | 903 | 1036 | 5 contra 4 | 84% | sim (0,6 s) | não atirou; dano 0 | 95; saiu da linha de visão | — | não | -0,9 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_39.html#replay?round=17&t=70.34) | sim / não / depende da tática |
| 8 | match_45 | 4 | 0:35 | YEKINDAR | molodoy | ropz | 1136 | 452 | 4 contra 4 | 53% | sim (1,2 s) | não atirou; dano 0 | 79; saiu da linha de visão | — | não | -3,6 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_45.html#replay?round=4&t=35.12) | sim / não / depende da tática |
| 9 | match_45 | 7 | 0:59 | FalleN | yuurih | flameZ | 996 | 797 | 5 contra 5 | 31% | sim (0,6 s) | não atirou; dano 0 | 370; saiu da linha de visão | — | não | -1,2 | explícito | o matador ficou visível para ele, ele não atirou nem causou dano e recuou ou saiu da linha de visão; o dado mostra posição e tempo, não intenção | [abrir](docs/match_45.html#replay?round=7&t=59.33) | sim / não / depende da tática |

#### Perdeu a troca

Frase de como melhorar: "Na troca, não pique o mesmo ângulo que acabou de matar o aliado. Mude o ângulo ou jogue uma flash no matador antes."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? | recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_02 | 10 | 0:43 | OG_Pablo_ | -olik | Krimbo | 684 | 1452 | 3 contra 3 | 46% | sim (0,5 s) | atirou; dano 0 | -20 | 1 | não | -5,4 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_02.html#replay?round=10&t=42.78) | sim / não / depende da tática |
| 2 | match_04 | 3 | 0:14 | donk666 | nedorufe | shiFu- | 565 | 838 | 4 contra 5 | 39% | sim (0,1 s) | não atirou; dano 26 | 5 | 1 | não | -3,2 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_04.html#replay?round=3&t=13.67) | sim / não / depende da tática |
| 3 | match_08 | 8 | 0:42 | PoisonLilies | KENNY-_ | certa1n | 1030 | 1560 | 3 contra 3 | 45% | sim (0,6 s) | atirou; dano 0 | -38 | 1 | não | -5,0 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_08.html#replay?round=8&t=41.75) | sim / não / depende da tática |
| 4 | match_11 | 10 | 0:12 | iM | makazze | donk | 146 | 434 | 4 contra 5 | 25% | não | não atirou; dano 50 | 0 | 0 | não | -2,3 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_11.html#replay?round=10&t=12.16) | sim / não / depende da tática |
| 5 | match_21 | 3 | 1:12 | woxic | Wicadia | makazze | 754 | 1666 | 3 contra 5 | 13% | sim (1,0 s) | atirou; dano 58 | -1 | 1 | não | -1,4 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_21.html#replay?round=3&t=71.52) | sim / não / depende da tática |
| 6 | match_22 | 6 | 0:25 | w0nderful | b1t | kyxsan | 615 | 297 | 3 contra 4 | 17% | sim (0,5 s) | atirou; dano 0 | -2 | 1 | não | -1,1 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_22.html#replay?round=6&t=25.12) | sim / não / depende da tática |
| 7 | match_32 | 26 | 1:00 | molodoy | FalleN | kyousuke | 272 | 702 | 3 contra 5 | 13% | sim (0,5 s) | atirou; dano 0 | -1; saiu da linha de visão | 1 | não | -2,7 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_32.html#replay?round=26&t=59.73) | sim / não / depende da tática |
| 8 | match_32 | 28 | 0:35 | kyousuke | m0NESY | molodoy | 121 | 1252 | 4 contra 5 | 28% | sim (0,3 s) | atirou; dano 0 | -23 | 1 | não | -2,0 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_32.html#replay?round=28&t=34.67) | sim / não / depende da tática |
| 9 | match_33 | 14 | 0:42 | torzsi | Brollan | ZywOo | 359 | 1256 | 4 contra 5 | 28% | sim (0,9 s) | atirou; dano 0 | -16 | 1 | não | -2,6 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_33.html#replay?round=14&t=41.61) | sim / não / depende da tática |
| 10 | match_46 | 16 | 1:37 | FalleN | yuurih | flameZ | 353 | 1301 | 3 contra 4 | 28% | sim (0,4 s) | atirou; dano 0 | 0 | 1 | não | -3,0 | explícito | foi para a troca (engajou o matador) e morreu sem matá-lo, com no máximo um inimigo à vista | [abrir](docs/match_46.html#replay?round=16&t=97.45) | sim / não / depende da tática |

#### Morreu sozinho

Frase de como melhorar: "Se não é o lurker, jogue onde um aliado consiga te trocar e avise a posição. Morrer sem troca dá vantagem numérica de graça."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? | recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_04 | 19 | 0:25 | MolO11 | — | somehxw | 2530 | 598 | 2 contra 5 | 5% | não | — | — | — | não | -0,4 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_04.html#replay?round=19&t=25.16) | sim / não / depende da tática |
| 2 | match_05 | 17 | 1:20 | gwizdakk | — | donk666 | 1656 | 597 | 2 contra 1 | 78% | não | — | — | — | não | -0,2 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_05.html#replay?round=17&t=80.3) | sim / não / depende da tática |
| 3 | match_11 | 20 | 1:16 | tN1R | — | makazze | 888 | 529 | 5 contra 4 | 76% | não | — | — | — | não | -3,3 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_11.html#replay?round=20&t=76.16) | sim / não / depende da tática |
| 4 | match_15 | 15 | 1:04 | YEKINDAR | — | makazze | 1664 | 1354 | 3 contra 4 | 28% | não | — | — | — | não | -0,2 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_15.html#replay?round=15&t=64.44) | sim / não / depende da tática |
| 5 | match_20 | 30 | 0:55 | kyousuke | — | molodoy | 1151 | 843 | 2 contra 3 | 17% | não | — | — | — | não | -6,7 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_20.html#replay?round=30&t=54.58) | sim / não / depende da tática |
| 6 | match_22 | 7 | 1:15 | Wicadia | — | w0nderful | 1528 | 776 | 4 contra 3 | 74% | não | — | — | — | não | -1,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_22.html#replay?round=7&t=74.61) | sim / não / depende da tática |
| 7 | match_23 | 20 | 1:12 | apEX | — | eksiver | 1998 | 1295 | 3 contra 2 | 74% | não | — | — | — | não | -4,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_23.html#replay?round=20&t=72.44) | sim / não / depende da tática |
| 8 | match_25 | 19 | 0:25 | w0nderful | — | chopper | 1046 | 1071 | 5 contra 5 | 42% | não | — | — | — | não | -0,3 | depende da tática | segurar sozinho um ângulo de abertura é o trabalho do AWPer; a função não é firme nesta partida | [abrir](docs/match_25.html#replay?round=19&t=24.94) | sim / não / depende da tática |
| 9 | match_26 | 11 | 0:29 | zont1x | — | flameZ | 1991 | 877 | 4 contra 5 | 18% | não | — | — | — | não | -1,3 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_26.html#replay?round=11&t=29.27) | sim / não / depende da tática |
| 10 | match_45 | 15 | 0:24 | YEKINDAR | — | apEX | — | 418 | 5 contra 5 | 35% | não | — | — | — | não | -0,0 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_45.html#replay?round=15&t=23.98) | sim / não / depende da tática |

#### Primeira morte sem troca

Frase de como melhorar: "Sem ser o entry, evite o primeiro contato sozinho. Espere a informação ou alguém para trocar."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | situação | chance de vitória antes | matador visível? (s na janela) | atirou ou deu dano no matador? | recuou (u) | inimigos visíveis ao mesmo tempo | morte trocada? (por quem, a que distância) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_01 | 11 | 0:13 | s-chilla | — | donk666 | 1103 | 608 | 5 contra 5 | 52% | — | — | — | — | não | -4,7 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_01.html#replay?round=11&t=12.77) | sim / não / depende da tática |
| 2 | match_02 | 5 | 0:12 | bezimienny | — | OG_Pablo_ | 494 | 839 | 5 contra 5 | 39% | — | — | — | — | não | -3,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_02.html#replay?round=5&t=12.12) | sim / não / depende da tática |
| 3 | match_09 | 16 | 0:18 | newnickname7 | — | donk666 | 385 | 164 | 5 contra 5 | 49% | — | — | — | — | não | -1,6 | depende da tática | segurar sozinho um ângulo de abertura é o trabalho do AWPer | [abrir](docs/match_09.html#replay?round=16&t=18.31) | sim / não / depende da tática |
| 4 | match_12 | 12 | 0:35 | flameZ | — | molodoy | 828 | 769 | 5 contra 5 | 50% | — | — | — | — | não | -3,5 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_12.html#replay?round=12&t=34.86) | sim / não / depende da tática |
| 5 | match_26 | 12 | 0:31 | donk | — | apEX | 546 | 502 | 5 contra 5 | 43% | — | — | — | — | não | -1,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_26.html#replay?round=12&t=30.84) | sim / não / depende da tática |
| 6 | match_32 | 26 | 0:56 | YEKINDAR | — | m0NESY | 129 | 1598 | 5 contra 5 | 53% | — | — | — | — | não | -7,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_32.html#replay?round=26&t=55.52) | sim / não / depende da tática |
| 7 | match_42 | 30 | 0:54 | kyousuke | — | torzsi | 188 | 1322 | 5 contra 5 | 54% | — | — | — | — | não | -11,5 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_42.html#replay?round=30&t=53.97) | sim / não / depende da tática |
| 8 | match_46 | 4 | 1:01 | ZywOo | — | yuurih | 215 | 1273 | 5 contra 5 | 61% | — | — | — | — | não | -3,3 | depende da tática | segurar sozinho um ângulo de abertura é o trabalho do AWPer | [abrir](docs/match_46.html#replay?round=4&t=60.92) | sim / não / depende da tática |
| 9 | match_52 | 2 | 0:18 | controlez | — | ropz | 411 | 1299 | 5 contra 5 | 59% | — | — | — | — | não | -3,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_52.html#replay?round=2&t=18.06) | sim / não / depende da tática |
| 10 | match_53 | 15 | 0:12 | Mzinho | — | flameZ | 103 | 241 | 5 contra 5 | 56% | — | — | — | — | não | -1,0 | depende da tática | abrir o round é a função do entry; o que pesa é se o time trocou | [abrir](docs/match_53.html#replay?round=15&t=12.17) | sim / não / depende da tática |

#### Flash no time

Frase de como melhorar: "Avise antes de soltar e prefira a pop flash por cima do ângulo do aliado, não na frente dele."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado mais atingido | situação | chance de vitória antes | cegueira desta flash (s) | soma do jogador no lado (s) | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_20 | 24 | 1:02 | NiKo | kyxsan | 5 contra 4 | 50% | 6,78 | 14,20 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_20.html#replay?round=24&t=61.72) | sim / não / depende da tática |
| 2 | match_29 | 14 | 1:24 | FalleN | KSCERATO | 5 contra 4 | 60% | 4,86 | 7,71 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_29.html#replay?round=14&t=83.59) | sim / não / depende da tática |
| 3 | match_32 | 19 | 0:45 | TeSeS | m0NESY | 4 contra 2 | 92% | 7,59 | 15,52 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_32.html#replay?round=19&t=44.72) | sim / não / depende da tática |
| 4 | match_32 | 29 | 0:07 | yuurih | KSCERATO | 5 contra 5 | 48% | 1,43 | 27,55 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_32.html#replay?round=29&t=7.12) | sim / não / depende da tática |
| 5 | match_39 | 2 | 1:19 | donk | chopper | 4 contra 5 | 42% | 5,49 | 15,00 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_39.html#replay?round=2&t=78.59) | sim / não / depende da tática |
| 6 | match_39 | 4 | 1:30 | Aleksib | iM | 5 contra 4 | 68% | 8,74 | 9,89 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_39.html#replay?round=4&t=90.45) | sim / não / depende da tática |
| 7 | match_42 | 10 | 1:30 | torzsi | xertioN | 3 contra 2 | 78% | 1,21 | 56,24 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_42.html#replay?round=10&t=90.34) | sim / não / depende da tática |
| 8 | match_42 | 11 | 0:54 | torzsi | Brollan | 5 contra 4 | 66% | 0,98 | 56,24 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_42.html#replay?round=11&t=53.5) | sim / não / depende da tática |
| 9 | match_46 | 9 | 0:24 | yuurih | YEKINDAR | 5 contra 4 | 70% | 5,10 | 25,34 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_46.html#replay?round=9&t=24.16) | sim / não / depende da tática |
| 10 | match_51 | 18 | 0:45 | torzsi | Jimpphat | 3 contra 5 | 12% | 5,93 | 8,06 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_51.html#replay?round=18&t=44.88) | sim / não / depende da tática |

#### Dano de utilidade no time

Frase de como melhorar: "Confira onde o time está antes de soltar HE ou molotov num ponto de passagem."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado mais atingido | situação | chance de vitória antes | dano desta granada | soma do jogador no lado | ΔWPA | nível | motivo | replay | É erro mesmo? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_09 | 16 | 0:18 | wh1temink | newnickname7 | 5 contra 5 | 49% | 26,0 | 26,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_09.html#replay?round=16&t=17.75) | sim / não / depende da tática |
| 2 | match_20 | 25 | 0:10 | FalleN | YEKINDAR | 5 contra 5 | 58% | 26,0 | 26,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_20.html#replay?round=25&t=10.33) | sim / não / depende da tática |
| 3 | match_22 | 10 | 0:12 | woxic | XANTARES | 5 contra 5 | 45% | 27,0 | 27,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_22.html#replay?round=10&t=11.86) | sim / não / depende da tática |
| 4 | match_24 | 11 | 1:55 | jL | iM | 5 contra 3 | 55% | 43,0 | 45,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_24.html#replay?round=11&t=115.25) | sim / não / depende da tática |
| 5 | match_24 | 14 | 1:08 | chopper | donk | 5 contra 4 | 83% | 10,0 | 38,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_24.html#replay?round=14&t=67.5) | sim / não / depende da tática |
| 6 | match_30 | 11 | 0:34 | yuurih | KSCERATO | 5 contra 5 | 45% | 22,0 | 22,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_30.html#replay?round=11&t=34.5) | sim / não / depende da tática |
| 7 | match_31 | 28 | 0:13 | YEKINDAR | molodoy | 5 contra 5 | 55% | 23,0 | 23,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_31.html#replay?round=28&t=13.34) | sim / não / depende da tática |
| 8 | match_42 | 4 | 0:12 | torzsi | Brollan | 5 contra 5 | 40% | 23,0 | 23,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_42.html#replay?round=4&t=11.97) | sim / não / depende da tática |
| 9 | match_49 | 20 | 1:38 | Brollan | xertioN | 5 contra 5 | 49% | 21,0 | 21,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_49.html#replay?round=20&t=97.8) | sim / não / depende da tática |
| 10 | match_51 | 11 | 0:53 | NiKo | kyxsan | 5 contra 5 | 51% | 9,0 | 21,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_51.html#replay?round=11&t=52.67) | sim / não / depende da tática |

### 7.3 Sua resposta

Para cada tipo: quantos dos 10 exemplos você confirma, e se a frase de como melhorar serve. O tipo com 8 ou mais confirmados entra em `TIPOS_DE_ERRO_VALIDADOS` (`metrics/erros.py`) num item à parte; os reprovados ficam fora da tela, e eu trago uma proposta de ajuste com os números.
