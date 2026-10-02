"""Os números que o projeto CITA, calculados dos dados e gravados num lugar só.

POR QUE EXISTE: número digitado à mão envelhece. A página dizia "Nove partidas
(1.870 jogador-rounds)" com 52 partidas no corpus. Todo texto que cita o
corpus, a validação ou uma contagem lê `data/processed/numeros_citaveis.json`
-- a página da partida, a landing e o README.

Cada bloco diz de onde saiu. O que depende de `data/interim/` (que não vai
para o git) é recalculado quando o interim existe; sem ele (clone limpo, CI) o
valor gravado é MANTIDO e o bloco diz que foi mantido.

Uso:
    py -3.12 -m scripts.numeros_citaveis          # recalcula e grava
    py -3.12 -m scripts.numeros_citaveis --ver    # só imprime
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PROCESSED = RAIZ / "data" / "processed"
INTERIM = RAIZ / "data" / "interim"
SAIDA = PROCESSED / "numeros_citaveis.json"
ARMAS_SEM_MIRA = ["inferno", "planted_c4", "hegrenade"]


def corpus() -> dict:
    """Partidas, mapas e volume, do manifesto (versionado)."""
    partidas = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    por_origem: dict[str, int] = {}
    jogador_rounds = jogador_partidas = 0
    times = set()
    for p in partidas.values():
        por_origem[p.get("origem") or "desconhecida"] = por_origem.get(p.get("origem") or "desconhecida", 0) + 1
        n = sum(len((p.get("times") or {}).get(lado, {}).get("jogadores") or []) for lado in ("A", "B"))
        jogador_partidas += n
        jogador_rounds += n * int(p.get("rounds") or 0)
        if p.get("origem") == "profissional":
            times.update(t["nome"] for t in (p.get("times") or {}).values() if t.get("nome"))
    return {
        "fonte": "data/manifest.json",
        "partidas": len(partidas),
        "por_origem": dict(sorted(por_origem.items())),
        "mapas": sorted({p["mapa"] for p in partidas.values() if p.get("mapa")}),
        "times_profissionais": len(times),
        "jogador_partidas": jogador_partidas,
        "jogador_rounds": jogador_rounds,
    }


def convencao_de_angulos(anterior: dict | None) -> dict:
    """Erro mediano da mira do matador até a vítima no tick da kill, na
    convenção adotada (pitch positivo = olhar para baixo) e na invertida."""
    from metrics.geometry import add_aim_error_columns

    certos, invertidos, n_partidas = [], [], 0
    for d in sorted(INTERIM.glob("match_*")) if INTERIM.exists() else []:
        if not (d / "kills.parquet").exists():
            continue
        k = pl.read_parquet(d / "kills.parquet")
        if "attacker_pitch" not in k.columns:
            continue
        k = k.filter(pl.col("attacker_X").is_not_null() & pl.col("attacker_pitch").is_not_null()
                     & pl.col("victim_X").is_not_null() & (~pl.col("weapon").is_in(ARMAS_SEM_MIRA)))
        if k.height == 0:
            continue
        n_partidas += 1
        cols = dict(shooter_x="attacker_X", shooter_y="attacker_Y", shooter_z="attacker_Z",
                    shooter_yaw="attacker_yaw", target_x="victim_X", target_y="victim_Y", target_z="victim_Z")
        certos.append(add_aim_error_columns(k, shooter_pitch="attacker_pitch", **cols)["aim_error_deg"].to_numpy())
        inv = k.with_columns((-pl.col("attacker_pitch")).alias("_p"))
        invertidos.append(add_aim_error_columns(inv, shooter_pitch="_p", **cols)["aim_error_deg"].to_numpy())
    if not certos:
        return {**(anterior or {}), "mantido": "sem data/interim/ nesta máquina: valor da última medição"}
    c, i = np.concatenate(certos), np.concatenate(invertidos)
    # matador e vítima no mesmo ponto não têm direção: saem da conta
    ok = np.isfinite(c) & np.isfinite(i)
    c, i = c[ok], i[ok]
    return {
        "fonte": "data/interim/*/kills.parquet (metrics.geometry.add_aim_error_columns)",
        "erro_mediano_graus": round(float(np.median(c)), 2),
        "erro_mediano_invertida_graus": round(float(np.median(i)), 2),
        "kills": int(c.size), "partidas": n_partidas,
    }


def estilos() -> dict:
    nomes = json.loads((RAIZ / "clustering" / "cluster_names.json").read_text(encoding="utf-8"))
    grupos = [k for k in nomes if str(k).lstrip("-").isdigit()] if isinstance(nomes, dict) else nomes
    return {"fonte": "clustering/cluster_names.json", "grupos": len(grupos)}


def calcula() -> dict:
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    return {
        "_leia_isto": ("Gerado por py -3.12 -m scripts.numeros_citaveis. Não editar à mão: a página, a "
                       "landing e o README leem daqui."),
        "corpus": corpus(),
        "convencao_de_angulos": convencao_de_angulos(anterior.get("convencao_de_angulos")),
        "estilos": estilos(),
    }


def carrega() -> dict:
    return json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else calcula()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    doc = calcula()
    if "--ver" not in sys.argv:
        SAIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
