"""Mede quanto leva criar um grupo a partir do MAIOR round real do corpus, antes e depois do estado inicial numa linha só.

Fase 16b (B-2): com o teto de 300 operações por minuto por autor, subir o estado inicial em lotes (como a fase 13
fazia) pode levar minutos para uma tática grande; o requisito é no máximo 10 s em Fast 4G (mediana de 5).

Como se mede, sem fingir uma rede real (a parte B real mede depois, contra o servidor de verdade):
  * o CLIENTE é o de verdade (Chrome via Playwright, CPU 4x mais lenta, como `scripts/design/mede_lcp_cls.py`), com a
    SalaFalsa, que tem as mesmas regras das migrações e, aqui, um MODELO de rede: cada pedido demora a latência
    (165 ms) mais bytes do pedido / subida (1,5 Mbit/s), e a resposta, bytes / descida (9 Mbit/s) -- `opcoes.rede` do
    `ServidorFalso`;
  * "depois" = o `grupo.js` de agora (um pedido `cria_sala` com o estado inicial dentro);
  * "antes" = o `grupo.js` da fase 13 (commit BASE: `criar`, `entrar` e as operações em lotes de até 20 por janela de
    1,1 s) sobre o mesmo `sala.js` e o mesmo modelo de rede;
  * a estimativa por fórmula é a soma, sobre os pedidos feitos, de latência + bytes / subida, mais o processamento
    medido sem rede (o processamento do cliente em CPU 4x mais lenta).

Uso:  py -3.12 -m scripts.mede_criacao_do_grupo [--rodadas 5]
"""
from __future__ import annotations

import argparse
import io
import json
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEDICAO = PROJECT_ROOT / "supabase" / "medicao"
BASE = "fb2a81bb"   # o main da fase 13 a 15: o grupo.js que sobe o estado inicial em lotes
REDE = {"latenciaMs": 165, "subidaBps": 1_500_000, "descidaBps": 9_000_000}   # Fast 4G (mede_lcp_cls.py)
CPU = 4


def _web_do_antes(destino: Path) -> Path:
    """Uma cópia de dashboard/web de agora com o grupo.js do commit BASE (o cliente de antes)."""
    web = destino / "web"
    shutil.copytree(PROJECT_ROOT / "dashboard" / "web", web)
    antigo = subprocess.run(["git", "show", f"{BASE}:dashboard/web/grupo.js"], cwd=PROJECT_ROOT, capture_output=True,
                            check=True).stdout
    (web / "grupo.js").write_bytes(antigo)
    return web


def _pagina(mapa: str, destino: Path, rede: dict | None, web: Path | None) -> Path:
    from scripts import build_tactics_page as b

    original = b.WEB
    try:
        if web is not None:
            b.WEB = web
        falsa = {"uid": "u-tela", "atrasoMs": 0}
        if rede:
            falsa["rede"] = rede
        html = b.build_html(mapa, grupo={"modo": "falsa", "site": "https://exemplo.github.io/site/",
                                         "pagina": b.arquivo_da_pagina(mapa), "falsa": falsa})
    finally:
        b.WEB = original
    arquivo = destino / f"{'antes' if web else 'depois'}_{'rede' if rede else 'cpu'}_{mapa}.html"
    arquivo.write_text(html, encoding="utf-8")
    return arquivo


def _uma_rodada(navegador, arquivo: Path, doc: dict, cpu: int) -> dict:
    ctx = navegador.new_context(viewport={"width": 375, "height": 667})
    try:
        pg = ctx.new_page()
        cdp = ctx.new_cdp_session(pg)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(arquivo.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null && !!document.getElementById('pr-painel-grupo')")
        assert pg.evaluate("(d) => Prancheta.grupo.usaDocumento(d)", doc) == ""
        pg.evaluate("() => Prancheta._interno.abaDoPainel('grupo')")
        pg.fill("#gr-nick", "nomad")
        t0 = pg.evaluate("() => performance.now()")
        pg.click('[data-acao="criar"]')
        pg.wait_for_function("() => Grupo._interno.G().fase === 'dentro' && Grupo._interno.G().fila.length === 0 "
                             "&& !Grupo._interno.G().enviando", timeout=300000)
        s = (pg.evaluate("() => performance.now()") - t0) / 1000
        trafego = pg.evaluate("() => window.__servidorFalso.trafego")
        assert not erros, erros
        return {"s": s, "trafego": trafego}
    finally:
        ctx.close()


def mede(rodadas: int = 5) -> dict:
    from playwright import sync_api

    doc = json.loads((MEDICAO / "maior_round_documento.json").read_text(encoding="utf-8"))
    resumo = json.loads((MEDICAO / "maior_round_na_prancheta.json").read_text(encoding="utf-8"))
    mapa = resumo["maior_em_bytes"]["mapa"]
    pasta = Path(tempfile.mkdtemp(prefix="mede_criacao_"))
    web_antes = _web_do_antes(pasta)
    paginas = {
        ("antes", "rede"): _pagina(mapa, pasta, REDE, web_antes),
        ("depois", "rede"): _pagina(mapa, pasta, REDE, None),
        ("antes", "cpu"): _pagina(mapa, pasta, None, web_antes),
        ("depois", "cpu"): _pagina(mapa, pasta, None, None),
    }
    saida = {"mapa": mapa, "operacoes": len(doc["operacoes"]), "rodadas": rodadas, "cpu": CPU, "rede": REDE, "base": BASE}
    with sync_api.sync_playwright() as p:
        try:
            navegador = p.chromium.launch(channel="chrome")
        except Exception:
            navegador = p.chromium.launch()
        for (quem, tipo), arquivo in paginas.items():
            rs = [_uma_rodada(navegador, arquivo, doc, CPU) for _ in range(rodadas)]
            saida[f"{quem}_{tipo}"] = {"mediana_s": statistics.median(r["s"] for r in rs), "todas_s": [round(r["s"], 3) for r in rs],
                                      "pedidos": [(t["nome"], t["bytes"]) for t in rs[0]["trafego"]]}
        navegador.close()
    for quem in ("antes", "depois"):
        pedidos = saida[f"{quem}_rede"]["pedidos"]
        rede_s = sum(REDE["latenciaMs"] / 1000 + b * 8 / REDE["subidaBps"] for _, b in pedidos)
        saida[f"{quem}_formula_s"] = saida[f"{quem}_cpu"]["mediana_s"] + rede_s
        saida[f"{quem}_formula_rede_s"] = rede_s
    return saida


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rodadas", type=int, default=5)
    ap.add_argument("--grava", type=Path, default=None, help="escreve o resultado em JSON")
    a = ap.parse_args(argv)
    r = mede(a.rodadas)
    print(f"maior round real: {r['mapa']}, {r['operacoes']} operações; Fast 4G (165 ms, 1,5 Mbit/s), CPU {r['cpu']}x, "
          f"mediana de {r['rodadas']}")
    for quem in ("antes", "depois"):
        x = r[f"{quem}_rede"]
        print(f"{quem:6s} medido com modelo de rede: {x['mediana_s']:.2f} s {x['todas_s']}; "
              f"{len(x['pedidos'])} pedidos, {sum(b for _, b in x['pedidos'])} bytes enviados")
        print(f"       só processamento (sem rede): {r[f'{quem}_cpu']['mediana_s']:.2f} s; "
              f"fórmula (rede {r[f'{quem}_formula_rede_s']:.2f} s + processamento): {r[f'{quem}_formula_s']:.2f} s")
        print("       pedidos:", ", ".join(f"{n}({b} B)" for n, b in x["pedidos"]))
    if a.grava:
        a.grava.write_text(json.dumps(r, ensure_ascii=False, indent=1) + chr(10), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
