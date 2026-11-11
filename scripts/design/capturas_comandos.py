"""Capturas da aba Comandos da prancheta (C2): 6 estados x 3 tamanhos (375, 1366x657, 1440x900) x 2 temas (claro, escuro).

    py -3.12 -m scripts.design.capturas_comandos <pasta_de_saida>

A prancheta é sempre violeta (o `tema.js` não a toca), então as capturas "claro" e "escuro" saem iguais: o script as faz mesmo assim e diz quais são idênticas
byte a byte. Cada captura é a página inteira.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.build_tactics_page import build_html
from scripts.comandos_contexto import contexto

TAMANHOS = [("375", 375, 812), ("1366", 1366, 657), ("1440", 1440, 900)]
EXEMPLO = "tr 2 joga uma molotov na caverna aos 1:20 e roda pra TV correndo"
ESTADOS = [
    ("1-vazio", None),
    ("2-entendido", EXEMPLO),
    ("3-pergunta-botoes", "o 2 joga smoke na b"),
    ("4-pergunta-horario", "o 2 joga smoke na b|TR 2"),
    ("5-aplicado", EXEMPLO + "|aplica"),
    ("6-palavra-desconhecida", "tr 2 vai pro meio aos 1:00 rapidinho"),
    ("7-aplicado-e-desfeito", EXEMPLO + "|aplica|desfaz"),
]


def main() -> None:
    saida = Path(sys.argv[1]); saida.mkdir(parents=True, exist_ok=True)
    pagina = saida / "_prancheta_de_mirage.html"
    pagina.write_text(build_html("de_mirage"), encoding="utf-8")
    base_tr = next(p for p in contexto("de_mirage")["pontos"] if p["nome"] == "Base TR")
    hashes: dict[str, list[str]] = {}
    with sync_playwright() as p:
        nav = p.chromium.launch(channel="chrome")
        for tema in ("claro", "escuro"):
            for rotulo, w, h in TAMANHOS:
                ctx = nav.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
                ctx.add_init_script(f"try {{ localStorage.setItem('goatdemo:tema', '{tema}'); }} catch (e) {{}}")
                for nome, acao in ESTADOS:
                    pg = ctx.new_page()
                    pg.goto(pagina.as_uri()); pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
                    pg.evaluate("""([x, y]) => { const I = Prancheta._interno, S = I.S;
                        I.emiteLote([["cria_peca", { peca: "demo-tr2", lado: "t", rotulo: "2", passo: S.estado.passos[0].passo, x: x, y: y, nivel: 0 }]]); }""", [base_tr["x"], base_tr["y"]])
                    pg.evaluate("() => Prancheta._interno.abaDoPainel('comandos')")
                    if acao:
                        for parte in acao.split("|"):
                            if parte == "aplica":
                                pg.click("#pr-cmd-aplicar"); pg.evaluate("() => Prancheta._interno.defineTempo(37)")
                            elif parte == "desfaz":
                                pg.evaluate("() => Prancheta._interno.desfaz()")
                            elif parte == "TR 2":
                                pg.click(".pr-cmd-opcao >> text=TR 2")
                            else:
                                pg.fill("#pr-cmd-texto", parte); pg.click("#pr-cmd-entender")
                    pg.evaluate("() => window.scrollTo(0, 0)"); pg.mouse.move(2, 2); pg.wait_for_timeout(250)      # a barra de cima é fixa: a captura sai sempre do topo
                    arq = saida / f"{nome}-{rotulo}-{tema}.png"
                    pg.screenshot(path=str(arq), full_page=True)
                    hashes.setdefault(f"{nome}-{rotulo}", []).append(hashlib.sha256(arq.read_bytes()).hexdigest())
                    pg.close()
                ctx.close()
        nav.close()
    iguais = [k for k, v in hashes.items() if len(set(v)) == 1]
    print(f"{len(hashes) * 2} capturas; claro e escuro idênticos em {len(iguais)} de {len(hashes)} pares")


if __name__ == "__main__":
    main()
