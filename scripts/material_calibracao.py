"""
Gera MATERIAL_DE_CALIBRACAO.md: tudo que depende de julgamento do Pedro, junto,
no formato "olhar e confirmar".

    py -3.12 -m scripts.material_calibracao

Quatro seções:
  1. PISOS de função: distribuição, cortes candidatos e os NOMES de cada lado;
  2. GRUPOS de estilo: perfil, quem concentra, 5 rounds representativos e
     sugestões de nome (a escolha continua do Pedro, em cluster_names.json);
  3. FORÇA das granadas: distribuição com os rótulos aplicados e um exemplo de cada;
  4. CONSOLE: um comando pronto de um arremesso específico, para testar no jogo.

O arquivo é saída GERADA (decisão 24), mas é pequeno e vive no repositório de
propósito: é o documento que o Pedro responde, e o histórico dele é o registro
de quando cada limiar foi decidido.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from clustering.playstyle import describe_clusters  # noqa: E402
from metrics.identidade import com_nome_de_exibicao  # noqa: E402
from metrics.grenade_throws import grenade_throws, grupos_de_forca, rotula_forca, trajetorias  # noqa: E402
from metrics.player_roles import TRAIT_SPECS  # noqa: E402
from parsing.parser import load_interim  # noqa: E402
from scripts.calibration_report import carrega, cortes_com_nomes  # noqa: E402

PROCESSED = PROJECT_ROOT / "data" / "processed"
INTERIM = PROJECT_ROOT / "data" / "interim"
SAIDA = PROJECT_ROOT / "MATERIAL_DE_CALIBRACAO.md"

# Partidas usadas na amostra de força de arremesso (o módulo é caro: ~1 min por
# partida). Seis bastam: 2.268 arremessos, e os três grupos já aparecem.
PARTIDAS_FORCA = ("match_01", "match_05", "match_38", "match_43", "match_47", "match_52")
# O arremesso do roteiro de console. Escolhido por ser smoke de CT clássica, em
# pé, parado e com a menor ancoragem residual da partida.
CONSOLE = ("match_38", 2, "jL")

# Sugestões de nome para cada grupo. São SUGESTÕES, não rótulos: a nomeação é do
# Pedro (decisão 8) e mora em clustering/cluster_names.json.
SUGESTOES = {
    "longe do time": ("Segura sozinho", "Âncora isolado", "Posição fixa"),
    "joga por baixo": ("Mira fora da altura", "Crosshair baixo", "—"),
    "passa por muitas regiões": ("Joga o round inteiro", "Rodando com o time", "Default paciente"),
    "encosta no adversário cedo": ("Pressão cedo", "Entrada em bloco", "Executa junto"),
}
FEATURES = ["avg_distance_from_team", "max_distance_from_team", "distinct_places",
            "time_of_first_contact_s", "frac_entering_fight", "crosshair_score", "height_score"]


def secao_pisos() -> list[str]:
    """Seção 1: distribuição, método declarado e casos de fronteira de cada piso
    (scripts/proposta_pisos.py). Pedido do Pedro: decidir o corte olhando o
    raciocínio, não só a lista final."""
    from scripts import proposta_pisos as pp

    df = pp.carrega()
    out = ["## 1. Pisos de função", "",
           "Gerado por `py -3.12 -m scripts.proposta_pisos`. O rótulo exige **liderar o próprio time** na "
           "métrica E passar do piso; o piso barra o líder que não é destacado. Para cada função: a distribuição "
           "completa (todos os jogador-partidas e só os líderes), três métodos objetivos -- **maior vazio** entre "
           "valores consecutivos, **Otsu** (menor variância dentro das duas classes) e **vale da densidade** (KDE) "
           "--, o veredito de concordância e os líderes mais próximos de cada corte. Métodos que concordam = corte "
           "real; métodos que discordam = a métrica é um contínuo e o piso é convenção. Os pisos continuam "
           "ABSOLUTOS. O que é seu: olhar a fronteira e dizer se aquele jogador jogou a função naquela partida.", ""]
    for t in pp.TRAIT_SPECS:
        out.append(pp.relata(pp.analisa(df, t)))
    return out


def secao_grupos() -> list[str]:
    """Seção 2: perfil de cada grupo, estabilidade ao reajuste e nomes candidatos
    presos ao perfil (scripts/proposta_grupos.py)."""
    from scripts.proposta_grupos import proposta_md

    return proposta_md() + [""]


def secao_forca() -> list[str]:
    partes = []
    for mid in PARTIDAS_FORCA:
        if not (INTERIM / mid / "ticks.parquet").exists():
            continue
        t = load_interim(INTERIM, mid)
        pr, _ = grenade_throws(t, 64)
        if pr.height:
            fr = pl.read_parquet(PROCESSED / mid / "rounds.parquet").select("round_num", "freeze_end")
            partes.append(pr.join(fr.with_columns(pl.col("round_num").cast(pr.schema["round_num"])),
                                  on="round_num", how="left").with_columns(pl.lit(mid).alias("match_id")))
    d = pl.concat(partes, how="diagonal_relaxed").drop_nulls("velocidade_arremesso")
    v = d["velocidade_arremesso"].to_numpy()
    g = grupos_de_forca(v)
    d = d.with_columns(pl.col("velocidade_arremesso").map_elements(
        lambda x: rotula_forca(x, g), return_dtype=pl.Utf8).alias("forca"))
    out = ["## 3. Rótulos de força do arremesso", "",
           f"{d.height} arremessos em {d['match_id'].n_unique()} partidas. Os grupos saem por moda "
           "(decisão 5); os rótulos foram aplicados PELA ORDEM (mais lento = curto) e estão marcados "
           "\"(a confirmar)\" no código até você responder.", "",
           "| Grupo | Centro | Arremessos | Exemplo |", "|---|---|---|---|"]
    for (rot,), grp in d.group_by("forca", maintain_order=True):
        e = grp.filter(pl.col("reproducao_exata") & (pl.col("movimento") == "parado"))
        e = (e if e.height else grp).sort("velocidade_arremesso").row(min(1, max(0, (e.height or 1) - 1)), named=True)
        seg = (e["tick_soltura"] - e["freeze_end"]) / 64
        out.append(f"| {rot} | {grp['velocidade_arremesso'].mean():.0f} u/s | {grp.height} | "
                   f"{e['thrower']}, {e['kind']}, {e['match_id']} round {e['round_num']} "
                   f"({int(seg // 60)}:{int(seg % 60):02d}), {e['postura']}, {e['movimento']} |")
    bordas = np.arange(0, 900, 50)
    cont, _ = np.histogram(v, bins=bordas)
    out += ["", "```"]
    for i, n in enumerate(cont):
        out.append(f"{bordas[i]:>4}-{bordas[i + 1]:<4} u/s | {'#' * int(50 * n / max(cont.max(), 1)):<50} {n:>4}"
                   f"  {rotula_forca(float(bordas[i] + 25), g)}")
    out += ["```", "", "**Sua resposta:** curto/médio/longo pela ordem está certo? ____", ""]
    return out


def secao_console() -> list[str]:
    mid, rn, jogador = CONSOLE
    t = load_interim(INTERIM, mid)
    pr, _ = grenade_throws(t, 64)
    c = pr.filter((pl.col("round_num") == rn) & (pl.col("thrower") == jogador) & (pl.col("kind") == "smoke"))
    if c.height == 0:
        return ["## 4. Teste do comando de console", "", "arremesso de referência não encontrado", ""]
    r = c.sort("residuo").row(0, named=True)
    traj = trajetorias(t["grenades"], t["rounds"]).filter(
        (pl.col("entity_id") == r["entity_id"]) & (pl.col("round_num") == rn)).sort("tick")
    fim = traj.row(-1, named=True)
    fr = dict(t["rounds"].select("round_num", "freeze_end").iter_rows())
    seg = (r["tick_soltura"] - fr[rn]) / 64
    mapa = json.loads((PROCESSED / mid / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    return ["## 4. Teste do comando de console", "",
            f"Arremesso: **{jogador}**, smoke, **{mid}** ({mapa}) round {rn}, "
            f"{int(seg // 60)}:{int(seg % 60):02d} do round (tick {r['tick_soltura']}). "
            f"Ancoragem com resíduo de {r['residuo']:.2f}u, em pé, parado.", "",
            "1. Servidor local no mapa, com:", "",
            "```",
            "sv_cheats 1; mp_warmup_end; mp_freezetime 0; sv_infinite_ammo 1; sv_grenade_trajectory_prac_pipreview 1",
            "```", "",
            "2. Com a smoke na mão, sem se mover:", "",
            "```",
            f"setpos {r['x']:.2f} {r['y']:.2f} {r['z']:.2f}; setang {r['pitch']:.2f} {r['yaw']:.2f} 0",
            "```", "",
            "3. Solte com o **botão esquerdo** (arremesso cheio), em pé, parado.", "",
            f"**Certo:** a smoke para em ({fim['X']:.0f}, {fim['Y']:.0f}, {fim['Z']:.0f}). "
            "O preview da trajetória mostra o ponto antes de você soltar.", "",
            "**Se errar, me mande:** a saída do `getpos` logo depois do `setpos`; onde a smoke caiu "
            "(nome do lugar); e se o erro foi de DISTÂNCIA (curta ou longa demais -> altura ou pitch) "
            "ou de LADO (esquerda ou direita -> yaw).", "",
            "**Sua resposta:** funcionou? ____", ""]


# Direção no radar a partir do yaw do CS2: 0° aponta para +X (direita do
# radar), 90° para +Y (cima), e o ângulo cresce no sentido anti-horário.
_DIRECOES = ["direita", "direita-cima", "cima", "esquerda-cima",
             "esquerda", "esquerda-baixo", "baixo", "direita-baixo"]


def _direcao(yaw: float) -> str:
    return _DIRECOES[int(((yaw % 360) + 22.5) // 45) % 8]


def angulos_distintos(mapa: str) -> tuple[pl.DataFrame, int, int]:
    """Ângulos de entrada de um mapa, juntando o mesmo ângulo que reaparece em
    partidas diferentes.

    O pipeline deriva os ângulos POR PARTIDA (`derive_entry_angles`, moda circular
    do yaw do atacante, mínimo de 4 kills). A mesma região costuma produzir o
    mesmo ângulo em várias partidas; juntá-los pelo mesmo raio da derivação dá o
    ângulo distinto e duas medidas de sustentação: em QUANTAS PARTIDAS ele
    aparece e quantas kills somam. Seis kills vindas de uma partida só são mais
    frágeis que seis vindas de cinco -- podem ser o hábito de um time, não do
    mapa. Devolve (ângulos, ângulos por partida, número de partidas).
    """
    from metrics.map_angles import YAW_CLUSTER_RADIUS_DEG, _circular_mean, derive_entry_angles
    from parsing.parser import kills_do_round_jogado

    man = json.loads((PROJECT_ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    partidas = [m for m, v in man.items() if v.get("mapa") == mapa
                and (PROJECT_ROOT / "data" / "interim" / m / "kills.parquet").exists()]
    por_partida = []
    for m in partidas:
        rounds = pl.read_parquet(PROCESSED / m / "rounds.parquet")
        kills = kills_do_round_jogado(pl.read_parquet(PROJECT_ROOT / "data" / "interim" / m / "kills.parquet"), rounds)
        por_partida.append(derive_entry_angles(kills).with_columns(pl.lit(m).alias("match_id")))
    if not por_partida:
        return pl.DataFrame(), 0, 0
    a = pl.concat(por_partida)

    def distancia(x: float, y: float) -> float:
        d = abs(x - y) % 360
        return min(d, 360 - d)

    grupos = []
    for (place, side), g in a.group_by("place", "side", maintain_order=True):
        linhas = sorted(g.iter_rows(named=True), key=lambda r: (-r["n_kills"], r["match_id"]))
        usados = [False] * len(linhas)
        for i, r in enumerate(linhas):
            if usados[i]:
                continue
            membros = [r]
            usados[i] = True
            for j in range(i + 1, len(linhas)):
                if not usados[j] and distancia(linhas[j]["yaw"], r["yaw"]) <= YAW_CLUSTER_RADIUS_DEG:
                    membros.append(linhas[j])
                    usados[j] = True
            grupos.append({
                "place": place, "side": side,
                "yaw": float(_circular_mean(np.array([x["yaw"] for x in membros]))),
                "partidas": len({x["match_id"] for x in membros}),
                "kills": sum(x["n_kills"] for x in membros),
            })
    ordem = pl.DataFrame(grupos).sort(["partidas", "kills", "place", "side"])
    return ordem, a.height, len(partidas)


def secao_angulos_nuke() -> list[str]:
    angulos, n_por_partida, n_partidas = angulos_distintos("de_nuke")
    out = ["## 5. Ângulos de entrada da Nuke, do menos sustentado para o mais", ""]
    if angulos.height == 0:
        return out + ["Sem partidas de Nuke com interim no disco.", ""]
    uma = angulos.filter(pl.col("partidas") == 1).height
    out += [
        f"{angulos.height} ângulos distintos, juntando os {n_por_partida} que o pipeline deriva partida a partida "
        f"nas {n_partidas} Nuke do corpus (mesmo ângulo em partidas diferentes = mesma região, mesmo lado, yaw "
        f"a menos de 20°). **{uma} aparecem numa partida só** -- podem ser hábito de um time naquele dia, não "
        "ângulo do mapa. A Nuke é o mapa de partição menos confiável do projeto (os dois sites empilhados "
        "na vertical), então é aqui que o julgamento humano mais vale.",
        "",
        "Yaw na convenção do CS2: 0° para a direita do radar, 90° para cima, crescendo no sentido anti-horário. "
        "O que você confirmar ou corrigir vira `MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`, que tem "
        "prioridade sobre o derivado.",
        "",
        "| # | região | lado | yaw | direção no radar | partidas | kills | sua resposta |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, r in enumerate(angulos.iter_rows(named=True), 1):
        out.append(f"| {i} | {r['place']} | {r['side'].upper()} | {r['yaw']:.0f}° | {_direcao(r['yaw'])} | "
                   f"{r['partidas']} | {r['kills']} | ____ |")
    out += ["", "**Sua resposta:** para cada linha, *confirma*, *descarta* (não é ângulo de verdade) ou "
                "*corrige* o yaw.", ""]
    return out


def main() -> None:
    partes = ["# Material de calibração", "",
              "Gerado por `py -3.12 -m scripts.material_calibracao`. Cada seção termina com a "
              "pergunta que só você responde; as respostas viram constante com data e tamanho de "
              "corpus no CLAUDE.md.", ""]
    partes += secao_pisos() + secao_grupos() + secao_forca() + secao_console() + secao_angulos_nuke()
    SAIDA.write_text("\n".join(partes), encoding="utf-8")
    print(f"Gravado em {SAIDA.relative_to(PROJECT_ROOT)} ({SAIDA.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
