"""Gera tests/fixtures/tatica_v1.json COM O CÓDIGO DO FORMATO 1, pela interface da página.

Só reproduz a fixture num checkout da tag `baseline-antes-tatica` (e5a01a8): depois
dela a prancheta passa a exportar o formato 2. Uso: py -3.12 gera_tatica_v1.py <pasta_temporária>
import json, sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.stdout.reconfigure(encoding="utf-8")
R = Path(r"C:\Users\User\Desktop\Projetos Claude\01 - Parser de Replay CS2")
sys.path.insert(0, str(R))
from scripts.build_tactics_page import build_html
from metrics.tactics import aplica, valida, OPERACOES
S = Path(sys.argv[1]); html = S / "prancheta_antiga_de_mirage.html"
html.write_text(build_html("de_mirage"), encoding="utf-8")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 1300, "height": 950}, accept_downloads=True)
    pg = ctx.new_page(); erros = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(html.as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    c = pg.locator("#pr-mapa").bounding_box()
    at = lambda fx, fy: (c["x"] + c["width"] * fx, c["y"] + c["height"] * fy)
    def banco(lado, rot, fx, fy):
        f = pg.locator(f'.pr-ficha.{lado}[data-rotulo="{rot}"]').bounding_box()
        pg.mouse.move(f["x"] + 16, f["y"] + 16); pg.mouse.down(); pg.mouse.move(*at(fx, fy), steps=6); pg.mouse.up()
    def arrasta(a, b_):
        pg.mouse.move(*at(*a)); pg.mouse.down(); pg.mouse.move(*at(*b_), steps=6); pg.mouse.up()
    def mao(arma, o, d):
        pg.click(f'[data-arma="{arma}"]'); pg.click('[data-ferramenta="granada"]')
        pg.mouse.click(*at(*o)); pg.mouse.click(*at(*d)); pg.click('[data-ferramenta="mover"]')

    pg.fill("#pr-autor", "pedro"); pg.press("#pr-autor", "Tab")
    pg.fill("#pr-titulo", "Fixture v1: execução B"); pg.press("#pr-titulo", "Tab")          # renomeia
    banco("ct", "1", 0.62, 0.72); banco("t", "1", 0.35, 0.30); banco("t", "2", 0.30, 0.40)  # cria_peca x3
    pg.fill("#pr-passo-titulo", "posições"); pg.press("#pr-passo-titulo", "Tab")          # renomeia_passo
    pg.click("#pr-novo-passo")                                                           # cria_passo
    pg.fill("#pr-passo-titulo", "entrada"); pg.press("#pr-passo-titulo", "Tab")
    arrasta((0.62, 0.72), (0.55, 0.60))                                                  # move_peca
    pg.click('[data-arma="smoke"]'); pg.click('[data-ferramenta="buscar"]')
    pg.mouse.click(*at(0.48, 0.52)); pg.locator(".pr-lista li").first.click()           # cria_granada real
    mao("smoke", (0.35, 0.30), (0.45, 0.45))                                             # cria_granada à mão
    arrasta((0.45, 0.45), (0.50, 0.40))                                                  # move_granada
    mao("he", (0.30, 0.40), (0.40, 0.55))
    pg.locator("#pr-selecao button", has_text="Apagar granada").click()                  # remove_granada
    pg.mouse.click(*at(0.30, 0.40))
    pg.locator("#pr-selecao button", has_text="Tirar do mapa").click()                   # remove_peca
    pg.click("#pr-novo-passo"); mao("flash", (0.55, 0.60), (0.60, 0.50))                  # passo 3 + flash
    pg.click("#pr-remove-passo")                                                         # remove_passo
    pg.evaluate("() => Prancheta._interno.gravaAgora()")
    with pg.expect_download() as dl:
        pg.click("#pr-exporta")
    doc = json.loads(Path(dl.value.path()).read_text(encoding="utf-8"))
    estado_js = pg.evaluate("() => Prancheta._interno.S.estado")
    assert not erros, erros
    b.close()

tipos = sorted({o["tipo"] for o in doc["operacoes"]})
faltam = sorted(set(OPERACOES) - set(tipos))
assert not faltam, f"faltam operações: {faltam}"
assert any(o["tipo"] == "cria_granada" and o.get("arremesso") for o in doc["operacoes"]), "sem arremesso real"
assert estado_js == aplica(doc["operacoes"]) == valida(doc), "JS e Python discordam"
(R / "tests/fixtures/tatica_v1.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
(R / "tests/fixtures/tatica_v1_estado.json").write_text(json.dumps(estado_js, ensure_ascii=False, indent=1), encoding="utf-8")
print("operações:", len(doc["operacoes"]), "tipos:", tipos)
print("estado: passos", len(estado_js["passos"]), "peças", len(estado_js["pecas"]), "granadas",
      [(g["arma"], g["arremesso"] is not None) for g in estado_js["granadas"].values()])
