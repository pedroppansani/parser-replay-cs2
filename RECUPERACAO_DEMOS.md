# Recuperação das demos apagadas (plano, NADA executado)

Gerado em 2026-09-27 a partir de `data/manifest.json`. As 52 demos foram apagadas
por `scripts/clean_match.py` em 2026-09-19 02:52 (horário local), com a autorização
"pode apagar só as demos"; só a match_23 sobreviveu (tinha mudado de pasta).
Uma demo baixada de novo só substitui a apagada se o sha256 do `.dem` bater
com o da coluna (hash do arquivo `.dem`, não do pacote baixado).

| partida | origem | mapa | evento / confronto (mapa da série) | HLTV | arquivos .dem | sha256 no manifesto | dá para baixar de novo? |
|---|---|---|---|---|---|---|---|
| match_01 | faceit | de_ancient | - | não | 1 | sim: `1-0007ce25-1e02-40fa-9eb0-1bba64c71b12-1-1.dem` 796b51156e56985d… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_02 | faceit | de_mirage | - | não | 1 | sim: `1-07642af7-6568-4661-9aeb-a420adeaad61-1-1.dem` 698bf3f2f4adbf06… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_03 | faceit | de_anubis | - | não | 1 | sim: `1-22abf937-659e-4363-9933-cc2a2ae99370-1-1.dem` 522d50f86f5298d4… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_04 | faceit | de_ancient | - | não | 1 | sim: `1-50a6313e-9399-4821-848e-f3b25a683149-1-1.dem` 8335d600fc7d2771… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_05 | faceit | de_nuke | - | não | 1 | sim: `1-764e1ec7-1f00-4168-9eed-9741ee3a00e6-1-1.dem` b371cd555eefa72a… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_06 | faceit | de_mirage | - | não | 1 | sim: `1-7de2c606-5a1c-4496-9a78-4f9e066aa348-1-1.dem` 7b8894a2ffc23646… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_07 | faceit | de_mirage | - | não | 1 | sim: `1-9be6d5a6-abda-4110-908d-deae67dee533-1-1.dem` eb8853783b98a789… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_08 | faceit | de_mirage | - | não | 1 | sim: `1-a2985358-eb2a-4b11-b891-534de044e54e-1-1.dem` d280be30ec5469dc… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_09 | faceit | de_mirage | - | não | 1 | sim: `1-c4169514-a91a-470c-9fa7-11413f06ff45-1-1.dem` d73e40ae595453e9… | incerto: demo de FACEIT, pode ter expirado; o id da partida está no nome do arquivo |
| match_10 | profissional | de_dust2 | iem-cologne-major-2026 / natus-vincere-vs-spirit (1) | sim | 1 | sim: `natus-vincere-vs-spirit-m1-dust2.dem` 00bdd0bfd427775a… | sim: página da HLTV registrada (https://www.hltv.org/matches/2394900/natus-vincere-vs-spirit) |
| match_11 | profissional | de_anubis | iem-cologne-major-2026 / natus-vincere-vs-spirit (2) | sim | 1 | sim: `natus-vincere-vs-spirit-m2-anubis.dem` 8ae575cacb202bbc… | sim: página da HLTV registrada (https://www.hltv.org/matches/2394900/natus-vincere-vs-spirit) |
| match_12 | profissional | de_overpass | iem-rio-2026 / furia-vs-vitality (1) | sim | 2 | sim: `furia-vs-vitality-m1-overpass-p1.dem` d6ded5f8f72cdc11…; `furia-vs-vitality-m1-overpass-p2.dem` 214cd0f09b4a3475… | sim: página da HLTV registrada (https://www.hltv.org/matches/2393243/furia-vs-vitality) |
| match_14 | profissional | de_ancient | iem-rio-2026 / furia-vs-vitality (2) | sim | 1 | sim: `furia-vs-vitality-m2-ancient.dem` a423d8fa9bcd7724… | sim: página da HLTV registrada (https://www.hltv.org/matches/2393243/furia-vs-vitality) |
| match_15 | profissional | de_mirage | iem-rio-2026 / natus-vincere-vs-furia (1) | sim | 1 | sim: `natus-vincere-vs-furia-m1-mirage.dem` 1bfb43118089c783… | sim: página da HLTV registrada (https://www.hltv.org/matches/2393228/natus-vincere-vs-furia) |
| match_16 | profissional | de_nuke | iem-rio-2026 / natus-vincere-vs-furia (3) | sim | 1 | sim: `natus-vincere-vs-furia-m3-nuke.dem` 87356d11bdeb8616… | sim: página da HLTV registrada (https://www.hltv.org/matches/2393228/natus-vincere-vs-furia) |
| match_17 | profissional | de_dust2 | iem-rio-2026 / natus-vincere-vs-furia (2) | sim | 1 | sim: `natus-vincere-vs-furia-m2-dust2.dem` bc517609cf2e2086… | sim: página da HLTV registrada (https://www.hltv.org/matches/2393228/natus-vincere-vs-furia) |
| match_18 | profissional | de_anubis | pgl-cluj-napoca-2026 / furia-vs-falcons (3) | sim | 1 | sim: `furia-vs-falcons-m3-anubis.dem` 42aa5f5826231e01… | sim: página da HLTV registrada (https://www.hltv.org/matches/2389969/furia-vs-falcons) |
| match_19 | profissional | de_inferno | pgl-cluj-napoca-2026 / furia-vs-falcons (2) | sim | 1 | sim: `furia-vs-falcons-m2-inferno.dem` c358451d9f613bec… | sim: página da HLTV registrada (https://www.hltv.org/matches/2389969/furia-vs-falcons) |
| match_20 | profissional | de_mirage | pgl-cluj-napoca-2026 / furia-vs-falcons (1) | sim | 1 | sim: `furia-vs-falcons-m1-mirage.dem` 3ada17dbeb8b7122… | sim: página da HLTV registrada (https://www.hltv.org/matches/2389969/furia-vs-falcons) |
| match_21 | profissional | de_nuke | starladder-starseries-fall-2026 / natus-vincere-vs-aurora (1) | não | 1 | sim: `natus-vincere-vs-aurora-m1-nuke.dem` d84b02b61af2e213… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_22 | profissional | de_mirage | starladder-starseries-fall-2026 / natus-vincere-vs-aurora (2) | não | 1 | sim: `natus-vincere-vs-aurora-m2-mirage.dem` 067680a00c73c69d… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_23 | profissional | de_dust2 | starladder-starseries-fall-2026 / vitality-vs-magic (2) | sim | 1 | sim: `vitality-vs-magic-m2-dust2.dem` f18e6acd0f4dcf35… | não precisa: está no disco e no backup de 2026-09-27 |
| match_24 | profissional | de_dust2 | blast-open-lisbon-2025 / spirit-vs-natus-vincere (1) | não | 1 | sim: `spirit-vs-natus-vincere-m1-dust2.dem` 51ced3a89c8e8bba… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_25 | profissional | de_anubis | blast-open-lisbon-2025 / spirit-vs-natus-vincere (2) | não | 1 | sim: `spirit-vs-natus-vincere-m2-anubis.dem` b9a4b505d1c079ba… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_26 | profissional | de_anubis | blast-open-lisbon-2025 / vitality-vs-spirit (1) | não | 1 | sim: `vitality-vs-spirit-m1-anubis.dem` 3b2169c84d3d6473… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_27 | profissional | de_nuke | blast-open-lisbon-2025 / vitality-vs-spirit (2) | não | 1 | sim: `vitality-vs-spirit-m2-nuke.dem` de0b5de35e98b352… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_28 | profissional | de_mirage | blast-open-lisbon-2025 / vitality-vs-spirit (3) | não | 1 | sim: `vitality-vs-spirit-m3-mirage.dem` cf8a96f821b87aee… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_29 | profissional | de_inferno | blast-rivals-2025-season-2 / furia-vs-falcons (1) | não | 1 | sim: `furia-vs-falcons-m1-inferno.dem` ea651630d1bcd206… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_30 | profissional | de_nuke | blast-rivals-2025-season-2 / furia-vs-falcons (2) | não | 1 | sim: `furia-vs-falcons-m2-nuke.dem` 91d445ca120fb4fc… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_31 | profissional | de_train | blast-rivals-2025-season-2 / furia-vs-falcons (3) | não | 1 | sim: `furia-vs-falcons-m3-train.dem` 2735218148a4a12a… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_32 | profissional | de_mirage | blast-rivals-2025-season-2 / furia-vs-falcons (4) | não | 1 | sim: `furia-vs-falcons-m4-mirage.dem` c20f551ef270bd34… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_33 | profissional | de_dust2 | iem-dallas-2025 / mouz-vs-vitality (1) | não | 1 | sim: `mouz-vs-vitality-m1-dust2.dem` 372557cd3b27fbda… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_34 | profissional | de_mirage | iem-dallas-2025 / mouz-vs-vitality (2) | não | 1 | sim: `mouz-vs-vitality-m2-mirage.dem` 6ed3d0ed29588b08… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_35 | profissional | de_inferno | iem-dallas-2025 / mouz-vs-vitality (3) | não | 1 | sim: `mouz-vs-vitality-m3-inferno.dem` 617673668137ac4f… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_36 | profissional | de_mirage | iem-katowice-2025 / natus-vincere-vs-spirit (1) | não | 1 | sim: `natus-vincere-vs-spirit-m1-mirage.dem` a4e69281dfacf9f2… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_37 | profissional | de_dust2 | iem-katowice-2025 / natus-vincere-vs-spirit (2) | não | 1 | sim: `natus-vincere-vs-spirit-m2-dust2.dem` 077731a93eebecf6… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_38 | profissional | de_mirage | iem-katowice-2025 / natus-vincere-vs-spirit (1) | não | 1 | sim: `natus-vincere-vs-spirit-m1-mirage.dem` 0b170f4706cc446f… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_39 | profissional | de_dust2 | iem-katowice-2025 / natus-vincere-vs-spirit (2) | não | 3 | sim: `natus-vincere-vs-spirit-m2-dust2-p1.dem` 669af697b423c2cc…; `natus-vincere-vs-spirit-m2-dust2-p2.dem` 68e4ecf46575438a…; `natus-vincere-vs-spirit-m2-dust2-p3.dem` dc0f8c4bfdeed063… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_40 | profissional | de_nuke | iem-katowice-2025 / natus-vincere-vs-spirit (3) | não | 1 | sim: `natus-vincere-vs-spirit-m3-nuke.dem` ff92283d6a9c6c8e… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_41 | profissional | de_inferno | iem-krakw-2026 / falcons-vs-mouz (1) | sim | 2 | sim: `falcons-vs-mouz-m1-inferno-p1.dem` 24d5c304b7614d54…; `falcons-vs-mouz-m1-inferno-p2.dem` 4164738a697e2300… | sim: página da HLTV registrada (https://www.hltv.org/matches/2389660/falcons-vs-mouz) |
| match_42 | profissional | de_dust2 | iem-krakw-2026 / falcons-vs-mouz (2) | sim | 1 | sim: `falcons-vs-mouz-m2-dust2.dem` 0a3129ba726a1023… | sim: página da HLTV registrada (https://www.hltv.org/matches/2389660/falcons-vs-mouz) |
| match_43 | profissional | de_mirage | iem-krakw-2026 / furia-vs-vitality (1) | não | 1 | sim: `furia-vs-vitality-m1-mirage.dem` 9019e9ee6cdeee54… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_44 | profissional | de_inferno | iem-krakw-2026 / furia-vs-vitality (2) | não | 1 | sim: `furia-vs-vitality-m2-inferno.dem` affd22a7fb10a99d… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_45 | profissional | de_nuke | iem-krakw-2026 / furia-vs-vitality (3) | não | 1 | sim: `furia-vs-vitality-m3-nuke.dem` 2b2f6f3ceeb869dc… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_46 | profissional | de_overpass | iem-krakw-2026 / furia-vs-vitality (4) | não | 1 | sim: `furia-vs-vitality-m4-overpass.dem` 24370e1f72c2f2ca… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_47 | profissional | de_nuke | iem-krakw-2026 / vitality-vs-mouz (1) | não | 1 | sim: `vitality-vs-mouz-m1-nuke.dem` 061cb84a8f284815… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_48 | profissional | de_dust2 | iem-krakw-2026 / vitality-vs-mouz (2) | não | 1 | sim: `vitality-vs-mouz-m2-dust2.dem` c33d48b9dbb8f079… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_49 | profissional | de_mirage | starladder-budapest-major-2025 / mouz-vs-falcons (1) | não | 1 | sim: `mouz-vs-falcons-m1-mirage.dem` 80e8b0f338d0294d… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_50 | profissional | de_inferno | starladder-budapest-major-2025 / mouz-vs-falcons (2) | não | 1 | sim: `mouz-vs-falcons-m2-inferno.dem` bcda5d9d0dfdee6a… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_51 | profissional | de_nuke | starladder-budapest-major-2025 / mouz-vs-falcons (3) | não | 1 | sim: `mouz-vs-falcons-m3-nuke.dem` daf6611302cc68db… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_52 | profissional | de_mirage | starladder-budapest-major-2025 / vitality-vs-the-mongolz (1) | não | 1 | sim: `vitality-vs-the-mongolz-m1-mirage.dem` 3433a2ab957a174f… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |
| match_53 | profissional | de_dust2 | starladder-budapest-major-2025 / vitality-vs-the-mongolz (2) | não | 1 | sim: `vitality-vs-the-mongolz-m2-dust2.dem` 9c2f1d0d9ad881df… | provável: campeonato sem link da HLTV no manifesto; achar a série pelo evento e confronto |

Resumo: {'sim': 12, 'provável': 30, 'incerto': 9, 'não precisa': 1}. sha256 disponível para as 52 partidas.

## Lista de busca: campeonato sem link da HLTV (30 partidas, NADA baixado)

Para achar a série na HLTV pelo evento, o confronto e a data. A data é a de
modificação do .dem (costuma ser o fim da gravação), não a conferida na HLTV.

| partida | evento | confronto | mapa da série | mapa | data do arquivo | sha256 (16) |
|---|---|---|---|---|---|---|
| match_21 | starladder-starseries-fall-2026 | natus-vincere-vs-aurora | 1 | de_nuke | 2026-09-17T13:23 | d84b02b61af2e213 |
| match_22 | starladder-starseries-fall-2026 | natus-vincere-vs-aurora | 2 | de_mirage | 2026-09-17T13:56 | 067680a00c73c69d |
| match_24 | blast-open-lisbon-2025 | spirit-vs-natus-vincere | 1 | de_dust2 | 2025-03-28T18:05 | 51ced3a89c8e8bba |
| match_25 | blast-open-lisbon-2025 | spirit-vs-natus-vincere | 2 | de_anubis | 2025-03-28T18:28 | b9a4b505d1c079ba |
| match_26 | blast-open-lisbon-2025 | vitality-vs-spirit | 1 | de_anubis | 2025-03-29T18:14 | 3b2169c84d3d6473 |
| match_27 | blast-open-lisbon-2025 | vitality-vs-spirit | 2 | de_nuke | 2025-03-29T19:04 | de0b5de35e98b352 |
| match_28 | blast-open-lisbon-2025 | vitality-vs-spirit | 3 | de_mirage | 2025-03-29T20:07 | cf8a96f821b87aee |
| match_29 | blast-rivals-2025-season-2 | furia-vs-falcons | 1 | de_inferno | 2025-11-16T10:19 | ea651630d1bcd206 |
| match_30 | blast-rivals-2025-season-2 | furia-vs-falcons | 2 | de_nuke | 2025-11-16T10:19 | 91d445ca120fb4fc |
| match_31 | blast-rivals-2025-season-2 | furia-vs-falcons | 3 | de_train | 2025-11-16T10:20 | 2735218148a4a12a |
| match_32 | blast-rivals-2025-season-2 | furia-vs-falcons | 4 | de_mirage | 2025-11-16T10:20 | c20f551ef270bd34 |
| match_33 | iem-dallas-2025 | mouz-vs-vitality | 1 | de_dust2 | 2025-05-25T17:34 | 372557cd3b27fbda |
| match_34 | iem-dallas-2025 | mouz-vs-vitality | 2 | de_mirage | 2025-05-25T18:38 | 6ed3d0ed29588b08 |
| match_35 | iem-dallas-2025 | mouz-vs-vitality | 3 | de_inferno | 2025-05-25T19:45 | 617673668137ac4f |
| match_36 | iem-katowice-2025 | natus-vincere-vs-spirit | 1 | de_mirage | 2025-02-08T15:50 | a4e69281dfacf9f2 |
| match_37 | iem-katowice-2025 | natus-vincere-vs-spirit | 2 | de_dust2 | 2025-02-08T17:25 | 077731a93eebecf6 |
| match_38 | iem-katowice-2025 | natus-vincere-vs-spirit | 1 | de_mirage | 2025-02-03T12:47 | 0b170f4706cc446f |
| match_39 | iem-katowice-2025 | natus-vincere-vs-spirit | 2 | de_dust2 | 2025-02-03T14:11 | 669af697b423c2cc; 68e4ecf46575438a; dc0f8c4bfdeed063 |
| match_40 | iem-katowice-2025 | natus-vincere-vs-spirit | 3 | de_nuke | 2025-02-03T15:33 | ff92283d6a9c6c8e |
| match_43 | iem-krakw-2026 | furia-vs-vitality | 1 | de_mirage | 2026-02-08T13:54 | 9019e9ee6cdeee54 |
| match_44 | iem-krakw-2026 | furia-vs-vitality | 2 | de_inferno | 2026-02-08T15:04 | affd22a7fb10a99d |
| match_45 | iem-krakw-2026 | furia-vs-vitality | 3 | de_nuke | 2026-02-08T15:52 | 2b2f6f3ceeb869dc |
| match_46 | iem-krakw-2026 | furia-vs-vitality | 4 | de_overpass | 2026-02-08T17:15 | 24370e1f72c2f2ca |
| match_47 | iem-krakw-2026 | vitality-vs-mouz | 1 | de_nuke | 2026-02-07T16:57 | 061cb84a8f284815 |
| match_48 | iem-krakw-2026 | vitality-vs-mouz | 2 | de_dust2 | 2026-02-07T17:59 | c33d48b9dbb8f079 |
| match_49 | starladder-budapest-major-2025 | mouz-vs-falcons | 1 | de_mirage | 2025-12-06T15:18 | 80e8b0f338d0294d |
| match_50 | starladder-budapest-major-2025 | mouz-vs-falcons | 2 | de_inferno | 2025-12-06T16:43 | bcda5d9d0dfdee6a |
| match_51 | starladder-budapest-major-2025 | mouz-vs-falcons | 3 | de_nuke | 2025-12-06T16:53 | daf6611302cc68db |
| match_52 | starladder-budapest-major-2025 | vitality-vs-the-mongolz | 1 | de_mirage | 2025-12-11T17:12 | 3433a2ab957a174f |
| match_53 | starladder-budapest-major-2025 | vitality-vs-the-mongolz | 2 | de_dust2 | 2025-12-11T18:07 | 9c2f1d0d9ad881df |

## Download das 12 com link (autorizado, NÃO feito)

A HLTV responde 403 ao acesso automatizado (curl e WebFetch, 2026-09-27). O
download tem de ser feito no navegador: 6 séries, 7,55 GB de .dem no corpus (o
pacote de cada série traz também os mapas fora do corpus). Depois de salvar em
`demos/`, cada .dem é conferido pelo sha256 do manifesto antes de entrar.
