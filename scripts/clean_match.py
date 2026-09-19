"""
Apaga a demo e os dados crus de uma partida, SÓ depois de conferir que o
processado dela está íntegro, e registra a limpeza no manifesto.

Sem --confirmar, não apaga nada: mostra o que conferiu e o que apagaria.

O QUE SE PERDE AO APAGAR O data/interim/
----------------------------------------
Os dados crus (ticks, kills, danos) são a entrada de tudo que RECALCULA uma
partida: process_demo --from-interim, build_insights, build_breakdown,
export_replay e as calibrações (fit_rating, fit_archetype_reference). Depois
da limpeza, a partida continua no site exatamente como está, mas mudança de
métrica ou de texto não chega mais nela, e ela sai da recalibração do rating
-- a menos que a demo seja baixada de novo (o manifesto guarda o hash e o link
da HLTV para isso). O interim pesa ~15MB por partida contra 200-500MB da demo:
--manter-interim apaga só a demo e preserva a capacidade de recalcular.

Uso:
    py -3.12 -m scripts.clean_match match_43                    # só confere
    py -3.12 -m scripts.clean_match match_43 --confirmar        # apaga
    py -3.12 -m scripts.clean_match match_43 --confirmar --manter-interim
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import polars as pl

from metrics.sides import placar_valido
from scripts import manifest as mf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"

# O que o site e o dashboard leem de uma partida. Sem qualquer um destes, a
# página não se regenera -- e depois da limpeza não há de onde refazê-lo.
ARQUIVOS_OBRIGATORIOS = (
    "match_meta.json",
    "insights.json",
    "web_payload.json",
    "replay.json",
    "breakdown.json",
    "rounds.parquet",
    "adr_summary.parquet",
    "kast_summary.parquet",
)


def verifica(match_id: str) -> list[str]:
    """Problemas que impedem a limpeza. Lista vazia = pode apagar.

    Junta TODOS os problemas em vez de parar no primeiro: quem vai apagar dado
    quer a lista inteira antes de decidir.
    """
    d = PROCESSED_DIR / match_id
    if not d.is_dir():
        return [f"{match_id} não existe em data/processed/"]
    problemas = []

    for nome in ARQUIVOS_OBRIGATORIOS:
        if not (d / nome).is_file():
            problemas.append(f"falta {nome}")

    for p in sorted(d.glob("*.parquet")):
        try:
            pl.read_parquet(p)
        except Exception as err:
            problemas.append(f"{p.name} não abre: {err}")
    lidos = {}
    for p in sorted(d.glob("*.json")):
        try:
            lidos[p.name] = json.loads(p.read_text(encoding="utf-8"))
        except Exception as err:
            problemas.append(f"{p.name} não abre: {err}")

    if {"match_meta.json", "insights.json"} <= lidos.keys() and (d / "rounds.parquet").is_file():
        n = pl.read_parquet(d / "rounds.parquet").height
        meta_n = lidos["match_meta.json"].get("n_rounds")
        partida = lidos["insights.json"].get("match", {})
        a, b = partida.get("score_a"), partida.get("score_b")
        if meta_n != n:
            problemas.append(f"match_meta diz {meta_n} rounds, rounds.parquet tem {n}")
        if a is None or b is None or not placar_valido(a, b, n):
            problemas.append(f"placar impossível: {a}-{b} em {n} rounds")
        replay = lidos.get("replay.json", {})
        if "rounds" in replay and len(replay["rounds"]) != n:
            problemas.append(f"replay.json tem {len(replay['rounds'])} rounds, a partida tem {n}")

    # A identidade da demo tem que estar registrada ANTES de ela sumir.
    linha = mf.carrega()["partidas"].get(match_id)
    if linha is None:
        problemas.append("partida fora do manifesto: rode `py -3.12 -m scripts.manifest` antes")
    else:
        for x in linha.get("demos", []):
            if x.get("existe", True) and not x.get("sha256"):
                problemas.append(f"manifesto sem hash de {x.get('arquivo')}")

    # A página tem que se regenerar só com o processado.
    if not problemas:
        try:
            from scripts.build_web_page import build_html

            build_html(match_id)
        except Exception as err:
            problemas.append(f"a página não se regenera sem o interim: {err}")
    return problemas


def _alvos(match_id: str, manter_interim: bool) -> list[Path]:
    linha = mf.carrega()["partidas"].get(match_id, {})
    alvos = [mf.PROJECT_ROOT / x["caminho"] for x in linha.get("demos", [])
             if (mf.PROJECT_ROOT / x["caminho"]).is_file()]
    interim = INTERIM_DIR / match_id
    if not manter_interim and interim.is_dir():
        alvos.append(interim)
    return alvos


def _tamanho(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def limpa(match_id: str, confirmar: bool = False, manter_interim: bool = False) -> dict:
    """Confere e, com `confirmar`, apaga. Devolve o que foi (ou seria) feito."""
    problemas = verifica(match_id)
    if problemas:
        return {"ok": False, "problemas": problemas, "removidos": [], "bytes": 0}
    alvos = _alvos(match_id, manter_interim)
    total = sum(_tamanho(p) for p in alvos)
    if not confirmar:
        return {"ok": True, "simulado": True, "removidos": [str(p) for p in alvos], "bytes": total}
    for p in alvos:
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()
    mf.registra_limpeza(match_id, alvos, total)
    return {"ok": True, "simulado": False, "removidos": [str(p) for p in alvos], "bytes": total}


def main() -> None:
    ap = argparse.ArgumentParser(description="Apaga demo e interim de uma partida já processada.")
    ap.add_argument("match_ids", nargs="+")
    ap.add_argument("--confirmar", action="store_true", help="apaga de verdade (sem isto, só confere)")
    ap.add_argument("--manter-interim", action="store_true",
                    help="apaga só a demo; a partida continua recalculável")
    args = ap.parse_args()
    for mid in args.match_ids:
        r = limpa(mid, args.confirmar, args.manter_interim)
        if not r["ok"]:
            print(f"[{mid}] NÃO LIMPA -- processado não está íntegro:")
            for p in r["problemas"]:
                print(f"    - {p}")
            continue
        verbo = "apagaria" if r["simulado"] else "apagou"
        print(f"[{mid}] íntegro; {verbo} {r['bytes'] / 1e6:.0f}MB:")
        for p in r["removidos"]:
            print(f"    - {mf.relativo(p)}")
        if r["simulado"]:
            print("    (simulação: rode de novo com --confirmar para apagar)")


if __name__ == "__main__":
    main()
