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

Gerado por `py -3.12 -m scripts.calibracao.erros_do_jogador` (fase 12, decisão 46). Os tipos de erro de `metrics/erros.py` sobre as 52 partidas do corpus. Nenhum tipo aparece no site até você confirmar os exemplos: `TIPOS_DE_ERRO_VALIDADOS` começa vazia. Para ver a aba com todos os tipos marcados "em validação": `py -3.12 -m scripts.build_site --mostrar-erros-nao-validados` (gera em `preview/`, fora do git e nunca publicado).

### 7.0 Ocorrências por tipo no corpus

| tipo | antes dos filtros | depois dos filtros | explícito | depende da tática | saiu pelos filtros (motivo: n) |
|---|---|---|---|---|---|
| Não trocou o aliado | 3413 | 1841 | 1841 | 0 | round de economia do time: 845; em duelo próprio: 309; cego no momento: 208; time guardando arma (pós-plant perdido): 188; sem arma de fogo: 19; depois do fim do round: 3 |
| Possível bait | 1365 | 848 | 848 | 0 | round de economia do time: 279; em duelo próprio: 105; cego no momento: 70; time guardando arma (pós-plant perdido): 48; sem arma de fogo: 13; depois do fim do round: 2 |
| Perdeu a troca | 1282 | 812 | 812 | 0 | round de economia do time: 370; time guardando arma (pós-plant perdido): 99; depois do fim do round: 1 |
| Morreu isolado | 3593 | 2066 | 0 | 2066 | round de economia do time: 627; time guardando arma (pós-plant perdido): 499; sem aliado vivo (1 contra N): 385; depois do fim do round: 16 |
| Primeira morte sem troca | 859 | 691 | 0 | 691 | round de economia do time: 164; time guardando arma (pós-plant perdido): 4 |
| Flash no time | 3091 | 530 | 530 | 0 | abaixo do limiar da partida: 2284; round de economia do time: 207; time guardando arma (pós-plant perdido): 54; depois do fim do round: 16 |
| Dano de utilidade no time | 195 | 28 | 28 | 0 | abaixo do limiar da partida: 157; round de economia do time: 7; depois do fim do round: 3 |
| Utilidade no bolso | não criado | — | — | — | o inventário na hora da morte não existe no dado (decisão 46) |

**Mudança da fase 15 (decisão 46).** "Flash no time" e "dano de utilidade no time" eram somas da partida (CT e TR juntos); passam a ser POR LADO, com o mesmo limiar (`SEG_CEGUEIRA_ALIADO` 27 s e `DANO_UTILIDADE_ALIADO` 20) aplicado a cada lado. Ocorrências que seguem na tela (depois dos filtros), no corpus de 52 jogos: flash no time 880 antes, 530 depois; dano de utilidade no time 32 antes, 28 depois (o total detectado não muda: 3091 e 195). Os 10 exemplos sorteados abaixo NÃO foram refeitos.

Ordem dos níveis (a primeira regra que se aplica decide): 1) round de eco ou pistola do time, ou time guardando arma (evento depois do plant num round que o time perdeu): fora; 2) morreu isolado sendo lurker: depende; 3) primeira morte sem troca sendo entry: depende; 4) morreu isolado ou primeira morte do AWPer no duelo de abertura: depende; 5) função só tendência: o motivo diz que a função não é firme; 6) não trocou, possível bait, perdeu a troca, flash no time e dano de utilidade no time: explícito; 7) o resto: depende. Por isso "morreu isolado" e "primeira morte sem troca" saem sempre como "depende da tática" (só o motivo muda).

### 7.1 As constantes novas

Valor proposto, origem, histograma no corpus e quantas ocorrências (depois dos filtros) cada tipo teria no valor mais baixo e no mais alto da faixa. As outras constantes ficam no valor proposto em cada varredura.

#### `DIST_TROCA` = 600 unidades

Origem: o raio de apoio do projeto (RAIO_COMPANHEIRO = 600 do perfil e das funções: "o alcance em que uma troca ainda acontece"). O histograma é a distância de cada aliado vivo a quem morreu, na hora da morte, no mesmo andar.

Mediana 976,2, p75 1605,7, p90 2296,5, p95 2697,5.

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
| Não trocou o aliado | 1099 | 1841 | 2668 |
| Possível bait | 434 | 848 | 1392 |
| Perdeu a troca | 812 | 812 | 812 |
| Morreu isolado | 2627 | 2066 | 1568 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 880 | 880 | 880 |
| Dano de utilidade no time | 32 | 32 | 32 |

#### `S_DUELO` = 2 s

Origem: tempo de um duelo de rifle (reação de ~0,25 s mais 0,3 a 1 s para matar), com folga. O histograma é, para cada aliado a até DIST_TROCA de quem morreu, o tempo desde o último dano que ele deu ou levou de um inimigo antes da morte.

Mediana 4,8, p75 19,8, p90 46,7, p95 63,2.

```
        0-0.5        477 #######################
      0.5-1          204 ##########
        1-1.5        134 ######
      1.5-2          134 ######
        2-2.5        123 ######   <- proposto
      2.5-3          105 #####
        3-4          170 ########
        4-5          114 #####
        5-7          205 ##########
        7-10         185 #########
       10-15         180 #########
  >= 15              834 ########################################
  (2865 valores, em s)
```

| tipo | S_DUELO = 1 | proposto (2) | S_DUELO = 4 |
|---|---|---|---|
| Não trocou o aliado | 1927 | 1841 | 1685 |
| Possível bait | 881 | 848 | 795 |
| Perdeu a troca | 812 | 812 | 812 |
| Morreu isolado | 2066 | 2066 | 2066 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 880 | 880 | 880 |
| Dano de utilidade no time | 32 | 32 | 32 |

#### `SEG_CEGUEIRA_ALIADO` = 27 s

Origem: o percentil 90 da soma de cegueira imposta ao próprio time por jogador-partida no corpus (fora eco e pós-plant perdido).

Mediana 8,7, p75 16,9, p90 27,1, p95 35,2.

```
        0-0.01        31 #####################
     0.01-2           51 ###################################
        2-4           53 ####################################
        4-6           56 ######################################
        6-8           54 #####################################
        8-10          45 ###############################
       10-12          34 #######################
       12-15          44 ##############################
       15-20          55 #####################################
       20-30          59 ########################################   <- proposto
  >= 30               38 ##########################
  (520 valores, em s)
```

| tipo | SEG_CEGUEIRA_ALIADO = 5 | proposto (27) | SEG_CEGUEIRA_ALIADO = 20 |
|---|---|---|---|
| Não trocou o aliado | 1841 | 1841 | 1841 |
| Possível bait | 848 | 848 | 848 |
| Perdeu a troca | 812 | 812 | 812 |
| Morreu isolado | 2066 | 2066 | 2066 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 2534 | 880 | 1257 |
| Dano de utilidade no time | 32 | 32 | 32 |

#### `SEG_CEGUEIRA_ALIADO_UMA` = 4,8 s

Origem: o percentil 90 da cegueira nos aliados por flash no corpus (uma flash cheia cega de 2 a 5 s; perto do topo é a flash que estourou na cara do aliado). O histograma é a cegueira nos aliados por flash.

Mediana 1,6, p75 3,2, p90 4,8, p95 5,8.

```
        0-0.5        313 ##################
      0.5-1          709 ########################################
        1-1.5        310 #################
      1.5-2          337 ###################
        2-2.5        174 ##########
      2.5-3          175 ##########
        3-3.5        177 ##########
      3.5-4          128 #######
        4-5          246 ##############   <- proposto
  >= 5               245 ##############
  (2814 valores, em s)
```

| tipo | SEG_CEGUEIRA_ALIADO_UMA = 2 | proposto (4,8) | SEG_CEGUEIRA_ALIADO_UMA = 4 |
|---|---|---|---|
| Não trocou o aliado | 1841 | 1841 | 1841 |
| Possível bait | 848 | 848 | 848 |
| Perdeu a troca | 812 | 812 | 812 |
| Morreu isolado | 2066 | 2066 | 2066 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 1465 | 880 | 1026 |
| Dano de utilidade no time | 32 | 32 | 32 |

#### `DANO_UTILIDADE_ALIADO` = 20 de dano

Origem: o percentil 95 do dano de HE e molotov no próprio time por jogador-partida no corpus (fora eco e pós-plant perdido).

Mediana 0,0, p75 1,0, p90 10,0, p95 19,0.

```
        0-0.01       388 ########################################
     0.01-10          75 ########
       10-25          43 ####   <- proposto
       25-40          10 #
       40-50           3 
       50-60           1 
       60-80           0 
       80-100          0 
      100-150          0 
  >= 150               0 
  (520 valores, em de dano)
```

| tipo | DANO_UTILIDADE_ALIADO = 25 | proposto (20) | DANO_UTILIDADE_ALIADO = 100 |
|---|---|---|---|
| Não trocou o aliado | 1841 | 1841 | 1841 |
| Possível bait | 848 | 848 | 848 |
| Perdeu a troca | 812 | 812 | 812 |
| Morreu isolado | 2066 | 2066 | 2066 |
| Primeira morte sem troca | 691 | 691 | 691 |
| Flash no time | 880 | 880 | 880 |
| Dano de utilidade no time | 18 | 32 | 0 |

#### `MIN_GRANADAS_NO_BOLSO`: não criada

O tipo "Utilidade no bolso" exige o inventário na hora da morte. O parser lê o inventário só no fim do freeze time (`PROPS_DA_COMPRA` em `parsing/parser.py`, a tabela `compra`); na hora da morte não há o que ler. Pela regra do pedido, o tipo não foi criado e nada foi estimado (decisão 46).

### 7.1b Quantos pontos a melhorar cada jogador teria

Uma ocorrência só vira "ponto a melhorar" quando a contagem do jogador num lado fica ACIMA do percentil 75 da referência (os jogador-lados do corpus com a mesma função no mesmo lado; com menos de 20 deles, todos os jogador-lados daquele lado) e tem pelo menos 2 ocorrências. Um jogador-lado é um jogador numa partida, num dos lados (1040 no corpus). A tela mostra no máximo 3 por jogador; as contagens abaixo são as brutas, sem esse corte.

#### Distribuição da contagem por jogador-lado, por tipo e lado

| tipo | lado | jogador-lados | média | mediana | p75 | p90 | máximo | com 0 |
|---|---|---|---|---|---|---|---|---|
| Não trocou o aliado | CT | 520 | 0,93 | 1,0 | 2,0 | 2,0 | 7 | 43% |
| Não trocou o aliado | TR | 520 | 2,61 | 2,0 | 4,0 | 5,0 | 15 | 15% |
| Possível bait | CT | 520 | 0,44 | 0,0 | 1,0 | 1,0 | 4 | 65% |
| Possível bait | TR | 520 | 1,19 | 1,0 | 2,0 | 3,0 | 7 | 38% |
| Perdeu a troca | CT | 520 | 0,51 | 0,0 | 1,0 | 2,0 | 4 | 64% |
| Perdeu a troca | TR | 520 | 1,06 | 1,0 | 2,0 | 3,0 | 6 | 40% |
| Morreu isolado | CT | 520 | 2,35 | 2,0 | 3,0 | 4,0 | 7 | 11% |
| Morreu isolado | TR | 520 | 1,63 | 1,0 | 2,0 | 3,0 | 6 | 21% |
| Primeira morte sem troca | CT | 520 | 0,54 | 0,0 | 1,0 | 2,0 | 4 | 59% |
| Primeira morte sem troca | TR | 520 | 0,78 | 1,0 | 1,0 | 2,0 | 6 | 50% |
| Flash no time | CT | 520 | 0,62 | 0,0 | 0,0 | 1,0 | 15 | 82% |
| Flash no time | TR | 520 | 1,07 | 0,0 | 1,0 | 3,0 | 21 | 73% |
| Dano de utilidade no time | CT | 520 | 0,03 | 0,0 | 0,0 | 0,0 | 2 | 97% |
| Dano de utilidade no time | TR | 520 | 0,03 | 0,0 | 0,0 | 0,0 | 2 | 98% |

#### Pontos a melhorar por jogador-partida, por percentil

| percentil | jogador-partidas | com pelo menos 1 | % | média | com 0 | com 1 | com 2 | com 3 ou mais |
|---|---|---|---|---|---|---|---|---|
| 50 | 520 | 481 | 92% | 2,88 | 39 | 95 | 109 | 277 |
| 75 (proposto) | 520 | 402 | 77% | 1,67 | 118 | 150 | 121 | 131 |
| 90 | 520 | 244 | 47% | 0,75 | 276 | 148 | 61 | 35 |

Pares (tipo, lado) que viram ponto a melhorar, por tipo:

| tipo | p50 | p75 | p90 |
|---|---|---|---|
| Não trocou o aliado | 349 | 153 | 76 |
| Possível bait | 194 | 110 | 43 |
| Perdeu a troca | 210 | 120 | 62 |
| Morreu isolado | 465 | 229 | 76 |
| Primeira morte sem troca | 157 | 139 | 52 |
| Flash no time | 116 | 111 | 77 |
| Dano de utilidade no time | 6 | 6 | 6 |

#### O efeito de `DIST_TROCA` em "não trocou" e "possível bait"

Cada linha recalcula as ocorrências do corpus com outro `DIST_TROCA` (o atual está marcado) e refaz a referência com elas. Ponto a melhorar com o percentil 75. O valor da constante NÃO muda agora: depende da sua calibração.

| `DIST_TROCA` | tipo | ocorrências no corpus | média por jogador-lado | jogador-partidas com pelo menos 1 ponto a melhorar | % |
|---|---|---|---|---|---|
| 400 | Não trocou o aliado | 1099 | 1,06 | 141 | 27% |
| 400 | Possível bait | 434 | 0,42 | 79 | 15% |
| 600 (atual) | Não trocou o aliado | 1841 | 1,77 | 143 | 28% |
| 600 (atual) | Possível bait | 848 | 0,82 | 106 | 20% |
| 800 | Não trocou o aliado | 2668 | 2,57 | 165 | 32% |
| 800 | Possível bait | 1392 | 1,34 | 122 | 23% |

### 7.2 Dez exemplos por tipo

Sorteados com semente fixa (20261013), no máximo 2 por partida, só entre as ocorrências que passaram nos filtros. O relógio é o tempo decorrido desde o fim do freeze time. O link abre o replay naquele round, 3 s antes do instante (gere o site com `py -3.12 -m scripts.build_site`). Distâncias em unidades do jogo, no mesmo andar; "—" quando não se aplica ou estão em andares diferentes. ΔWPA em pontos de chance de vitória da partida, pela estimativa do modelo (negativo = o time perdeu chance).

**Regra de publicação:** o tipo só aparece no site com pelo menos 8 dos 10 confirmados: "sim" quando o nível é explícito, ou "depende da tática" quando o nível é depende.

#### Não trocou o aliado

Frase de como melhorar: "Jogue a uma distância de troca do parceiro e mirando o mesmo ponto que ele. Se ele cair, o matador está exposto por alguns segundos: é a sua janela."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_22 | 18 | 1:12 | Jimpphat | XANTARES | makazze | 155 | 738 | 636 | 3 contra 5 | — | -0,0 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_22.html#replay?round=18&t=72.47) | sim / não / depende da tática | sim / reescrever |
| 2 | match_25 | 11 | 1:25 | iM | w0nderful | donk | 56 | 928 | 969 | 3 contra 3 | — | -1,0 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_25.html#replay?round=11&t=85.06) | sim / não / depende da tática | sim / reescrever |
| 3 | match_33 | 9 | 0:41 | xertioN | Brollan | mezii | 203 | 859 | 663 | 5 contra 5 | — | -1,7 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_33.html#replay?round=9&t=41.19) | sim / não / depende da tática | sim / reescrever |
| 4 | match_38 | 17 | 1:34 | zont1x | donk | jL | 362 | 1382 | 1035 | 3 contra 3 | — | -6,1 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_38.html#replay?round=17&t=93.89) | sim / não / depende da tática | sim / reescrever |
| 5 | match_40 | 20 | 0:39 | magixx | donk | w0nderful | 338 | 148 | 228 | 5 contra 5 | — | -3,7 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_40.html#replay?round=20&t=39.41) | sim / não / depende da tática | sim / reescrever |
| 6 | match_40 | 23 | 1:12 | magixx | donk | Aleksib | 249 | 663 | 417 | 4 contra 5 | — | -3,0 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_40.html#replay?round=23&t=71.75) | sim / não / depende da tática | sim / reescrever |
| 7 | match_41 | 15 | 0:42 | kyousuke | NiKo | Brollan | 185 | 789 | 904 | 5 contra 4 | — | -4,3 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_41.html#replay?round=15&t=42.03) | sim / não / depende da tática | sim / reescrever |
| 8 | match_45 | 12 | 1:26 | FalleN | yuurih | mezii | 244 | 60 | 188 | 4 contra 5 | — | -0,1 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_45.html#replay?round=12&t=85.92) | sim / não / depende da tática | sim / reescrever |
| 9 | match_49 | 9 | 0:40 | Spinx | Jimpphat | TeSeS | 306 | 1263 | 1025 | 3 contra 4 | — | -1,1 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_49.html#replay?round=9&t=39.86) | sim / não / depende da tática | sim / reescrever |
| 10 | match_50 | 16 | 1:34 | kyousuke | kyxsan | Spinx | 179 | 783 | 870 | 4 contra 5 | — | -0,8 | explícito | o aliado morreu perto dele e o matador saiu vivo da janela de troca | [abrir](docs/match_50.html#replay?round=16&t=94.25) | sim / não / depende da tática | sim / reescrever |

#### Possível bait

Frase de como melhorar: "Se você é o segundo a entrar, entre logo atrás e ao lado, não atrás de parede. Combinem antes quem entra e quem troca."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_03 | 20 | 0:37 | PAiN-M- | Unihi | lilpeepfan- | 4 | 318 | 318 | 5 contra 5 | — | -0,7 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_03.html#replay?round=20&t=36.61) | sim / não / depende da tática | sim / reescrever |
| 2 | match_08 | 20 | 0:26 | donk666 | certa1n | gwizdakk | 300 | 1122 | 1082 | 3 contra 5 | — | -0,7 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_08.html#replay?round=20&t=26.48) | sim / não / depende da tática | sim / reescrever |
| 3 | match_17 | 11 | 0:44 | YEKINDAR | molodoy | Aleksib | 543 | 1585 | 1044 | 4 contra 3 | — | -1,4 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_17.html#replay?round=11&t=44.3) | sim / não / depende da tática | sim / reescrever |
| 4 | match_19 | 5 | 1:18 | molodoy | FalleN | kyousuke | 63 | 872 | 853 | 3 contra 5 | — | -0,5 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_19.html#replay?round=5&t=77.67) | sim / não / depende da tática | sim / reescrever |
| 5 | match_29 | 8 | 0:37 | yuurih | YEKINDAR | NiKo | 455 | 834 | 757 | 3 contra 4 | — | -0,6 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_29.html#replay?round=8&t=37.28) | sim / não / depende da tática | sim / reescrever |
| 6 | match_37 | 17 | 0:59 | Aleksib | b1t | donk | 322 | 1546 | 1273 | 4 contra 1 | — | -0,1 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_37.html#replay?round=17&t=58.91) | sim / não / depende da tática | sim / reescrever |
| 7 | match_38 | 14 | 0:49 | magixx | SH1R0 | Aleksib | 535 | 1079 | 732 | 3 contra 3 | — | -7,1 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_38.html#replay?round=14&t=49.39) | sim / não / depende da tática | sim / reescrever |
| 8 | match_45 | 6 | 0:19 | flameZ | mezii | yuurih | 457 | 602 | 145 | 5 contra 5 | — | -2,1 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_45.html#replay?round=6&t=18.83) | sim / não / depende da tática | sim / reescrever |
| 9 | match_48 | 9 | 1:09 | ZywOo | apEX | torzsi | 272 | 1189 | 1005 | 5 contra 5 | — | -2,8 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_48.html#replay?round=9&t=68.53) | sim / não / depende da tática | sim / reescrever |
| 10 | match_51 | 14 | 1:05 | Spinx | Brollan | TeSeS | 177 | 1076 | 938 | 5 contra 5 | — | -1,8 | explícito | estava atrás do aliado, não atirou no matador e sobreviveu à janela de troca; o dado mostra posição e tempo, não intenção | [abrir](docs/match_51.html#replay?round=14&t=65.06) | sim / não / depende da tática | sim / reescrever |

#### Perdeu a troca

Frase de como melhorar: "Na troca, não pique o mesmo ângulo que acabou de matar o aliado. Mude o ângulo ou jogue uma flash no matador antes."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_01 | 3 | 0:16 | 9amaterasu9 | s-chilla | donk666 | 66 | 767 | 785 | 4 contra 3 | — | -3,7 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_01.html#replay?round=3&t=15.61) | sim / não / depende da tática | sim / reescrever |
| 2 | match_08 | 11 | 0:52 | KENNY-_ | -EsD | donk666 | 562 | 598 | 946 | 2 contra 3 | — | -1,5 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_08.html#replay?round=11&t=52.36) | sim / não / depende da tática | sim / reescrever |
| 3 | match_12 | 3 | 1:32 | apEX | ropz | FalleN | 620 | 884 | 272 | 2 contra 4 | — | -0,7 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_12.html#replay?round=3&t=91.56) | sim / não / depende da tática | sim / reescrever |
| 4 | match_21 | 5 | 0:35 | b1t | iM | Jimpphat | — | — | 622 | 2 contra 3 | — | -2,1 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_21.html#replay?round=5&t=35.36) | sim / não / depende da tática | sim / reescrever |
| 5 | match_28 | 18 | 0:53 | sh1ro | zont1x | flameZ | 588 | 411 | 185 | 1 contra 4 | — | -0,5 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_28.html#replay?round=18&t=53.39) | sim / não / depende da tática | sim / reescrever |
| 6 | match_33 | 15 | 1:38 | Spinx | Jimpphat | ropz | 101 | 382 | 477 | 2 contra 1 | — | -4,7 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_33.html#replay?round=15&t=97.67) | sim / não / depende da tática | sim / reescrever |
| 7 | match_42 | 23 | 0:57 | Spinx | torzsi | kyousuke | 683 | 385 | 1062 | 2 contra 2 | — | -8,5 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_42.html#replay?round=23&t=56.72) | sim / não / depende da tática | sim / reescrever |
| 8 | match_46 | 23 | 1:15 | yuurih | molodoy | ZywOo | 602 | 798 | 239 | 2 contra 5 | — | -0,5 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_46.html#replay?round=23&t=75.11) | sim / não / depende da tática | sim / reescrever |
| 9 | match_49 | 11 | 1:27 | NiKo | TeSeS | torzsi | 1350 | 873 | 1027 | 3 contra 2 | — | -1,6 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_49.html#replay?round=11&t=87.42) | sim / não / depende da tática | sim / reescrever |
| 10 | match_50 | 11 | 1:39 | Brollan | Spinx | m0NESY | 1162 | 1170 | 578 | 4 contra 5 | — | -3,6 | explícito | foi para a troca e morreu sem matar quem matou o aliado | [abrir](docs/match_50.html#replay?round=11&t=98.98) | sim / não / depende da tática | sim / reescrever |

#### Morreu isolado

Frase de como melhorar: "Se não é o lurker, jogue perto de um aliado e avise a posição. Morrer sozinho dá vantagem numérica de graça."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_06 | 5 | 0:26 | -_-siNNer | — | pradablade | 1660 | 128 | — | 4 contra 5 | — | -1,2 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_06.html#replay?round=5&t=25.98) | sim / não / depende da tática | sim / reescrever |
| 2 | match_06 | 18 | 0:39 | adamS | — | donk666 | 912 | 594 | — | 4 contra 1 | — | -0,0 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_06.html#replay?round=18&t=38.81) | sim / não / depende da tática | sim / reescrever |
| 3 | match_15 | 6 | 0:15 | FalleN | — | iM | 1412 | 1673 | — | 5 contra 5 | — | -2,7 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_15.html#replay?round=6&t=15.02) | sim / não / depende da tática | sim / reescrever |
| 4 | match_24 | 12 | 0:58 | jL | — | donk | 1056 | 626 | — | 5 contra 4 | — | -3,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_24.html#replay?round=12&t=58.38) | sim / não / depende da tática | sim / reescrever |
| 5 | match_30 | 19 | 0:27 | NiKo | — | YEKINDAR | 679 | 706 | — | 5 contra 5 | — | -1,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_30.html#replay?round=19&t=27.06) | sim / não / depende da tática | sim / reescrever |
| 6 | match_36 | 9 | 0:30 | donk | — | b1t | 1619 | 585 | — | 3 contra 3 | — | -1,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_36.html#replay?round=9&t=29.58) | sim / não / depende da tática | sim / reescrever |
| 7 | match_36 | 9 | 1:05 | b1t | — | chopper | 612 | 842 | — | 3 contra 1 | — | -0,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_36.html#replay?round=9&t=64.61) | sim / não / depende da tática | sim / reescrever |
| 8 | match_37 | 28 | 1:21 | iM | — | donk | 1638 | 667 | — | 3 contra 4 | — | -5,3 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_37.html#replay?round=28&t=81.09) | sim / não / depende da tática | sim / reescrever |
| 9 | match_49 | 8 | 1:37 | kyousuke | — | Spinx | 610 | 291 | — | 2 contra 2 | — | -3,3 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_49.html#replay?round=8&t=97.17) | sim / não / depende da tática | sim / reescrever |
| 10 | match_50 | 12 | 1:05 | Jimpphat | — | NiKo | 934 | 138 | — | 5 contra 5 | — | -4,9 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_50.html#replay?round=12&t=65.12) | sim / não / depende da tática | sim / reescrever |

#### Primeira morte sem troca

Frase de como melhorar: "Sem ser o entry, evite o primeiro contato sozinho. Espere a informação ou alguém para trocar."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_01 | 11 | 0:13 | s-chilla | — | donk666 | 1103 | 608 | — | 5 contra 5 | — | -4,7 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_01.html#replay?round=11&t=12.77) | sim / não / depende da tática | sim / reescrever |
| 2 | match_02 | 5 | 0:12 | bezimienny | — | OG_Pablo_ | 494 | 839 | — | 5 contra 5 | — | -3,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_02.html#replay?round=5&t=12.12) | sim / não / depende da tática | sim / reescrever |
| 3 | match_09 | 16 | 0:18 | newnickname7 | — | donk666 | 385 | 164 | — | 5 contra 5 | — | -1,6 | depende da tática | segurar sozinho um ângulo de abertura é o trabalho do AWPer | [abrir](docs/match_09.html#replay?round=16&t=18.31) | sim / não / depende da tática | sim / reescrever |
| 4 | match_12 | 12 | 0:35 | flameZ | — | molodoy | 828 | 769 | — | 5 contra 5 | — | -3,5 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_12.html#replay?round=12&t=34.86) | sim / não / depende da tática | sim / reescrever |
| 5 | match_26 | 12 | 0:31 | donk | — | apEX | 546 | 502 | — | 5 contra 5 | — | -1,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_26.html#replay?round=12&t=30.84) | sim / não / depende da tática | sim / reescrever |
| 6 | match_32 | 26 | 0:56 | YEKINDAR | — | m0NESY | 129 | 1598 | — | 5 contra 5 | — | -7,1 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_32.html#replay?round=26&t=55.52) | sim / não / depende da tática | sim / reescrever |
| 7 | match_42 | 30 | 0:54 | kyousuke | — | torzsi | 188 | 1322 | — | 5 contra 5 | — | -11,5 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_42.html#replay?round=30&t=53.97) | sim / não / depende da tática | sim / reescrever |
| 8 | match_46 | 4 | 1:01 | ZywOo | — | yuurih | 215 | 1273 | — | 5 contra 5 | — | -3,3 | depende da tática | segurar sozinho um ângulo de abertura é o trabalho do AWPer | [abrir](docs/match_46.html#replay?round=4&t=60.92) | sim / não / depende da tática | sim / reescrever |
| 9 | match_52 | 2 | 0:18 | controlez | — | ropz | 411 | 1299 | — | 5 contra 5 | — | -3,8 | depende da tática | o dado mostra posição e tempo, não o que o time pediu | [abrir](docs/match_52.html#replay?round=2&t=18.06) | sim / não / depende da tática | sim / reescrever |
| 10 | match_53 | 15 | 0:12 | Mzinho | — | flameZ | 103 | 241 | — | 5 contra 5 | — | -1,0 | depende da tática | abrir o round é a função do entry; o que pesa é se o time trocou | [abrir](docs/match_53.html#replay?round=15&t=12.17) | sim / não / depende da tática | sim / reescrever |

#### Flash no time

Frase de como melhorar: "Avise antes de soltar e prefira a pop flash por cima do ângulo do aliado, não na frente dele."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_05 | 16 | 1:01 | lilpeepfan- | dorfen | — | — | — | — | 3 contra 1 | 4,9 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_05.html#replay?round=16&t=60.81) | sim / não / depende da tática | sim / reescrever |
| 2 | match_09 | 17 | 0:09 | Magnojezzz | zzeraj | — | — | — | — | 0 contra 0 | 6,1 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_09.html#replay?round=17&t=8.81) | sim / não / depende da tática | sim / reescrever |
| 3 | match_31 | 3 | 0:13 | molodoy | YEKINDAR | — | — | — | — | 0 contra 0 | 2,0 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_31.html#replay?round=3&t=12.53) | sim / não / depende da tática | sim / reescrever |
| 4 | match_31 | 14 | 1:10 | KSCERATO | FalleN | — | — | — | — | 4 contra 2 | 3,2 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_31.html#replay?round=14&t=69.72) | sim / não / depende da tática | sim / reescrever |
| 5 | match_37 | 21 | 0:08 | chopper | magixx | — | — | — | — | 0 contra 0 | 6,2 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_37.html#replay?round=21&t=8.22) | sim / não / depende da tática | sim / reescrever |
| 6 | match_38 | 19 | 0:08 | b1t | iM | — | — | — | — | 0 contra 0 | 3,8 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_38.html#replay?round=19&t=7.59) | sim / não / depende da tática | sim / reescrever |
| 7 | match_42 | 2 | 1:06 | m0NESY | NiKo | — | — | — | — | 5 contra 4 | 3,2 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_42.html#replay?round=2&t=66.19) | sim / não / depende da tática | sim / reescrever |
| 8 | match_42 | 36 | 0:10 | torzsi | Spinx | — | — | — | — | 0 contra 0 | 4,8 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_42.html#replay?round=36&t=9.91) | sim / não / depende da tática | sim / reescrever |
| 9 | match_50 | 9 | 0:17 | NiKo | kyousuke | — | — | — | — | 0 contra 0 | 4,4 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_50.html#replay?round=9&t=17.34) | sim / não / depende da tática | sim / reescrever |
| 10 | match_51 | 6 | 0:30 | kyxsan | NiKo | — | — | — | — | 0 contra 0 | 5,2 | — | explícito | a flash dele cegou o próprio time | [abrir](docs/match_51.html#replay?round=6&t=29.53) | sim / não / depende da tática | sim / reescrever |

#### Dano de utilidade no time

Frase de como melhorar: "Confira onde o time está antes de soltar HE ou molotov num ponto de passagem."

**A frase serve?** sim / reescrever: ____

| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador | dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | match_04 | 17 | 0:19 | nedorufe | L1nkero | — | — | — | — | 5 contra 4 | 9,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_04.html#replay?round=17&t=18.62) | sim / não / depende da tática | sim / reescrever |
| 2 | match_20 | 18 | 0:20 | TeSeS | kyousuke | — | — | — | — | 4 contra 4 | 38,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_20.html#replay?round=18&t=20.05) | sim / não / depende da tática | sim / reescrever |
| 3 | match_20 | 25 | 0:10 | FalleN | YEKINDAR | — | — | — | — | 0 contra 0 | 26,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_20.html#replay?round=25&t=10.33) | sim / não / depende da tática | sim / reescrever |
| 4 | match_24 | 18 | 0:35 | chopper | zont1x | — | — | — | — | 0 contra 0 | 28,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_24.html#replay?round=18&t=35.28) | sim / não / depende da tática | sim / reescrever |
| 5 | match_33 | 10 | 1:36 | ZywOo | flameZ | — | — | — | — | 0 contra 0 | 22,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_33.html#replay?round=10&t=95.59) | sim / não / depende da tática | sim / reescrever |
| 6 | match_39 | 11 | 1:28 | chopper | donk | — | — | — | — | 4 contra 3 | 24,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_39.html#replay?round=11&t=88.17) | sim / não / depende da tática | sim / reescrever |
| 7 | match_39 | 18 | 0:10 | magixx | chopper | — | — | — | — | 0 contra 0 | 45,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_39.html#replay?round=18&t=9.61) | sim / não / depende da tática | sim / reescrever |
| 8 | match_40 | 27 | 1:14 | b1t | iM | — | — | — | — | 2 contra 2 | 17,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_40.html#replay?round=27&t=73.64) | sim / não / depende da tática | sim / reescrever |
| 9 | match_40 | 30 | 0:28 | b1t | w0nderful | — | — | — | — | 0 contra 0 | 7,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_40.html#replay?round=30&t=28.34) | sim / não / depende da tática | sim / reescrever |
| 10 | match_50 | 10 | 0:25 | Brollan | Spinx | — | — | — | — | 0 contra 0 | 27,0 | — | explícito | a granada dele feriu o próprio time | [abrir](docs/match_50.html#replay?round=10&t=25.45) | sim / não / depende da tática | sim / reescrever |

### 7.3 Sua resposta

Para cada tipo: quantos dos 10 exemplos você confirma, e se a frase de como melhorar serve. O tipo com 8 ou mais confirmados entra em `TIPOS_DE_ERRO_VALIDADOS` (`metrics/erros.py`) num item à parte; os reprovados ficam fora da tela, e eu trago uma proposta de ajuste com os números.
