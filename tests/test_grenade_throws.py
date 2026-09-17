"""
Testes da ficha de execução de arremesso.

Os sintéticos aqui são construídos com a MESMA geometria que o módulo procura
(olhos + offset na direção da mira), o que os torna um teste de ida e volta: se
a convenção de ângulo ou a altura de olhos estiverem trocadas no código, o
arremesso sintético não é encontrado.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import polars as pl
import pytest

from metrics.grenade_throws import (
    ALTURA_OLHOS_AGACHADO,
    ALTURA_OLHOS_EM_PE,
    ALTURA_OLHOS_MAX,
    ALTURA_OLHOS_MIN,
    FATOR_HERANCA,
    MAX_RESIDUO_ANCORAGEM,
    OFFSET_VERTICAL_SOLTURA,
    colisoes,
    direcao_da_mira,
    grenade_throws,
    grupos_de_forca,
    motivo_aproximado,
    rotula_forca,
)

TICKRATE = 64
FREEZE = 64 * 31
ROUND_TICKS = 64 * 128
OFFSET_MAO = 26.5          # o que o corpus mede; o sintético é construído com ele


def _rounds(n: int = 1) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "round_num": list(range(1, n + 1)),
            "start": [i * ROUND_TICKS for i in range(1, n + 1)],
            "freeze_end": [i * ROUND_TICKS + FREEZE for i in range(1, n + 1)],
            "end": [i * ROUND_TICKS + 64 * 110 for i in range(1, n + 1)],
        }
    ).with_columns(pl.col("round_num").cast(pl.UInt32))


def _cenario(
    arremessos: list[dict], n_rounds: int = 1, convencao_invertida: bool = False
) -> dict[str, pl.DataFrame]:
    """Monta ticks/grenades/shots para uma lista de arremessos sintéticos.

    Cada arremesso é um dicionário com: round, tick, pitch, yaw, velocidade,
    agachado, velocidade_do_jogador (vetor 3D) e posição dos pés.

    A trajetória é gerada com a MESMA física que o módulo assume -- inclusive o
    fator de herança medido --, então o teste confere que o código recupera o
    que foi gerado, e não que ele concorda consigo mesmo por construção.
    """
    tick_rows, gren_rows, shot_rows = [], [], []
    sinal = 1.0 if convencao_invertida else -1.0  # invertida = pitch positivo olha pra CIMA

    for n, a in enumerate(arremessos):
        rn = a.get("round", 1)
        base = rn * ROUND_TICKS + FREEZE
        t_soltura = base + a["tick"]
        sid = a.get("steamid", 100 + n)
        v_jog = np.array(a.get("v_jogador", [0.0, 0.0, 0.0]), dtype=float)
        pes0 = np.array(a.get("pes", [0.0, 0.0, 0.0]), dtype=float)
        altura = ALTURA_OLHOS_AGACHADO if a.get("agachado") else ALTURA_OLHOS_EM_PE

        # ticks do jogador: anda com velocidade constante durante todo o round
        for dt in range(-40, 60):
            t = t_soltura + dt
            if t < base:
                continue
            pes = pes0 + v_jog * (dt / TICKRATE)
            tick_rows.append({
                "round_num": rn, "tick": t, "steamid": sid, "name": f"p{sid}",
                "side": "t", "X": pes[0], "Y": pes[1], "Z": pes[2],
                "pitch": a["pitch"], "yaw": a["yaw"], "is_walking": a.get("andando", False),
            })

        p = np.radians(a["pitch"])
        y = np.radians(a["yaw"])
        u = np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), sinal * np.sin(p)])
        origem = pes0 + np.array([0.0, 0.0, altura + OFFSET_VERTICAL_SOLTURA]) + OFFSET_MAO * u
        v_proj = u * a["velocidade"] + FATOR_HERANCA * v_jog

        # o primeiro sample do projétil cai um tick ANTES da soltura, que é o
        # deslocamento sistemático que a ancoragem mede no dado real
        for k in range(a.get("n_samples", 6)):
            ponto = origem + v_proj * (k / TICKRATE) + np.array(a.get("desvio", [0, 0, 0])) * k
            gren_rows.append({
                "round_num": rn, "tick": t_soltura - 1 + k, "steamid": sid,
                "thrower_steamid": sid, "thrower": f"p{sid}",
                "grenade_type": a.get("classe", "CSmokeGrenadeProjectile"),
                "entity_id": 900 + n,
                "X": ponto[0], "Y": ponto[1], "Z": ponto[2],
            })

        shot_rows.append({
            "round_num": rn, "tick": t_soltura - a.get("atraso", 7),
            "player_steamid": sid, "weapon": a.get("arma", "weapon_smokegrenade"),
        })

    def df(rows):
        return pl.DataFrame(rows).with_columns(pl.col("round_num").cast(pl.UInt32))

    return {
        "rounds": _rounds(n_rounds),
        "ticks": df(tick_rows),
        "grenades": df(gren_rows),
        "shots": df(shot_rows),
    }


def _um(**kw) -> dict:
    base = {"tick": 300, "pitch": -10.0, "yaw": 45.0, "velocidade": 675.0}
    base.update(kw)
    return base


# --- Convenção de ângulo (decisão 9) ----------------------------------------

def test_pitch_positivo_olha_para_baixo():
    """Decisão 9 do CLAUDE.md, no vetor de direção."""
    assert direcao_da_mira(np.array([45.0]), np.array([0.0]))[0][2] < 0
    assert direcao_da_mira(np.array([-45.0]), np.array([0.0]))[0][2] > 0


def test_a_convencao_invertida_quebra_a_altura_derivada():
    """Controle da decisão 9. Se passar nas duas convenções, não mede nada.

    Onde o sinal do pitch aparece: NÃO no resíduo da ancoragem, que é
    horizontal e portanto cego ao eixo Z. Ele aparece na ALTURA DOS OLHOS
    derivada -- com o sinal trocado, o termo `offset * u_z` entra invertido e a
    altura erra por 2·offset·sen(pitch), que a 35° são mais de 30 unidades.

    É exatamente assim que a convenção se validou no corpus real: só com o sinal
    certo a altura derivada cai em 64,17u, o valor que o projeto já supunha.
    """
    pedido = [_um(pitch=35.0)]   # pitch bem inclinado, senão o sinal quase não importa

    pr_ok, _ = grenade_throws(_cenario(pedido), TICKRATE)
    pr_inv, _ = grenade_throws(_cenario(pedido, convencao_invertida=True), TICKRATE)

    assert abs(pr_ok["altura_olhos"][0] - ALTURA_OLHOS_EM_PE) < 1.0
    erro_invertido = abs(pr_inv["altura_olhos"][0] - ALTURA_OLHOS_EM_PE)
    assert erro_invertido > 25.0, f"o sinal trocado só errou {erro_invertido:.1f}u"
    # e o arremesso invertido nem sequer pode ser oferecido como reprodutível
    assert not pr_inv["reproducao_exata"][0]


# --- A) Ancoragem -----------------------------------------------------------

def test_a_ancoragem_acha_o_tick_da_soltura_e_nao_o_do_clique():
    """O clique fica 7 ticks antes; o ângulo que importa é o da soltura.

    O jogador está em MOVIMENTO de propósito. Com ele parado, a posição e a mira
    são idênticas em toda a janela, o resíduo fica plano e o tick é
    genuinamente indeterminado -- medido no corpus, é o que acontece em boa
    parte dos arremessos. A indeterminação é inofensiva ali (a mira varia 0,29°
    na mediana), mas torna este teste sem conteúdo: só dá pra provar que a
    ancoragem acha o tick certo quando existe um tick certo a achar.
    """
    tab = _cenario([_um(atraso=7, v_jogador=[180.0, 140.0, 0.0])])
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr["tick_soltura"][0] - pr["tick_clique"][0] == 7
    assert pr["residuo"][0] < 1.0


@pytest.mark.parametrize("match_id", ["match_01", "match_05", "match_09"])
def test_a_ancoragem_converge_no_dado_real(match_id):
    """Trava a taxa de convergência: se cair, a ficha inteira perde o chão.

    Medido no corpus das 9 partidas: 99,9% dos 3.020 arremessos ficam abaixo do
    limiar, com resíduo mediano de 0,5 unidade. 95% é piso com folga larga --
    ele existe para pegar regressão, não para ser apertado.
    """
    processed = Path("data/processed") / match_id
    interim = Path("data/interim") / match_id
    if not (interim / "grenades.parquet").exists():
        pytest.skip(f"{match_id} sem dado interim")

    tabelas = {
        "rounds": pl.read_parquet(processed / "rounds.parquet"),
        "ticks": pl.read_parquet(interim / "ticks.parquet"),
        "grenades": pl.read_parquet(interim / "grenades.parquet"),
        "shots": pl.read_parquet(interim / "shots.parquet"),
    }
    _, resumo = grenade_throws(tabelas, TICKRATE)
    assert resumo["arremessos"] > 200
    assert resumo["taxa_convergencia"] >= 0.95
    assert resumo["residuo_mediano"] < 2.0


@pytest.mark.parametrize("match_id", ["match_01", "match_05"])
def test_a_altura_dos_olhos_derivada_e_fisicamente_plausivel(match_id):
    """Ela é MEDIDA, não chutada -- então precisa cair onde o jogo põe.

    O projeto supõe 64 unidades em pé. A medição no corpus dá 64,17 depois de
    descontar o deslocamento vertical da soltura, o que valida a suposição em
    vez de contrariá-la.
    """
    processed = Path("data/processed") / match_id
    interim = Path("data/interim") / match_id
    if not (interim / "grenades.parquet").exists():
        pytest.skip(f"{match_id} sem dado interim")

    tabelas = {
        "rounds": pl.read_parquet(processed / "rounds.parquet"),
        "ticks": pl.read_parquet(interim / "ticks.parquet"),
        "grenades": pl.read_parquet(interim / "grenades.parquet"),
        "shots": pl.read_parquet(interim / "shots.parquet"),
    }
    _, resumo = grenade_throws(tabelas, TICKRATE)
    em_pe = resumo["altura_olhos_em_pe"]
    assert ALTURA_OLHOS_MIN < em_pe < ALTURA_OLHOS_MAX
    assert abs(em_pe - ALTURA_OLHOS_EM_PE) < 3.0


# --- B) Força ---------------------------------------------------------------

def test_a_forca_e_relativa_ao_jogador():
    """O MESMO arremesso feito parado e correndo tem que sair na mesma classe.

    É o erro que a maioria comete: sem descontar a velocidade de quem arremessou,
    todo run-throw curto é classificado como arremesso longo. Medido no corpus,
    o desconto leva a mediana de parado e correndo de 674 x 727 u/s para
    672,0 x 672,7.
    """
    tab = _cenario([
        _um(velocidade=675.0, v_jogador=[0.0, 0.0, 0.0]),
        _um(velocidade=675.0, v_jogador=[180.0, 140.0, 0.0], round=2),
    ], n_rounds=2)
    pr, _ = grenade_throws(tab, TICKRATE)

    v = pr["velocidade_arremesso"].to_list()
    assert abs(v[0] - v[1]) < 15.0, f"parado {v[0]:.1f} x correndo {v[1]:.1f}"

    grupos = grupos_de_forca(np.array(v * 15))  # repetido só para bater o mínimo do grupo
    assert rotula_forca(v[0], grupos) == rotula_forca(v[1], grupos)


def test_arremessos_de_forca_diferente_nao_caem_na_mesma_classe():
    """Curto, médio e longo têm que sobreviver ao agrupamento.

    Os centros vêm da medição no corpus: 201, 440 e 674 u/s.
    """
    velocidades = np.concatenate([
        np.random.default_rng(0).normal(c, 8.0, 60) for c in (201.0, 440.0, 674.0)
    ])
    grupos = grupos_de_forca(velocidades)
    assert len(grupos) == 3
    rotulos = {rotula_forca(c, grupos) for c, _ in grupos}
    assert len(rotulos) == 3
    # e a ordem é do mais fraco para o mais forte
    assert [round(c) for c, _ in grupos] == sorted(round(c) for c, _ in grupos)


def test_o_rotulo_de_forca_e_neutro_ate_o_pedro_confirmar():
    """Decisão 8 aplicada aqui: o código mede o grupo, não batiza o grupo."""
    grupos = grupos_de_forca(np.concatenate([np.full(40, 200.0), np.full(40, 675.0)]))
    nomes = [rotula_forca(c, grupos) for c, _ in grupos]
    assert nomes == ["força A", "força B"]
    assert not any("curto" in n or "longo" in n for n in nomes)


# --- C) Postura -------------------------------------------------------------

def test_arremesso_agachado_sai_classificado_como_agachado():
    tab = _cenario([_um(agachado=True)])
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr["postura"][0] == "agachado"
    assert abs(pr["altura_olhos"][0] - ALTURA_OLHOS_AGACHADO) < 3.0


def test_arremesso_em_pe_sai_classificado_como_em_pe():
    tab = _cenario([_um(agachado=False)])
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr["postura"][0] == "em pé"


def test_movimento_separa_parado_de_correndo():
    tab = _cenario([
        _um(v_jogador=[0.0, 0.0, 0.0]),
        _um(v_jogador=[180.0, 140.0, 0.0], round=2),
    ], n_rounds=2)
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr.sort("round_num")["movimento"].to_list() == ["parado", "correndo"]


# --- D) Colisões ------------------------------------------------------------

def test_trajetoria_reta_nao_acusa_colisao():
    ticks = np.arange(0, 10, dtype=np.int64)
    traj = np.stack([ticks * 12.0, ticks * 5.0, np.full(10, 100.0)], axis=-1)
    assert colisoes(traj, ticks, TICKRATE) == []


def test_ricochete_acusa_colisao():
    """Uma reta que vira 90° no meio: é isso que bater na parede parece."""
    ida = np.stack([np.arange(6) * 12.0, np.zeros(6), np.full(6, 100.0)], axis=-1)
    volta = np.stack([
        np.full(6, ida[-1, 0]), np.arange(1, 7) * 12.0, np.full(6, 100.0)
    ], axis=-1)
    traj = np.vstack([ida, volta])
    ticks = np.arange(traj.shape[0], dtype=np.int64)
    assert len(colisoes(traj, ticks, TICKRATE)) >= 1


def test_granada_parada_no_chao_nao_vira_colisao_a_cada_tremida():
    """Depois que ela para, cada ruído de posição viraria uma 'colisão'."""
    ticks = np.arange(0, 12, dtype=np.int64)
    rng = np.random.default_rng(1)
    traj = np.tile(np.array([500.0, 500.0, 0.0]), (12, 1)) + rng.normal(0, 0.05, (12, 3))
    assert colisoes(traj, ticks, TICKRATE) == []


# --- F) Honestidade ---------------------------------------------------------

def test_residuo_alto_nao_pode_afirmar_reproducao_exata():
    """Lineup errado é pior que nenhum lineup: o cara treina errado."""
    ruim = {"tick_soltura": 100, "residuo": MAX_RESIDUO_ANCORAGEM + 1,
            "giro_na_soltura": 10.0, "altura_olhos": 64.0}
    motivo = motivo_aproximado(ruim)
    assert motivo is not None and "ancoragem" in motivo

    girando = {"tick_soltura": 100, "residuo": 0.2,
               "giro_na_soltura": 900.0, "altura_olhos": 64.0}
    assert "girava" in (motivo_aproximado(girando) or "")

    bom = {"tick_soltura": 100, "residuo": 0.2,
           "giro_na_soltura": 10.0, "altura_olhos": 64.0}
    assert motivo_aproximado(bom) is None


def test_arremesso_sem_ancoragem_nunca_sai_como_exato():
    assert motivo_aproximado({"tick_soltura": None}) is not None


# --- Warmup -----------------------------------------------------------------

def test_arremesso_antes_do_fim_do_freeze_nao_entra():
    """Decisão 8b: o que acontece no tempo parado não pertence a round nenhum."""
    tab = _cenario([_um(tick=300), _um(tick=-200, round=1, steamid=777)])
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr.height == 1
    assert 777 not in pr["steamid"].to_list()


def test_granada_no_inventario_nao_e_arremesso():
    """CFlashbang é a flash PARADA no inventário, não a arremessada."""
    tab = _cenario([_um(classe="CFlashbang")])
    pr, _ = grenade_throws(tab, TICKRATE)
    assert pr.height == 0
