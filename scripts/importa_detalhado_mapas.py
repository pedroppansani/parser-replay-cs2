"""
Importa os Detailed stats da HLTV transcritos POR MAPA para os gabaritos.

    py -3.12 -m scripts.importa_detalhado_mapas            # confere e mostra
    py -3.12 -m scripts.importa_detalhado_mapas --gravar   # grava nos gabaritos

Entrada: `data/reference/brutos/hltv_detalhado_por_mapa_*.tsv` (a transcrição,
versionada, para ter procedência).
Saída:
  - `hltv_detalhado.json`: uma série por grupo de mapas, com as contagens
    SOMADAS (é a unidade que a escada compara) e o detalhe de cada mapa;
  - `hltv_componentes.json`: KAST e Swing por mapa, para as partidas que ainda
    não estão lá (as que já estão são conferidas, nunca sobrescritas).

TRÊS CONFERÊNCIAS, e nenhuma usa o nosso número para decidir o casamento:
  1. transcrição: as aberturas de um mapa somam exatamente o número de rounds, e
     as feitas por um time são as sofridas pelo outro -- erro de digitação
     aparece aqui, antes de chegar perto do corpus;
  2. casamento: mapa + elenco + número de rounds (lido do KAST: 76,2% = 16/21).
     O K-D NÃO entra, senão o degrau 1 da escada vira circular;
  3. procedência: o rating colado bate com o que já está em hltv_ratings.json
     para aquela partida -- é o critério com que os prints sempre foram casados.
Se qualquer uma falha, nada é gravado.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

REF = PROJECT_ROOT / "data" / "reference"
BRUTOS = REF / "brutos"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"

# Nome na HLTV -> nome na demo, quando diferem. A identidade é o steamid
# (metrics/identidade.py); aqui só se casa o texto da página com o da demo.
APELIDOS_HLTV = {"sh1ro": "SH1R0", "Techno": "Techno4K", "mzinho": "Mzinho"}

# Tolerância de arredondamento do KAST da página (uma casa decimal).
TOL_KAST = 0.051

# Rating da página contra o já registrado: o print tem duas casas.
TOL_RATING = 0.005

CONTAGENS = ["op_k", "op_d", "mk", "clutches", "kills", "hs", "assist", "assist_flash", "mortes", "trocadas"]


def le_brutos() -> pl.DataFrame:
    partes = [pl.read_csv(f, separator="\t", comment_prefix="#") for f in sorted(BRUTOS.glob("hltv_detalhado_por_mapa_*.tsv"))]
    return pl.concat(partes, how="vertical_relaxed") if partes else pl.DataFrame()


def rounds_pelo_kast(kasts: list[float]) -> int | None:
    """Menor número de rounds que reproduz TODOS os KASTs do mapa no arredondamento."""
    for n in range(10, 70):
        if all(abs(round(k / 100 * n) / n * 100 - k) < TOL_KAST for k in kasts):
            return n
    return None


def confere_transcricao(d: pl.DataFrame) -> list[str]:
    erros = []
    for (serie, mapa), g in d.group_by("serie", "mapa", maintain_order=True):
        n = rounds_pelo_kast(g["kast_pct"].to_list())
        times = g["time"].unique(maintain_order=True).to_list()
        if len(times) != 2 or g.height != 10:
            erros.append(f"{serie} {mapa}: {g.height} jogadores em {len(times)} times")
            continue
        a, b = (g.filter(pl.col("time") == t) for t in times)
        if n is None:
            erros.append(f"{serie} {mapa}: KAST não reproduz um número de rounds")
        elif g["op_k"].sum() != n:
            erros.append(f"{serie} {mapa}: aberturas somam {g['op_k'].sum()}, rounds {n}")
        if a["op_k"].sum() != b["op_d"].sum() or b["op_k"].sum() != a["op_d"].sum():
            erros.append(f"{serie} {mapa}: aberturas feitas e sofridas não fecham entre os times")
    return erros


def casa_com_o_corpus(d: pl.DataFrame) -> tuple[dict, list[str]]:
    """(serie, mapa) -> match_id, por mapa + elenco + rounds. Nunca pelo K-D."""
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    casamento, erros = {}, []
    for (serie, mapa), g in d.group_by("serie", "mapa", maintain_order=True):
        n = rounds_pelo_kast(g["kast_pct"].to_list())
        elenco = {APELIDOS_HLTV.get(j, j).lower() for j in g["jogador"]}
        candidatos = [
            mid for mid, v in man.items()
            if (v.get("mapa") or "").replace("de_", "") == mapa and v.get("rounds") == n
            and {j.lower() for t in ("A", "B") for j in v["times"][t]["jogadores"]} == elenco
        ]
        if len(candidatos) != 1:
            erros.append(f"{serie} {mapa} ({n} rounds): {len(candidatos)} partidas candidatas {candidatos}")
        else:
            casamento[(serie, mapa)] = candidatos[0]
    return casamento, erros


def confere_rating(d: pl.DataFrame, casamento: dict) -> list[str]:
    ratings = json.loads((REF / "hltv_ratings.json").read_text(encoding="utf-8"))["partidas"]
    erros = []
    for r in d.iter_rows(named=True):
        mid = casamento.get((r["serie"], r["mapa"]))
        if not mid:
            continue
        registrado = (ratings.get(mid, {}).get("jogadores") or {})
        nome = APELIDOS_HLTV.get(r["jogador"], r["jogador"])
        oficial = registrado.get(nome, registrado.get(r["jogador"]))
        if oficial is not None and abs(oficial - r["rating"]) > TOL_RATING:
            erros.append(f"{mid} {r['jogador']}: rating colado {r['rating']} contra {oficial} registrado")
    return erros


def series(d: pl.DataFrame, casamento: dict) -> dict:
    """Entradas no formato de hltv_detalhado.json, somando os mapas de cada série."""
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    out = {}
    for (serie,), g in d.group_by("serie", maintain_order=True):
        mapas = g["mapa"].unique(maintain_order=True).to_list()
        mids = [casamento[(serie, m)] for m in mapas]
        rounds = sum(man[m]["rounds"] for m in mids)
        jogadores = {}
        for (nome,), h in g.group_by("jogador", maintain_order=True):
            kast_rounds = sum(round(k / 100 * man[casamento[(serie, m)]]["rounds"])
                              for k, m in zip(h["kast_pct"], h["mapa"]))
            dano = sum(adr * man[casamento[(serie, m)]]["rounds"] for adr, m in zip(h["adr"], h["mapa"]))
            jogadores[nome] = {
                "op_kills": int(h["op_k"].sum()), "op_mortes": int(h["op_d"].sum()),
                "mk_rounds": int(h["mk"].sum()), "clutches": int(h["clutches"].sum()),
                "kills": int(h["kills"].sum()), "hs": int(h["hs"].sum()),
                "assist": int(h["assist"].sum()), "assist_flash": int(h["assist_flash"].sum()),
                "mortes": int(h["mortes"].sum()), "mortes_trocadas": int(h["trocadas"].sum()),
                "kast_rounds": kast_rounds, "kast_pct": round(100 * kast_rounds / rounds, 1),
                # ADR da série reconstruído dos ADRs por mapa (arredondados a 0,1): serve
                # para conferência grossa, não para o degrau 2, que usa o placar por mapa
                "adr": round(dano / rounds, 1),
            }
        out[serie] = {
            "mapas": mids, "rounds_no_corpus": rounds, "serie_completa_no_corpus": True,
            "fonte": "transcrito POR MAPA (brutos/hltv_detalhado_por_mapa_*.tsv) e somado; "
                     "rating, swing e mk_rating da série não são deriváveis dos mapas e ficam de fora",
            "jogadores": jogadores,
            "por_mapa": {casamento[(serie, m)]: g.filter(pl.col("mapa") == m).drop("serie").to_dicts() for m in mapas},
        }
    return out


def componentes(d: pl.DataFrame, casamento: dict) -> dict:
    """KAST e Swing por mapa no formato de hltv_componentes.json, nomes como na demo."""
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    out = {}
    for (serie, mapa), g in d.group_by("serie", "mapa", maintain_order=True):
        mid = casamento[(serie, mapa)]
        n = man[mid]["rounds"]
        out[mid] = {"rounds": n, "jogadores": {
            APELIDOS_HLTV.get(r["jogador"], r["jogador"]): {
                "kast_pct": r["kast_pct"], "kast_rounds": round(r["kast_pct"] / 100 * n), "swing_pct": r["swing"]}
            for r in g.iter_rows(named=True)}}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--gravar", action="store_true")
    args = ap.parse_args()

    d = le_brutos()
    print(f"{d.height} linhas, {d.select('serie', 'mapa').unique(maintain_order=True).height} mapas, "
          f"{d['serie'].n_unique()} séries")
    erros = confere_transcricao(d)
    casamento, e2 = casa_com_o_corpus(d)
    erros += e2 + confere_rating(d, casamento)
    for (serie, mapa), mid in casamento.items():
        print(f"  {serie:<40} {mapa:<7} -> {mid}")
    if erros:
        print("\nFALHOU -- nada gravado:")
        for e in erros:
            print("  ", e)
        raise SystemExit(1)
    print("\n1. transcrição: aberturas fecham em todos os mapas")
    print("2. casamento: mapa + elenco + rounds, um candidato por mapa")
    print("3. procedência: rating colado = rating já registrado em todos os jogadores")

    novas_series = series(d, casamento)
    novos_comp = componentes(d, casamento)
    if not args.gravar:
        print("\n(simulação: use --gravar)")
        return

    det_arq = REF / "hltv_detalhado.json"
    det = json.loads(det_arq.read_text(encoding="utf-8"))
    det["series"].update(novas_series)
    for hltv, demo in APELIDOS_HLTV.items():
        det.setdefault("apelidos", {}).setdefault(hltv, demo)
    det_arq.write_text(json.dumps(det, ensure_ascii=False, indent=2), encoding="utf-8")

    comp_arq = REF / "hltv_componentes.json"
    comp = json.loads(comp_arq.read_text(encoding="utf-8"))
    acrescentadas, divergentes = [], []
    for mid, v in novos_comp.items():
        if mid not in comp["partidas"]:
            comp["partidas"][mid] = v
            acrescentadas.append(mid)
            continue
        for nome, x in v["jogadores"].items():
            y = comp["partidas"][mid]["jogadores"].get(nome)
            if y and (y["kast_pct"] != x["kast_pct"] or y["swing_pct"] != x["swing_pct"]):
                divergentes.append(f"{mid} {nome}: {y} contra {x}")
    comp["partidas"] = dict(sorted(comp["partidas"].items()))
    comp_arq.write_text(json.dumps(comp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ngravado: {len(novas_series)} séries em hltv_detalhado.json; "
          f"componentes acrescentados: {acrescentadas or 'nenhum'}")
    if divergentes:
        print("ATENÇÃO, componentes já registrados que divergem do colado (não sobrescritos):")
        for x in divergentes:
            print("  ", x)


if __name__ == "__main__":
    main()
