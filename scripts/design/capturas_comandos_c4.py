"""Capturas da aba Comandos com o arremesso real (C4): 7 situações do cartão "O que entendi" x 3 tamanhos (375, 1366x657, 1440x900) x 2 temas.

    py -3.12 -m scripts.design.capturas_comandos_c4 <pasta_de_saida>

1 arremesso real perto da peça · 2 arremesso longe, com os botões · 3 a corrida que chega depois do horário pedido · 4 nenhum arremesso real · 5 a molotov sem voo ·
6 o "depois" com horário e o comando cortado (os dois cartões que ficaram da C3) · 7 o aviso "recebe muita molotov de CT" (poucos do lado certo, muitos do outro).
A prancheta é sempre violeta: o claro e o escuro saem iguais, e o script diz em quantos pares. As páginas geradas vão para uma pasta temporária.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.build_tactics_page import build_html
from scripts.comandos_contexto import contexto

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
RAIZ = Path(__file__).resolve().parents[2]
MAPA = "de_mirage"
BUSCA = """([a, al, l, x, y]) => { const b = Prancheta._interno.cmdBuscaReal(a, al, l, { x: x, y: y });
    return b.grupos.map(g => ({ id: g.r.id, dist: g.dist, voo: g.voo, origem: g.r.origem })); }"""


def _ponto(nome):
    return next(p for p in contexto(MAPA, so_conferidos=True)["pontos"] if p["nome"] == nome)


def _alvo(nome):
    ps = [p for p in contexto(MAPA, so_conferidos=True)["pontos"] if p["nome"] == nome]
    return {"tipo": "ponto", "id": ps[0]["id"], "ids": [p["id"] for p in ps], "nome": nome, "x": ps[0]["x"], "y": ps[0]["y"], "andar": "único"}


def _ficha(pg, x, y):
    pg.evaluate("""([x, y]) => { const I = Prancheta._interno, S = I.S;
        I.emiteLote([["cria_peca", { peca: "demo-tr2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: x, y: y, nivel: 0 }]]); }""", [x, y])


def _escolhe_posicoes(nav, pagina):
    """As posições da ficha de cada situação, achadas no dado (nada à mão): perto da saída, longe dela, muito longe, e a saída de uma molotov sem voo."""
    pg = nav.new_page(); pg.goto(pagina.as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
    janela = _alvo("Janelão")
    base = _ponto("Base TR")
    todos = pg.evaluate(BUSCA, ["smoke", janela, "t", base["x"], base["y"]])
    perto = todos[3]["origem"]                                              # a ficha já está num ponto de saída de uma smoke real no Janelão
    longe = muito_longe = None
    for p in contexto(MAPA, so_conferidos=True)["pontos"]:
        g = pg.evaluate(BUSCA, ["smoke", janela, "t", p["x"], p["y"]])
        if g and longe is None and g[0]["dist"] >= 400:
            longe = p
        if g and muito_longe is None and g[0]["dist"] >= 900:
            muito_longe = p
    sem_voo = None
    pts = contexto(MAPA, so_conferidos=True)["pontos"]
    lib = json.loads((RAIZ / "data" / "lineups" / f"{MAPA}.json").read_text(encoding="utf-8"))["arremessos"]
    for r in lib:
        if r["arma"] != "molotov" or r["lado"] != "t" or r.get("voo_s") is not None:
            continue
        for p in pts:
            if math.hypot(r["destino"][0] - p["x"], r["destino"][1] - p["y"]) <= 150:
                g = pg.evaluate(BUSCA, ["molotov", _alvo(p["nome"]), "t", r["origem"][0], r["origem"][1]])
                if g and not g[0]["voo"] and g[0]["dist"] <= 50:
                    sem_voo = (p, r["origem"]); break
        if sem_voo:
            break
    pg.close()
    assert perto and longe and muito_longe and sem_voo
    return perto, longe, muito_longe, sem_voo


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    pagina = Path(tempfile.mkdtemp(prefix="capturas_c4_")) / "prancheta_de_mirage.html"
    pagina.write_text(build_html(MAPA), encoding="utf-8")
    hashes: dict[str, list[str]] = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        perto, longe, muito_longe, (p_sem_voo, origem_sem_voo) = _escolhe_posicoes(nav, pagina)
        base = _ponto("Base TR")
        situacoes = [
            ("1-real-perto-da-peca", (perto[0], perto[1]), "tr 2 joga smoke no janelão aos 1:20", None),
            ("2-real-longe-com-botoes", (longe["x"], longe["y"]), "tr 2 joga smoke no janelão aos 1:20", None),
            ("3-corrida-chega-depois-do-horario", (muito_longe["x"], muito_longe["y"]), "tr 2 joga smoke no janelão aos 1:52", "levar"),
            ("4-nenhum-arremesso-real", (base["x"], base["y"]), "tr 2 joga smoke na tv aos 1:20", None),
            ("5-molotov-sem-voo", (origem_sem_voo[0], origem_sem_voo[1]), f"tr 2 joga molotov no {p_sem_voo['nome']} aos 1:20", None),
            ("6-depois-com-horario-e-cortado", (base["x"], base["y"]), "tr 2 corre pro meio aos 1:30 e depois corre pra b, tr 2 corre pro top of mid aos 1:25", None),
            ("7-aviso-de-lado-caverna", (base["x"], base["y"]), "tr 2 joga molotov na caverna aos 1:20", None),
        ]
        for tema in ("claro", "escuro"):
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
                for nome, (x, y), frase, clique in situacoes:
                    pg = ctx.new_page()
                    pg.goto(pagina.as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                    _ficha(pg, x, y)
                    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
                    pg.fill("#pr-cmd-texto", frase); pg.click("#pr-cmd-entender")
                    if clique:
                        pg.click(f"[data-escolha={clique}]")
                    pg.evaluate("() => window.scrollTo(0, 0)"); pg.mouse.move(2, 2); pg.wait_for_timeout(250)
                    arq = saida / f"{nome}-{rotulo}-{tema}.png"
                    pg.screenshot(path=str(arq), full_page=True)
                    hashes.setdefault(f"{nome}-{rotulo}", []).append(hashlib.sha256(arq.read_bytes()).hexdigest())
                    if tema == "claro" and rotulo == "1440":
                        print(f"{nome}: {pg.inner_text('#pr-cmd-resultado').replace(chr(10), ' | ')}")
                    pg.close()
                ctx.close()
        nav.close()
    iguais = [k for k, v in hashes.items() if len(set(v)) == 1]
    print(f"{len(hashes) * 2} capturas; claro e escuro idênticos em {len(iguais)} de {len(hashes)} pares")


if __name__ == "__main__":
    main()
