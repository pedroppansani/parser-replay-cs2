# Recuperação das demos apagadas

## RESUMO: o que baixar (só isto)

5 séries, pela página da HLTV (botão "GOTV Demo"), soltas em `demos/entrada/`:

| # | série | página | mapas do corpus |
|---|---|---|---|
| 1 | NaVi x Spirit, IEM Cologne Major 2026 | https://www.hltv.org/matches/2394900/natus-vincere-vs-spirit | match_10 Dust2, match_11 Anubis |
| 2 | FURIA x Vitality, IEM Rio 2026 | https://www.hltv.org/matches/2393243/furia-vs-vitality | match_12 Overpass, match_14 Ancient |
| 3 | NaVi x FURIA, IEM Rio 2026 | https://www.hltv.org/matches/2393228/natus-vincere-vs-furia | match_15 Mirage, match_16 Nuke, match_17 Dust2 |
| 4 | FURIA x Falcons, PGL Cluj-Napoca 2026 | https://www.hltv.org/matches/2389969/furia-vs-falcons | match_18 Anubis, match_19 Inferno, match_20 Mirage |
| 5 | Falcons x MOUZ, IEM Kraków 2026 | https://www.hltv.org/matches/2389660/falcons-vs-mouz | match_41 Inferno, match_42 Dust2 |

NÃO precisa baixar: Vitality x Magic (match_23 já está no disco), as 30 de
campeonato sem link (só a lista de busca, mais abaixo) e as 9 da FACEIT.
Depois de soltar os arquivos, me avise; eu rodo `py -3.12 -m scripts.importa_demos`,
que confere cada .dem pelo sha256. O resto deste arquivo é referência.

---

## Referência

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

## Para baixar (6 séries com link da HLTV; download MANUAL, pelo navegador)

A HLTV responde 403 a acesso automatizado. Baixe cada série pela página (botão
"GOTV Demo") e solte o arquivo, compactado ou não, em `demos/entrada/`. Depois:

    py -3.12 -m scripts.importa_demos --simular   # confere o que vai acontecer
    py -3.12 -m scripts.importa_demos             # importa pelo sha256, copia para o backup
    py -3.12 -m scripts.manifest                  # marca as demos como existentes

O nome do pacote abaixo é o PROVÁVEL (é o nome da pasta onde o .dem estava antes
de ser apagado); ele não importa, porque o script identifica cada .dem pelo
sha256. O pacote traz também os mapas da série fora do corpus: eles ficam em
`demos/entrada/` e são listados. A match_23 já está no disco (não precisa baixar
a série vitality-vs-magic, a não ser pelos outros mapas).

### iem-cologne-major-2026 · natus-vincere-vs-spirit

- página: https://www.hltv.org/matches/2394900/natus-vincere-vs-spirit
- pacote provável: `iem-cologne-major-2026-natus-vincere-vs-spirit-bo3-kgjfQml_20SbX4SdXD-5FD.rar`
- .dem do corpus no pacote: 0.82 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_10 | de_dust2 | 1 | `natus-vincere-vs-spirit-m1-dust2.dem` | `00bdd0bfd427775a3cd1844a726c84353dad37517b89a887597a895ba4fc88ff` |
| match_11 | de_anubis | 2 | `natus-vincere-vs-spirit-m2-anubis.dem` | `8ae575cacb202bbcf13b26ccd6984c01bd95eeb0243a74daa74fa53e15321db2` |

### iem-rio-2026 · furia-vs-vitality

- página: https://www.hltv.org/matches/2393243/furia-vs-vitality
- pacote provável: `iem-rio-2026-furia-vs-vitality-bo3--OutGDctKNBZKy28qkTgMB - Copia.rar`
- .dem do corpus no pacote: 1.16 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_12 | de_overpass | 1 | `furia-vs-vitality-m1-overpass-p1.dem` | `d6ded5f8f72cdc11dfe86949752f3158b789aeb8981ef07e2a13feb08dc0ecb4` |
| match_12 | de_overpass | 1 | `furia-vs-vitality-m1-overpass-p2.dem` | `214cd0f09b4a347592e340645e6dff1e75c60d76b6a04b2086a06b20e504f0b9` |
| match_14 | de_ancient | 2 | `furia-vs-vitality-m2-ancient.dem` | `a423d8fa9bcd7724118cccdde81bc99dac9b0de37ec3692822bc4427d638a2ae` |

### iem-rio-2026 · natus-vincere-vs-furia

- página: https://www.hltv.org/matches/2393228/natus-vincere-vs-furia
- pacote provável: `iem-rio-2026-natus-vincere-vs-furia-bo3-qLZX6MdaBCbmtkWux805qr.rar`
- .dem do corpus no pacote: 1.49 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_15 | de_mirage | 1 | `natus-vincere-vs-furia-m1-mirage.dem` | `1bfb43118089c78331bd7b517e849fe12941a0ce9f1619b34b7b1c91c47dfa6d` |
| match_16 | de_nuke | 3 | `natus-vincere-vs-furia-m3-nuke.dem` | `87356d11bdeb8616cf13b148e8f3db69554383440bc29ca4826be4522fbb91d6` |
| match_17 | de_dust2 | 2 | `natus-vincere-vs-furia-m2-dust2.dem` | `bc517609cf2e20861613bfe1cedb1e7ecfda12b744f2f6a22b08f91c8334cf3d` |

### pgl-cluj-napoca-2026 · furia-vs-falcons

- página: https://www.hltv.org/matches/2389969/furia-vs-falcons
- pacote provável: `pgl-cluj-napoca-2026-furia-vs-falcons-bo3-OfIsfrpSwnaD_LueyZEScm.rar`
- .dem do corpus no pacote: 1.86 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_18 | de_anubis | 3 | `furia-vs-falcons-m3-anubis.dem` | `42aa5f5826231e0141ba712a0a6b6aa30d360f333a87fecf8eda0d8bfcd6905f` |
| match_19 | de_inferno | 2 | `furia-vs-falcons-m2-inferno.dem` | `c358451d9f613becab0966efbbe113ab805d236f1a898020f3f16327777cc974` |
| match_20 | de_mirage | 1 | `furia-vs-falcons-m1-mirage.dem` | `3ada17dbeb8b7122f1e96f8041cdd0db60728885c43c217ef82047421884b39b` |

### starladder-starseries-fall-2026 · vitality-vs-magic

- página: https://www.hltv.org/matches/2398089/vitality-vs-magic
- pacote provável: `starladder-starseries-fall-2026-vitality-vs-magic-bo3-qBHOW2KPqxQBIay8cnoYpu - Copia.rar`
- .dem do corpus no pacote: 0.36 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_23 | de_dust2 | 2 | `vitality-vs-magic-m2-dust2.dem` | `f18e6acd0f4dcf3574323bbb6237a0e65cd1f55a1a009404e9635df7818f7574` |

### iem-krakw-2026 · falcons-vs-mouz

- página: https://www.hltv.org/matches/2389660/falcons-vs-mouz
- pacote provável: `iem-krakw-2026-falcons-vs-mouz-bo3-0NmDSYe_8UmJAHamjCMBo8.rar`
- .dem do corpus no pacote: 1.86 GB (o pacote tem os outros mapas da série também)

| partida | mapa | mapa da série | arquivo .dem | sha256 esperado |
|---|---|---|---|---|
| match_41 | de_inferno | 1 | `falcons-vs-mouz-m1-inferno-p1.dem` | `24d5c304b7614d54505e4d42e0caeba8ec196d0e96e705bee9e31962331f5cb7` |
| match_41 | de_inferno | 1 | `falcons-vs-mouz-m1-inferno-p2.dem` | `4164738a697e23005ccda4c6ebc2c2a5f59bd2fdfc39de4da59a85e74d9d37dd` |
| match_42 | de_dust2 | 2 | `falcons-vs-mouz-m2-dust2.dem` | `0a3129ba726a10239fdbcc0da9050c5aad02a17d975ee5cb0f658b75ba0895f4` |

Total de .dem do corpus a baixar (sem a match_23): 7.19 GB.

## O que o próximo gabarito precisa cobrir

As faixas do jump-throw sem gabarito (decisão 21a), que hoje ficam neutras:
- soltura de 0 a 5 ticks depois da decolagem (inclui soltar no próprio tick do pulo);
- soltura de 14 a 18 ticks depois da decolagem (a fronteira entre a vz fixa e a vz real).
Cada demo recuperada é gabarito de botão, postura e posição; procure nelas
arremessos nessas faixas antes de mexer nas constantes.


## Para validar o rating (partidas de times FORA do corpus)

**Para que serve.** O erro do rating contra a HLTV que o projeto cita é medido
deixando de fora partidas dos mesmos times que estão no treino. A prova de que
o modelo não aprendeu o estilo desses times é avaliá-lo em partidas de times
que ele nunca viu. A lista é do Pedro (a HLTV bloqueia automação, e link de
partida não se inventa).

### Critérios

1. **Times fora do corpus.** Nenhum dos dois times pode ser um destes: FURIA,
   Natus Vincere, Vitality, Spirit, MOUZ, Falcons, Aurora, The MongolZ, magic.
2. **Pelo menos 4 times de tier 2** entre os escolhidos (fora do top 20 da HLTV).
   O corpus é todo de topo; é no tier 2 que o rating pode se comportar diferente.
3. **Mapas variados.** O corpus tem pouco de Ancient, Train, Overpass e Anubis.
   Evite mais de 3 mapas da mesma série.
4. **Partidas de 2026.**
5. De 10 a 15 mapas no total. Demo dividida em partes (`-p1`, `-p2`) serve: solte todas.

### Tabela (preencha)

| # | Link da partida na HLTV | Link das estatísticas do mapa | Mapa | Demo baixada? |
|---|---|---|---|---|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |
| 11 | | | | |
| 12 | | | | |
| 13 | | | | |
| 14 | | | | |
| 15 | | | | |

- **Link da partida:** `https://www.hltv.org/matches/<id>/...`, de onde sai o botão "GOTV Demo".
- **Link das estatísticas do mapa:** `https://www.hltv.org/stats/matches/mapstatsid/<id>/...`.
  É a página com rating, K-D, ADR, KAST e Swing por jogador DAQUELE mapa (a da
  série soma os mapas e não serve).

### Depois do download

1. Solte o arquivo (o `.rar` ou o `.dem`) em `demos/entrada/`.
2. Copie a tabela de estatísticas do mapa (os dois times) para um arquivo de
   texto em `data/reference/brutos/`, um por mapa, com o nome
   `hltv_validacao_<n>.txt`, onde `<n>` é o número da linha acima.
3. Me avise. Eu rodo `py -3.12 -m scripts.importa_demos`, que importa pelo
   sha256 e copia para o backup, e processo as partidas.
4. **A avaliação é única, com tudo congelado**, como foi nos arremessos: o
   modelo de round, a economia, a referência e os pesos ficam como estão, e eu
   não olho o rating oficial dessas partidas antes de congelar. O erro médio e
   a correlação nelas vão para `numeros_citaveis.json` como "partidas de times
   fora do corpus".

Isto é uma etapa própria: o resto do trabalho não espera por ela.
