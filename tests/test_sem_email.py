"""Nenhum e-mail nas páginas geradas (plano v2-0 §4.11): o diálogo "Adicionar demo" e o rodapé usam só o link de
Issues do GitHub."""
from __future__ import annotations

import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
# um "@" com cara de e-mail: algo@dominio.tld (o "@media" do CSS e o "@font-face" não têm nada antes do @)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def test_o_detector_acha_um_email_e_ignora_o_css():
    assert EMAIL.search("escreva para alguem.x@exemplo.com.br")
    assert not EMAIL.search("@media (max-width: 640px) { } @font-face { } @keyframes varre")


def test_nenhuma_pagina_gerada_tem_email():
    from scripts.build_jogadores import build_html as jogadores
    from scripts.build_site import build_index, match_summary
    from scripts.build_tactics_page import build_html as prancheta
    from scripts.build_web_page import build_html as partida
    from scripts.numeros_citaveis import SAIDA
    ids = sorted(d.name for d in (RAIZ / "data" / "processed").glob("match_*"))
    partidas = [m for m in (match_summary(i) for i in ids) if m]
    numeros = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else None
    paginas = {"landing": build_index(partidas, "https://github.com/pedroppansani/parser-replay-cs2", [], numeros=numeros),
               "prancheta": prancheta("de_mirage"), "jogadores": jogadores()}
    if partidas:
        paginas["partida"] = partida(partidas[0]["id"])
    for nome, html in paginas.items():
        achado = EMAIL.search(html)
        assert achado is None, (nome, achado.group(0) if achado else None)
