"""Regras do jogo que vários módulos usam. Uma regra, um lugar (auditoria, item 4.8).

Antes, a janela de trade estava escrita em cinco módulos e o round da troca de
lado em quatro, cada um com o seu "a mesma do resto do projeto". Trocar uma
delas exigia achar todas. Os módulos agora importam daqui (os nomes antigos
continuam como apelido local, para não mexer em quem os usa).
"""
from __future__ import annotations

# Janela de trade: matar quem acabou de matar um companheiro dentro de 5 s.
# 5 s é a faixa usada por HLTV/Leetify (a maioria fica entre 3 e 5 s); varrida
# no corpus em scripts/calibracao/varre_trade.py (decisão 7h).
JANELA_DE_TRADE_S = 5.0

# MR12: o lado troca depois do round 12 no tempo regulamentar. A prorrogação
# (MR3) e o formato lido da demo ficam em metrics/sides.py.
HALFTIME_ROUND = 12

# Nome do mapa como a página escreve (seletor, índice, título da partida).
NOME_DO_MAPA = {
    "de_ancient": "Ancient",
    "de_cache": "Cache",
    "de_anubis": "Anubis",
    "de_dust2": "Dust II",
    "de_inferno": "Inferno",
    "de_mirage": "Mirage",
    "de_nuke": "Nuke",
    "de_overpass": "Overpass",
    "de_train": "Train",
    "de_vertigo": "Vertigo",
}
