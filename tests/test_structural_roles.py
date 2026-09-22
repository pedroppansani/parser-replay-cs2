"""
Testes das funções estruturais.

Os sintéticos são construídos para isolar UMA dimensão de cada vez, porque a
decisão entre âncora, rotativo e coringa é bidimensional (dispersão do início ×
distância início→contato) e um fixture que mexe nas duas ao mesmo tempo não prova
qual das duas o código usou.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from metrics.structural_roles import (
    DISPERSAO_INICIO_VARIADA,
    FUNCOES,
    MIN_SHARE_SNIPER_SECUNDARIO,
    ROLES_MANUAL_FILE,
    atribui_funcao,
    carrega_roles_manual,
    pontua,
    structural_roles,
)

TICKRATE = 64
# Múltiplos de 64 de propósito: `positioning.position_samples` amostra a cada 64
# ticks, e com um freeze_end fora da grade o fixture não gerava amostra nenhuma.
FREEZE = 64 * 31          # 1984
ROUND_TICKS = 64 * 128    # 8192
# Amostras (1 por segundo) em que o jogador fica parado na posição de setup.
# Tem que cobrir o SETUP_SECONDS_AFTER_FREEZE de positioning.py (10s).
SETUP_AMOSTRAS = 12


def _rounds(n: int) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "round_num": list(range(1, n + 1)),
            "start": [i * ROUND_TICKS for i in range(1, n + 1)],
            "freeze_end": [i * ROUND_TICKS + FREEZE for i in range(1, n + 1)],
            "end": [i * ROUND_TICKS + 64 * 110 for i in range(1, n + 1)],
            "official_end": [i * ROUND_TICKS + 64 * 116 for i in range(1, n + 1)],
            "winner": ["ct"] * n,
            "reason": ["t_killed"] * n,
            "bomb_plant": [None] * n,
        },
        schema_overrides={"bomb_plant": pl.Int64},
    ).with_columns(pl.col("round_num").cast(pl.UInt32))


def _cenario(
    n_rounds: int,
    lado: str,
    inicio_por_round,          # round -> (x, y, place)
    contato_por_round,         # round -> (x, y, segundos) ou None
    arma: str = "AK-47",
    companheiros_em=None,      # round -> (x, y) onde os 4 companheiros ficam
):
    """Cinco jogadores do mesmo lado; o jogador 1 é o alvo do teste."""
    pos, tick_rows, dmg = [], [], []
    outro_lado = "t" if lado == "ct" else "ct"

    for r in range(1, n_rounds + 1):
        ix, iy, iplace = inicio_por_round(r)
        contato = contato_por_round(r)
        cx, cy = (companheiros_em(r) if companheiros_em else (ix + 2000.0, iy))

        # O jogador FICA na posição de setup durante a janela de setup e só
        # depois se desloca -- que é o que um time faz de verdade. O fixture
        # antigo o movia desde o tick zero, e aí a foto de setup (10s depois do
        # freeze) já o pegava no meio do caminho.
        for amostra in range(SETUP_AMOSTRAS + 12):
            tick = r * ROUND_TICKS + FREEZE + amostra * TICKRATE
            if contato and amostra >= SETUP_AMOSTRAS:
                passo = (amostra - SETUP_AMOSTRAS) / 11
                tx = ix + (contato[0] - ix) * passo
                ty = iy + (contato[1] - iy) * passo
            else:
                tx, ty = ix, iy
            pos.append({"round_num": r, "tick": tick, "steamid": 1, "name": "alvo",
                        "side": lado, "X": tx, "Y": ty, "Z": 0.0, "place": iplace})
            tick_rows.append({"round_num": r, "tick": tick, "steamid": 1, "name": "alvo",
                              "side": lado, "X": tx, "Y": ty, "Z": 0.0, "is_alive": True,
                              "place": iplace, "active_weapon_name": arma,
                              "current_equip_value": 4000})
            for sid in range(2, 6):
                pos.append({"round_num": r, "tick": tick, "steamid": sid, "name": f"p{sid}",
                            "side": lado, "X": cx, "Y": cy + sid * 20, "Z": 0.0,
                            "place": "Meio"})
                tick_rows.append({"round_num": r, "tick": tick, "steamid": sid, "name": f"p{sid}",
                                  "side": lado, "X": cx, "Y": cy + sid * 20, "Z": 0.0,
                                  "is_alive": True, "place": "Meio",
                                  "active_weapon_name": "AK-47", "current_equip_value": 4000})
            # dois adversários, para os dois bombsites existirem no mapa
            for j, (sid, px, py, pl_nome) in enumerate(
                [(11, -3000.0, 0.0, "BombsiteA"), (12, 3000.0, 0.0, "BombsiteB")]
            ):
                pos.append({"round_num": r, "tick": tick, "steamid": sid, "name": f"q{sid}",
                            "side": outro_lado, "X": px, "Y": py, "Z": 0.0, "place": pl_nome})
                tick_rows.append({"round_num": r, "tick": tick, "steamid": sid, "name": f"q{sid}",
                                  "side": outro_lado, "X": px, "Y": py, "Z": 0.0,
                                  "is_alive": True, "place": pl_nome,
                                  "active_weapon_name": "AK-47", "current_equip_value": 4000})

        if contato:
            t_contato = r * ROUND_TICKS + FREEZE + int(contato[2] * TICKRATE)
            dmg.append({"round_num": r, "tick": t_contato,
                        "attacker_steamid": 11, "victim_steamid": 1, "dmg_health_real": 30})
        # os companheiros encostam depois, para o alvo ser o primeiro do time
        dmg.append({"round_num": r, "tick": r * ROUND_TICKS + FREEZE + 40 * TICKRATE,
                    "attacker_steamid": 12, "victim_steamid": 2, "dmg_health_real": 30})

    def df(rows):
        return pl.DataFrame(rows).with_columns(pl.col("round_num").cast(pl.UInt32))

    bomb = pl.DataFrame(
        {"round_num": [1, 1], "tick": [10_000, 10_001], "event": ["plant", "plant"],
         "X": [-3000.0, 3000.0], "Y": [0.0, 0.0], "Z": [0.0, 0.0],
         "bombsite": ["BombsiteA", "BombsiteB"], "steamid": [11, 12]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    kills = pl.DataFrame(
        schema={"round_num": pl.UInt32, "tick": pl.Int64, "attacker_steamid": pl.Int64,
                "victim_steamid": pl.Int64, "weapon": pl.String}
    )
    return {
        "ticks": df(tick_rows), "rounds": _rounds(n_rounds), "damages": df(dmg),
        "kills": kills, "bomb": bomb, "grenades": None,
    }


TEAM_OF = {**{i: "A" for i in range(1, 6)}, **{i: "B" for i in (11, 12)}}


def _funcoes_do_alvo(tables) -> list[str | None]:
    por_round, _ = structural_roles(tables, TEAM_OF, "de_teste", tickrate=TICKRATE)
    alvo = por_round.filter(pl.col("steamid") == 1).sort("round_num")
    return alvo["funcao"].to_list()


# --- As três funções de CT --------------------------------------------------

def test_ancora_sintetico_nao_sai_como_rotativo_nem_coringa():
    """Sempre a mesma região de bombsite, deslocamento baixo."""
    tables = _cenario(
        12, "ct",
        inicio_por_round=lambda r: (-3000.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-3000.0 + 120, 60.0, 25.0),
    )
    funcoes = _funcoes_do_alvo(tables)
    assert funcoes.count("ancora") >= 8, funcoes
    assert "rotativo" not in funcoes
    assert "coringa" not in funcoes


def test_rotativo_sintetico_nao_sai_como_coringa():
    """Início sempre igual e central; contato sempre longe do início."""
    tables = _cenario(
        12, "ct",
        inicio_por_round=lambda r: (0.0, 0.0, "Meio"),
        contato_por_round=lambda r: ((-2600.0 if r % 2 else 2600.0), 0.0, 30.0),
    )
    funcoes = _funcoes_do_alvo(tables)
    assert funcoes.count("rotativo") >= 8, funcoes
    assert "coringa" not in funcoes


def test_coringa_sintetico_nao_sai_como_ancora():
    """Início diferente a cada round, mesmo com deslocamento baixo dentro dele."""
    pontos = [(-2500.0, 0.0, "Meio"), (2500.0, 0.0, "Meio"),
              (0.0, 2500.0, "Meio"), (0.0, -2500.0, "Meio")]

    tables = _cenario(
        12, "ct",
        inicio_por_round=lambda r: pontos[r % 4],
        contato_por_round=lambda r: (pontos[r % 4][0] + 80, pontos[r % 4][1] + 40, 20.0),
    )
    funcoes = _funcoes_do_alvo(tables)
    assert funcoes.count("coringa") >= 8, funcoes
    assert "ancora" not in funcoes


# --- Lurker: conjunção, não disjunção ---------------------------------------

def test_lurker_precisa_das_tres_condicoes_juntas():
    """Só isolado, sem contato tardio nem região diferente, não é lurk."""
    # isolado (longe dos companheiros) mas encosta PRIMEIRO e na mesma área
    tables = _cenario(
        12, "t",
        inicio_por_round=lambda r: (-2900.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2900.0, 0.0, 5.0),
        companheiros_em=lambda r: (-2880.0, 0.0),
    )
    funcoes = _funcoes_do_alvo(tables)
    assert "lurker" not in funcoes, funcoes


def test_lurker_sintetico_com_as_tres_sai_como_lurker():
    """Controle: se nunca sair lurker, o teste acima não mede nada."""
    tables = _cenario(
        12, "t",
        inicio_por_round=lambda r: (2900.0, 0.0, "BombsiteB"),
        contato_por_round=lambda r: (2900.0, 0.0, 55.0),
        companheiros_em=lambda r: (-2900.0, 0.0),
    )
    assert "lurker" in _funcoes_do_alvo(tables)


# --- Entry exige o time vindo atrás -----------------------------------------

def test_entry_sem_o_time_vindo_atras_nao_e_entry():
    """Entrar primeiro com o time do outro lado do mapa é jogada individual."""
    tables = _cenario(
        12, "t",
        inicio_por_round=lambda r: (-2900.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2900.0, 0.0, 6.0),
        companheiros_em=lambda r: (2900.0, 0.0),   # time no bombsite oposto
    )
    assert "entry" not in _funcoes_do_alvo(tables)


# --- AWPer exige consistência -----------------------------------------------

def test_rifler_que_pegou_awp_largada_em_dois_rounds_nao_e_awper():
    """2 de 24 rounds com a arma não é função, é evento isolado."""
    tables = _cenario(
        24, "ct",
        inicio_por_round=lambda r: (-3000.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2900.0, 60.0, 25.0),
    )
    # troca a arma do alvo só em 2 rounds
    tables["ticks"] = tables["ticks"].with_columns(
        pl.when((pl.col("steamid") == 1) & pl.col("round_num").is_in([3, 7]))
        .then(pl.lit("AWP"))
        .otherwise(pl.col("active_weapon_name"))
        .alias("active_weapon_name")
    )
    funcoes = _funcoes_do_alvo(tables)
    assert "awper" not in funcoes, funcoes
    assert 2 / 24 < MIN_SHARE_SNIPER_SECUNDARIO


def test_awper_consistente_sai_como_awper():
    """Controle do teste acima."""
    tables = _cenario(
        12, "ct",
        inicio_por_round=lambda r: (-3000.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2900.0, 60.0, 25.0),
        arma="AWP",
    )
    assert "awper" in _funcoes_do_alvo(tables)


# --- Lado -------------------------------------------------------------------

def test_funcao_de_ct_nunca_aparece_em_round_de_tr():
    tables = _cenario(
        12, "t",
        inicio_por_round=lambda r: (-2900.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2500.0, 0.0, 20.0),
    )
    por_round, _ = structural_roles(tables, TEAM_OF, "de_teste", tickrate=TICKRATE)
    so_ct = {k for k, v in FUNCOES.items() if v[1] == "ct"}
    so_t = {k for k, v in FUNCOES.items() if v[1] == "t"}

    erradas = por_round.filter(
        ((pl.col("side") == "t") & pl.col("funcao").is_in(list(so_ct)))
        | ((pl.col("side") == "ct") & pl.col("funcao").is_in(list(so_t)))
    )
    assert erradas.height == 0


# --- IGL nunca automático ---------------------------------------------------

def test_o_codigo_nunca_escreve_em_roles_manual():
    """IGL é atribuição humana. O código LÊ o arquivo e nunca o cria nem altera.

    O teste roda o pipeline inteiro e confere que o arquivo não foi tocado —
    incluindo o caso de ele não existir, em que continuar não existindo é o
    comportamento certo.
    """
    antes = ROLES_MANUAL_FILE.exists()
    carimbo = ROLES_MANUAL_FILE.stat().st_mtime if antes else None

    tables = _cenario(
        12, "ct",
        inicio_por_round=lambda r: (-3000.0, 0.0, "BombsiteA"),
        contato_por_round=lambda r: (-2900.0, 60.0, 25.0),
    )
    structural_roles(tables, TEAM_OF, "de_teste", tickrate=TICKRATE)

    assert ROLES_MANUAL_FILE.exists() == antes, "o código criou ou apagou roles_manual.json"
    if antes:
        assert ROLES_MANUAL_FILE.stat().st_mtime == carimbo, "o código escreveu em roles_manual.json"


def test_roles_manual_ausente_devolve_vazio_sem_estourar():
    assert carrega_roles_manual(Path("nao_existe_roles_manual.json")) == {}


def test_nenhuma_funcao_automatica_se_chama_igl():
    """IGL não pode entrar na lista de funções atribuídas pelo código."""
    assert "igl" not in FUNCOES
    for chave, (rotulo, _lado) in FUNCOES.items():
        assert "igl" not in rotulo.lower()


# --- Varredura dos dados reais ----------------------------------------------

PROCESSED = Path(__file__).resolve().parent.parent / "data" / "processed"
PARTIDAS = sorted(
    d.name for d in PROCESSED.glob("match_*") if (d / "structural_roles.parquet").exists()
)


@pytest.mark.skipif(not PARTIDAS, reason="funções estruturais ainda não processadas")
@pytest.mark.parametrize("match_id", PARTIDAS)
def test_dados_reais_respeitam_o_lado(match_id):
    tabela = pl.read_parquet(PROCESSED / match_id / "structural_roles.parquet")
    so_ct = {k for k, v in FUNCOES.items() if v[1] == "ct"}
    so_t = {k for k, v in FUNCOES.items() if v[1] == "t"}
    erradas = tabela.filter(
        ((pl.col("side") == "t") & pl.col("funcao").is_in(list(so_ct)))
        | ((pl.col("side") == "ct") & pl.col("funcao").is_in(list(so_t)))
    )
    assert erradas.height == 0, f"{match_id}: {erradas.height} funções no lado errado"


# --- Trader -----------------------------------------------------------------
#
# O trader é o único papel definido POR RELAÇÃO a outro jogador: ele é o segundo
# homem da entrada. O fixture então precisa de dois jogadores com papéis
# diferentes no mesmo round, e o que varia entre os dois testes é só a distância
# do apoio até o entry no instante do contato.

def _cenario_entrada(distancia_do_apoio: float, n_rounds: int = 10):
    """Entry (sid 1) abre e morre; apoio (sid 2) troca a morte dele.

    `distancia_do_apoio` é a distância entre os dois no tick em que o entry toma
    o primeiro contato -- é exatamente o que separa "entrou junto" de "chegou
    depois", e é a única coisa que muda entre os dois testes.
    """
    pos, tick_rows, dmg, kill_rows = [], [], [], []
    ex, ey = 500.0, 0.0          # onde o entry vai brigar

    for r in range(1, n_rounds + 1):
        t_contato = r * ROUND_TICKS + FREEZE + 14 * TICKRATE
        for amostra in range(SETUP_AMOSTRAS + 12):
            tick = r * ROUND_TICKS + FREEZE + amostra * TICKRATE
            vivos = [
                (1, ex, ey, "Meio"),
                (2, ex + distancia_do_apoio, ey, "Meio"),
                (3, ex, ey + 3000.0, "Meio"),
                (4, ex, ey + 3200.0, "Meio"),
                (5, ex, ey + 3400.0, "Meio"),
            ]
            for sid, x, y, place in vivos:
                # o entry some das amostras depois de morrer
                if sid == 1 and tick > t_contato + 2 * TICKRATE:
                    continue
                linha = {"round_num": r, "tick": tick, "steamid": sid, "name": f"p{sid}",
                         "side": "t", "X": x, "Y": y, "Z": 0.0, "place": place}
                pos.append(linha)
                tick_rows.append({**linha, "is_alive": True,
                                  "active_weapon_name": "AK-47", "current_equip_value": 4000})
            for sid, px, py, pl_nome in [(11, -3000.0, 0.0, "BombsiteA"),
                                         (12, 3000.0, 0.0, "BombsiteB")]:
                linha = {"round_num": r, "tick": tick, "steamid": sid, "name": f"q{sid}",
                         "side": "ct", "X": px, "Y": py, "Z": 0.0, "place": pl_nome}
                pos.append(linha)
                tick_rows.append({**linha, "is_alive": True,
                                  "active_weapon_name": "AK-47", "current_equip_value": 4000})

        # o entry encosta primeiro, o apoio logo depois (segundo no contato)
        dmg.append({"round_num": r, "tick": t_contato, "attacker_steamid": 11,
                    "victim_steamid": 1, "dmg_health_real": 100})
        dmg.append({"round_num": r, "tick": t_contato + TICKRATE, "attacker_steamid": 2,
                    "victim_steamid": 11, "dmg_health_real": 50})
        dmg.append({"round_num": r, "tick": t_contato + 25 * TICKRATE, "attacker_steamid": 12,
                    "victim_steamid": 3, "dmg_health_real": 30})
        # o CT mata o entry e o apoio troca dentro da janela
        kill_rows.append({"round_num": r, "tick": t_contato, "attacker_steamid": 11,
                          "victim_steamid": 1, "weapon": "ak47"})
        kill_rows.append({"round_num": r, "tick": t_contato + 2 * TICKRATE,
                          "attacker_steamid": 2, "victim_steamid": 11, "weapon": "ak47"})

    def df(rows):
        return pl.DataFrame(rows).with_columns(pl.col("round_num").cast(pl.UInt32))

    bomb = pl.DataFrame(
        {"round_num": [1, 1], "tick": [10_000, 10_001], "event": ["plant", "plant"],
         "X": [-3000.0, 3000.0], "Y": [0.0, 0.0], "Z": [0.0, 0.0],
         "bombsite": ["BombsiteA", "BombsiteB"], "steamid": [11, 12]}
    ).with_columns(pl.col("round_num").cast(pl.UInt32))

    return {
        "ticks": df(tick_rows), "rounds": _rounds(n_rounds), "damages": df(dmg),
        "kills": df(kill_rows).with_columns(pl.col("tick").cast(pl.Int64)),
        "bomb": bomb, "grenades": None,
    }


def _funcoes_de(tables, steamid: int) -> list[str | None]:
    por_round, _ = structural_roles(tables, TEAM_OF, "de_teste", tickrate=TICKRATE)
    alvo = por_round.filter(pl.col("steamid") == steamid).sort("round_num")
    return alvo["funcao"].to_list()


def test_quem_entra_junto_e_troca_a_morte_do_entry_sai_como_trader():
    tables = _cenario_entrada(distancia_do_apoio=200.0)
    assert _funcoes_de(tables, 2) == ["trader"] * 10
    # e o entry continua sendo o entry: são duas funções, não uma disputa
    assert "entry" in _funcoes_de(tables, 1)


def test_quem_troca_a_morte_mas_estava_longe_nao_e_trader():
    """Trade tardio de quem não entrou junto não é a função trader.

    O jogador faz exatamente a mesma kill de troca do teste anterior; a única
    diferença é que no instante do contato do entry ele estava a 2.000u dali.
    Quem chega depois e limpa não é o segundo homem da entrada.
    """
    tables = _cenario_entrada(distancia_do_apoio=2000.0)
    assert "trader" not in _funcoes_de(tables, 2)


def test_candidatos_a_igl_nao_escrevem_nada():
    """A lista de candidatos é material para o Pedro decidir (decisão 7g): o
    script só LÊ. Nenhuma chamada de escrita e nenhuma referência ao arquivo
    manual podem aparecer nele."""
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent / "scripts" / "igl_candidatos.py").read_text(encoding="utf-8")
    codigo = "\n".join(l for l in fonte.splitlines() if not l.strip().startswith("#"))
    corpo = codigo.split('"""', 2)[-1]  # fora da docstring do módulo
    for proibido in ("write_text", "write_parquet", ".write(", "open(", "ROLES_MANUAL", "json.dump"):
        assert proibido not in corpo, proibido


# --- empate na função dominante ---------------------------------------------

def _por_round_sintetico(contagens: dict[str, int], n: int = 12) -> pl.DataFrame:
    """Um jogador, um lado: `contagens` rounds em cada função, o resto sem função."""
    linhas, r = [], 1
    for funcao, k in contagens.items():
        for _ in range(k):
            linhas.append({"round_num": r, "steamid": 1, "name": "x", "side": "t",
                           "funcao": funcao, "pontuacao": 0.5 + 0.01 * r})
            r += 1
    while r <= n:
        linhas.append({"round_num": r, "steamid": 1, "name": "x", "side": "t", "funcao": None, "pontuacao": None})
        r += 1
    return pl.DataFrame(linhas, schema_overrides={"funcao": pl.String, "pontuacao": pl.Float64})


def test_empate_na_contagem_e_sem_funcao_dominante_com_todas_as_empatadas():
    """REGRESSÃO (match_44 flameZ, decisão 28): entry, lurker, suporte e trader
    com 1 round cada. A "dominante" saía da pontuação média, que variava com a
    ordem de hash -- entry numa execução, lurker na outra. Empate declarado."""
    from metrics.structural_roles import resume_por_lado, texto_empate

    r = resume_por_lado(_por_round_sintetico({"entry": 1, "lurker": 1, "suporte": 1, "trader": 1})).row(0, named=True)
    assert r["funcao"] is None
    assert r["empate_funcao"] is True
    assert sorted(r["funcoes_empatadas"]) == ["entry", "lurker", "suporte", "trader"]
    assert r["rounds_empatadas"] == [1, 1, 1, 1]
    t = texto_empate(r)
    assert t.startswith("sem função dominante:") and "Lurker 8% (1 de 12)" in t and " vs " in t


def test_um_round_de_diferenca_ainda_define_a_funcao_com_margem_zero():
    from metrics.structural_roles import MARGEM_EMPATE_FUNCAO_ROUNDS, resume_por_lado, texto_empate

    assert MARGEM_EMPATE_FUNCAO_ROUNDS == 0
    r = resume_por_lado(_por_round_sintetico({"entry": 5, "lurker": 4})).row(0, named=True)
    assert r["funcao"] == "entry" and r["empate_funcao"] is False
    assert r["funcoes_empatadas"] is None and texto_empate(r) == ""


def test_a_margem_estende_o_empate_quando_for_decidida(monkeypatch):
    """A constante é o botão: com margem de 1 round, 5 contra 4 vira empate."""
    import metrics.structural_roles as sr

    monkeypatch.setattr(sr, "MARGEM_EMPATE_FUNCAO_ROUNDS", 1)
    r = sr.resume_por_lado(_por_round_sintetico({"entry": 5, "lurker": 4})).row(0, named=True)
    assert r["funcao"] is None and r["funcoes_empatadas"] == ["entry", "lurker"]
    assert "Entry fragger 42% (5 de 12) vs Lurker 33% (4 de 12)" in sr.texto_empate(r)
