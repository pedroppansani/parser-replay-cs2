"""Tabela de impacto de uma mudança que mexe em número na tela.

Compara `data/processed/*/insights.json` de uma revisão do git (`--antes`,
padrão `main`) com o que está no disco: quantos jogador-partidas mudaram de
rating, de marca de amostra fraca e de MVP, e o erro médio e a correlação do
rating contra o oficial da HLTV (`data/reference/hltv_ratings.json`, só as
partidas com `usar_na_calibracao`) antes e depois.

Uso:
    py -3.12 -m scripts.impacto_rating [--antes main] [--lista 20]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
PROCESSED = RAIZ / "data" / "processed"
HLTV = RAIZ / "data" / "reference" / "hltv_ratings.json"


def insights(rev: str | None) -> dict[str, dict]:
    out = {}
    for d in sorted(PROCESSED.glob("match_*")):
        rel = (d / "insights.json").relative_to(RAIZ).as_posix()
        if rev is None:
            if (d / "insights.json").exists():
                out[d.name] = json.loads((d / "insights.json").read_text(encoding="utf-8"))
            continue
        r = subprocess.run(["git", "show", f"{rev}:{rel}"], capture_output=True, cwd=RAIZ)
        if r.returncode == 0:
            out[d.name] = json.loads(r.stdout.decode("utf-8"))
    return out


def contra_a_hltv(ins: dict[str, dict]) -> dict:
    oficial = json.loads(HLTV.read_text(encoding="utf-8"))["partidas"]
    nosso, deles = [], []
    for partida, o in oficial.items():
        if not o.get("usar_na_calibracao") or partida not in ins:
            continue
        por_nome = {p["name"]: p.get("rating") for p in ins[partida]["players"]}
        for nome, r in (o.get("jogadores") or {}).items():
            if r is not None and por_nome.get(nome) is not None:
                nosso.append(por_nome[nome]); deles.append(r)
    a, b = np.array(nosso), np.array(deles)
    return {"n": int(a.size), "erro_medio": float(np.abs(a - b).mean()),
            "correlacao": float(np.corrcoef(a, b)[0, 1]), "media_nossa": float(a.mean()), "media_hltv": float(b.mean())}


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--antes", default="main")
    ap.add_argument("--lista", type=int, default=20)
    a = ap.parse_args()
    antes, depois = insights(a.antes), insights(None)
    mud, fraca, mvp, total = [], [], [], 0
    for partida, d in depois.items():
        x = antes.get(partida)
        if x is None:
            continue
        pa = {p["steamid"]: p for p in x["players"]}
        for p in d["players"]:
            q = pa.get(p["steamid"])
            if q is None:
                continue
            total += 1
            if q.get("rating") != p.get("rating"):
                mud.append((partida, p["name"], q.get("rating"), p.get("rating")))
            if q.get("rating_amostra_fraca") != p.get("rating_amostra_fraca"):
                fraca.append((partida, p["name"], q.get("rating_amostra_fraca"), p.get("rating_amostra_fraca")))
        ma, md = (x.get("mvp_card") or {}).get("name"), (d.get("mvp_card") or {}).get("name")
        if ma != md:
            mvp.append((partida, ma, md))
    print(f"jogador-partidas comparados: {total}")
    print(f"rating mudou em {len(mud)}; amostra fraca mudou em {len(fraca)}; MVP mudou em {len(mvp)} partidas")
    for linha in mud[: a.lista]:
        print("  rating:", linha)
    for linha in fraca[: a.lista]:
        print("  amostra fraca:", linha)
    for linha in mvp[: a.lista]:
        print("  MVP:", linha)
    ha, hd = contra_a_hltv(antes), contra_a_hltv(depois)
    print("\n| contra a HLTV | n | erro médio | correlação | média nossa | média HLTV |\n|---|---|---|---|---|---|")
    for nome, h in (("antes", ha), ("depois", hd)):
        print(f"| {nome} | {h['n']} | {h['erro_medio']:.4f} | {h['correlacao']:.4f} | {h['media_nossa']:.4f} | {h['media_hltv']:.4f} |")
    print(f"\nvariação do erro médio: {hd['erro_medio'] - ha['erro_medio']:+.4f}")


if __name__ == "__main__":
    main()
