"""Os casos que o Pedro já julgou na seção 7.2 do material (fase 18, item 18.3), com os dados reais.

Cada caso confere a classificação nova contra o que ele escreveu. Pulado sem o interim ou sem a malha do mapa
(`py -3.12 -m scripts.visao_malhas`). O que os dados mostram em cada caso (quem estava visível, se engajou,
se recuou, a chance de vitória) está no relatório da fase 18.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import polars as pl
import pytest

from metrics import erros as E
from metrics.erros import visao as V

RAIZ = Path(__file__).resolve().parent.parent
TIPOS_DE_TROCA = (E.NAO_TROCOU, E.POSSIVEL_BAIT, E.PERDEU_A_TROCA, E.MORREU_SOZINHO, E.PRIMEIRA_MORTE_SEM_TROCA)


def _mapa(m: str) -> str | None:
    meta = RAIZ / "data" / "processed" / m / "match_meta.json"
    return json.loads(meta.read_text(encoding="utf-8")).get("map_name") if meta.exists() else None


def _pula_sem_dado(m: str) -> None:
    if not (RAIZ / "data" / "interim" / m / "ticks.parquet").exists():
        pytest.skip(f"sem o interim de {m}")
    if not V.malha_disponivel(_mapa(m) or ""):
        pytest.skip(f"sem a malha de {_mapa(m)} (py -3.12 -m scripts.visao_malhas)")


@lru_cache(maxsize=None)
def _partida(m: str) -> E.Partida:
    return E.carrega_partida(m)


@lru_cache(maxsize=None)
def _ocorrencias(m: str) -> pl.DataFrame:
    return E.ocorrencias(_partida(m))


def _do(m: str, rn: int, nome: str, tipos=TIPOS_DE_TROCA) -> list[dict]:
    _pula_sem_dado(m)
    oc = _ocorrencias(m)
    return oc.filter((pl.col("round_num") == rn) & (pl.col("name") == nome) & pl.col("tipo").is_in(list(tipos))).to_dicts()


def test_bait_1_pain_match_03_round_20_nao_e_bait():
    """Colado no aliado (4 unidades) e à mesma distância do matador (318 e 318): nem era "atrás". Pela regra
    nova, só seria bait com o matador visível e o recuo sem engajar."""
    oc = [o for o in _do("match_03", 20, "PAiN-M-") if o["tick"] == 142858]
    bait = next(o for o in oc if o["tipo"] == E.POSSIVEL_BAIT)
    assert abs(bait["dist_matador_jogador"] - bait["dist_matador_aliado"]) < 1.0       # o empate de distância
    esperado = (bait["matador_visivel"] and E.visto_o_bastante(bait["seg_matador_visivel"])
                and not bait["atirou_no_matador"] and not bait["dano_no_matador"] and E.recuou_o_bastante(bait["recuo"]))
    assert (bait["filtro"] is None) == bool(esperado)
    assert bait["filtro"] is not None                    # o dado: o matador não ficou visível para ele


def test_bait_6_aleksib_match_37_round_17_4_contra_1_fica_fora():
    oc = [o for o in _do("match_37", 17, "Aleksib") if o["tipo"] in (E.NAO_TROCOU, E.POSSIVEL_BAIT)]
    assert oc and all(o["filtro"] in (E.FILTRO_ROUND_DECIDIDO, E.FILTRO_FIM_DO_ROUND) for o in oc)
    # o evento é antes do fim do round (o filtro do fim não estava quebrado): sai pelo round decidido
    rounds = pl.read_parquet(RAIZ / "data" / "processed" / "match_37" / "rounds.parquet")
    fim = rounds.filter(pl.col("round_num") == 17)["end"][0]
    assert all(o["tick"] < fim and o["filtro"] == E.FILTRO_ROUND_DECIDIDO for o in oc)
    assert all((o["vivos_time"], o["vivos_adversario"]) == (4, 1) and o["chance_vitoria"] > E.LIMIAR_ROUND_GANHO
               for o in oc)


@pytest.mark.parametrize("m, rn, nome", [("match_49", 11, "NiKo"), ("match_50", 11, "Brollan")])
def test_perdeu_a_troca_9_e_10_so_fica_se_engajou(m, rn, nome):
    """"Perdeu a troca" só existe se ele foi trocar (engajou o matador); senão vira "morreu sozinho" ou nada
    (se foi trocado). A distância (1.350 e 1.162 do aliado) é contexto."""
    oc = _do(m, rn, nome)
    perdeu = [o for o in oc if o["tipo"] == E.PERDEU_A_TROCA]
    assert perdeu
    for o in perdeu:
        engajou = o["atirou_no_matador"] or (o["dano_no_matador"] or 0) > 0
        if o["filtro"] is None:
            assert engajou and (o["inimigos_visiveis"] or 0) <= 1 and not o["trocada"]
        if o["trocada"]:
            # morte trocada: nada conta para a morte dele, em nenhum tipo
            da_morte = [x for x in oc if x["tick"] == o["tick"] and x["filtro"] is None
                        and x["tipo"] in (E.PERDEU_A_TROCA, E.MORREU_SOZINHO, E.PRIMEIRA_MORTE_SEM_TROCA)]
            assert da_morte == []


def test_perdeu_a_troca_9_niko_foi_trocado():
    o = next(x for x in _do("match_49", 11, "NiKo") if x["tipo"] == E.PERDEU_A_TROCA)
    assert o["atirou_no_matador"] and o["trocada"] and o["filtro"] == E.FILTRO_MORTE_TROCADA


def test_perdeu_a_troca_10_brollan_fica():
    o = next(x for x in _do("match_50", 11, "Brollan") if x["tipo"] == E.PERDEU_A_TROCA)
    assert o["filtro"] is None and o["dano_no_matador"] > 0 and o["inimigos_visiveis"] == 1


def test_perdeu_a_troca_5_sh1ro_match_28_round_18_1_contra_4_fica_fora():
    oc = [o for o in _do("match_28", 18, "sh1ro") if o["tipo"] == E.PERDEU_A_TROCA]
    assert oc and all(o["filtro"] is not None for o in oc)
    assert all(o["inimigos_visiveis"] >= 2 for o in oc)             # dois ou mais visíveis ao mesmo tempo


# flash e dano no time aos 0:08–0:17 que saíam "0 contra 0" (seção 7.2: flash nº 2, 3, 5, 7, 9, 10; dano nº 2, 3,
# 5, 6, 7, 9, 10). Uma amostra deles, com a partida, o round, o jogador e o tempo desde o fim do freeze.
ZERO_A_ZERO = [
    ("match_09", 17, "Magnojezzz", 8.81, E.FLASH_NO_TIME), ("match_31", 3, "molodoy", 12.53, E.FLASH_NO_TIME),
    ("match_37", 21, "chopper", 8.22, E.FLASH_NO_TIME), ("match_42", 36, "torzsi", 9.91, E.FLASH_NO_TIME),
    ("match_50", 9, "NiKo", 17.34, E.FLASH_NO_TIME), ("match_20", 25, "FalleN", 10.33, E.DANO_DE_UTILIDADE_NO_TIME),
    ("match_39", 18, "magixx", 9.61, E.DANO_DE_UTILIDADE_NO_TIME),
    ("match_50", 10, "Brollan", 25.45, E.DANO_DE_UTILIDADE_NO_TIME),
]


@pytest.mark.parametrize("m, rn, nome, seg, tipo", ZERO_A_ZERO)
def test_a_situacao_da_flash_e_do_dano_no_inicio_do_round_nao_e_0_contra_0(m, rn, nome, seg, tipo):
    _pula_sem_dado(m)
    p = _partida(m)
    fn = E.flash_no_time if tipo == E.FLASH_NO_TIME else E.dano_de_utilidade_no_time
    oc = [o for o in fn(p) if o["round_num"] == rn and o["name"] == nome and abs(o["segundos"] - seg) < 0.05]
    assert len(oc) == 1
    assert oc[0]["vivos_time"] > 0 and oc[0]["vivos_adversario"] > 0
    assert oc[0]["vivos_time"] + oc[0]["vivos_adversario"] >= 8      # no início do round quase todos vivos
