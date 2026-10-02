"""Compara a PÁGINA INTEIRA de uma partida, aba por aba, entre duas revisões.

O `compara_capturas.py` confere quadros fixos do mapa; este confere o resto da
página (resumo, placar, jogadores, perfil, estilos), em desktop e em celular,
para mudanças que mexem no layout (doctype, CSS, textos).

A página "antes" usa o template, o JS e o CSS de `dashboard/web/` na revisão
`--antes`; a "depois", os da árvore de trabalho. Os DADOS são os do disco nas
duas (a comparação é de apresentação, não de número).

Uso:
    py -3.12 -m scripts.compara_paginas --antes main [--partidas match_23 match_02] [--saida pasta]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
WEB = RAIZ / "dashboard" / "web"
ARQUIVOS = ("template.html", "map_core.js", "annotations.js", "annotations.css")
TAMANHOS = {"desktop": (1300, 950), "celular": (390, 844)}


def _pagina(partida: str, rev: str | None, pasta: Path) -> Path:
    import scripts.build_web_page as b
    original = b.TEMPLATE
    try:
        if rev is not None:
            origem = pasta / f"web_{rev.replace('/', '_')}"
            origem.mkdir(parents=True, exist_ok=True)
            for nome in ARQUIVOS:
                r = subprocess.run(["git", "show", f"{rev}:dashboard/web/{nome}"], capture_output=True, cwd=RAIZ, check=True)
                (origem / nome).write_bytes(r.stdout)
            b.TEMPLATE = origem / "template.html"
        html = b.build_html(partida)
    finally:
        b.TEMPLATE = original
    arq = pasta / f"{partida}_{'depois' if rev is None else 'antes'}.html"
    arq.write_text(html, encoding="utf-8")
    return arq


def compara(partidas: list[str], antes: str, saida: Path, tamanhos: list[str]) -> list[dict]:
    from PIL import Image, ImageChops
    from playwright.sync_api import sync_playwright

    saida.mkdir(parents=True, exist_ok=True)
    linhas = []
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for partida in partidas:
            paginas = {"antes": _pagina(partida, antes, saida), "depois": _pagina(partida, None, saida)}
            for tam in tamanhos:
                w, h = TAMANHOS[tam]
                fotos: dict[str, dict[str, Path]] = {}
                info = {}
                for lado, arq in paginas.items():
                    pg = nav.new_page(viewport={"width": w, "height": h})
                    pg.goto(arq.as_uri())
                    pg.wait_for_load_state("networkidle")
                    pg.evaluate("() => document.fonts.ready")
                    abas = pg.eval_on_selector_all("[role=tab][data-tab]", "els => els.map(e => e.dataset.tab)")
                    info[lado] = {"modo": pg.evaluate("() => document.compatMode"),
                                  "largura": pg.evaluate("() => document.documentElement.scrollWidth"),
                                  "titulo": pg.title()}
                    for aba in abas:
                        pg.click(f'[role=tab][data-tab="{aba}"]')
                        pg.wait_for_timeout(350)
                        f = saida / f"{partida}_{tam}_{aba}_{lado}.png"
                        pg.screenshot(path=str(f), full_page=True)
                        fotos.setdefault(aba, {})[lado] = f
                    pg.close()
                for aba, par in fotos.items():
                    a, d = Image.open(par["antes"]).convert("RGB"), Image.open(par["depois"]).convert("RGB")
                    if a.size != d.size:
                        linhas.append({"partida": partida, "tamanho": tam, "aba": aba, "resultado": f"tamanho {a.size} -> {d.size}", "pixels": None})
                        continue
                    dif = ImageChops.difference(a, d)
                    caixa = dif.getbbox()
                    n = 0 if caixa is None else sum(1 for px in dif.getdata() if px != (0, 0, 0))
                    if n:
                        dif.point(lambda v: 255 if v else 0).save(saida / f"{partida}_{tam}_{aba}_diferenca.png")
                    linhas.append({"partida": partida, "tamanho": tam, "aba": aba,
                                   "resultado": "idêntico" if not n else f"diferente em {caixa}", "pixels": n})
                linhas.append({"partida": partida, "tamanho": tam, "aba": "(página)", "resultado": str(info), "pixels": None})
        nav.close()
    return linhas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", default="main")
    ap.add_argument("--partidas", nargs="*", default=["match_23", "match_02"])
    ap.add_argument("--tamanhos", nargs="*", default=["desktop"], choices=list(TAMANHOS))
    ap.add_argument("--saida", type=Path, default=None)
    a = ap.parse_args()
    saida = a.saida or Path(tempfile.mkdtemp(prefix="compara_paginas_"))
    for l in compara(a.partidas, a.antes, saida, a.tamanhos):
        print(f"{l['partida']} {l['tamanho']:8s} {l['aba']:10s} {l['resultado']}" + ("" if l["pixels"] is None else f" ({l['pixels']} px)"))
    print("imagens em", saida)


if __name__ == "__main__":
    main()
