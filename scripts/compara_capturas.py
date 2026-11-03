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
    py -3.12 -m scripts.compara_capturas --antes main --depois HEAD --contra-referencias notas/design/referencias/pc-windows
    py -3.12 -m scripts.compara_capturas --antes main --depois HEAD --grava-referencias notas/design/referencias/pc-windows

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
import datetime
import json
import platform
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

# Vizinhança de um jogador, em pixels do RADAR. O que manda é o NOME, não a
# ponta (14) nem o anel de cegueira (12,5): 9 letras de 12px em DM Mono têm
# ~33 de meia largura, a 19 acima do centro com a direção ligada -- o canto do
# nome fica a ~45 do centro. Medido na etapa 1: com 40 sobravam 35 pixels
# (pontas de nomes longos), com 48 nenhum.
RAIO_VIZINHANCA_PADRAO = 48

VALOR_DIRECAO = {"ligada": "1", "desligada": "0"}

# De onde vieram as capturas guardadas (cartão 19, regra do Pedro de 2026-11-03): o MESMO código dá o mesmo PNG na mesma máquina,
# mas o texto e as bordas do radar mudam entre Windows e Linux. Por isso, ao lado das referências fica um `origem.json`, e a
# ferramenta AVISA quando elas são de outra máquina, em vez de só acusar diferença.
ARQUIVO_DE_ORIGEM = "origem.json"
NAVEGADOR_ATUAL: dict = {}   # preenchido por `_captura`: {"nome", "versao"}


def origem_desta_maquina(navegador: dict | None = None) -> dict:
    """Sistema, navegador e versão desta máquina (o que vai no `origem.json` e o que se compara com ele)."""
    nav = navegador or NAVEGADOR_ATUAL
    return {
        "sistema": f"{platform.system()} {platform.release()} ({platform.machine()})",
        "familia": platform.system(),
        "navegador": nav.get("nome") or "desconhecido",
        "versao": nav.get("versao") or "desconhecida",
        "gerado_em": datetime.date.today().isoformat(),
    }


def motivos_de_outra_maquina(referencia: dict | None, atual: dict) -> list[str]:
    """O que separa a origem das referências desta máquina; lista vazia = a mesma máquina (família do sistema, navegador e
    versão MAIOR do navegador). Sem origem gravada, não dá para saber: conta como outra máquina."""
    if not referencia:
        return ["as referências não têm `origem.json`: não dá para saber de onde vieram"]
    motivos = []
    if referencia.get("familia") != atual.get("familia"):
        motivos.append(f"sistema: referências {referencia.get('sistema')}, esta máquina {atual.get('sistema')}")
    if referencia.get("navegador") != atual.get("navegador"):
        motivos.append(f"navegador: referências {referencia.get('navegador')}, esta máquina {atual.get('navegador')}")
    maior = lambda v: str(v).split(".")[0]
    if maior(referencia.get("versao")) != maior(atual.get("versao")):
        motivos.append(f"versão do navegador: referências {referencia.get('versao')}, esta máquina {atual.get('versao')}")
    return motivos


def mascara_de_diferenca(a, b):
    """Imagem "L": 255 onde o pixel difere em QUALQUER canal. A conversão da diferença para cinza arredondava para zero um
    degrau só no vermelho ou no azul e a ferramenta dizia "idêntico" com PNG diferentes."""
    from PIL import ImageChops

    r, g, azul = ImageChops.difference(a, b).split()
    return ImageChops.lighter(ImageChops.lighter(r, g), azul).point(lambda v: 255 if v > 0 else 0)


def le_origem(pasta: Path) -> dict | None:
    f = pasta / ARQUIVO_DE_ORIGEM
    return json.loads(f.read_text(encoding="utf-8")) if f.is_file() else None


def grava_referencias(saida: Path, pasta: Path, quadros: list[str]) -> None:
    """Copia os quadros "depois" para `pasta` como referências e grava de onde vieram."""
    pasta.mkdir(parents=True, exist_ok=True)
    for q in quadros:
        shutil.copyfile(saida / f"{q}_depois.png", pasta / f"{q}_depois.png")
    (pasta / ARQUIVO_DE_ORIGEM).write_text(
        json.dumps(origem_desta_maquina(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compara_com_referencias(saida: Path, pasta: Path, quadros: list[str]) -> list[str]:
    """Linhas do relatório contra as referências guardadas. De OUTRA máquina: só o aviso, sem acusar diferença."""
    from PIL import Image

    atual = origem_desta_maquina()
    motivos = motivos_de_outra_maquina(le_origem(pasta), atual)
    if motivos:
        return [
            f"AVISO: as referências de {pasta} são de OUTRA máquina e NÃO são comparáveis com estas capturas:",
            *[f"  - {m}" for m in motivos],
            "  Texto (nomes) e bordas do radar variam entre máquinas; a diferença NÃO indica erro. Gere a base da `main` NESTA",
            "  máquina (use --antes main) e só compare capturas geradas aqui. Nada foi comparado com as referências.",
        ]
    linhas = [f"referências de {pasta} (mesma máquina: {atual['sistema']}, {atual['navegador']} {atual['versao']}):"]
    for q in quadros:
        ref = Image.open(pasta / f"{q}_depois.png").convert("RGB")
        novo = Image.open(saida / f"{q}_depois.png").convert("RGB")
        if ref.size != novo.size:
            linhas.append(f"  {q:24s} TAMANHO DIFERENTE {ref.size} x {novo.size}")
            continue
        caixa = mascara_de_diferenca(ref, novo).getbbox()
        linhas.append(f"  {q:24s} {'idêntico às referências' if caixa is None else 'DIFERENTE das referências, na caixa ' + str(caixa)}")
    return linhas

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
# as fontes hospedadas no site (decisão 48) ficam ao lado das páginas, como no build; a revisão antiga não as tem
import shutil
if Path("dashboard/web/fontes").is_dir():
    shutil.copytree("dashboard/web/fontes", saida / "fontes", dirs_exist_ok=True)
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
        from scripts.design._comum import ARGS_DETERMINISTICOS, chrome
        b = chrome(p, ARGS_DETERMINISTICOS)
        from scripts.design._comum import NAVEGADOR_USADO
        NAVEGADOR_ATUAL.update({"nome": NAVEGADOR_USADO["nome"], "versao": b.version})
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
            # dois traços, sempre nas mesmas coordenadas do MAPA: caneta em arco e
            # seta. O mapa é medido DEPOIS de abrir o desenho -- a barra abre
            # recolhida (auditoria 5.1) e, aberta, empurra o mapa para baixo.
            pg.click("#anot-toggle")
            c = pg.locator("#map").bounding_box()
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
            # medido de novo: fechar o desenho recolhe a barra e o mapa sobe
            pg.screenshot(path=str(saida / f"{nome}_{sufixo}.png"), clip=pg.locator("#map").bounding_box())
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
        # design-E2: o painel da direita tem abas; os passos ficam na aba Tática (a página antiga não tem as abas)
        pg.evaluate("() => { if (Prancheta._interno.abaDoPainel) Prancheta._interno.abaDoPainel('tatica'); }")
        pg.click('[data-passo="2"]')
        pg.mouse.move(2, 2)
        pg.wait_for_timeout(400)
        pg.screenshot(path=str(saida / f"{QUADRO_PRANCHETA}_{sufixo}.png"),
                      clip=pg.locator("#pr-mapa").bounding_box())
        ctx.close()
        b.close()
    return registros


def _compara(saida: Path, nome: str, jogadores: list, raio: float) -> str:
    from PIL import Image

    a = Image.open(saida / f"{nome}_antes.png").convert("RGB")
    d = Image.open(saida / f"{nome}_depois.png").convert("RGB")
    if a.size != d.size:
        return f"TAMANHO DIFERENTE {a.size} x {d.size}"
    dif = mascara_de_diferenca(a, d)
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
    ap.add_argument("--contra-referencias", type=Path, default=None, metavar="PASTA",
                    help="compara os quadros \"depois\" com as referências guardadas em PASTA (avisa se são de outra máquina)")
    ap.add_argument("--grava-referencias", type=Path, default=None, metavar="PASTA",
                    help="grava os quadros \"depois\" em PASTA como referências, com o `origem.json` desta máquina")
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
        nomes = [q[0] for q in QUADROS_REPLAY] + [QUADRO_PRANCHETA]
        if args.contra_referencias:
            print("\n".join(compara_com_referencias(saida, args.contra_referencias, nomes)))
        if args.grava_referencias:
            grava_referencias(saida, args.grava_referencias, nomes)
            print(f"referências gravadas em {args.grava_referencias} (origem: {origem_desta_maquina()['sistema']}, "
                  f"{NAVEGADOR_ATUAL.get('nome')} {NAVEGADOR_ATUAL.get('versao')})")
        print(f"imagens em {saida}")
    finally:
        shutil.rmtree(temp / "paginas_antes", ignore_errors=True)
        shutil.rmtree(temp / "paginas_depois", ignore_errors=True)
        subprocess.run(["git", "worktree", "prune"], cwd=PROJECT_ROOT, check=False)


if __name__ == "__main__":
    main()
