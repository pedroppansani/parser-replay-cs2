"""Capturas do Round swing na página da partida (RS2): a tabela de jogadores e a linha do Perfil nos 3 estados, em 3 tamanhos e nos 2 temas (aqui o claro e o escuro DIFEREM).

    py -3.12 -m scripts.design.capturas_round_swing <pasta_de_saida>

1 tabela da partida (match_21) · 2 Perfil com poucos rounds (match_09) · 3 Perfil de 30 a 99 rounds (match_21) · 4 Perfil estável comparado com quem tem poucos rounds (match_23).
Os jogadores de cada estado saem do dado (`data/player_profiles/round_swing.json`), nada à mão. As páginas geradas vão para uma pasta temporária.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.build_web_page import build_html
from scripts.design_head import TEMA_JS

RAIZ = Path(__file__).resolve().parents[2]
TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]


def _nome_no_estado(partida: str, estado: str) -> str:
    agg = json.loads((RAIZ / "data/player_profiles/round_swing.json").read_text(encoding="utf-8"))["jogadores"]
    ins = json.loads((RAIZ / "data/processed" / partida / "insights.json").read_text(encoding="utf-8"))
    for p in sorted(ins["players"], key=lambda p: p["name"].lower()):
        b = agg[str(p["steamid"])]
        if estado == "poucos" and b["poucos_rounds"] or estado == "estavel" and b["estavel"] or estado == "inter" and not b["poucos_rounds"] and not b["estavel"]:
            return p["name"]
    raise SystemExit(f"{partida}: ninguém no estado {estado}")


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    so = sys.argv[2:] or None                                       # só estas situações (prefixo do nome), p. ex. "1" "1b"
    pasta = Path(tempfile.mkdtemp(prefix="capturas_rs2_"))
    shutil.copyfile(RAIZ / "dashboard/web" / TEMA_JS if (RAIZ / "dashboard/web" / TEMA_JS).exists() else RAIZ / "docs" / TEMA_JS, pasta / TEMA_JS)
    for m in ("match_09", "match_21", "match_23"):
        (pasta / f"{m}.html").write_text(build_html(m), encoding="utf-8")
    situacoes = [
        ("1-tabela-da-partida", "match_21", "jogadores", None, None),
        ("1b-tabela-rolada-ate-o-fim", "match_21", "jogadores", None, None),
        ("2-perfil-poucos-rounds", "match_09", "perfil", _nome_no_estado("match_09", "poucos"), None),
        ("3-perfil-30-a-99-rounds", "match_21", "perfil", _nome_no_estado("match_21", "inter"), None),
        ("4-perfil-estavel-e-comparado", "match_23", "perfil", _nome_no_estado("match_23", "estavel"), _nome_no_estado("match_23", "poucos")),
    ]
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for esquema, tema in (("light", "claro"), ("dark", "escuro")):
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, color_scheme=esquema, device_scale_factor=1)
                for nome, m, aba, a, b in situacoes:
                    if so and nome.split("-")[0] not in so:
                        continue
                    pg = ctx.new_page(); erros = []
                    pg.on("pageerror", lambda e: erros.append(str(e)))
                    pg.goto((pasta / f"{m}.html").as_uri())
                    pg.wait_for_timeout(400)
                    pg.locator(f'[data-tab="{aba}"]').first.click()
                    pg.wait_for_timeout(300)
                    if a:
                        pg.locator(f'#pf-botoes button[data-nome="{a}"]').click()
                    if b:
                        pg.select_option("#pf-b", b)
                    pg.wait_for_timeout(300)
                    alvo = "#players-legenda" if aba == "jogadores" else "#pf-cab"
                    if nome.startswith("1b"):
                        if w > 420:
                            pg.close(); continue                      # a rolagem da caixa só existe no celular
                        pg.evaluate("(() => { const t = document.querySelector('.tabela-jog'); t.scrollLeft = t.scrollWidth; })()")
                    pg.locator(alvo).scroll_into_view_if_needed()
                    topo = "#players" if aba == "jogadores" else "#pf-botoes"
                    box = pg.locator(topo).bounding_box(); fim = pg.locator(alvo).bounding_box()
                    sy = pg.evaluate("scrollY")
                    y0 = max(0, box["y"] - 70 + sy)
                    y1 = fim["y"] + fim["height"] + 40 + sy
                    pg.evaluate("window.scrollTo(0, 0)")             # a barra fixa do topo não cobre o recorte
                    arq = saida / f"{nome}-{rotulo}-{tema}.png"
                    pg.screenshot(path=str(arq), full_page=True, clip={"x": 0, "y": y0, "width": w, "height": min(y1 - y0, 1400)})
                    assert not erros, erros
                    pg.close()
                ctx.close()
        nav.close()
    print(f"capturas em {saida}")


if __name__ == "__main__":
    main()
