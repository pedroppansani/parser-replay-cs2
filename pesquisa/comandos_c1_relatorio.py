"""C1: o relatório das 30 frases (o que o leitor entendeu em cada uma), gerado do próprio leitor.

    py -3.12 -m pesquisa.comandos_c1_relatorio <saida.md>
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

from scripts.comandos_contexto import contexto
from tests.test_comandos_leitor import CASOS, LEITOR

MAPAS = {"de_mirage": "Mirage", "de_inferno": "Inferno", "de_dust2": "Dust2", "de_nuke": "Nuke"}


def quando_de(a):
    q = a["quando"]
    if not q:
        return "sem horário"
    return {"relogio": lambda: f"aos {q['segundos_restantes'] // 60}:{q['segundos_restantes'] % 60:02d} (relógio)", "inicio": lambda: f"aos {q['segundos']} s do início",
            "depois": lambda: "depois", "junto": lambda: "ao mesmo tempo"}[q["tipo"]]()


def humano(a):
    quem = " + ".join((f"{q['lado'].upper()} {q['num']}" if q["lado"] and q["num"] else f"jogador {q['num']} (time?)" if q["num"] else f"{q['funcao']} (quem?)" if q.get("funcao") else "?")
                      + (f" [{q['funcao']}]" if q.get("funcao") and q["lado"] else "") for q in a["quem"]) or "quem?"
    alvo = (a["alvo"]["nome"] + (f" ({a['alvo']['lugar']})" if a["alvo"]["lugar"] and a["alvo"]["lugar"] != a["alvo"]["nome"] else "")) if a["alvo"] else "?"
    o = {"lancar": f"{a['granada'] or 'granada?'} em {alvo}", "mover": f"{a['modo']} até {alvo}", "segurar": f"segura {alvo}",
         "esperar": f"espera {a['espera_s']} s" if a["espera_s"] is not None else "espera ?", None: f"ação? (alvo {alvo})"}[a["tipo"]]
    return f"{quem}: {o}, {quando_de(a)}" + (f", duração pedida {a['duracao_s']} s" if a["duracao_s"] is not None else "")


def main() -> None:
    linhas = ["| # | mapa | frase | o que o leitor entendeu | o que pergunta | avisos |", "|---|---|---|---|---|---|"]
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(); pg.goto("about:blank"); pg.add_script_tag(path=str(LEITOR))
        for n, mapa, frase, jog, *_ in CASOS:
            r = pg.evaluate("([f, c]) => LeitorDeComandos.le(f, c)", [frase, contexto(mapa, jogadores=jog)])
            ent = "<br>".join(humano(a) for a in r["acoes"])
            per = "<br>".join(f"{p['texto']}" + (f" [{' / '.join(o['rotulo'] for o in p['opcoes'][:4])}]" if p["opcoes"] else "") for p in r["perguntas"]) or ("pronto para confirmar" + (", com aviso" if r["avisos"] else ""))
            av = ", ".join(a["codigo"] for a in r["avisos"]) or ""
            av += (", " if av else "") + "depende do deslocamento (ação %d)" % [a["indice"] for a in r["acoes"] if a["depende_do_deslocamento"]][0] if any(a["depende_do_deslocamento"] for a in r["acoes"]) else ""
            linhas.append(f"| {n} | {MAPAS[mapa]} | \"{frase}\" | {ent} | {per} | {av} |")
        b.close()
    Path(sys.argv[1]).write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
