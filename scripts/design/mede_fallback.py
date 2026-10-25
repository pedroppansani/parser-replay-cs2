"""Mede no Chrome os fallbacks da Geist e da Geist Mono e imprime os 4 @font-face (decisão 48; entrega §3.2).

NÃO roda no build nem nos testes: precisa do `fontTools` (fora do requirements.txt) e do Chrome (Playwright).
Adaptado do protótipo da v2 (`validacao/mede_fallback.py`): lê as fontes de `dashboard/web/fontes/` e só
IMPRIME; os 4 @font-face impressos são colados à mão em `dashboard/web/tokens.css` (nenhum arquivo é gravado).

    py -3.12 -m scripts.design.mede_fallback

Método: `size-adjust` = largura da mesma frase em Geist ÷ em Arial (por peso, 100 px); ascent/descent = hhea da
Geist ÷ size-adjust. Um @font-face por peso, porque o negrito sintético do Arial ficava 4,7% mais estreito que o
Arial Bold. Depois confere, no mesmo navegador: altura de bloco e largura de linha, fonte web x fallback.
Limite: medido com Arial/Consolas (Windows); no macOS a mono cai em ui-monospace/Menlo sem métrica medida.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path

FONTES = Path(__file__).resolve().parent.parent.parent / "dashboard" / "web" / "fontes"
AMOSTRA = ("Cada round, explicado. Veja a partida de CS2 como uma jogada: onde cada um estava, o que cada granada fez e "
           "por que o round virou. Jogadores, placar, estilos e perfil; comparação com o grupo. Ação, avaliação, função, "
           "região. 0123456789")
NUM = "0123456789 1:14 13 × 10 27 de 36 +0,14 74% R12"
CASOS = [("Geist", FONTES / "geist-latin.woff2", "Arial", AMOSTRA, "normal"),
         ("Geist Mono", FONTES / "geist-mono-latin.woff2", "Consolas", NUM, "mono")]

LARGURA_JS = ("([f,p,t])=>{const s=document.createElement('span');s.style.cssText=`font:${p} 100px \"${f}\";"
              "white-space:nowrap`;s.textContent=t;document.body.append(s);const r=s.getBoundingClientRect().width;"
              "s.remove();return r}")
CONFERE_JS = ("([a,b,t,l,s,p,lh])=>{const m=f=>{const d=document.createElement('div');"
              "d.style.cssText=`width:${l}px;font:${p} ${s}px/${lh} \"${f}\"`;d.textContent=t;document.body.append(d);"
              "const h=d.getBoundingClientRect().height;const sp=document.createElement('span');"
              "sp.style.cssText=`font:${p} ${s}px \"${f}\";white-space:nowrap`;sp.textContent=t.slice(0,60);"
              "document.body.append(sp);const w=sp.getBoundingClientRect().width;d.remove();sp.remove();return [h,w]};"
              "return [m(a),m(b)]}")


def _hhea(p: Path) -> tuple[int, int, int, int]:
    from fontTools.ttLib import TTFont
    f = TTFont(p)
    return f["head"].unitsPerEm, f["hhea"].ascent, f["hhea"].descent, f["hhea"].lineGap


def _uri(p: Path) -> str:
    return "data:font/woff2;base64," + base64.b64encode(p.read_bytes()).decode()


def main() -> int:
    from playwright.sync_api import sync_playwright
    html = ("<!doctype html><meta charset=utf-8><style>" + "".join(
        f'@font-face{{font-family:"{n}";src:url({_uri(p)}) format("woff2");font-weight:400 600}}' for n, p, *_ in CASOS)
        + "</style><body>")
    res = {}
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome")
        pg = b.new_page()
        pg.set_content(html)
        pg.evaluate("document.fonts.load('400 20px Geist')")
        pg.evaluate("document.fonts.load('400 20px \"Geist Mono\"')")
        pg.wait_for_timeout(500)
        for nome, arq, local, texto, chave in CASOS:
            w = {(fam, peso): pg.evaluate(LARGURA_JS, [fam, peso, texto]) for fam in (nome, local) for peso in (400, 600)}
            adj = (w[(nome, 400)] / w[(local, 400)] + w[(nome, 600)] / w[(local, 600)]) / 2
            upm, asc, desc, gap = _hhea(arq)
            res[chave] = dict(familia=nome, local=local, size_adjust=adj, ascent=asc / upm / adj,
                              descent=-desc / upm / adj, line_gap=gap / upm / adj,
                              razao400=w[(nome, 400)] / w[(local, 400)], razao600=w[(nome, 600)] / w[(local, 600)])
        css = ""
        for r in res.values():
            nomefb = r["familia"] + " Fallback"
            asc_r, desc_r, gap_r = (r[k] * r["size_adjust"] for k in ("ascent", "descent", "line_gap"))
            for pesos, loc, adj in (("100 500", r["local"], r["razao400"]), ("600 900", r["local"] + " Bold", r["razao600"])):
                css += (f'@font-face{{font-family:"{nomefb}";src:local("{loc}");font-weight:{pesos};'
                        f'size-adjust:{adj * 100:.2f}%;ascent-override:{asc_r / adj * 100:.2f}%;'
                        f'descent-override:{desc_r / adj * 100:.2f}%;line-gap-override:{gap_r / adj * 100:.2f}%}}\n')
        pg.set_content(html + "<style>" + css + "</style>")
        pg.wait_for_timeout(300)
        print("== @font-face medidos (colar em dashboard/web/tokens.css) ==")
        print(css, end="")
        print("\n== conferência: fonte web x fallback (mesmo texto, mesma caixa) ==")
        for nome, fb, texto, larg in [("Geist", "Geist Fallback", AMOSTRA, 343), ("Geist", "Geist Fallback", AMOSTRA, 600),
                                      ("Geist Mono", "Geist Mono Fallback", NUM, 200)]:
            for tam, peso, lh in [(16, 400, "1.55"), (14, 400, "normal"), (40, 600, "1.1"), (18, 400, "normal")]:
                (hw, ww), (hf, wf) = pg.evaluate(CONFERE_JS, [nome, fb, texto, larg, tam, peso, lh])
                print(f"{nome:<10} {tam:>2}px {peso} lh {lh:<6} caixa {larg}px: altura web {hw:6.1f} fallback {hf:6.1f} "
                      f"(dif {hf - hw:+.1f}); linha de 60 car. {ww:6.1f} x {wf:6.1f} ({(wf / ww - 1) * 100:+.1f}%)")
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
