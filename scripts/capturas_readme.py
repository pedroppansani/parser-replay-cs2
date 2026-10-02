"""Gera as capturas do README, sempre nos mesmos quadros, em `assets/readme/`.

O README apontava para `docs/img/*.png`, e `docs/` é saída do site, ignorada
pelo git: no GitHub as imagens davam 404. As capturas agora são versionadas em
`assets/readme/` e REGERADAS por este script a partir do site atual -- nunca
editadas à mão.

Quadros (fixos): a partida é a MESMA do botão "Ver uma partida" da landing
(scripts/build_site.partida_de_exemplo, critério declarado lá); o replay vai a
45% do round ROUND, com a direção do olhar ligada.

Uso:
    py -3.12 -m scripts.capturas_readme
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
SAIDA = RAIZ / "assets" / "readme"
ROUND = 6
LARGURA, ALTURA = 1280, 900
# (arquivo, aba, seletor do recorte)
ABAS = [("insights.png", "insights", '[data-panel="insights"]'),
        ("jogadores.png", "jogadores", '[data-panel="jogadores"]'),
        ("perfil.png", "perfil", '[data-panel="perfil"]')]


def gera() -> list[Path]:
    import json
    import tempfile

    from playwright.sync_api import sync_playwright

    from scripts.build_tactics_page import build_html as prancheta_html
    from scripts.build_web_page import build_html

    from scripts.build_site import PROCESSED_DIR, match_summary, partida_de_exemplo

    SAIDA.mkdir(parents=True, exist_ok=True)
    resumos = [m for m in (match_summary(d.name) for d in sorted(PROCESSED_DIR.glob("match_*")) if d.is_dir()) if m]
    PARTIDA = partida_de_exemplo(resumos)["id"]
    mapa = json.loads((RAIZ / "data" / "processed" / PARTIDA / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    pasta = Path(tempfile.mkdtemp(prefix="capturas_readme_"))
    partida = pasta / f"{PARTIDA}.html"
    partida.write_text(build_html(PARTIDA), encoding="utf-8")
    prancheta = pasta / f"prancheta_{mapa}.html"
    prancheta.write_text(prancheta_html(mapa), encoding="utf-8")
    feitas = []
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        ctx = nav.new_context(viewport={"width": LARGURA, "height": ALTURA}, device_scale_factor=1)
        ctx.add_init_script("try { localStorage.setItem('replay:direcao', '1'); } catch (e) {}")
        pg = ctx.new_page()
        pg.goto(partida.as_uri())
        pg.wait_for_load_state("networkidle")
        pg.evaluate("() => document.fonts.ready")
        # replay: o round fixo, a 45% dele
        pg.locator("#strip button", has_text=str(ROUND)).first.click()
        pg.evaluate("""() => { const s = document.getElementById('scrub');
            s.value = Math.round(s.max * 0.45); s.dispatchEvent(new Event('input', {bubbles: true})); }""")
        pg.wait_for_timeout(400)
        pg.locator(".stage").first.screenshot(path=str(SAIDA / "replay.png"))
        feitas.append(SAIDA / "replay.png")
        for arquivo, aba, seletor in ABAS:
            pg.click(f'[role=tab][data-tab="{aba}"]')
            pg.wait_for_timeout(400)
            # recorte pela página inteira: o screenshot do elemento rola a tela e a
            # barra de abas (fixa) ficava por cima do começo do painel
            pg.evaluate("() => window.scrollTo(0, 0)")
            caixa = pg.locator(seletor).bounding_box()
            pg.screenshot(path=str(SAIDA / arquivo), full_page=True, clip=caixa)
            feitas.append(SAIDA / arquivo)
        pg.goto(prancheta.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(SAIDA / "prancheta.png"))
        feitas.append(SAIDA / "prancheta.png")
        nav.close()
    return feitas


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    for f in gera():
        print(f"{f.relative_to(RAIZ).as_posix()}  {f.stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
