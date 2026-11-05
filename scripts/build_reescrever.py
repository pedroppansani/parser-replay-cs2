"""Gera a página reescrever.html: a escolha do round a reescrever (Reescrever R1, decisão 56).

Os rounds sugeridos (R0, `leitura/sugeridos.py`) e a busca por partida e round. Autocontida, abre como arquivo local: os dados vão
embutidos (`json_em_script`), o texto vem do Python (decisão 18) e nada da partida é baixado.

O botão leva ao Replay da partida no round (`#replay?round=N&t=S`, o endereço da fase 12); o modo Reescrever em si é o R2.
"""
from __future__ import annotations

import html
from pathlib import Path

from leitura.reescrever import FRASE_FIXA_FORTE, FRASE_FIXA_RESTO
from scripts.json_em_script import js
from scripts.meta_da_pagina import MARCA, meta_tags

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "dashboard" / "web"
ARQUIVO = "reescrever.html"

TITULO = "Reescrever um round"
TEXTOS = {
    "titulo": TITULO,
    "frase": "Escolha um round, volte a um instante e mude o caminho de quem quiser: o site mostra o seu plano ao lado do que aconteceu de verdade.",
    # a frase fixa de honestidade (design, §5): negrito e resto
    "fixa_forte": FRASE_FIXA_FORTE,
    "fixa_resto": FRASE_FIXA_RESTO,
    "sugeridos": "Rounds sugeridos",
    "buscar": "Buscar uma partida",
    "rotulo_busca": "Partida: time, mapa ou evento",
    "rotulo_faixa": "Rounds da partida",
    "contagem": "{n} partida(s)",
    "vazio": "Nenhuma partida com \"{q}\".",
    "limpar": "Limpar a busca",
    "round": "Round",
    "rounds": "rounds",
    "botao": "Reescrever o round {n}",
    "motivo": {"decisivo": "Decidiu a partida", "momento": "Momento do round", "erro": "Erro"},
    "max_linhas": 12,
}


def dados_da_pagina(matches: list[dict], sugeridos: dict) -> dict:
    """As partidas (todas, para a busca) com os sugeridos de cada uma. `matches` vem de `build_site.match_summary`. `grupo` ordena a
    lista curta como a landing: a partida de exemplo (o mesmo critério dela), depois as profissionais, depois as da FACEIT."""
    from scripts.build_site import partida_de_exemplo
    exemplo = partida_de_exemplo(matches)
    partidas = []
    for m in matches:
        lados = m.get("lados") or {}
        if not lados.get("A") or not lados.get("B"):
            continue
        partidas.append({
            "grupo": 0 if exemplo and m["id"] == exemplo["id"] else 1 if m.get("origem") == "profissional" else 2,
            "id": m["id"], "file": m["file"], "map_label": m["map_label"], "evento": m.get("evento"), "rounds": m["rounds"],
            "lados": [{"nome": lados[k]["nome"], "pontos": lados[k]["pontos"]} for k in ("A", "B")],
            "sugeridos": (sugeridos["partidas"].get(m["id"]) or {}).get("sugeridos", []),
        })
    return {"partidas": partidas}


def build_html(matches: list[dict], sugeridos: dict, site: str | None = None) -> str:
    from scripts.build_web_page import REPO
    from scripts.design_head import aplica, topo_do_site, v2_js
    pagina = aplica((WEB / "reescrever.html").read_text(encoding="utf-8")
                    .replace("<!--__TOPO__-->", topo_do_site("reescrever", REPO))
                    .replace("/*__V2_JS__*/", v2_js())
                    .replace("<!--__TITULO__-->", html.escape(f"{TITULO} · {MARCA}"))
                    .replace("<!--__META__-->", meta_tags(f"{TITULO} · {MARCA}", TEXTOS["frase"], site, ARQUIVO))
                    .replace("/*__TEXTOS__*/null", js(TEXTOS)))
    # o dado do corpus por último: um nome de time com cara de marcador não é reescrito por nenhuma substituição
    return pagina.replace("/*__DADOS__*/null", js(dados_da_pagina(matches, sugeridos)))
