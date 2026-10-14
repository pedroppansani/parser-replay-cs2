"""Mede, para todo round do corpus, o tamanho da tática que "Abrir round na prancheta" cria (decisão 47, fase 16b).

É a ORIGEM dos tetos de uso das salas (supabase/migrations, notas/seguranca/grupos.md, `B-2`): abre cada
round pela própria `criaDoRound` de `tactics.js` (Chrome via Playwright, na página da prancheta do mapa) e
conta as operações e os bytes MEDIDOS COMO O BANCO MEDE (o texto do jsonb de cada operação:
`Sala.tamanhoNoServidor`, que o PGlite confere). Não grava nada no repositório; imprime o relatório e, com
`--grava-maior`, escreve o documento do maior round (para os testes do PGlite e da parte B).

Uso:
    py -3.12 -m scripts.mede_round_na_prancheta [--grava-maior CAMINHO.json] [--quadro 40]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
WEB = PROJECT_ROOT / "dashboard" / "web"
QUADRO_PADRAO = 40   # o instante de onde o replay abre o round (como tests/test_round_na_prancheta.py)


def _mede_lote(mapa: str, itens: list) -> list[dict]:
    """Um navegador, uma página da prancheta do mapa, um lote de rounds (roda num processo próprio)."""
    from playwright import sync_api

    from scripts.build_tactics_page import build_html

    with sync_api.sync_playwright() as p:
        try:
            navegador = p.chromium.launch(channel="chrome")
        except Exception:
            navegador = p.chromium.launch()
        arquivo = Path(tempfile.mkdtemp(prefix="mede_round_")) / f"prancheta_{mapa}.html"
        arquivo.write_text(build_html(mapa), encoding="utf-8")
        pg = navegador.new_page(viewport={"width": 1400, "height": 1000})
        pg.goto(arquivo.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        pg.add_script_tag(path=str(WEB / "sala.js"))
        res = pg.evaluate("""(itens) => {
            const I = Prancheta._interno, S = I.S, saida = [];
            for (const [nome, payload] of itens) {
                I.criaDoRound(payload);
                const ops = S.doc.operacoes.map(o => Sala.tamanhoNoServidor(o));
                saida.push({ nome, ops: ops.length, bytes: ops.reduce((a, b) => a + b, 0),
                             maiorOp: Math.max(...ops), acima8kb: ops.filter(b => b > 8192).length,
                             compacto: JSON.stringify(S.doc.operacoes).length });
            }
            return saida;
        }""", itens)
        navegador.close()
    for r in res:
        r["mapa"] = mapa
    return res


def _documento_do_round(mapa: str, payload: dict) -> dict:
    from playwright import sync_api

    from scripts.build_tactics_page import build_html

    with sync_api.sync_playwright() as p:
        try:
            navegador = p.chromium.launch(channel="chrome")
        except Exception:
            navegador = p.chromium.launch()
        arquivo = Path(tempfile.mkdtemp(prefix="mede_round_")) / f"prancheta_{mapa}.html"
        arquivo.write_text(build_html(mapa), encoding="utf-8")
        pg = navegador.new_page(viewport={"width": 1400, "height": 1000})
        pg.goto(arquivo.as_uri())
        pg.wait_for_function("() => Prancheta._interno.S.estado !== null")
        doc = pg.evaluate("""(payload) => { Prancheta._interno.criaDoRound(payload);
            return JSON.parse(JSON.stringify(Prancheta._interno.S.doc)); }""", payload)
        navegador.close()
    return doc


LOTE = 40   # rounds por processo: cada round leva ~1 s no navegador (cada operação reaplica o log)


def mede(quadro: int = QUADRO_PADRAO, grava_maior: Path | None = None, processos: int = 8) -> dict:
    from concurrent.futures import ProcessPoolExecutor

    from metrics.round_na_prancheta import TOLERANCIA_U, payload_do_round

    por_mapa: dict[str, list] = {}
    for f in sorted(PROCESSED.glob("*/replay.json")):
        rep = json.loads(f.read_text(encoding="utf-8"))
        mapa = rep.get("map") or rep.get("map_name")
        for rd in rep["rounds"]:
            por_mapa.setdefault(mapa, []).append(
                [f"{f.parent.name} round {rd['round']}", payload_do_round(rep, rd, TOLERANCIA_U, f.parent.name, quadro)])
    tarefas = [(mapa, itens[i:i + LOTE]) for mapa, itens in sorted(por_mapa.items()) for i in range(0, len(itens), LOTE)]
    medidas: list[dict] = []
    with ProcessPoolExecutor(max_workers=processos) as pool:
        for res in pool.map(_mede_lote, [t[0] for t in tarefas], [t[1] for t in tarefas]):
            medidas += res
    por_ops = max(medidas, key=lambda r: r["ops"])
    por_bytes = max(medidas, key=lambda r: r["bytes"])
    if grava_maior is not None:
        payload = next(pl for itens in por_mapa.values() for nm, pl in itens if nm == por_bytes["nome"])
        grava_maior.write_text(json.dumps(_documento_do_round(por_bytes["mapa"], payload), ensure_ascii=False),
                               encoding="utf-8")
    return {"rounds": len(medidas), "maior_em_operacoes": por_ops, "maior_em_bytes": por_bytes,
            "rounds_com_operacao_acima_de_8kb": sum(1 for r in medidas if r["acima8kb"]),
            "todos": medidas}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--quadro", type=int, default=QUADRO_PADRAO)
    ap.add_argument("--grava-maior", type=Path, default=None)
    a = ap.parse_args(argv)
    r = mede(a.quadro, a.grava_maior)
    print(f"rounds medidos: {r['rounds']}; com operação acima de 8 KB: {r['rounds_com_operacao_acima_de_8kb']}")
    for rotulo in ("maior_em_operacoes", "maior_em_bytes"):
        m = r[rotulo]
        print(f"{rotulo}: {m['nome']} ({m['mapa']}): {m['ops']} operações, {m['bytes']} bytes (jsonb), "
              f"maior operação {m['maiorOp']} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
