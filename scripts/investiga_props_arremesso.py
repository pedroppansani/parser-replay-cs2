"""Item 7, investigação com propriedades da demo: de onde vem o grupo de ~784 u/s.

EXPLORATÓRIO. Não muda o parser de produção, não sobe versão, não grava nada em
data/. Lê o .dem de novo, pede ao demoparser propriedades que o parser de
produção não extrai e compara com o que `metrics.grenade_throws` deriva da
posição.

Uso:
    py -3.12 -m scripts.investiga_props_arremesso            # todas as partidas com .dem no disco
    py -3.12 -m scripts.investiga_props_arremesso match_23   # só as indicadas
    py -3.12 -m scripts.investiga_props_arremesso --corpus   # a regra só com posição, sem .dem
    py -3.12 -m scripts.investiga_props_arremesso --gabarito match_10 ...  # grava tests/fixtures/gabarito_arremessos_<partida>.json.gz

O .dem de cada partida é o `source_dem` do match_meta.json; se o caminho não
existir mais, procura o mesmo nome de arquivo dentro de demos/. Partida sem .dem
é listada e pulada. (Em 2026-09-27 só a match_23 tinha o .dem no disco.)

O que a demo grava e o parser de produção não guarda (inventário completo no
relatório do item 7):
  projétil  m_vInitialVelocity, m_vInitialPosition  -- a velocidade e o ponto de
            nascimento que o JOGO deu à granada: o gabarito, sem derivar nada;
  arma      m_flThrowStrength (0, 0,5 ou 1 = o botão), m_bJumpThrow;
  jogador   m_flDuckAmount, m_bDucked, m_flDuckRootOffset, m_flDuckViewOffset,
            m_nLastJumpTick, m_flLastJumpVelocityZ, m_hGroundEntity.
A velocidade do jogador (m_vecVelocity) NÃO é gravada; `velocity_X/Y/Z` do
demoparser é calculada por ele a partir da posição (conferido abaixo).

Testes:
  T1  vz do jogador derivada da posição x vz da física do pulo (último pulo
      gravado, gravidade 800), por duck_amount;
  T2  velocidade relativa refeita com o gabarito do projétil e com a vz do pulo;
  T3  grupos pela velocidade inicial gravada e pelo botão gravado;
  T4  herança horizontal e vertical por arremesso, com o gabarito;
  T5  ponto de nascimento gravado x olhos assumidos, por postura e duck_amount.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from demoparser2 import DemoParser

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import metrics.grenade_throws as gt  # noqa: E402
from parsing.parser import load_interim  # noqa: E402

TICKRATE = 64
GRAVIDADE = 800.0                     # sv_gravity padrão, a mesma da investigação (b)
MS = "CCSPlayerPawn.CCSPlayer_MovementServices."
PROPS_JOGADOR = {
    MS + "m_flDuckAmount": "duck_amount",
    MS + "m_bDucked": "ducked",
    MS + "m_flDuckRootOffset": "duck_root_offset",
    MS + "m_flDuckViewOffset": "duck_view_offset",
    MS + "m_nLastJumpTick": "ultimo_pulo",
    MS + "m_flLastJumpVelocityZ": "vz_do_pulo",
    "CCSPlayerPawn.m_hGroundEntity": "chao",
    "velocity_X": "vx_dp", "velocity_Y": "vy_dp", "velocity_Z": "vz_dp",
}
PROPS_GRANADA = ["Grenade.m_vInitialVelocity", "Grenade.m_vInitialPosition",
                 "Grenade.m_flThrowStrength", "Grenade.m_bJumpThrow"]
ARMA_NA_MAO = {"smoke": ("CSmokeGrenade",), "flash": ("CFlashbang",), "he": ("CHEGrenade",),
               "molotov": ("CMolotovGrenade", "CIncendiaryGrenade"), "decoy": ("CDecoyGrenade",)}
SEM_CHAO = 16777215                   # handle inválido: o jogador está no ar
CONFIRMADOS = (198.0, 443.0, 675.0)
CENTRO_EXTRA = 784.0


def acha_dem(meta: dict) -> Path | None:
    p = Path(meta["source_dem"])
    if p.is_file():
        return p
    achados = [q for q in (RAIZ / "demos").rglob(p.name) if q.is_file()]
    return achados[0] if achados else None


def arremessos_da_partida(partida: str) -> list[dict]:
    """Os arremessos como o módulo de produção os vê (tick oficial, velocidades derivadas)."""
    t = load_interim(RAIZ / "data/interim", partida)
    t["rounds"] = pl.read_parquet(RAIZ / "data/processed" / partida / "rounds.parquet")
    traj = gt.trajetorias(t.get("grenades"), t["rounds"])
    tk = gt._Ticks(t["ticks"])
    crus = gt._lancamentos_crus(traj, gt._eventos_de_arremesso(t.get("shots"), t["rounds"]))
    anc, _ = gt.ancora_arremessos(crus, tk, TICKRATE)
    anc, _ = gt.aplica_tick_oficial(anc, t.get("grenade_thrown"), TICKRATE)
    out = []
    for a in anc:
        if a.get("tick_soltura") is None or a["traj"].shape[0] < 2 or a.get("pitch") is None:
            continue
        est = gt._estado_do_jogador(tk, a["steamid"], a["tick_soltura"], TICKRATE)
        if est.get("velocidade_vetor") is None:
            continue
        dt = (a["ticks"][1] - a["ticks"][0]) / TICKRATE
        out.append({**a, "vp": (a["traj"][1] - a["traj"][0]) / dt,
                    "vj": np.asarray(est["velocidade_vetor"], dtype=float),
                    "u": gt.direcao_da_mira(np.array([a["pitch"]]), np.array([a["yaw"]]))[0]})
    return out


def props_da_demo(dem: Path, arremessos: list[dict]) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    p = DemoParser(str(dem))
    g = pl.from_pandas(p.parse_grenades(extra=PROPS_GRANADA))
    # o id de entidade é reaproveitado entre rounds: o casamento é por id E tick
    proj = (g.filter(pl.col("grenade_type").str.ends_with("Projectile")
                     & pl.col("Grenade.m_vInitialVelocity").is_not_null())
            .sort("tick"))
    arma = g.filter(~pl.col("grenade_type").str.ends_with("Projectile")).select(
        "grenade_type", "tick", "steamid", "Grenade.m_flThrowStrength", "Grenade.m_bJumpThrow")
    ticks = sorted({int(a["tick_soltura"]) + d for a in arremessos for d in range(-2, 3)})
    # nem toda build grava todo campo (m_flDuckRootOffset falta em demos mais
    # antigas): o demoparser devolve a tabela SEM a coluna; o que faltar vem
    # nulo, declarado
    jog = pl.from_pandas(p.parse_ticks(list(PROPS_JOGADOR) + ["X", "Y", "Z"], ticks=ticks))
    for k, v in PROPS_JOGADOR.items():
        if k in jog.columns:
            jog = jog.rename({k: v})
        else:
            print(f"   {dem.name}: sem o campo {k}")
            jog = jog.with_columns(pl.lit(None).alias(v))
    # m_nLastJumpTick não está na base de tick da demo: medido, ele muda no
    # próprio tick da decolagem com valor 2·tick + c (meio-tick), c fixo por
    # demo. c sai das mudanças do campo, não de chute.
    pulos = (pl.from_pandas(p.parse_ticks([MS + "m_nLastJumpTick"]))
             .rename({MS + "m_nLastJumpTick": "lj"}).sort("steamid", "tick")
             .with_columns(pl.col("lj").cast(pl.Int64).diff().over("steamid").alias("d"))
             .filter(pl.col("d").is_not_null() & (pl.col("d") != 0)))
    c = (pulos["lj"].cast(pl.Int64) - 2 * pulos["tick"].cast(pl.Int64))
    base = int(c.mode()[0])
    print(f"   m_nLastJumpTick = 2·tick + {base} em {(c == base).mean():.1%} das {pulos.height} decolagens")
    jog = jog.with_columns(((pl.col("ultimo_pulo").cast(pl.Int64) - base) / 2).alias("ultimo_pulo"))
    return proj, arma, jog


def mediana(x, casas: int = 1) -> str:
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], dtype=float)
    if not x.size:
        return "-"
    return (f"{np.median(x):7.{casas}f} [{np.percentile(x, 25):6.{casas}f}, "
            f"{np.percentile(x, 75):6.{casas}f}] n={x.size}")


def main(partidas: list[str]) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    linhas = []
    for partida in partidas:
        meta = json.loads((RAIZ / "data/processed" / partida / "match_meta.json").read_text(encoding="utf-8"))
        dem = acha_dem(meta)
        if dem is None:
            print(f"{partida}: sem .dem no disco, pulada")
            continue
        arr = arremessos_da_partida(partida)
        proj, arma, jog = props_da_demo(dem, arr)
        pj: dict[int, list[dict]] = {}
        for r in proj.iter_rows(named=True):
            pj.setdefault(int(r["grenade_entity_id"]), []).append(r)
        jt = {(int(r["steamid"]), int(r["tick"])): r for r in jog.iter_rows(named=True)}
        casados = 0
        for a in arr:
            r = next((q for q in pj.get(int(a["entity_id"]), [])
                      if 0 <= q["tick"] - int(a["tick_soltura"]) <= 4), None)
            j = jt.get((int(a["steamid"]), int(a["tick_soltura"])))
            if r is None or j is None:
                continue
            casados += 1
            # a arma na mão no último tick ANTES da soltura: no próprio tick a
            # entidade já pode ser a PRÓXIMA granada do mesmo tipo, com força 0
            # (achado na validação: 4 botões "errados" eram leitura errada)
            m = arma.filter(pl.col("steamid") == a["steamid"]).filter(
                pl.col("grenade_type").is_in(list(ARMA_NA_MAO.get(a["kind"], ())))
                & pl.col("tick").is_between(int(a["tick_soltura"]) - 4, int(a["tick_soltura"]) - 1)).sort("tick")
            forca = m["Grenade.m_flThrowStrength"][-1] if m.height else None
            pulo = m["Grenade.m_bJumpThrow"][-1] if m.height else None
            ts = int(a["tick_soltura"])
            vz_pulo = None
            if j["ultimo_pulo"] is not None and 0 <= ts - j["ultimo_pulo"] <= 128:
                vz_pulo = j["vz_do_pulo"] - GRAVIDADE * (ts - j["ultimo_pulo"]) / TICKRATE
            jm, jp = jt.get((int(a["steamid"]), ts - 1)), jt.get((int(a["steamid"]), ts + 1))
            linhas.append({
                "partida": partida, "round": a["round_num"], "jogador": a["thrower"], "arma": a["kind"],
                "tick": ts, "pitch": a["pitch"], "yaw": a["yaw"],
                "vp": a["vp"], "vj": a["vj"], "u": a["u"],
                "v0": np.asarray(r["Grenade.m_vInitialVelocity"], dtype=float),
                "p0": np.asarray(r["Grenade.m_vInitialPosition"], dtype=float),
                "pes": np.asarray(a["pos_soltura"], dtype=float),
                "altura_derivada": a.get("altura_olhos"),
                "forca_gravada": forca, "jump_throw": pulo,
                "no_ar": abs(a["vj"][2]) >= gt.VELOCIDADE_VERTICAL_NO_AR,
                "no_chao_gravado": j["chao"] != SEM_CHAO,
                "duck": j["duck_amount"], "ducked": j["ducked"], "root": j["duck_root_offset"],
                "view_off": j["duck_view_offset"], "ticks_do_pulo": (ts - j["ultimo_pulo"]) if j["ultimo_pulo"] else None,
                "vz_pulo": vz_pulo, "vz_dp": j["vz_dp"],
                "root_mudou": (None if jm is None or jp is None else float(jp["duck_root_offset"] - jm["duck_root_offset"])),
            })
        print(f"{partida} ({meta['map_name']}): {len(arr)} arremessos, {casados} casados com a demo")
    if not linhas:
        print("nenhuma partida com .dem: nada a medir")
        return
    relatorio(linhas)


def direcao_do_lancamento(pitch: float, yaw: float) -> np.ndarray:
    """Direção em que o jogo LANÇA a granada: o pitch é remapeado para
    -10 + pitch·80/90 (medido no chão contra o gabarito: resíduo mediano 0,000°)."""
    p = np.radians(-10 + pitch * 80 / 90)
    y = np.radians(yaw)
    return np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), -np.sin(p)])


def botao(forca) -> float | None:
    """m_flThrowStrength vem 0, 0,5 ou 1, com ruído em torno de 0,5 (0,46-0,59)."""
    return None if forca is None else round(float(forca) * 2) / 2


def vz_de_decolagem(x: dict) -> float | None:
    """A vz gravada no instante do pulo (m_flLastJumpVelocityZ)."""
    if x["vz_pulo"] is None:
        return None
    return x["vz_pulo"] + GRAVIDADE * x["ticks_do_pulo"] / TICKRATE


def relatorio(L: list[dict]) -> None:
    for x in L:
        x["rel"] = float(np.linalg.norm(x["vp"] - gt.FATOR_HERANCA * x["vj"]))
        x["rel_v0"] = float(np.linalg.norm(x["v0"] - gt.FATOR_HERANCA * x["vj"]))
        x["grupo"] = min(CONFIRMADOS + (CENTRO_EXTRA,), key=lambda c: abs(c - x["rel"]))
        x["b"] = botao(x["forca_gravada"])
    ar = [x for x in L if x["no_ar"]]
    print(f"\narremessos casados: {len(L)}; no ar (|vz| >= {gt.VELOCIDADE_VERTICAL_NO_AR:g}): {len(ar)}; "
          f"no grupo de 784 (centro mais próximo): {sum(x['grupo'] == CENTRO_EXTRA for x in L)}")

    print("\n== 0. conferências")
    d = [x["vz_dp"] - x["vj"][2] for x in L if x["vz_dp"] is not None]
    print("   velocity_Z do demoparser - vz derivada pelo módulo:", mediana(d), "(é derivada da posição)")
    print("   no ar pela posição:", len(ar), "| destes, sem chão na demo:", sum(not x["no_chao_gravado"] for x in ar),
          "| no chão pela demo (escada/rampa):", sum(x["no_chao_gravado"] for x in ar))
    print("   |vp derivada - v0 gravada| (u/s):", mediana([float(np.linalg.norm(x["vp"] - x["v0"])) for x in L]))

    print("\n== velocidade do lançamento por botão gravado, no chão: |v0 - 1,25·vj|")
    S: dict = {}
    for x in L:
        if not x["no_ar"] and x["b"] is not None:
            S.setdefault(x["b"], []).append(x["rel_v0"])
    for b in sorted(S):
        print(f"   botão {b}: {mediana(S[b])}")
    S = {b: float(np.median(v)) for b, v in S.items()}

    print("\n== direção do lançamento (chão, botão 1): pitch do lançamento - pitch da mira")
    chao1 = [x for x in L if not x["no_ar"] and x["b"] == 1.0]
    pw = np.array([-np.degrees(np.arcsin(w[2] / np.linalg.norm(w)))
                   for w in (x["v0"] - gt.FATOR_HERANCA * x["vj"] for x in chao1)])
    pa = np.array([x["pitch"] for x in chao1])
    print("   resíduo contra -10 + pitch·80/90:", mediana(pw - (-10 + pa * 80 / 90)),
          "| contra o pitch da mira:", mediana(pw - pa))

    # a velocidade do jogador que o JOGO usou, tirada do gabarito
    for x in L:
        x["vji"] = (None if x["b"] not in S else
                    (x["v0"] - S[x["b"]] * direcao_do_lancamento(x["pitch"], x["yaw"])) / gt.FATOR_HERANCA)

    faixas = (("duck = 0", lambda v: v == 0), ("0 < duck < 1", lambda v: 0 < v < 1), ("duck = 1", lambda v: v >= 1))
    print("\n== T1. vz do jogador no ar: derivada da posição x física do pulo x a que o JOGO usou (do gabarito)")
    for nome, f in faixas:
        s = [x for x in ar if x["vz_pulo"] is not None and f(x["duck"])]
        print(f"   {nome:14s} derivada - pulo {mediana([x['vj'][2] - x['vz_pulo'] for x in s])}"
              f" | usada pelo jogo {mediana([x['vji'][2] for x in s if x['vji'] is not None])}")
    for nome, s in (("grupo 784", [x for x in ar if x["grupo"] == CENTRO_EXTRA]),
                    ("resto no ar", [x for x in ar if x["grupo"] != CENTRO_EXTRA])):
        s = [x for x in s if x["vz_pulo"] is not None]
        print(f"   {nome:14s} derivada - pulo {mediana([x['vj'][2] - x['vz_pulo'] for x in s])}"
              f" | usada pelo jogo {mediana([x['vji'][2] for x in s if x['vji'] is not None])}"
              f" | ticks do pulo {mediana([x['ticks_do_pulo'] for x in s])}")
    print("   por tick desde o pulo: tick | n | vz derivada | vz do pulo | vz usada pelo jogo")
    for t in range(0, 40):
        s = [x for x in ar if x["ticks_do_pulo"] == t and x["vji"] is not None]
        if s:
            print(f"     {t:3d} {len(s):3d} {np.median([x['vj'][2] for x in s]):8.1f} "
                  f"{np.median([x['vz_pulo'] for x in s]):8.1f} {np.median([x['vji'][2] for x in s]):8.1f}")
    s = [x for x in ar if x["vji"] is not None and not x["no_chao_gravado"] and x["vz_pulo"] is not None]
    print("   vz usada - (vz de decolagem gravada - 80):",
          mediana([x["vji"][2] - (vz_de_decolagem(x) - GRAVIDADE * 0.1) for x in s]))
    s = [x for x in ar if x["vji"] is not None and x["no_chao_gravado"]]
    print("   no ar pela posição mas no chão pela demo: vz usada", mediana([x["vji"][2] for x in s]))

    print("\n== T2. % no ar perto dos três grupos")

    def perto(vs):
        vs = [v for v in vs if v is not None]
        return f"{np.mean([min(abs(v - c) for c in CONFIRMADOS) <= gt.RAIO_GRUPO_FORCA for v in vs]):.1%} (n={len(vs)})"

    def pela_regra(x, v):
        if x["no_chao_gravado"]:
            vz = 0.0
        elif x["vz_pulo"] is not None:
            vz = vz_de_decolagem(x) - GRAVIDADE * 0.1
        else:
            vz = x["vj"][2]
        return float(np.linalg.norm(v - gt.FATOR_HERANCA * np.array([x["vj"][0], x["vj"][1], vz])))
    print("   produção (projétil e jogador derivados):   ", perto([x["rel"] for x in ar]))
    print("   projétil GRAVADO, jogador derivado:        ", perto([x["rel_v0"] for x in ar]))
    print("   projétil derivado, vz pela regra do jogo:  ", perto([pela_regra(x, x["vp"]) for x in ar]))
    print("   projétil GRAVADO, vz pela regra do jogo:   ", perto([pela_regra(x, x["v0"]) for x in ar]))

    print("\n== T3. botão gravado x grupo pela velocidade (produção)")
    tab: dict = {}
    for x in L:
        tab.setdefault((x["b"], "no ar" if x["no_ar"] else "chão"), []).append(x)
    for (b, onde), s in sorted(tab.items(), key=lambda k: (k[0][0] is None, k[0][0] or 0, k[0][1])):
        grupos: dict = {}
        for x in s:
            grupos[int(x["grupo"])] = grupos.get(int(x["grupo"]), 0) + 1
        print(f"   botão {b!s:4s} {onde:6s} n={len(s):4d} | |v0 - 1,25·vj| {mediana([x['rel_v0'] for x in s])}"
              f" | grupo pela produção {dict(sorted(grupos.items()))}")

    print("\n== T4. herança: v0 = S·u_lançamento + kh·vj_h + kv·vz (u com o pitch remapeado)")
    casos = (("chão, jogador a mais de 100 u/s", [x for x in L if not x["no_ar"] and np.hypot(*x["vj"][:2]) > 100], "vj"),
             ("no ar, vz derivada", [x for x in ar if not x["no_chao_gravado"]], "vj"),
             ("no ar, vz da regra (decolagem - 80)",
              [x for x in ar if not x["no_chao_gravado"] and x["vz_pulo"] is not None], "regra"))
    for nome, s, qual in casos:
        sol = []
        for x in s:
            vzj = x["vj"][2] if qual == "vj" else vz_de_decolagem(x) - GRAVIDADE * 0.1
            M = np.column_stack([direcao_do_lancamento(x["pitch"], x["yaw"]),
                                 [x["vj"][0], x["vj"][1], 0.0], [0.0, 0.0, vzj]])
            if abs(np.linalg.det(M)) > 1e-3:
                sol.append(np.linalg.solve(M, x["v0"]))
        sol = np.array(sol) if sol else np.zeros((0, 3))
        print(f"   {nome:36s} S {mediana(sol[:, 0])} | kh {mediana(sol[:, 1], 3)} | kv {mediana(sol[:, 2], 3)}")

    print("\n== T5. ponto de nascimento GRAVADO: altura sobre os pés, tirado o avanço na direção do lançamento")
    for x in L:
        e = x["p0"] - x["pes"]
        y = np.radians(x["yaw"])
        dh = float(e[0] * np.cos(y) + e[1] * np.sin(y))
        x["altura_nascimento"] = float(e[2] + dh * np.tan(np.radians(-10 + x["pitch"] * 80 / 90)))
    for onde, f in (("chão", lambda x: not x["no_ar"]), ("ar", lambda x: x["no_ar"] and not x["no_chao_gravado"])):
        for dn, fd in faixas:
            for b in (1.0, 0.5, 0.0):
                s = [x for x in L if f(x) and fd(x["duck"]) and x["b"] == b]
                if s:
                    print(f"   {onde:4s} {dn:12s} botão {b}: nascimento {mediana([x['altura_nascimento'] for x in s])}"
                          f" | altura do módulo {mediana([x['altura_derivada'] for x in s])}"
                          f" | duck_view_offset {mediana([x['view_off'] for x in s])}")
    print("   no ar depois de pulo (botão 1, duck 0), altura do nascimento sobre o chão da DECOLAGEM:")
    for t in range(0, 40):
        s = [x for x in ar if x["ticks_do_pulo"] == t and x["vz_pulo"] is not None and x["b"] == 1.0 and x["duck"] == 0]
        if s:
            tau = t / TICKRATE
            sobre = [x["altura_nascimento"] + vz_de_decolagem(x) * tau - GRAVIDADE / 2 * tau ** 2 for x in s]
            print(f"     tick {t:3d} n={len(s):3d} sobre a decolagem {np.median(sobre):6.2f}"
                  f" | sobre os pés {np.median([x['altura_nascimento'] for x in s]):6.2f}")
    fa = [x for x in L if x["altura_derivada"] is not None
          and x["altura_derivada"] <= gt.ALTURA_OLHOS_AGACHADO_MAX and x["duck"] == 0]
    causas: dict = {}
    for x in fa:
        k = ("ar" if x["no_ar"] else "chão", x["b"])
        causas[k] = causas.get(k, 0) + 1
    print(f"   falsos agachados do módulo (altura <= {gt.ALTURA_OLHOS_AGACHADO_MAX:g}, duck 0): {len(fa)};"
          f" por (onde, botão): {causas}")

    print("\n== o grupo 784, arremesso a arremesso")
    for x in L:
        if x["grupo"] == CENTRO_EXTRA:
            usada = "-" if x["vji"] is None else f"{x['vji'][2]:.0f}"
            print(f"   r{x['round']:>2} {x['jogador']:10s} {x['arma']:7s} botão {x['b']} jump_throw {x['jump_throw']}"
                  f" duck {x['duck']:.2f} ticks do pulo {x['ticks_do_pulo']} | rel {x['rel']:.0f}"
                  f" | vz derivada {x['vj'][2]:.0f} usada pelo jogo {usada}")


def regra_no_corpus() -> None:
    """A regra vertical aplicada SÓ COM POSIÇÃO, no corpus inteiro (sem .dem).

    No ar (parábola de queda livre na soltura: segunda diferença da altura igual
    à gravidade por >= 2 ticks), a vz herdada é a de decolagem menos 0,1 s de
    gravidade; fora disso, 0. A vz de decolagem é a moda de m_flLastJumpVelocityZ
    medida na match_23 (298,868; 8% dos pulos saem com 301,993).
    """
    vz_jogo = 298.868 - GRAVIDADE * 0.1
    g_tick = -GRAVIDADE / TICKRATE ** 2
    todos = []
    for d in sorted((RAIZ / "data/interim").glob("match_*")):
        t = load_interim(RAIZ / "data/interim", d.name)
        tk = gt._Ticks(t["ticks"])
        for a in arremessos_da_partida(d.name):
            dj = tk.por_jogador[int(a["steamid"])]
            idx = tk.indices(a["steamid"], np.arange(a["tick_soltura"] - 80, a["tick_soltura"] + 2, dtype=np.int64))
            n = 0
            if idx is not None:
                z = dj["pos"][idx, 2]
                d2 = z[2:] - 2 * z[1:-1] + z[:-2]
                i = len(d2) - 2
                while i >= 0 and abs(d2[i] - g_tick) < 0.05:
                    n += 1
                    i -= 1
            vz = vz_jogo if n >= 2 else 0.0
            todos.append({"ar": abs(a["vj"][2]) >= gt.VELOCIDADE_VERTICAL_NO_AR,
                          "rel": float(np.linalg.norm(a["vp"] - gt.FATOR_HERANCA * a["vj"])),
                          "regra": float(np.linalg.norm(
                              a["vp"] - gt.FATOR_HERANCA * np.array([a["vj"][0], a["vj"][1], vz])))})
        print(f"   {d.name}: {len(todos)}", flush=True)
    conf = np.array(CONFIRMADOS)

    def perto(v):
        v = np.asarray(v)
        return f"{np.mean(np.min(np.abs(v[:, None] - conf[None]), axis=1) <= gt.RAIO_GRUPO_FORCA):.1%}"
    ar = [x for x in todos if x["ar"]]
    print(f"\ncorpus: {len(todos)} arremessos, {len(ar)} no ar")
    print(f"no ar perto dos 3 grupos: produção {perto([x['rel'] for x in ar])} -> regra {perto([x['regra'] for x in ar])}")
    print(f"todos:                    produção {perto([x['rel'] for x in todos])} -> regra {perto([x['regra'] for x in todos])}")
    print("grupos no ar, produção:", [(round(c), n) for c, n in gt.grupos_de_forca(np.array([x["rel"] for x in ar]))])
    print("grupos no ar, regra:   ", [(round(c), n) for c, n in gt.grupos_de_forca(np.array([x["regra"] for x in ar]))])


# Janela de posição dos pés guardada no gabarito: a produção acha a decolagem
# pela parábola dos ticks anteriores à soltura (a mesma JANELA_DECOLAGEM_TICKS).
JANELA_Z_GABARITO = 64
PASTA_GABARITO = RAIZ / "tests/fixtures"


# as partes da demo e o deslocamento de cada uma: as mesmas do complemento da
# rota B (código de produção, conferido por X, Y, Z contra o interim)
from scripts.complementa_interim import demos_da_partida, deslocamento_da_parte  # noqa: E402,F401


def gera_gabarito(partida: str = "match_23") -> Path:
    """Grava o gabarito de uma partida em tests/fixtures (compactado).

    Por arremesso: o que a demo diz (botão, jump-throw, chão, postura,
    velocidade e posição iniciais do projétil) e as ENTRADAS que a produção
    usa (tick da soltura, pés, mira, dois primeiros pontos do projétil e os
    pés nos ticks anteriores). Os testes rodam só com ele, sem .dem e sem
    interim. Demo em várias partes: cada parte é casada com o interim pelo
    deslocamento de tick que a fusão aplicou.
    """
    import gzip
    import hashlib
    dems = demos_da_partida(partida)
    arr = arremessos_da_partida(partida)
    t = load_interim(RAIZ / "data/interim", partida)
    tk = gt._Ticks(t["ticks"])
    ticks_ev = np.array(sorted(t["grenade_thrown"]["tick"].to_list())) if t.get("grenade_thrown") is not None else np.array([])
    partes = []
    for dem in dems:
        p = DemoParser(str(dem))
        partes.append((dem, p, deslocamento_da_parte(p, ticks_ev) if len(dems) > 1 else 0))
    partes.sort(key=lambda x: x[2])
    saida = []
    for k, (dem, p, desloc) in enumerate(partes):
        fim = partes[k + 1][2] if k + 1 < len(partes) else None
        meus = [a for a in arr if a["tick_soltura"] >= desloc and (fim is None or a["tick_soltura"] < fim)]
        # os ticks da demo desta parte = os do interim menos o deslocamento
        na_demo = [{**a, "tick_soltura": int(a["tick_soltura"]) - desloc} for a in meus]
        proj, arma, jog = props_da_demo(dem, na_demo)
        pj: dict[int, list[dict]] = {}
        for r in proj.iter_rows(named=True):
            pj.setdefault(int(r["grenade_entity_id"]), []).append(r)
        jt = {(int(r["steamid"]), int(r["tick"])): r for r in jog.iter_rows(named=True)}
        for a, ad in zip(meus, na_demo):
            ts, td = int(a["tick_soltura"]), int(ad["tick_soltura"])
            r = next((q for q in pj.get(int(a["entity_id"]), []) if 0 <= q["tick"] - td <= 4), None)
            j = jt.get((int(a["steamid"]), td))
            idx = tk.indices(a["steamid"], np.arange(ts - JANELA_Z_GABARITO, ts + 2, dtype=np.int64))
            if r is None or j is None or idx is None:
                continue
            pos = tk.por_jogador[int(a["steamid"])]["pos"][idx]
            # força lida no tick ANTES da soltura: no próprio tick a entidade já
            # pode ser a PRÓXIMA granada do mesmo tipo, com força 0
            m = arma.filter(pl.col("steamid") == a["steamid"]).filter(
                pl.col("grenade_type").is_in(list(ARMA_NA_MAO.get(a["kind"], ())))
                & pl.col("tick").is_between(td - 4, td - 1)).sort("tick")
            if not m.height:
                continue
            saida.append({
                "id": f"{partida}:{a['round_num']}:{a['entity_id']}",
                "arma": a["kind"],
                "demo": {
                    "forca": round(float(m["Grenade.m_flThrowStrength"][-1]), 4),
                    "jump_throw": bool(m["Grenade.m_bJumpThrow"][-1]),
                    "no_chao": j["chao"] != SEM_CHAO,
                    "duck_amount": round(float(j["duck_amount"]), 4),
                    "ducked": bool(j["ducked"]),
                    "duck_view_offset": None if j["duck_view_offset"] is None else round(float(j["duck_view_offset"]), 4),
                    "tick_do_pulo": None if j["ultimo_pulo"] is None else float(j["ultimo_pulo"]) + desloc,
                    "vz_decolagem": round(float(j["vz_do_pulo"]), 4),
                    "v0": [round(float(v), 3) for v in r["Grenade.m_vInitialVelocity"]],
                    "p0": [round(float(v), 3) for v in r["Grenade.m_vInitialPosition"]],
                },
                "entrada": {
                    "tick_soltura": ts,
                    "pitch": round(float(a["pitch"]), 4),
                    "yaw": round(float(a["yaw"]), 4),
                    "pes": [round(float(v), 3) for v in a["pos_soltura"]],
                    "pos_vizinhos": [[round(float(v), 3) for v in pos[-3]], [round(float(v), 3) for v in pos[-1]]],
                    "z_janela": [round(float(v), 3) for v in pos[:, 2]],
                    "xy_janela": [[round(float(v), 3) for v in par] for par in pos[:, :2]],
                    "proj_ticks": [int(a["ticks"][0]), int(a["ticks"][1])],
                    "proj_pontos": [[round(float(v), 3) for v in a["traj"][0]], [round(float(v), 3) for v in a["traj"][1]]],
                },
            })
    shas = []
    for dem, _, _ in partes:
        h = hashlib.sha256()
        with open(dem, "rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                h.update(bloco)
        shas.append(h.hexdigest())
    doc = {
        "_leia_isto": ("Gabarito de arremessos: 'demo' = propriedades gravadas pelo jogo; 'entrada' = o "
                       "que a produção usa. z_janela e xy_janela vão de tick_soltura-64 a tick_soltura+1 "
                       "(tabela de ticks); pos_vizinhos = pés em tick_soltura-1 e +1. Ticks na base do "
                       "interim (partes de demo dividida já deslocadas). Gerado por "
                       "py -3.12 -m scripts.investiga_props_arremesso --gabarito <partida>"),
        "partida": partida, "tickrate": TICKRATE, "sha256_do_dem": shas, "arremessos": saida,
    }
    arq = PASTA_GABARITO / f"gabarito_arremessos_{partida}.json.gz"
    with gzip.open(arq, "wt", encoding="utf-8", compresslevel=9) as f:
        f.write(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"{arq.name}: {len(saida)} arremessos de {len(arr)}, {len(partes)} parte(s), "
          f"deslocamentos {[x[2] for x in partes]}, {arq.stat().st_size / 1e3:.0f} kB")
    return arq


if __name__ == "__main__":
    if sys.argv[1:2] == ["--gabarito"]:
        sys.stdout.reconfigure(encoding="utf-8")
        for partida in (sys.argv[2:] or ["match_23"]):
            gera_gabarito(partida)
    elif sys.argv[1:] == ["--corpus"]:
        sys.stdout.reconfigure(encoding="utf-8")
        regra_no_corpus()
    else:
        main(sys.argv[1:] or sorted(p.name for p in (RAIZ / "data/interim").glob("match_*")))
