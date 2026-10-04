"""Rota B (decisão 21a): a verdade do arremesso gravada na demo.

Três camadas:
- a LIGAÇÃO da força à granada que saiu, com dados sintéticos no formato do
  `parse_grenades` (roda sempre);
- a leitura no interim das 13 partidas com demo: os 4 casos desta rodada, o
  gabarito inteiro e lido x inferido -- o teste permanente da rota A (pulados
  sem `data/interim/`);
- o que protege o interim e a versão: o complemento não sobrescreve, a versão
  do parser é lida do interim, a fusão de partes desloca o último pulo.
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path

import polars as pl
import pytest

from parsing import verdade_do_arremesso as va

RAIZ = Path(__file__).resolve().parent.parent
INTERIM = RAIZ / "data" / "interim"
FIXTURES = RAIZ / "tests" / "fixtures"

# as mesmas metas dos testes da rota A no gabarito (test_rotina_arremesso)
from tests.test_rotina_arremesso import META, META_POSTURA  # noqa: E402

# Os 4 arremessos em que ler a força NO tick da soltura dava 0 (a entidade já
# era a próxima granada): a força lida tem de ser a do arremesso.
CASOS_DA_RODADA = {"match_16:19:147": 0.5, "match_20:27:255": 1.0,
                   "match_41:21:172": 1.0, "match_42:4:375": 1.0}

# Catraca da origem inferida (primeiro ponto do projétil recuado um tick de
# voo) contra m_vInitialPosition, nas 13 partidas: mediana 0,081-0,086 u e p99
# 0,120-0,124 u por partida (2026-09-28). Só pode melhorar.
CATRACA_ORIGEM_MEDIANA = 0.09
CATRACA_ORIGEM_P99 = 0.13


# ---------------------------------------------------------------------------
# A ligação, com dados sintéticos
# ---------------------------------------------------------------------------

def _linha(tick, ent, sid, tipo, forca=None, v0=None, p0=None, pulo=False):
    return {"tick": tick, "grenade_entity_id": ent, "steamid": sid, "grenade_type": tipo,
            "Grenade.m_flThrowStrength": forca, "Grenade.m_bJumpThrow": pulo if forca is not None else None,
            "Grenade.m_vInitialVelocity": v0, "Grenade.m_vInitialPosition": p0}


def _proj(tick, ent, sid, tipo, n=3):
    return [_linha(tick + k, ent, sid, tipo, v0=[1.0, 2.0, 3.0], p0=[10.0, 20.0, 30.0]) for k in range(n)]


def _g(linhas):
    esquema = {"tick": pl.Int32, "grenade_entity_id": pl.Int32, "steamid": pl.UInt64, "grenade_type": pl.Utf8,
               "Grenade.m_flThrowStrength": pl.Float32, "Grenade.m_bJumpThrow": pl.Boolean,
               "Grenade.m_vInitialVelocity": pl.List(pl.Float32), "Grenade.m_vInitialPosition": pl.List(pl.Float32)}
    return pl.DataFrame(linhas, schema=esquema)


def _por_projetil(tabela):
    return {r["entity_id"]: r for r in tabela.iter_rows(named=True)}


def test_forca_e_da_granada_que_saiu_nao_da_proxima():
    """O caso desta rodada: em t a entidade da arma já é a próxima granada,
    com força 0. Lida em t-1, a força é a do arremesso."""
    linhas = [_linha(t, 193, 7, "CHEGrenade", 0.5) for t in range(95, 100)]
    linhas += [_linha(t, 350, 7, "CHEGrenade", 0.0) for t in range(100, 104)]
    linhas += _proj(100, 147, 7, "CHEGrenadeProjectile")
    tab, cont = va.tabela_de_arremessos(_g(linhas))
    r = _por_projetil(tab)[147]
    assert r["forca"] == 0.5 and r["ligacao"] == "t-1" and r["entidade_arma"] == 193
    assert cont["t-1"] == 1 and r["tick"] == 100 and (r["v0_x"], r["p0_z"]) == (1.0, 30.0)


def test_duas_candidatas_desempata_pela_arma_consumida():
    """Duas granadas do tipo no tick anterior: vale a que deixa de existir."""
    linhas = [_linha(t, 10, 7, "CFlashbang", 1.0) for t in range(95, 100)]          # sai da mão
    linhas += [_linha(t, 11, 7, "CFlashbang", 0.0) for t in range(95, 104)]         # continua
    linhas += _proj(100, 90, 7, "CFlashbangProjectile")
    r = _por_projetil(va.tabela_de_arremessos(_g(linhas))[0])[90]
    assert r["forca"] == 1.0 and r["ligacao"] == "arma_consumida" and r["entidade_arma"] == 10


def test_duas_candidatas_que_continuam_vivas_ficam_ambiguas():
    linhas = [_linha(t, 10, 7, "CFlashbang", 1.0) for t in range(95, 104)]
    linhas += [_linha(t, 11, 7, "CFlashbang", 0.0) for t in range(95, 104)]
    linhas += _proj(100, 90, 7, "CFlashbangProjectile")
    r = _por_projetil(va.tabela_de_arremessos(_g(linhas))[0])[90]
    assert r["forca"] is None and r["ligacao"] == "ambigua"


def test_demo_que_pula_tick_le_no_ultimo_tick_gravado():
    """Sem linha nenhuma em t-1 (a demo pulou o tick), o anterior é o último
    GRAVADO -- declarado como tal."""
    linhas = [_linha(t, 20, 7, "CSmokeGrenade", 1.0) for t in (95, 96, 97, 98)]
    linhas += [_linha(t, 21, 7, "CSmokeGrenade", 0.0) for t in (100, 101)]
    linhas += _proj(100, 91, 7, "CSmokeGrenadeProjectile")
    r = _por_projetil(va.tabela_de_arremessos(_g(linhas))[0])[91]
    assert r["forca"] == 1.0 and r["ligacao"] == "tick_anterior"


def test_sem_arma_do_tipo_a_forca_fica_nula_e_declarada():
    linhas = [_linha(t, 30, 7, "CSmokeGrenade", 1.0) for t in range(95, 104)]    # outro tipo
    linhas += _proj(100, 92, 7, "CMolotovProjectile")
    r = _por_projetil(va.tabela_de_arremessos(_g(linhas))[0])[92]
    assert r["forca"] is None and r["ligacao"] == "sem_arma"


def test_incendiaria_vira_o_mesmo_projetil_da_molotov():
    linhas = [_linha(t, 40, 7, "CIncendiaryGrenade", 0.5) for t in range(95, 100)]
    linhas += _proj(100, 93, 7, "CMolotovProjectile")
    r = _por_projetil(va.tabela_de_arremessos(_g(linhas))[0])[93]
    assert r["forca"] == 0.5 and r["ligacao"] == "t-1"


def test_id_de_projetil_reaproveitado_vira_dois_arremessos():
    linhas = [_linha(t, 50, 7, "CHEGrenade", 1.0) for t in range(95, 100)]
    linhas += [_linha(t, 51, 7, "CHEGrenade", 0.0) for t in range(295, 300)]
    linhas += _proj(100, 94, 7, "CHEGrenadeProjectile") + _proj(300, 94, 7, "CHEGrenadeProjectile")
    tab, _ = va.tabela_de_arremessos(_g(linhas))
    assert tab.filter(pl.col("entity_id") == 94)["tick"].to_list() == [100, 300]
    assert tab.filter(pl.col("entity_id") == 94)["forca"].to_list() == [1.0, 0.0]


def test_botao_e_postura_lidos():
    from metrics.grenade_throws import botao_da_forca_lida, postura_lida
    assert [botao_da_forca_lida(x) for x in (0.0, 0.2031, 0.4797, 0.5203, 0.6141, 1.0)] == [0.0, 0.0, 0.5, 0.5, 0.5, 1.0]
    assert botao_da_forca_lida(None) is None
    assert postura_lida(True, 1.0) == "agachado"
    assert postura_lida(False, 0.0) == "em pé"
    assert postura_lida(False, 0.4) is None           # agachamento parcial não é afirmado
    assert postura_lida(None, None) is None


# ---------------------------------------------------------------------------
# No interim das partidas com demo
# ---------------------------------------------------------------------------

def _gabaritos() -> dict[str, dict]:
    out = {}
    for f in sorted(FIXTURES.glob("gabarito_arremessos_*.json.gz")):
        d = json.loads(gzip.decompress(f.read_bytes()).decode("utf-8"))
        out[d["partida"]] = d
    return out


def _lidos(partida: str) -> pl.DataFrame:
    arq = INTERIM / partida / "arremessos_demo.parquet"
    if not arq.exists():
        pytest.skip(f"{partida} sem as tabelas da rota B no interim")
    return pl.read_parquet(arq)


def test_os_4_casos_da_rodada_leem_a_forca_do_arremesso_e_nao_0():
    gab = _gabaritos()
    for ident, esperado in CASOS_DA_RODADA.items():
        partida, rnd, ent = ident.split(":")
        # o id de entidade se repete no mesmo round (match_16, round 19, tem
        # dois projéteis 147): o tick da soltura do gabarito desfaz
        (a,) = [x for x in gab[partida]["arremessos"] if x["id"] == ident]
        r = _lidos(partida).filter((pl.col("round_num") == int(rnd)) & (pl.col("entity_id") == int(ent))
                                   & (pl.col("tick") == a["entrada"]["tick_soltura"]))
        assert r.height == 1, ident
        assert r["forca"][0] == esperado and r["forca"][0] != 0, (ident, r["forca"][0])
        assert r["ligacao"][0] == "t-1", ident


def test_a_leitura_do_parser_bate_com_o_gabarito_inteiro():
    """Força, velocidade e ponto de nascimento lidos pelo parser de produção
    contra o gabarito versionado, arremesso a arremesso, nas 13 partidas."""
    gab = _gabaritos()
    assert len(gab) == 13
    for partida, d in gab.items():
        lidos = {(r["entity_id"], r["tick"]): r for r in _lidos(partida).iter_rows(named=True)}
        for a in d["arremessos"]:
            ent = int(a["id"].split(":")[2])
            r = lidos.get((ent, int(a["entrada"]["tick_soltura"])))
            assert r is not None, a["id"]
            assert abs(r["forca"] - a["demo"]["forca"]) < 1e-4, (a["id"], r["forca"], a["demo"]["forca"])
            assert max(abs(r[f"v0_{e}"] - v) for e, v in zip("xyz", a["demo"]["v0"])) < 0.01, a["id"]
            if a["demo"].get("p0") is not None:
                assert max(abs(r[f"p0_{e}"] - v) for e, v in zip("xyz", a["demo"]["p0"])) < 0.01, a["id"]


@pytest.fixture(scope="module")
def comparacoes():
    from metrics.verdade_do_arremesso import compara, partidas_com_verdade
    if not INTERIM.exists():
        pytest.skip("sem data/interim/")
    partidas = partidas_com_verdade()
    if not partidas:
        pytest.skip("nenhuma partida com as tabelas da rota B")
    return {p: compara(p) for p in partidas}


def test_as_13_partidas_do_gabarito_tem_a_verdade_da_demo(comparacoes):
    assert set(_gabaritos()) <= set(comparacoes)


def test_lido_e_inferido_concordam_nas_taxas_da_rota_a(comparacoes):
    """O teste PERMANENTE da rota A: o inferido é calculado com as tabelas
    novas retiradas de propósito, e tem de concordar com o lido nas mesmas
    metas dos testes da rota A no gabarito. Neutro do inferido não conta
    como discordância (neutro não afirma)."""
    for partida, r in comparacoes.items():
        for campo, meta in (("botao", META), ("no_ar", META), ("postura", META_POSTURA)):
            c = r[campo]
            assert c["n"] > 0, (partida, campo)
            assert c["iguais"] / c["n"] >= meta, (partida, campo, f"{c['iguais']}/{c['n']}", c["diferentes"])


def test_cada_arremesso_declara_a_fonte_e_a_demo_vence(comparacoes):
    for partida, r in comparacoes.items():
        f = r["fonte_lida"]
        # com a verdade da demo, quase tudo sai lido (o que falta é projétil
        # sem arma ligada ou jogador sem linha de movimento, declarado)
        assert f["fonte_do_botao"] >= 0.95 * r["arremessos"], (partida, f)
        assert f["fonte_da_postura"] >= 0.95 * r["arremessos"], (partida, f)


def test_catraca_da_origem_inferida(comparacoes):
    for partida, r in comparacoes.items():
        o = r["origem"]
        assert o["n"] > 0, partida
        assert o["mediana"] <= CATRACA_ORIGEM_MEDIANA, (partida, o)
        assert o["p99"] <= CATRACA_ORIGEM_P99, (partida, o)


def test_sem_as_tabelas_tudo_sai_inferido():
    """Partida sem .dem (a maioria do corpus): fonte inferida em todo campo."""
    from metrics.grenade_throws import grenade_throws
    from parsing.parser import TABELAS_DA_VERDADE, load_interim
    if not (INTERIM / "match_23" / "arremessos_demo.parquet").exists():
        pytest.skip("sem o interim da match_23")
    t = load_interim(INTERIM, "match_23")
    t["rounds"] = pl.read_parquet(RAIZ / "data" / "processed" / "match_23" / "rounds.parquet")
    pr, _ = grenade_throws({k: v for k, v in t.items() if k not in TABELAS_DA_VERDADE}, 64)
    for c in ("fonte_do_botao", "fonte_da_postura", "fonte_do_no_ar"):
        assert set(pr[c].drop_nulls().unique().to_list()) == {"inferido"}, c
    assert pr["forca_lida"].null_count() == pr.height


# ---------------------------------------------------------------------------
# Interim e versão
# ---------------------------------------------------------------------------

def test_complemento_nunca_sobrescreve(tmp_path, monkeypatch):
    import scripts.complementa_interim as ci
    (tmp_path / "match_x").mkdir()
    (tmp_path / "match_x" / "movimento.parquet").write_bytes(b"existente")
    monkeypatch.setattr(ci, "INTERIM", tmp_path)
    with pytest.raises(SystemExit, match="não sobrescreve"):
        ci.complementa("match_x")
    assert (tmp_path / "match_x" / "movimento.parquet").read_bytes() == b"existente"


def test_versao_do_parser_e_lida_do_interim(tmp_path):
    from parsing.versao import ARQUIVO_DO_COMPLEMENTO, versao_do_parser_do_interim, versoes
    assert versao_do_parser_do_interim(tmp_path) is None             # interim antigo, sem registro
    (tmp_path / "header.json").write_text(json.dumps({"map_name": "de_x"}), encoding="utf-8")
    assert versao_do_parser_do_interim(tmp_path) is None
    (tmp_path / "header.json").write_text(json.dumps({"versao_do_parser": 2}), encoding="utf-8")
    assert versao_do_parser_do_interim(tmp_path) == 2
    (tmp_path / ARQUIVO_DO_COMPLEMENTO).write_text(json.dumps({"versao_do_parser": 3}), encoding="utf-8")
    assert versao_do_parser_do_interim(tmp_path) == 3                # o complemento vence
    assert versoes(parser=1)["parser"] == 1


def test_fusao_de_partes_desloca_o_tick_do_ultimo_pulo(tmp_path):
    from parsing.parser import merge_interim
    for k, (ticks, pulo) in enumerate((([1, 2, 10], [None, 1.5, 9.0]), ([1, 5], [None, 3.0])), start=1):
        d = tmp_path / f"p{k}"
        d.mkdir()
        pl.DataFrame({"tick": ticks, "steamid": [7] * len(ticks), "tick_do_ultimo_pulo": pulo},
                     schema={"tick": pl.Int32, "steamid": pl.UInt64, "tick_do_ultimo_pulo": pl.Float64}
                     ).write_parquet(d / "movimento.parquet")
        (d / "header.json").write_text("{}", encoding="utf-8")
    merge_interim(tmp_path, ["p1", "p2"], "junta")
    m = pl.read_parquet(tmp_path / "junta" / "movimento.parquet")
    assert m["tick"].to_list() == [1, 2, 10, 12, 16]                  # parte 2 depois de 10 + 1
    assert m["tick_do_ultimo_pulo"].to_list() == [None, 1.5, 9.0, None, 14.0]


def test_movimento_grava_com_o_tick_em_delta_e_le_igual(tmp_path):
    import pyarrow.parquet as pq
    df = pl.DataFrame({"tick": list(range(100)) * 1, "steamid": [7] * 100, "duck_amount": [0.0] * 100},
                      schema={"tick": pl.Int32, "steamid": pl.UInt64, "duck_amount": pl.Float32})
    va.grava_movimento(df, tmp_path / "m.parquet")
    assert pl.read_parquet(tmp_path / "m.parquet").equals(df)
    assert "DELTA_BINARY_PACKED" in pq.ParquetFile(tmp_path / "m.parquet").metadata.row_group(0).column(0).encodings
