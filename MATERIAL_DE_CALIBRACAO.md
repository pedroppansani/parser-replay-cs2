# Material de calibração

Gerado por `py -3.12 -m scripts.material_calibracao`. Cada seção termina com a pergunta que só você responde; as respostas viram constante com data e tamanho de corpus no CLAUDE.md.

## 1. Pisos de função

Gerado por `py -3.12 -m scripts.proposta_pisos`. O rótulo exige **liderar o próprio time** na métrica E passar do piso; o piso barra o líder que não é destacado. Para cada função: a distribuição completa (todos os jogador-partidas e só os líderes), três métodos objetivos -- **maior vazio** entre valores consecutivos, **Otsu** (menor variância dentro das duas classes) e **vale da densidade** (KDE) --, o veredito de concordância e os líderes mais próximos de cada corte. Métodos que concordam = corte real; métodos que discordam = a métrica é um contínuo e o piso é convenção. Os pisos continuam ABSOLUTOS. O que é seu: olhar a fronteira e dizer se aquele jogador jogou a função naquela partida.

### AWPer — `awp_share`, piso atual 0.250

430 jogador-partidas profissionais em 43 partidas; 86 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.042     167 ##############################################
     0.042-0.083      84 #######################
     0.083-0.125      48 #############
     0.125-0.167      29 ########
     0.167-0.208      12 ###
     0.208-0.250      11 ###
     0.250-0.292       5 #   <- atual, vazio (todos), otsu (todos), vale (todos)
     0.292-0.333       3 #
     0.333-0.375       9 ##
     0.375-0.417       5 #
     0.417-0.458       6 ##
     0.458-0.500      10 ###
     0.500-0.542      12 ###
     0.542-0.583       7 ##
     0.583-0.625      10 ###
     0.625-0.667       6 ##
     0.667-0.708       3 #
     0.708-0.750       3 #
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.056-0.094       2 ######
     0.094-0.133       1 ###
     0.133-0.171       2 ######   <- vazio (líderes)
     0.171-0.210       3 #########
     0.210-0.248       5 ###############
     0.248-0.287       1 ###   <- atual
     0.287-0.326       2 ######
     0.326-0.364       7 #####################
     0.364-0.403       6 ##################
     0.403-0.441       1 ###   <- otsu (líderes)
     0.441-0.480      15 ##############################################
     0.480-0.519       6 ##################
     0.519-0.557       8 #########################
     0.557-0.596       8 #########################
     0.596-0.634      10 ###############################
     0.634-0.673       4 ############
     0.673-0.711       3 #########
     0.711-0.750       2 ######
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.250 | 73 de 86 |
| vazio (todos) | 0.271 | 73 de 86 |
| otsu (todos) | 0.271 | 73 de 86 |
| vale (todos) | 0.289 | 72 de 86 |
| vazio (líderes) | 0.158 | 81 de 86 |
| otsu (líderes) | 0.414 | 57 de 86 |
| vale (líderes) | sem corte (distribuição unimodal) | — |

- todos: espalhamento 0.12 amplitude interquartil (0.143) -> **CONCORDAM**, mediana 0.271
- líderes: espalhamento 1.13 amplitude interquartil (0.227) -> **discordam**

**Veredito: corte real em 0.271** (métodos concordam entre todos). Piso atual 0.250: 73 líderes com rótulo; sugerido: 73.

**Fronteira do corte atual (0.250)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | awp_share |
|---|---|---|---|---|---|
| rótulo | ZywOo | Team Vitality | match_43 | mirage | 0.333 |
| rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.333 |
| rótulo | w0nderful | Natus Vincere | match_15 | mirage | 0.312 |
| rótulo | ZywOo | Team Vitality | match_14 | ancient | 0.304 |
| rótulo | torzsi | MOUZ | match_35 | inferno | 0.286 |
| — corte 0.250 — | | | | | |
| sem rótulo | ZywOo | Team Vitality | match_35 | inferno | 0.238 |
| sem rótulo | w0nderful | Natus Vincere | match_38 | mirage | 0.238 |
| sem rótulo | 910 | The MongolZ | match_52 | mirage | 0.222 |
| sem rótulo | sh1ro | Team Spirit | match_28 | mirage | 0.217 |
| sem rótulo | w0nderful | Natus Vincere | match_25 | anubis | 0.211 |

**Fronteira do corte sugerido (0.271)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | awp_share |
|---|---|---|---|---|---|
| rótulo | ZywOo | Team Vitality | match_43 | mirage | 0.333 |
| rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.333 |
| rótulo | w0nderful | Natus Vincere | match_15 | mirage | 0.312 |
| rótulo | ZywOo | Team Vitality | match_14 | ancient | 0.304 |
| rótulo | torzsi | MOUZ | match_35 | inferno | 0.286 |
| — corte 0.271 — | | | | | |
| sem rótulo | ZywOo | Team Vitality | match_35 | inferno | 0.238 |
| sem rótulo | w0nderful | Natus Vincere | match_38 | mirage | 0.238 |
| sem rótulo | 910 | The MongolZ | match_52 | mirage | 0.222 |
| sem rótulo | sh1ro | Team Spirit | match_28 | mirage | 0.217 |
| sem rótulo | w0nderful | Natus Vincere | match_25 | anubis | 0.211 |

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

### Lurker — `off_team_share`, piso atual 0.400

429 jogador-partidas profissionais em 43 partidas; 109 líderes de time (empate na liderança conta os dois).

Distribuição -- TODOS (as marcas são os cortes de cada método):
```
     0.000-0.056      79 ##############################################   <- vazio (todos)
     0.056-0.111      24 ##############
     0.111-0.167      37 ######################
     0.167-0.222      25 ###############   <- vale (todos)
     0.222-0.278      31 ##################
     0.278-0.333      21 ############   <- otsu (todos)
     0.333-0.389      51 ##############################
     0.389-0.444      34 ####################   <- atual
     0.444-0.500      16 #########
     0.500-0.556      46 ###########################
     0.556-0.611      28 ################
     0.611-0.667       9 #####
     0.667-0.722      12 #######
     0.722-0.778       4 ##
     0.778-0.833       6 ###
     0.833-0.889       3 ##
     0.889-0.944       0 
     0.944-1.000       3 ##
```

Distribuição -- LÍDERES (as marcas são os cortes de cada método):
```
     0.000-0.056      15 ######################################
     0.056-0.111       5 #############
     0.111-0.167       7 ##################
     0.167-0.222       4 ##########
     0.222-0.278       0    <- vazio (líderes), vale (líderes)
     0.278-0.333       1 ###   <- otsu (líderes)
     0.333-0.389       3 ########
     0.389-0.444       7 ##################   <- atual
     0.444-0.500       4 ##########
     0.500-0.556      18 ##############################################
     0.556-0.611      18 ##############################################
     0.611-0.667       7 ##################
     0.667-0.722       6 ###############
     0.722-0.778       2 #####
     0.778-0.833       6 ###############
     0.833-0.889       3 ########
     0.889-0.944       0 
     0.944-1.000       3 ########
```

| método | corte | líderes que levam o rótulo |
|---|---|---|
| atual | 0.400 | 74 de 109 |
| vazio (todos) | 0.033 | 94 de 109 |
| otsu (todos) | 0.321 | 77 de 109 |
| vale (todos) | 0.215 | 78 de 109 |
| vazio (líderes) | 0.243 | 78 de 109 |
| otsu (líderes) | 0.325 | 77 de 109 |
| vale (líderes) | 0.264 | 78 de 109 |

- todos: espalhamento 0.77 amplitude interquartil (0.375) -> **discordam**
- líderes: espalhamento 0.19 amplitude interquartil (0.433) -> **CONCORDAM**, mediana 0.264

**Veredito: corte real em 0.264** (métodos concordam entre líderes). Piso atual 0.400: 74 líderes com rótulo; sugerido: 78.

**Fronteira do corte atual (0.400)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | off_team_share |
|---|---|---|---|---|---|
| rótulo | mezii | Team Vitality | match_44 | inferno | 0.400 |
| rótulo | zont1x | Team Spirit | match_39 | dust2 | 0.400 |
| rótulo | apEX | Team Vitality | match_33 | dust2 | 0.400 |
| rótulo | YEKINDAR | FURIA | match_29 | inferno | 0.400 |
| rótulo | makazze | Natus Vincere | match_15 | mirage | 0.400 |
| — corte 0.400 — | | | | | |
| sem rótulo | m0NESY | Falcons | match_20 | mirage | 0.385 |
| sem rótulo | KSCERATO | FURIA | match_12 | overpass | 0.364 |
| sem rótulo | xertioN | MOUZ | match_50 | inferno | 0.364 |
| sem rótulo | YEKINDAR | FURIA | match_44 | inferno | 0.286 |
| sem rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.200 |

**Fronteira do corte sugerido (0.264)** -- os 5 líderes mais próximos de cada lado:

| lado | jogador | time | partida | mapa | off_team_share |
|---|---|---|---|---|---|
| rótulo | makazze | Natus Vincere | match_15 | mirage | 0.400 |
| rótulo | m0NESY | Falcons | match_20 | mirage | 0.385 |
| rótulo | xertioN | MOUZ | match_50 | inferno | 0.364 |
| rótulo | KSCERATO | FURIA | match_12 | overpass | 0.364 |
| rótulo | YEKINDAR | FURIA | match_44 | inferno | 0.286 |
| — corte 0.264 — | | | | | |
| sem rótulo | sh1ro | Team Spirit | match_27 | nuke | 0.200 |
| sem rótulo | Jimpphat | MOUZ | match_51 | nuke | 0.200 |
| sem rótulo | kyxsan | Team Falcons | match_51 | nuke | 0.182 |
| sem rótulo | woxic | Aurora Gaming | match_21 | nuke | 0.167 |
| sem rótulo | YEKINDAR | FURIA | match_16 | nuke | 0.154 |

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

O modelo em uso foi ajustado em **1870 jogador-rounds (as 9 partidas de FACEIT)** e aplicado às 52. Reajustado nas 52 (11520 jogador-rounds, sem gravar): índice de Rand ajustado **0.49**, e 79% dos rounds ficam no mesmo grupo. **Os quatro perfis reaparecem** -- são os mesmos quatro jeitos --, mas os NÚMEROS dos grupos trocam, e o maior deles perde parte dos rounds para outro. Por isso os nomes abaixo estão presos ao perfil, não ao número: se o modelo for reajustado, cada nome segue o seu perfil. Reajustar é decisão sua (`py -3.12 -m scripts.fit_global_clusters`); recomendo antes de gravar os nomes.

| perfil | grupo hoje | vira no reajuste | rounds que ficam juntos |
|---|---|---|---|
| longe | 0 | 2 | 2334 de 2749 (85%) |
| mira | 1 | 0 | 736 de 762 (97%) |
| roda | 2 | 3 | 3343 de 5276 (63%) |
| junto | 3 | 1 | 2725 de 2733 (100%) |

### Perfil "longe" -- grupo 0 hoje (2749 jogador-rounds, 24% do corpus; CT 2011, TR 738)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| distância média do time **(distingue)** | 1161.14u | 709.70u | +1.25 |
| maior distância do time no round **(distingue)** | 1779.22u | 1238.95u | +1.09 |
| regiões diferentes visitadas **(distingue)** | 4.70 | 5.99 | -0.55 |
| placement da mira (0-100) | 72.06 | 68.39 | +0.35 |
| mira na altura da cabeça (0-1) | 0.91 | 0.87 | +0.26 |
| tempo até o 1º contato | 43.76s | 47.84s | -0.13 |
| fração do tempo entrando em briga | 0.09 | 0.11 | -0.13 |

Mapa mais super-representado: inferno (1.3x a fatia do corpus).

**Nomes candidatos:**
- **Joga isolado** -- distância média do time 1161u contra 710u (+1.25 desvio)
- **Segura longe do time** -- maior distância no round 1779u (+1.09) com poucas regiões visitadas (-0.55): fica parado, longe
- **Posição solitária** -- 73% dos rounds deste grupo são de CT: é o jeito de defender um ponto sozinho

**Sua resposta:** perfil "longe" = ____

### Perfil "mira" -- grupo 1 hoje (762 jogador-rounds, 7% do corpus; CT 399, TR 363)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| mira na altura da cabeça (0-1) **(distingue)** | 0.51 | 0.87 | -2.69 |
| placement da mira (0-100) **(distingue)** | 50.33 | 68.39 | -1.71 |
| maior distância do time no round | 1007.53u | 1238.95u | -0.47 |
| fração do tempo entrando em briga | 0.15 | 0.11 | +0.33 |
| distância média do time | 597.55u | 709.70u | -0.31 |
| tempo até o 1º contato | 38.58s | 47.84s | -0.30 |
| regiões diferentes visitadas | 5.49 | 5.99 | -0.21 |

Mapa mais super-representado: nuke (2.1x a fatia do corpus). **Atenção:** 36% dos rounds deste grupo são em nuke (o corpus tem 17%, 2.1x) -- parte do grupo pode ser efeito do mapa, não estilo.

**Nomes candidatos:**
- **Mira fora da altura** -- mira na altura da cabeça 0.51 contra 0.87 (-2.69 desvio) -- o traço mais forte de todos os grupos
- **Crosshair baixo** -- placement 50 contra 68 (-1.71); o resto do perfil fica perto da média
- **Mira desajustada** -- o grupo é definido só pela mira: posição, tempo e movimento são os da média

**Sua resposta:** perfil "mira" = ____

### Perfil "roda" -- grupo 2 hoje (5276 jogador-rounds, 46% do corpus; CT 2306, TR 2970)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| regiões diferentes visitadas **(distingue)** | 7.43 | 5.99 | +0.61 |
| tempo até o 1º contato **(distingue)** | 64.85s | 47.84s | +0.55 |
| fração do tempo entrando em briga | 0.06 | 0.11 | -0.35 |
| distância média do time | 633.98u | 709.70u | -0.21 |
| placement da mira (0-100) | 67.03 | 68.39 | -0.13 |
| mira na altura da cabeça (0-1) | 0.88 | 0.87 | +0.06 |
| maior distância do time no round | 1223.85u | 1238.95u | -0.03 |

Mapa mais super-representado: overpass (1.4x a fatia do corpus).

**Nomes candidatos:**
- **Roda o mapa** -- 7.4 regiões por round contra 6.0 (+0.61 desvio)
- **Contato tardio** -- primeiro contato aos 65s contra 48s (+0.55)
- **Joga o relógio** -- chega tarde e evita briga (tempo entrando em briga -0.35 desvio)

**Sua resposta:** perfil "roda" = ____

### Perfil "junto" -- grupo 3 hoje (2733 jogador-rounds, 24% do corpus; CT 1044, TR 1689)

| feature | média do grupo | média geral | desvio (z) |
|---|---|---|---|
| maior distância do time no round **(distingue)** | 789.17u | 1238.95u | -0.91 |
| tempo até o 1º contato **(distingue)** | 21.70s | 47.84s | -0.85 |
| distância média do time **(distingue)** | 433.06u | 709.70u | -0.77 |
| fração do tempo entrando em briga **(distingue)** | 0.19 | 0.11 | +0.72 |
| regiões diferentes visitadas **(distingue)** | 4.64 | 5.99 | -0.57 |
| placement da mira (0-100) | 72.39 | 68.39 | +0.38 |
| mira na altura da cabeça (0-1) | 0.92 | 0.87 | +0.36 |

Mapa mais super-representado: ancient (1.9x a fatia do corpus). **Atenção:** 11% dos rounds deste grupo são em ancient (o corpus tem 6%, 1.9x) -- parte do grupo pode ser efeito do mapa, não estilo.

**Nomes candidatos:**
- **Junto e rápido** -- maior distância do time 789u contra 1239u (-0.91) e contato aos 22s (-0.85)
- **Entra em bloco** -- entra em briga +0.72 desvio acima da média, colado no time (-0.77)
- **Execução em grupo** -- 62% dos rounds deste grupo são de TR: é o jeito de executar um bomb junto

**Sua resposta:** perfil "junto" = ____

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
