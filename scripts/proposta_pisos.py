"""
Proposta ESTRUTURADA dos pisos de função: distribuição, método, casos de fronteira.

    py -3.12 -m scripts.proposta_pisos              # todas as funções
    py -3.12 -m scripts.proposta_pisos --funcao awp

Por que existe: escolher um corte olhando só a lista final é decidir no escuro
(pedido do Pedro, 2026-09-22). O corte ESTATÍSTICO sai daqui, por método
declarado; o que fica para o Pedro é o julgamento de domínio -- olhar os casos de
fronteira e dizer se aquele jogador, naquela partida, jogou a função ou não.

A REGRA QUE O PISO SERVE (metrics/player_roles.py): o rótulo exige LIDERAR o
próprio time na métrica E passar do piso. O piso barra o líder que não é
destacado ("o menos ruim de um time sem AWPer não é AWPer"). Por isso:
  - a distribuição mostrada é a de TODOS os jogador-partidas (diz se a função é
    uma população separada ou um contínuo);
  - os métodos rodam nos dois recortes -- todos e só os líderes de time --, porque
    é entre os líderes que o piso decide alguma coisa;
  - os casos de fronteira são LÍDERES perto do corte: são os únicos para quem o
    piso muda o rótulo.

OS TRÊS MÉTODOS (nenhum tem parâmetro escolhido olhando o resultado):
  vazio   maior salto entre valores consecutivos, dentro dos quantis
          [QUANTIL_VAZIO, 1 - QUANTIL_VAZIO] -- sem o recorte, o maior salto é
          quase sempre o de um outlier na cauda, que não separa população nenhuma;
  otsu    o corte que minimiza a variância dentro das duas classes (em 1D é a
          quebra natural de Jenks com duas classes);
  vale    o ponto de menor densidade entre as duas modas mais altas de uma KDE
          gaussiana com banda de Silverman; sem duas modas, não há vale -- e isso
          já é resposta: a distribuição é unimodal e o corte é convenção.
Concordância: dentro de CADA população, os cortes ficam a menos de
TOL_CONCORDANCIA da amplitude interquartil daquela população -> corte real.
Longe -> a distribuição não tem separação clara e o piso é mais frágil do que
parece. (Primeira versão media o espalhamento misturando as duas populações;
corrigido depois de ver que isso escondia a concordância do AWPer -- o critério
de 25% não mudou.)

Os pisos continuam ABSOLUTOS (decisão do Pedro): o método sugere um número fixo,
nunca "o percentil X do corpus".
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from metrics.identidade import com_nome_de_exibicao  # noqa: E402
from metrics.player_roles import TRAIT_SPECS  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
MANIFESTO = PROJECT_ROOT / "data" / "manifest.json"

# Quantis que delimitam onde o "maior vazio" é procurado. 2,5% em cada ponta
# tira o outlier isolado sem tirar uma população minoritária real (o AWPer é
# ~20% dos jogador-partidas e fica inteiro dentro).
QUANTIL_VAZIO = 0.025

# Dois cortes "concordam" se ficam a menos de 25% da amplitude interquartil da
# métrica um do outro. É relativo à escala da própria métrica: 0,03 de awp_share
# e 3 de ADR não são comparáveis em valor absoluto.
TOL_CONCORDANCIA = 0.25

# Pontos da KDE.
PONTOS_KDE = 512


# ---------------------------------------------------------------------------
# Métodos
# ---------------------------------------------------------------------------

def corte_vazio(x: np.ndarray) -> float | None:
    lo, hi = np.quantile(x, [QUANTIL_VAZIO, 1 - QUANTIL_VAZIO])
    v = np.sort(x[(x >= lo) & (x <= hi)])
    if len(v) < 3:
        return None
    saltos = np.diff(v)
    i = int(np.argmax(saltos))
    return float((v[i] + v[i + 1]) / 2)


def corte_otsu(x: np.ndarray) -> float | None:
    v = np.sort(x)
    melhor, corte = math.inf, None
    for i in range(1, len(v)):
        if v[i] == v[i - 1]:
            continue
        a, b = v[:i], v[i:]
        custo = a.var() * len(a) + b.var() * len(b)
        if custo < melhor:
            melhor, corte = custo, float((v[i - 1] + v[i]) / 2)
    return corte


def _kde(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = len(x)
    desvio = min(x.std(ddof=1), (np.quantile(x, 0.75) - np.quantile(x, 0.25)) / 1.349) or x.std(ddof=1)
    h = 0.9 * desvio * n ** (-1 / 5)  # Silverman
    grade = np.linspace(x.min(), x.max(), PONTOS_KDE)
    dens = np.exp(-0.5 * ((grade[:, None] - x[None, :]) / h) ** 2).sum(axis=1) / (n * h * math.sqrt(2 * math.pi))
    return grade, dens


def corte_vale(x: np.ndarray) -> float | None:
    if len(np.unique(x)) < 5:
        return None
    grade, d = _kde(x)
    picos = [i for i in range(1, len(d) - 1) if d[i] > d[i - 1] and d[i] >= d[i + 1]]
    if len(picos) < 2:
        return None  # unimodal: não há vale
    a, b = sorted(sorted(picos, key=lambda i: d[i], reverse=True)[:2])
    i = a + int(np.argmin(d[a:b + 1]))
    return float(grade[i])


METODOS = {"vazio": corte_vazio, "otsu": corte_otsu, "vale": corte_vale}


# ---------------------------------------------------------------------------
# Dados
# ---------------------------------------------------------------------------

def carrega() -> pl.DataFrame:
    """Uma linha por jogador-partida PROFISSIONAL, com o time pelo nome e quem lidera."""
    man = json.loads(MANIFESTO.read_text(encoding="utf-8"))["partidas"]
    partes = []
    for d in sorted(PROCESSED.glob("match_*")):
        info = man.get(d.name, {})
        if info.get("origem") != "profissional":
            continue
        r = pl.read_parquet(d / "player_roles.parquet").with_columns(
            pl.lit(d.name).alias("match_id"),
            pl.col("team").replace_strict({t: (info["times"][t]["nome"] or t) for t in ("A", "B")},
                                          default=pl.col("team")).alias("time"),
            pl.lit(info.get("mapa", "").replace("de_", "")).alias("mapa"),
        )
        partes.append(r)
    # identidade é o steamid; o nome mostrado é o nick mais frequente (metrics/identidade.py)
    return com_nome_de_exibicao(pl.concat(partes, how="diagonal_relaxed"))


def _histograma(x: np.ndarray, cortes: dict[str, float | None], largura: int = 46, faixas: int = 18) -> list[str]:
    lo, hi = float(x.min()), float(x.max())
    if hi == lo:
        return [f"  (todos os valores = {lo})"]
    bordas = np.linspace(lo, hi, faixas + 1)
    cont, _ = np.histogram(x, bordas)
    maior = cont.max()
    linhas = []
    for i, c in enumerate(cont):
        marcas = [k for k, v in cortes.items() if v is not None and bordas[i] <= v < bordas[i + 1]
                  or (i == faixas - 1 and v == hi)]
        barra = "#" * int(round(c / maior * largura))
        linhas.append(f"  {bordas[i]:>8.3f}-{bordas[i + 1]:<8.3f} {c:>4} {barra}" + (f"   <- {', '.join(marcas)}" if marcas else ""))
    return linhas


def _concordancia(cortes: dict[str, float | None], escala: float) -> tuple[bool, float, float | None]:
    """(concordam?, espalhamento em amplitudes interquartis, mediana dos cortes)."""
    validos = [v for v in cortes.values() if v is not None]
    if len(validos) < 2:
        return False, math.inf, (validos[0] if validos else None)
    espalhamento = (max(validos) - min(validos)) / escala
    return espalhamento <= TOL_CONCORDANCIA, espalhamento, float(np.median(validos))


def _iqr(x: np.ndarray) -> float:
    return float(np.quantile(x, 0.75) - np.quantile(x, 0.25)) or float(x.std()) or 1.0


def analisa(df: pl.DataFrame, trait) -> dict:
    """A concordância é medida DENTRO de cada população, com a escala dela.

    As duas respondem perguntas diferentes -- "a função é uma população separada
    entre todos os jogadores?" e "entre os líderes de time, onde o destacado se
    separa do que só lidera um time sem a função?" -- e misturar os cortes das
    duas numa medida só escondia concordância real (no AWPer, os três métodos
    caem em 0,27-0,29 entre todos os jogadores, e isso sumia na mistura).
    """
    col = trait.column
    base = df.drop_nulls(col)
    lider = base.filter(pl.col(col) == pl.col(col).max().over("match_id", "team"))
    pops = {"todos": base[col].to_numpy().astype(float), "líderes": lider[col].to_numpy().astype(float)}
    cortes = {"atual": trait.floor}
    conc = {}
    for pop, x in pops.items():
        c = {nome: f(x) for nome, f in METODOS.items()}
        cortes.update({f"{nome} ({pop})": v for nome, v in c.items()})
        conc[pop] = (*_concordancia(c, _iqr(x)), _iqr(x))
    # o piso decide entre os LÍDERES: se lá os métodos concordam, é esse o corte;
    # senão, o de todos os jogadores; senão, não há corte estatístico.
    for pop in ("líderes", "todos"):
        if conc[pop][0]:
            sugerido, pop_sugerida = conc[pop][2], pop
            break
    else:
        sugerido, pop_sugerida = None, None
    return {"trait": trait, "pops": pops, "lider_df": lider, "cortes": cortes, "conc": conc,
            "sugerido": sugerido, "pop_sugerida": pop_sugerida, "n_partidas": base["match_id"].n_unique()}


VIZINHOS = 5  # casos mais próximos de cada lado de cada corte


def _fronteira(lider: pl.DataFrame, col: str, corte: float, fmt) -> list[str]:
    acima = lider.filter(pl.col(col) >= corte).sort(col).head(VIZINHOS)
    abaixo = lider.filter(pl.col(col) < corte).sort(col, descending=True).head(VIZINHOS)
    linhas = [f"| lado | jogador | time | partida | mapa | {col} |", "|---|---|---|---|---|---|"]
    for r in acima.sort(col, descending=True).iter_rows(named=True):
        linhas.append(f"| rótulo | {r['name']} | {r['time']} | {r['match_id']} | {r['mapa']} | {fmt(r[col])} |")
    linhas.append(f"| — corte {fmt(corte)} — | | | | | |")
    for r in abaixo.iter_rows(named=True):
        linhas.append(f"| sem rótulo | {r['name']} | {r['time']} | {r['match_id']} | {r['mapa']} | {fmt(r[col])} |")
    return linhas


def relata(a: dict) -> str:
    t, col = a["trait"], a["trait"].column
    fmt = (lambda v: f"{v:.1f}") if t.floor >= 5 else (lambda v: f"{v:.3f}")
    lid = a["pops"]["líderes"]
    s = [f"### {t.label} — `{col}`, piso atual {fmt(t.floor)}", ""]
    s.append(f"{len(a['pops']['todos'])} jogador-partidas profissionais em {a['n_partidas']} partidas; "
             f"{len(lid)} líderes de time (empate na liderança conta os dois).")
    for pop in ("todos", "líderes"):
        s += ["", f"Distribuição -- {pop.upper()} (as marcas são os cortes de cada método):", "```"]
        s += _histograma(a["pops"][pop], {k: v for k, v in a["cortes"].items() if pop in k or k == "atual"})
        s.append("```")
    s += ["", "| método | corte | líderes que levam o rótulo |", "|---|---|---|"]
    for k, v in a["cortes"].items():
        if v is None:
            s.append(f"| {k} | sem corte (distribuição unimodal) | — |")
        else:
            s.append(f"| {k} | {fmt(v)} | {int((lid >= v).sum())} de {len(lid)} |")
    s.append("")
    for pop in ("todos", "líderes"):
        ok, esp, med, iqr = a["conc"][pop]
        estado = "CONCORDAM" if ok else ("sem cortes suficientes" if esp == math.inf else "discordam")
        s.append(f"- {pop}: espalhamento {esp:.2f} amplitude interquartil ({fmt(iqr)}) -> **{estado}**"
                 + (f", mediana {fmt(med)}" if med is not None and ok else ""))
    if a["sugerido"] is None:
        s += ["", "**Veredito: sem separação clara.** Nenhuma das duas populações tem métodos concordando: "
                  "a métrica é um contínuo aqui, e o piso é convenção, não corte estatístico. É o caso em que "
                  "a fronteira do piso ATUAL é tudo o que há para julgar."]
        candidatos = {"atual": t.floor}
    else:
        s += ["", f"**Veredito: corte real em {fmt(a['sugerido'])}** (métodos concordam entre {a['pop_sugerida']}). "
                  f"Piso atual {fmt(t.floor)}: {int((lid >= t.floor).sum())} líderes com rótulo; "
                  f"sugerido: {int((lid >= a['sugerido']).sum())}."]
        candidatos = {"atual": t.floor, "sugerido": a["sugerido"]}
    for nome, c in candidatos.items():
        s += ["", f"**Fronteira do corte {nome} ({fmt(c)})** -- os {VIZINHOS} líderes mais próximos de cada lado:", ""]
        s += _fronteira(a["lider_df"], col, c, fmt)
    s += ["", f"**Sua resposta:** os jogadores da fronteira jogaram de {t.label} naquelas partidas? "
              f"piso de {t.label} = ____", ""]
    return chr(10).join(s)


def main() -> None:
    ap = argparse.ArgumentParser(description="Proposta estruturada dos pisos de função.")
    ap.add_argument("--funcao", help="key do TRAIT_SPECS (awp, entry, support, lurk, anchor, trade, frag)")
    args = ap.parse_args()
    df = carrega()
    for t in TRAIT_SPECS:
        if args.funcao and t.key != args.funcao:
            continue
        print(relata(analisa(df, t)))


if __name__ == "__main__":
    main()
