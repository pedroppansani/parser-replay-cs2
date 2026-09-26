"""
Compara, pixel a pixel, os mesmos quadros do replay e da prancheta em duas
revisões do código.

PARA QUE SERVE
--------------
Provar que uma mudança visual ficou onde devia -- ou que uma refatoração não
mudou nada. Foi esta comparação que aprovou a etapa 0 (módulo compartilhado):
seis quadros idênticos pixel a pixel. Nas etapas seguintes ela mostra ONDE
mudou, com uma imagem de diferença.

Não entra na suíte do pytest: depende de git worktree e de navegador. É
ferramenta de revisão.

USO
---
    py -3.12 -m scripts.compara_capturas
    py -3.12 -m scripts.compara_capturas --antes baseline-antes-tatica --depois HEAD
    py -3.12 -m scripts.compara_capturas --depois TRABALHO          # árvore atual, sem commit
    py -3.12 -m scripts.compara_capturas --direcao desligada        # replay:direcao = 0
    py -3.12 -m scripts.compara_capturas --saida C:/tmp/comparacao

`--antes` e `--depois` aceitam qualquer revisão do git; `TRABALHO` é a pasta do
projeto como está (inclusive sem commit). Cada revisão gera as páginas no
PRÓPRIO worktree, com o código e o `data/processed/` daquela revisão.

`--direcao` grava `replay:direcao` no localStorage antes de a página abrir, nas
DUAS revisões (a que não conhece a chave simplesmente a ignora):
`ligada` = "1", `desligada` = "0", `padrao` = não grava nada.

QUADROS (fixos e nomeados)
--------------------------
    replay_mirage_r6        match_02, round 6, 45% do round, com dois traços
    replay_nuke_r9_andar0   match_05, round 9, 40%, andar 0 travado, dois traços
    replay_nuke_r9_andar1   match_05, round 9, 40%, andar 1 travado, dois traços
    prancheta_fixture_p2    prancheta da Mirage com tests/fixtures/tatica_v1.json, passo 2

SAÍDA
-----
Para cada quadro: "idêntico", ou a contagem de pixels diferentes e a caixa onde
eles estão. Em `--saida` ficam <quadro>_antes.png, <quadro>_depois.png e
<quadro>_diff.png (a imagem "depois" apagada, com os pixels que mudaram em
vermelho).

Nos quadros do replay, quando a revisão "depois" tem o MapCore, a ferramenta
também registra onde cada jogador foi desenhado e informa quantos pixels
diferentes caem FORA da vizinhança (`--raio`, em pixels do radar) de um jogador
VIVO no andar ativo -- é o critério de "a mudança ficou restrita ao jogador".
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRABALHO = "TRABALHO"

# (nome, partida, round, fração do round, andar travado ou None)
QUADROS_REPLAY = [
    ("replay_mirage_r6", "match_02", 6, 0.45, None),
    ("replay_nuke_r9_andar0", "match_05", 9, 0.40, 0),
    ("replay_nuke_r9_andar1", "match_05", 9, 0.40, 1),
]
QUADRO_PRANCHETA = "prancheta_fixture_p2"
MAPA_PRANCHETA = "de_mirage"
FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "tatica_v1.json"

# Vizinhança de um jogador, em pixels do RADAR: a ponta da direção vai a 14
# do centro, o anel de cegueira a 12,5, e a sombra do halo espalha ~6.
RAIO_VIZINHANCA_PADRAO = 24

VALOR_DIRECAO = {"ligada": "1", "desligada": "0"}

GERA_PAGINAS = r"""
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from scripts.build_web_page import build_html
from scripts.build_tactics_page import build_html as prancheta
saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
for mid in json.loads(sys.argv[2]):
    (saida / f"{mid}.html").write_text(build_html(mid), encoding="utf-8")
(saida / "prancheta.html").write_text(prancheta(sys.argv[3]), encoding="utf-8")
"""

# Registra onde cada jogador é desenhado (pixels do radar) quando a página tem
# o MapCore. A página antiga não tem, e aí nada é registrado.
REGISTRA_JOGADORES = """
(() => {
  window.__jogadores = [];
  const liga = () => {
    if (!window.MapCore || MapCore.__registrando) return;
    const f = MapCore.desenhaJogador;
    MapCore.desenhaJogador = function (c, x, y, o) {
      const t = c.getTransform();
      window.__jogadores.push({ x: x, y: y, estado: o.estado,
        sx: t.a * x + t.c * y + t.e, sy: t.b * x + t.d * y + t.f, k: t.a });
      return f.apply(this, arguments);
    };
    MapCore.__registrando = true;
  };
  document.addEventListener("DOMContentLoaded", liga);
})();
"""


def _gera_paginas(rev: str, destino: Path, trabalho_temp: Path) -> Path:
    """Gera as páginas da revisão `rev` em `destino`. Devolve a pasta."""
    partidas = sorted({q[1] for q in QUADROS_REPLAY})
    if rev == TRABALHO:
        raiz = PROJECT_ROOT
    else:
        raiz = trabalho_temp / f"wt_{abs(hash(rev))}"
        subprocess.run(["git", "worktree", "add", "--detach", "-q", str(raiz), rev],
                       cwd=PROJECT_ROOT, check=True)
    try:
        subprocess.run([sys.executable, "-c", GERA_PAGINAS, str(destino), json.dumps(partidas), MAPA_PRANCHETA],
                       cwd=raiz, check=True)
    finally:
        if rev != TRABALHO:
            subprocess.run(["git", "worktree", "remove", "--force", str(raiz)], cwd=PROJECT_ROOT, check=True)
    return destino


def _captura(paginas: Path, saida: Path, sufixo: str, direcao: str) -> dict:
    """Captura os quadros de uma revisão. Devolve {quadro: [jogadores registrados]}."""
    from playwright.sync_api import sync_playwright

    registros = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        for nome, mid, rnd, frac, andar in QUADROS_REPLAY:
            ctx = b.new_context(viewport={"width": 1400, "height": 1000}, device_scale_factor=1)
            if direcao in VALOR_DIRECAO:
                ctx.add_init_script(
                    f"try {{ localStorage.setItem('replay:direcao', '{VALOR_DIRECAO[direcao]}'); }} catch (e) {{}}")
            ctx.add_init_script(REGISTRA_JOGADORES)
            pg = ctx.new_page()
            erros = []
            pg.on("pageerror", lambda e: erros.append(str(e)))
            pg.goto((paginas / f"{mid}.html").as_uri())
            pg.locator('[data-tab="replay"]').first.click()
            pg.wait_for_function("() => window.MapAnnotations && MapAnnotations._interno.S.reprojecoes > 0")
            pg.locator("#strip button", has_text=str(rnd)).first.click()
            if andar is not None:
                pg.locator(f'.levelpick button[data-lv="{andar}"]').click()
            pg.evaluate(f"""() => {{ const s = document.getElementById('scrub');
                s.value = Math.floor(s.max * {frac}); s.dispatchEvent(new Event('input')); }}""")
            pg.evaluate("() => document.getElementById('map').scrollIntoView({block: 'center'})")
            pg.wait_for_timeout(700)
            c = pg.locator("#map").bounding_box()
            # dois traços, sempre nas mesmas coordenadas de tela: caneta em arco e seta
            pg.click("#anot-toggle")
            pg.mouse.move(c["x"] + c["width"] * .3, c["y"] + c["height"] * .3)
            pg.mouse.down()
            for i in range(1, 13):
                pg.mouse.move(c["x"] + c["width"] * (.3 + .02 * i),
                              c["y"] + c["height"] * (.3 + .012 * i * i / 6), steps=1)
            pg.mouse.up()
            pg.click('[data-ferramenta="seta"]')
            pg.mouse.move(c["x"] + c["width"] * .6, c["y"] + c["height"] * .7)
            pg.mouse.down()
            pg.mouse.move(c["x"] + c["width"] * .75, c["y"] + c["height"] * .55, steps=5)
            pg.mouse.up()
            pg.click("#anot-toggle")
            pg.mouse.move(2, 2)
            # o registro que vale é o do ÚLTIMO desenho do mapa
            pg.evaluate("() => { window.__jogadores = []; }")
            pg.evaluate("""() => { const s = document.getElementById('scrub');
                s.dispatchEvent(new Event('input')); }""")
            pg.wait_for_timeout(400)
            pg.screenshot(path=str(saida / f"{nome}_{sufixo}.png"), clip=c)
            dpr_css = pg.evaluate("() => document.getElementById('map').width / document.getElementById('map').clientWidth")
            registros[nome] = [dict(j, escala_css=1 / dpr_css) for j in pg.evaluate("() => window.__jogadores")]
            if erros:
                raise SystemExit(f"{nome} ({sufixo}): erro de JavaScript: {erros}")
            ctx.close()

        ctx = b.new_context(viewport={"width": 1300, "height": 950}, device_scale_factor=1)
        pg = ctx.new_page()
        pg.goto((paginas / "prancheta.html").as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        if not pg.evaluate("(t) => Prancheta._interno.importaTexto(t)", FIXTURE.read_text(encoding="utf-8")):
            raise SystemExit("a prancheta recusou a fixture v1")
        pg.click('[data-passo="2"]')
        pg.mouse.move(2, 2)
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(saida / f"{QUADRO_PRANCHETA}_{sufixo}.png"),
                      clip=pg.locator("#pr-mapa").bounding_box())
        ctx.close()
        b.close()
    return registros


def _compara(saida: Path, nome: str, jogadores: list, raio: float) -> str:
    from PIL import Image, ImageChops

    a = Image.open(saida / f"{nome}_antes.png").convert("RGB")
    d = Image.open(saida / f"{nome}_depois.png").convert("RGB")
    if a.size != d.size:
        return f"TAMANHO DIFERENTE {a.size} x {d.size}"
    dif = ImageChops.difference(a, d).convert("L").point(lambda v: 255 if v > 0 else 0)
    caixa = dif.getbbox()
    realce = Image.blend(d, Image.new("RGB", d.size, (0, 0, 0)), 0.6)
    realce.paste((255, 40, 40), mask=dif)
    realce.save(saida / f"{nome}_diff.png")
    if caixa is None:
        return "idêntico"
    pixels = [(x, y) for y in range(d.size[1]) for x in range(d.size[0]) if dif.getpixel((x, y))]
    texto = f"{len(pixels)} pixels diferentes, na caixa {caixa}"
    vivos = [j for j in jogadores if j["estado"] == "vivo"]
    if vivos:
        # centro de cada jogador na captura (pixels CSS) e o raio convertido
        centros = [(j["sx"] * j["escala_css"], j["sy"] * j["escala_css"]) for j in vivos]
        r = raio * vivos[0]["k"] * vivos[0]["escala_css"]
        fora = sum(1 for x, y in pixels if all((x - cx) ** 2 + (y - cy) ** 2 > r * r for cx, cy in centros))
        texto += f"; fora da vizinhança ({raio:g}px do radar) de jogador vivo no andar ativo: {fora}"
    return texto


def main() -> None:
    ap = argparse.ArgumentParser(description="Compara quadros do replay e da prancheta entre duas revisões.")
    ap.add_argument("--antes", default="baseline-antes-tatica")
    ap.add_argument("--depois", default="HEAD")
    ap.add_argument("--direcao", choices=["padrao", "ligada", "desligada"], default="padrao")
    ap.add_argument("--raio", type=float, default=RAIO_VIZINHANCA_PADRAO)
    ap.add_argument("--saida", type=Path, default=None)
    args = ap.parse_args()

    temp = Path(tempfile.mkdtemp(prefix="compara_capturas_"))
    saida = args.saida or temp / "resultado"
    saida.mkdir(parents=True, exist_ok=True)
    try:
        pa = _gera_paginas(args.antes, temp / "paginas_antes", temp)
        pd = _gera_paginas(args.depois, temp / "paginas_depois", temp)
        _captura(pa, saida, "antes", args.direcao)
        reg = _captura(pd, saida, "depois", args.direcao)
        print(f"{args.antes}  x  {args.depois}   (direção: {args.direcao})")
        for nome in [q[0] for q in QUADROS_REPLAY] + [QUADRO_PRANCHETA]:
            print(f"  {nome:24s} {_compara(saida, nome, reg.get(nome, []), args.raio)}")
        print(f"imagens em {saida}")
    finally:
        shutil.rmtree(temp / "paginas_antes", ignore_errors=True)
        shutil.rmtree(temp / "paginas_depois", ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=PROJECT_ROOT, check=False)


if __name__ == "__main__":
    main()
