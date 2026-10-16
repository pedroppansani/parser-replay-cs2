"""
Escada de validação do rating contra os números OFICIAIS da HLTV.

    py -3.12 -m scripts.escada_validacao            # todos os degraus
    py -3.12 -m scripts.escada_validacao --rapido   # sem o Round Swing (o mais lento)

Valida-se de baixo para cima, e um degrau só vale se o de baixo estiver exato:
rating final próximo com contagem errada é coincidência, e coincidência quebra
na partida seguinte.

    1. rounds, kills e mortes      -- contagem: tem que bater EXATO
    2. ADR                         -- exato no arredondamento da HLTV (0,1)
    3. KAST                        -- rounds inteiros: exato
    4. aberturas, multi-kills, HS  -- contagem por SÉRIE (Detailed stats): exato
    4b. assistência de flash       -- contagem por MAPA e por SÉRIE (A (f)): exato;
                                      informativo enquanto não bate (decisão 22j)
    5. Round Swing                -- aqui começa a aproximação: correlação e erro
    6. rating                      -- por último

Fontes oficiais, todas transcritas dos prints da HLTV:
  data/reference/hltv_placar.json      K, D, ADR (410 jogadores, 41 partidas)
  data/reference/hltv_componentes.json KAST e Swing (330 jogadores, 33 partidas)
  data/reference/hltv_ratings.json     rating (430 jogadores, 43 partidas)
  data/reference/hltv_detalhado.json   Detailed stats por série (50 jogadores, 5 séries)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from parsing.parser import kills_do_round_jogado  # noqa: E402

REF = PROJECT_ROOT / "data" / "reference"
PROCESSED = PROJECT_ROOT / "data" / "processed"
INTERIM = PROJECT_ROOT / "data" / "interim"

# A HLTV mostra o ADR com uma casa: a diferença que o arredondamento explica é
# metade do último dígito.
TOLERANCIA_ADR = 0.05

# Grafia da HLTV -> grafia gravada na demo, onde diferem.
APELIDOS = {"sh1ro": "SH1R0", "mzinho": "Mzinho", "Techno": "Techno4K"}


def _ler(nome: str) -> dict:
    return json.loads((REF / nome).read_text(encoding="utf-8"))["partidas"]


def _nome(n: str, conhecidos) -> str:
    return n if n in conhecidos else APELIDOS.get(n, n)


def contagens(interim: Path = INTERIM, partidas: list[str] | None = None) -> pl.DataFrame:
    """Degraus 1 a 3: uma linha por jogador com o oficial e o nosso lado a lado.

    `interim` e `partidas` existem para a fixture do CI (tests/fixtures/interim_ci,
    auditoria 5.7): o interim inteiro não é versionado."""
    placar = _ler("hltv_placar.json")
    comp = _ler("hltv_componentes.json")
    linhas = []
    for mid, v in placar.items():
        if partidas is not None and mid not in partidas:
            continue
        rounds = pl.read_parquet(PROCESSED / mid / "rounds.parquet")
        k = kills_do_round_jogado(pl.read_parquet(interim / mid / "kills.parquet"), rounds)
        kills = dict(k.filter(pl.col("attacker_side") != pl.col("victim_side")).group_by("attacker_name", maintain_order=True).len().iter_rows())
        mortes = dict(k.group_by("victim_name", maintain_order=True).len().iter_rows())
        adr = dict(pl.read_parquet(PROCESSED / mid / "adr_summary.parquet").select("name", "adr").iter_rows())
        kast = dict(pl.read_parquet(PROCESSED / mid / "kast_summary.parquet").select("name", "kast_rounds").iter_rows())
        of_comp = (comp.get(mid) or {}).get("jogadores", {})
        for nome, o in v["jogadores"].items():
            oc = of_comp.get(nome) or of_comp.get({b: a for a, b in APELIDOS.items()}.get(nome, "")) or {}
            linhas.append({
                "match_id": mid, "nome": nome,
                "rounds_oficial": v["rounds"], "rounds": rounds.height,
                "kills_oficial": o["kills"], "kills": kills.get(nome, 0),
                "mortes_oficial": o["mortes"], "mortes": mortes.get(nome, 0),
                "adr_oficial": o["adr"], "adr": adr.get(nome),
                "kast_oficial": oc.get("kast_rounds"), "kast": kast.get(nome),
            })
    return pl.DataFrame(linhas, infer_schema_length=None)


def detalhado() -> pl.DataFrame:
    """Degrau 4: contagens da página 'Detailed stats' da HLTV, que é por SÉRIE --
    os nossos mapas de cada série são somados antes de comparar. Série que não
    está inteira no corpus fica de fora."""
    arq = REF / "hltv_detalhado.json"
    if not arq.exists():
        return pl.DataFrame()
    ref = json.loads(arq.read_text(encoding="utf-8"))
    apelidos = ref.get("apelidos", {})
    linhas = []
    for serie, v in ref["series"].items():
        if not v.get("serie_completa_no_corpus"):
            continue
        soma: dict[str, dict] = {}
        for mid in v["mapas"]:
            rounds = pl.read_parquet(PROCESSED / mid / "rounds.parquet")
            k = kills_do_round_jogado(pl.read_parquet(INTERIM / mid / "kills.parquet"), rounds)
            inim = k.filter(pl.col("attacker_steamid").is_not_null() & (pl.col("attacker_side") != pl.col("victim_side")))
            # abertura = a primeira kill em inimigo do round (fogo amigo e bomba não abrem)
            primeira = inim.sort("tick").group_by("round_num", maintain_order=True).first()
            # clutch: a definição única do projeto (metrics/clutch.py, 1vX com X >= 1)
            from metrics.clutch import clutch_situations
            from metrics.player_roles import resolve_teams
            from metrics.sides import side_of_team

            ticks = pl.read_parquet(INTERIM / mid / "ticks.parquet", columns=["tick", "round_num", "steamid", "name", "side"])
            team_of, _ = resolve_teams(ticks)
            venc = {int(r["round_num"]): ("A" if r["winner"] == side_of_team("A", int(r["round_num"])) else "B")
                    for r in rounds.iter_rows(named=True)}
            cl, _ = clutch_situations(k, rounds, team_of, venc)
            nome_de = dict(ticks.group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
            ganhos = {}
            for r in cl.filter(pl.col("won")).iter_rows(named=True):
                ganhos[nome_de.get(r["steamid"])] = ganhos.get(nome_de.get(r["steamid"]), 0) + 1
            for nome in set(inim["attacker_name"].drop_nulls()) | set(k["victim_name"].drop_nulls()):
                meu = inim.filter(pl.col("attacker_name") == nome)
                s = soma.setdefault(nome, {"op_kills": 0, "op_mortes": 0, "mk_rounds": 0, "hs": 0, "clutches": 0})
                s["clutches"] += ganhos.get(nome, 0)
                s["op_kills"] += primeira.filter(pl.col("attacker_name") == nome).height
                s["op_mortes"] += primeira.filter(pl.col("victim_name") == nome).height
                s["mk_rounds"] += meu.group_by("round_num", maintain_order=True).len().filter(pl.col("len") >= 2).height
                s["hs"] += meu.filter(pl.col("headshot")).height
        for nome, o in v["jogadores"].items():
            x = soma.get(apelidos.get(nome, nome)) or soma.get(nome) or {}
            for campo in ("op_kills", "op_mortes", "mk_rounds", "hs", "clutches"):
                linhas.append({"serie": serie, "nome": nome, "campo": campo,
                               "oficial": o[campo], "nosso": x.get(campo, 0)})
    return pl.DataFrame(linhas)


def assistencia_flash() -> pl.DataFrame:
    """Degrau 4b: a assistência de flash que o pipeline GRAVA (`flash_assists` de
    `grenades_summary.parquet`, a mesma que entra em "kills em inimigo cego por
    flash" do perfil) contra a coluna A (f) da 'Detailed stats' da HLTV.

    Dois níveis, uma linha por (nível, jogador):
      - "mapa": as linhas transcritas por mapa (`brutos/hltv_detalhado_por_mapa_*.tsv`),
        casadas com a partida por mapa + elenco + rounds (nunca pelo número comparado);
      - "serie": as séries inteiras de `hltv_detalhado.json`, com os mapas somados.
    Lê só o processado (versionado): não precisa do interim. Contagem: exata, sem
    tolerância, como as do degrau 4. A definição da métrica NÃO muda aqui (cartão 1)."""
    from scripts import importa_detalhado_mapas as imp

    def gravado(mid: str) -> dict[str, int]:
        g = pl.read_parquet(PROCESSED / mid / "grenades_summary.parquet", columns=["name", "flash_assists"])
        return {n: int(v) for n, v in g.iter_rows()}

    linhas = []
    brutos = imp.le_brutos()
    if brutos.height:
        casamento, erros = imp.casa_com_o_corpus(brutos)
        if erros:
            raise SystemExit("transcrição por mapa não casa com o corpus: " + "; ".join(erros))
        for r in brutos.iter_rows(named=True):
            mid = casamento[(r["serie"], r["mapa"])]
            nosso = gravado(mid)
            linhas.append({"nivel": "mapa", "serie": r["serie"], "unidade": f"{mid} ({r['mapa']})",
                           "nome": r["jogador"], "oficial": int(r["assist_flash"]),
                           "nosso": nosso.get(_nome(r["jogador"], nosso), 0)})
    arq = REF / "hltv_detalhado.json"
    if arq.exists():
        ref = json.loads(arq.read_text(encoding="utf-8"))
        apelidos = ref.get("apelidos", {})
        for serie, v in ref["series"].items():
            if not v.get("serie_completa_no_corpus"):
                continue
            soma: dict[str, int] = {}
            for mid in v["mapas"]:
                for n, x in gravado(mid).items():
                    soma[n] = soma.get(n, 0) + x
            for nome, o in v["jogadores"].items():
                linhas.append({"nivel": "serie", "serie": serie, "unidade": "+".join(v["mapas"]),
                               "nome": nome, "oficial": int(o["assist_flash"]),
                               "nosso": soma.get(apelidos.get(nome, nome), soma.get(nome, 0))})
    if not linhas:
        return pl.DataFrame()
    return pl.DataFrame(linhas).with_columns((pl.col("nosso") - pl.col("oficial")).alias("dif"))


def assistencia_flash_no_tick_detectado(af: pl.DataFrame) -> pl.DataFrame:
    """DIAGNÓSTICO do degrau 4b, não número publicado: a MESMA definição
    (`metrics.grenades.flash_impact`, sem mudar janela nem limiar) recalculada do
    interim com o tickrate DETECTADO da demo (`metrics.timing`). O pipeline chama
    `compute_grenade_metrics` sem tickrate, e o padrão do módulo é 128; a demo é
    64, então a janela de cegueira gravada é o dobro da real (e a folga 1 s em vez
    de 0,5 s). Esta função só mede quanto disso explica a divergência; a correção
    é decisão do Pedro (cartão 1). Sem interim, devolve vazio."""
    from metrics.basic_metrics import roster_per_round
    from metrics.grenades import flash_impact
    from metrics.timing import detect_tickrate
    from parsing.parser import load_interim

    if af.height == 0 or not INTERIM.exists():
        return pl.DataFrame()
    por_partida: dict[str, dict[str, int]] = {}
    for unidade in af["unidade"].unique(maintain_order=True):
        for mid in unidade.split(" ")[0].split("+"):
            if mid in por_partida:
                continue
            if not (INTERIM / mid / "kills.parquet").exists():
                return pl.DataFrame()
            t = load_interim(INTERIM, mid)
            tr = detect_tickrate(t["rounds"], t["ticks"])["tickrate"]
            fi = flash_impact(t.get("player_blind"), t["kills"], roster_per_round(t["ticks"]), tr)
            por_partida[mid] = dict(fi.group_by("name", maintain_order=True)
                                    .agg(pl.col("flash_assists").sum()).iter_rows())
    apelidos = APELIDOS
    novos = []
    for r in af.iter_rows(named=True):
        x = 0
        for mid in r["unidade"].split(" ")[0].split("+"):
            p = por_partida[mid]
            x += p.get(r["nome"], p.get(apelidos.get(r["nome"], r["nome"]), 0))
        novos.append(x)
    return af.with_columns(pl.Series("no_tick_detectado", novos))


def _imprime_assistencia_flash(af: pl.DataFrame) -> None:
    print("\n4b. assistência de flash (coluna A (f) da 'Detailed stats', contagem exata):")
    for nivel, rotulo in (("mapa", "por mapa "), ("serie", "por série")):
        g = af.filter(pl.col("nivel") == nivel)
        if g.height == 0:
            continue
        print(f"   {rotulo} {int((g['dif'] == 0).sum())}/{g.height} exatos | nosso {int(g['nosso'].sum())}, "
              f"HLTV {int(g['oficial'].sum())} | acima {int((g['dif'] > 0).sum())}, abaixo {int((g['dif'] < 0).sum())}")
    if (af["dif"] != 0).any():
        print("   NÃO BATE: degrau informativo, a métrica não foi ajustada (decisão 22j, cartão 1).")
        print("   Divergências por mapa (nosso - HLTV):")
        with pl.Config(tbl_rows=-1, fmt_str_lengths=40):
            print(af.filter((pl.col("nivel") == "mapa") & (pl.col("dif") != 0))
                  .select("unidade", "nome", "nosso", "oficial", "dif"))
        diag = assistencia_flash_no_tick_detectado(af)
        if diag.height:
            print("   Diagnóstico (não publicado): a mesma definição com o tickrate detectado da demo,")
            print("   em vez do padrão 128 com que o pipeline grava (ver a nota 22j):")
            for nivel, rotulo in (("mapa", "por mapa "), ("serie", "por série")):
                g = diag.filter(pl.col("nivel") == nivel)
                d = g["no_tick_detectado"] - g["oficial"]
                print(f"   {rotulo} {int((d == 0).sum())}/{g.height} exatos | soma {int(g['no_tick_detectado'].sum())}, "
                      f"HLTV {int(g['oficial'].sum())} | acima {int((d > 0).sum())}, abaixo {int((d < 0).sum())}")


def swing() -> pl.DataFrame:
    """Degrau 5: o Round Swing deste projeto, em pontos percentuais, contra o oficial."""
    from metrics.rating import ModeloDeRound, carrega_referencia, rating
    from scripts.fit_rating import carrega_partida

    referencia = carrega_referencia()
    modelo = ModeloDeRound.da_referencia((referencia or {}).get("modelo_de_round"))
    linhas = []
    for mid, v in _ler("hltv_componentes.json").items():
        tabelas, team_of, vencedor, kast = carrega_partida(mid)
        _, resumo = rating(tabelas, team_of, vencedor, kast, 64, referencia=referencia, modelo=modelo)
        nick = dict(tabelas["ticks"].group_by("steamid", maintain_order=True).agg(pl.col("name").last()).iter_rows())
        nosso = {nick.get(j["steamid"]): 100 * j["sub_round_swing"] for j in resumo["jogadores"]}
        for nome, o in v["jogadores"].items():
            linhas.append({"match_id": mid, "nome": nome, "swing_oficial": o["swing_pct"],
                           "swing": nosso.get(_nome(nome, nosso))})
    return pl.DataFrame(linhas)


def rating_do_site() -> pl.DataFrame:
    """Degrau 6: o rating que a PÁGINA mostra (insights.json) contra o oficial."""
    linhas = []
    for mid, v in _ler("hltv_ratings.json").items():
        if not v.get("usar_na_calibracao"):
            continue
        ins = PROCESSED / mid / "insights.json"
        if not ins.exists():
            continue
        nosso = {p["name"]: p.get("rating") for p in json.loads(ins.read_text(encoding="utf-8"))["players"]}
        for nome, oficial in (v.get("jogadores") or {}).items():
            if oficial is not None:
                linhas.append({"match_id": mid, "nome": nome, "rating_oficial": oficial,
                               "rating": nosso.get(_nome(nome, nosso))})
    return pl.DataFrame(linhas).drop_nulls()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rapido", action="store_true", help="pula o degrau 5 (Round Swing), o mais lento")
    args = ap.parse_args()

    c = contagens()
    n = c.height
    por_partida = c.unique("match_id", maintain_order=True, keep="first")
    print(f"ESCADA DE VALIDAÇÃO -- {n} jogadores em {por_partida.height} partidas com K-D-ADR oficial\n")

    r_ok = int((por_partida["rounds"] == por_partida["rounds_oficial"]).sum())
    k_ok = c["kills"] == c["kills_oficial"]
    d_ok = c["mortes"] == c["mortes_oficial"]
    print(f"1. rounds   {r_ok}/{por_partida.height} partidas exatas")
    print(f"   kills    {int(k_ok.sum())}/{n} exatos | mortes {int(d_ok.sum())}/{n} exatos")
    ruins = c.filter(~(k_ok & d_ok))
    if ruins.height:
        print("   DEGRAU 1 NÃO ESTÁ EXATO -- os de cima são coincidência até isto ser explicado:")
        print(ruins.select("match_id", "nome", "kills_oficial", "kills", "mortes_oficial", "mortes"))

    dif = (c["adr"] - c["adr_oficial"])
    print(f"\n2. ADR      {int((dif.abs() <= TOLERANCIA_ADR).sum())}/{n} exatos no arredondamento | "
          f"maior diferença {dif.abs().max():.2f} | viés {dif.mean():+.3f}")
    fora = c.with_columns(dif.alias("dif")).filter(pl.col("dif").abs() > TOLERANCIA_ADR)
    if fora.height:
        print(fora.select("match_id", "nome", "adr_oficial", "adr", "dif").sort("dif"))

    ck = c.drop_nulls("kast_oficial")
    dk = ck["kast"] - ck["kast_oficial"]
    print(f"\n3. KAST     {int((dk == 0).sum())}/{ck.height} exatos | acima {int((dk > 0).sum())} "
          f"({int(dk.filter(dk > 0).sum()):+d} rounds) | abaixo {int((dk < 0).sum())} ({int(dk.filter(dk < 0).sum()):+d} rounds)")

    dt = detalhado()
    if dt.height:
        print(f"\n4. contagens da 'Detailed stats' (por série, {dt['serie'].n_unique()} séries):")
        for campo, g in dt.group_by("campo", maintain_order=True):
            print(f"   {campo[0]:<10} {int((g['nosso'] == g['oficial']).sum())}/{g.height} exatos")
        print("   (morte trocada: ver a nota 22j -- ainda não bate; assistência de flash: degrau 4b)")
    else:
        print("\n4. multi-kills e aberturas: sem data/reference/hltv_detalhado.json")

    af = assistencia_flash()
    if af.height:
        _imprime_assistencia_flash(af)

    if not args.rapido:
        s = swing().drop_nulls()
        x, y = s["swing"].to_numpy(), s["swing_oficial"].to_numpy()
        print(f"\n5. Swing    {s.height} jogadores | correlação {np.corrcoef(x, y)[0, 1]:.3f} | erro médio {np.mean(np.abs(x - y)):.2f} p.p. "
              f"| média {x.mean():+.2f} (oficial {y.mean():+.2f}) | inclinação {np.polyfit(y, x, 1)[0]:.2f}")

    rt = rating_do_site()
    x, y = rt["rating"].to_numpy(), rt["rating_oficial"].to_numpy()
    print(f"\n6. rating   {rt.height} jogadores | erro médio {np.mean(np.abs(x - y)):.3f} | viés {np.mean(x - y):+.3f} "
          f"| correlação {np.corrcoef(x, y)[0, 1]:.3f}   (o número da página, dentro da amostra)")


if __name__ == "__main__":
    main()
