"""Capturas da aba Comandos com o tempo real de corrida (C3): seis situações do cartão "O que entendi" x 3 tamanhos (375, 1366x657, 1440x900) x 2 temas.

    py -3.12 -m scripts.design.capturas_comandos_c3 <pasta_de_saida>

1 tempo real entre pontos do Pedro (Mirage, Base TR até Meio) · 2 tempo real entre áreas da demo (Mirage, TSpawn até TopofMid) · 3 estimado corrigido pelo fator do
mapa (andando) · 3b estimado em linha reta pura (Overpass, sem par com amostra) · 4 troca de andar com tempo real (Nuke, Secret até Tunnels) · 4b troca de andar sem
tempo real: pergunta a chegada (Nuke, CTSpawn até Tunnels) · 5 tempo real entre pontos na Dust2 (Base TR até Fora do Escuro).
A prancheta é sempre violeta (o `tema.js` não a toca): o claro e o escuro saem iguais, e o script diz em quantos pares.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.build_tactics_page import build_html
from scripts.comandos_contexto import contexto

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
RAIZ = Path(__file__).resolve().parents[2]


def _area(mapa, nome):
    return next(a for a in contexto(mapa)["areas"] if a["nome"] == nome)


def _ponto(mapa, nome):
    return next(p for p in contexto(mapa, so_conferidos=True)["pontos"] if p["nome"] == nome)


def situacoes():
    mirage_base = _ponto("de_mirage", "Base TR")
    dust_base = _ponto("de_dust2", "Base TR")
    sec, tsp, ov = _area("de_nuke", "Secret"), _area("de_nuke", "CTSpawn"), contexto("de_overpass")["areas"]
    return [
        ("1-real-entre-pontos", "de_mirage", (mirage_base["x"], mirage_base["y"], 0), "tr 2 corre pro meio aos 1:30"),
        ("2-real-entre-areas", "de_mirage", (_area("de_mirage", "TSpawn")["x"], _area("de_mirage", "TSpawn")["y"], 0), "tr 2 corre pro top of mid aos 1:30"),
        ("3-estimado-com-fator", "de_mirage", (mirage_base["x"], mirage_base["y"], 0), "tr 2 anda até o meio aos 1:30"),
        ("3b-estimado-sem-fator", "de_overpass", (ov[0]["x"], ov[0]["y"], 0), f"tr 2 corre pro {ov[1]['nome']} aos 1:30"),
        ("4-troca-de-andar-com-tempo-real", "de_nuke", (sec["x"], sec["y"], 1 if sec["andar"] == "baixo" else 0), "tr 2 corre pro tunnels aos 1:30"),
        ("4b-troca-de-andar-sem-tempo-real", "de_nuke", (tsp["x"], tsp["y"], 1 if tsp["andar"] == "baixo" else 0), "tr 2 corre pro tunnels aos 1:30"),
        ("5-real-entre-pontos-dust2", "de_dust2", (dust_base["x"], dust_base["y"], 0), "tr 2 corre pro fora do escuro aos 1:30"),
    ]


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    hashes: dict[str, list[str]] = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        paginas = {}
        for mapa in {s[1] for s in situacoes()}:
            paginas[mapa] = saida / f"_prancheta_de_{mapa}.html"
            paginas[mapa].write_text(build_html(mapa), encoding="utf-8")
        for tema in ("claro", "escuro"):
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
                for nome, mapa, (x, y, nivel), frase in situacoes():
                    pg = ctx.new_page()
                    pg.goto(paginas[mapa].as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                    pg.evaluate("""([x, y, nivel]) => { const I = Prancheta._interno, S = I.S;
                        I.emiteLote([["cria_peca", { peca: "demo-tr2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: x, y: y, nivel: nivel }]]); }""", [x, y, nivel])
                    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
                    pg.fill("#pr-cmd-texto", frase); pg.click("#pr-cmd-entender")
                    pg.evaluate("() => window.scrollTo(0, 0)"); pg.mouse.move(2, 2); pg.wait_for_timeout(250)
                    arq = saida / f"{nome}-{rotulo}-{tema}.png"
                    pg.screenshot(path=str(arq), full_page=True)
                    hashes.setdefault(f"{nome}-{rotulo}", []).append(hashlib.sha256(arq.read_bytes()).hexdigest())
                    texto = pg.inner_text("#pr-cmd-resultado").replace("\n", " | ")
                    if tema == "claro" and rotulo == "1440":
                        print(f"{nome}: {texto}")
                    pg.close()
                ctx.close()
        nav.close()
    iguais = [k for k, v in hashes.items() if len(set(v)) == 1]
    print(f"{len(hashes) * 2} capturas; claro e escuro idênticos em {len(iguais)} de {len(hashes)} pares")


if __name__ == "__main__":
    main()
