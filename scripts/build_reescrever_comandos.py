"""Os arquivos dos comandos dentro do Reescrever (CR2): o leitor, as regras do real, o plano e a tela da seção, mais o contexto de cada mapa.

A página da partida só traz a casca da seção "Comandos" (`dashboard/web/partida/12-reescrever-comandos.js`); quando a seção abre, ela carrega estes arquivos, na ordem
de `ORDEM`, e o do mapa (`comandos/real/<mapa>.js`, que entrega o contexto: pontos, áreas e textos). Mesmo molde da biblioteca de arremessos da troca de granada (R4).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web" / "comandos"
PASTA_DO_CONTEXTO = "comandos/real"
ORDEM = ["comandos/leitor.js", "comandos/plano.js", "comandos/real.js", "comandos/reescrever.js"]
ORIGENS = {"comandos/leitor.js": "leitor.js", "comandos/plano.js": "plano.js", "comandos/real.js": "real.js", "comandos/reescrever.js": "reescrever.js"}


def arquivo_do_contexto(mapa: str) -> str:
    return f"{PASTA_DO_CONTEXTO}/{mapa}.js"


def contexto_js(mapa: str) -> str | None:
    """O arquivo do contexto do mapa: chama `window.__recebeContextoDoReal(...)`, que a casca deixa pronta antes de carregá-lo. None se o mapa não tem pontos nem áreas."""
    from scripts.comandos_contexto import contexto_do_real
    ctx = contexto_do_real(mapa)
    if not ctx["pontos"] and not ctx["areas"]:
        return None
    return "window.__recebeContextoDoReal && window.__recebeContextoDoReal(" + json.dumps(ctx, ensure_ascii=False, separators=(",", ":")) + ");\n"


def arquivos_do_mapa(mapa: str) -> dict | None:
    """O que a página do mapa precisa saber: os caminhos (relativos à página) dos arquivos, na ordem de carregar, e o do contexto. None sem contexto."""
    if not mapa or contexto_js(mapa) is None:
        return None
    return {"arquivos": list(ORDEM), "contexto": arquivo_do_contexto(mapa)}


def escreve(destino: Path, mapas: list[str]) -> list[str]:
    """Escreve os arquivos ao lado das páginas (a raiz do site, ou a pasta de um teste); devolve os caminhos escritos."""
    escritos = []
    for rel, origem in ORIGENS.items():
        (destino / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(WEB / origem, destino / rel)
        escritos.append(rel)
    for mapa in mapas:
        js = contexto_js(mapa)
        if js is not None:
            f = destino / arquivo_do_contexto(mapa)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(js, encoding="utf-8")
            escritos.append(arquivo_do_contexto(mapa))
    return escritos
