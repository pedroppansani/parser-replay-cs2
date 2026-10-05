"""Gera tests/fixtures/tatica_v2.json COM O CÓDIGO DO FORMATO 2, pela interface (fase 8, item 8.0).

A tática nasce de um instante do replay (match_02, round 6: a origem do instante)
e passa por todas as operações do formato 2: passos com duração, girar, tirar,
apagar peça, granada com arremesso real e à mão, mover e apagar granada, vida
útil, traços, borracha, desfazer (anula) e refazer (reativa). É a base da
migração para o formato 3 e TEM de ser gerada pelo código antigo -- reproduz só
num checkout anterior ao formato 3 (tag `baseline-antes-fase-6` ou o commit do
8.0). Uso: py -3.12 tests/fixtures/gera_tatica_v2.py <pasta_temporária>
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
from metrics.tactics import OPERACOES, aplica, valida  # noqa: E402
from scripts.build_tactics_page import build_html as prancheta  # noqa: E402
from scripts.build_web_page import build_html as partida  # noqa: E402

S = Path(sys.argv[1])
S.mkdir(parents=True, exist_ok=True)
(S / "prancheta_de_mirage.html").write_text(prancheta("de_mirage"), encoding="utf-8")
(S / "match_02.html").write_text(partida("match_02"), encoding="utf-8")


def interno(pg, expr):
    return pg.evaluate(f"() => {{ const I = Prancheta._interno, S = I.S; return {expr}; }}")


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 1400, "height": 1000}, accept_downloads=True)
    pg = ctx.new_page()
    erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))

    # --- origem do instante: o replay abre a prancheta com os vivos do quadro
    pg.goto((S / "match_02.html").as_uri())
    pg.locator('[data-tab="replay"]').first.click()
    pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
    pg.locator("#strip button", has_text="6").first.click()
    pg.evaluate("() => { const s = document.getElementById('scrub'); s.value = 40; s.dispatchEvent(new Event('input')); }")
    pg.click("#anot-toggle")
    pg.click("#anot-tatica-instante")
    pg.wait_for_function("() => window.Prancheta && Prancheta._interno.S.estado !== null")

    c = pg.locator("#pr-mapa").bounding_box()
    largura = interno(pg, "I.radar().width")
    no_mapa = lambda fx, fy: (c["x"] + c["width"] * fx, c["y"] + c["height"] * fy)  # noqa: E731
    no_radar = lambda px, py: (c["x"] + px * c["width"] / largura, c["y"] + py * c["height"] / largura)  # noqa: E731

    def pixel_da_peca(pid, passo=0):
        q = interno(pg, f"I.quadroDoPasso(S.estado, {passo}, I.centro()).pecas['{pid}']")
        return interno(pg, f"I.jogoParaPixel({q['x']}, {q['y']})")

    def solta():
        pg.evaluate("() => document.activeElement && document.activeElement.blur()")

    pecas = interno(pg, "Object.keys(S.estado.pecas)")
    assert len(pecas) >= 3, pecas
    pg.fill("#pr-autor", "pedro"); pg.press("#pr-autor", "Tab")
    pg.fill("#pr-titulo", "Fixture v2: do replay"); pg.press("#pr-titulo", "Tab")                 # renomeia
    pg.fill("#pr-passo-titulo", "posições"); pg.press("#pr-passo-titulo", "Tab")                  # renomeia_passo
    pg.fill("#pr-passo-duracao", "3"); pg.press("#pr-passo-duracao", "Tab")                       # define_duracao
    pg.click("#pr-novo-passo")                                                                   # cria_passo
    pg.fill("#pr-passo-titulo", "entrada"); pg.press("#pr-passo-titulo", "Tab")
    pg.fill("#pr-passo-duracao", "4.5"); pg.press("#pr-passo-duracao", "Tab")
    solta()

    # move_peca: arrasta a primeira peça
    x, y = pixel_da_peca(pecas[0], 1)
    pg.mouse.move(*no_radar(x, y)); pg.mouse.down(); pg.mouse.move(*no_radar(x + 40, y - 30), steps=6); pg.mouse.up()
    # gira_peca: a alça da peça selecionada
    interno(pg, f"(S.sel = {{tipo: 'peca', id: '{pecas[0]}'}}, I.reprojeta(), 0)")
    ax, ay = interno(pg, f"I.alca('{pecas[0]}')")
    pg.mouse.move(*no_radar(ax, ay)); pg.mouse.down(); pg.mouse.move(*no_radar(ax + 40, ay + 40), steps=5); pg.mouse.up()
    # tira_peca: a segunda sai do mapa neste passo
    x, y = pixel_da_peca(pecas[1], 1)
    pg.click('aside [data-ferramenta="mover"]')
    pg.mouse.click(*no_radar(x, y))
    pg.click("#pr-tira-peca")
    # remove_peca: a terceira sai da tática
    x, y = pixel_da_peca(pecas[2], 1)
    pg.mouse.click(*no_radar(x, y))
    pg.click("#pr-apaga-peca")
    solta()

    # granada com arremesso real (buscar) e à mão
    pg.click('[data-arma="smoke"]'); pg.click('aside [data-ferramenta="buscar"]')
    pg.mouse.click(*no_mapa(0.48, 0.52))
    pg.locator(".pr-lista li").first.click()
    pg.click('[data-arma="molotov"]'); pg.click('aside [data-ferramenta="granada"]')
    pg.mouse.click(*no_mapa(0.30, 0.60)); pg.mouse.click(*no_mapa(0.35, 0.70))
    pg.click('aside [data-ferramenta="mover"]')
    gid = [g for g, v in interno(pg, "S.estado.granadas").items() if v["arma"] == "molotov"][0]
    pg.mouse.click(*no_mapa(0.35, 0.70))                                                         # seleciona
    pg.fill("#pr-vida", "2"); pg.press("#pr-vida", "Tab")                                         # define_vida
    d = interno(pg, f"S.estado.granadas['{gid}'].destino")
    px = interno(pg, f"I.jogoParaPixel({d[0]}, {d[1]})")
    pg.mouse.move(*no_radar(*px)); pg.mouse.down()
    pg.mouse.move(*no_radar(px[0] + 30, px[1] + 10), steps=5); pg.mouse.up()                     # move_granada
    pg.click('[data-arma="he"]'); pg.click('aside [data-ferramenta="granada"]')
    pg.mouse.click(*no_mapa(0.62, 0.30)); pg.mouse.click(*no_mapa(0.66, 0.34))
    pg.click('aside [data-ferramenta="mover"]')
    pg.mouse.click(*no_mapa(0.66, 0.34))
    pg.locator("#pr-selecao button", has_text="Apagar granada").click()                         # remove_granada
    solta()

    # traços: seta e caneta; a borracha apaga a seta
    pg.click('#pr-barra [data-ferramenta="seta"]')
    pg.mouse.move(*no_mapa(0.20, 0.20)); pg.mouse.down(); pg.mouse.move(*no_mapa(0.30, 0.25), steps=5); pg.mouse.up()
    pg.click('#pr-barra [data-ferramenta="caneta"]')
    pg.mouse.move(*no_mapa(0.70, 0.70)); pg.mouse.down()
    for i in range(1, 6):
        pg.mouse.move(*no_mapa(0.70 + 0.02 * i, 0.70 - 0.01 * i * i))
    pg.mouse.up()
    pg.click('#pr-barra [data-ferramenta="borracha"]')
    pg.mouse.click(*no_mapa(0.25, 0.225))
    pg.click('aside [data-ferramenta="mover"]')
    solta()

    # anula e reativa: desfaz a borracha e refaz; desfaz a caneta e deixa desfeita
    pg.keyboard.press("Control+z"); pg.keyboard.press("Control+y")
    pg.keyboard.press("Control+z")

    # um terceiro passo, removido (remove_passo)
    pg.click("#pr-novo-passo")
    pg.once("dialog", lambda dl: dl.accept())
    pg.click("#pr-remove-passo")

    interno(pg, "I.gravaAgora()")
    with pg.expect_download() as dl:
        pg.click("#pr-exporta")
    doc = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    estado_js = interno(pg, "S.estado")
    assert not erros, erros
    b.close()

tipos = sorted({o["tipo"] for o in doc["operacoes"]})
faltam = sorted(set(OPERACOES) - set(tipos))
assert not faltam, f"faltam operações: {faltam}"
assert doc.get("versao") == 2 and doc.get("origem"), "precisa ser formato 2 com a origem do instante"
assert any(o["tipo"] == "cria_granada" and o.get("arremesso") for o in doc["operacoes"]), "sem arremesso real"
assert estado_js == aplica(doc["operacoes"]) == valida(doc), "JS e Python discordam"
(R / "tests/fixtures/tatica_v2.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
(R / "tests/fixtures/tatica_v2_estado.json").write_text(json.dumps(estado_js, ensure_ascii=False, indent=1), encoding="utf-8")
print("operações:", len(doc["operacoes"]), "tipos:", tipos)
print("estado: passos", len(estado_js["passos"]), "peças", len(estado_js["pecas"]),
      "granadas", len(estado_js["granadas"]), "traços", len(estado_js["tracos"]))
