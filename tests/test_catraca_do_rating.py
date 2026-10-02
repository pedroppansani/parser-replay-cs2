"""Catraca do rating contra a HLTV: o portão de toda mudança no rating.

Os testes que existiam só olhavam a MÉDIA do rating (que o intercepto garante
por construção): um bug que embaralhasse a ordem dos jogadores passava. Este
recalcula, a partir do que é versionado, o erro médio e a correlação contra o
rating oficial e o KAST idêntico ao oficial, e falha se piorarem.

Os patamares são o MELHOR valor medido; quando um item melhora o número, o
patamar sobe junto (só pode melhorar). A folga absorve o arredondamento do
rating em duas casas na página, não mudança de modelo.

Mesmo padrão das catracas dos arremessos (tests/test_rotina_arremesso.py).
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from scripts.impacto_rating import contra_a_hltv, insights

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
REFERENCIA = RAIZ / "data" / "reference"

# Patamares medidos em 2026-10-02 (430 jogador-partidas de 43 mapas profissionais;
# rating da página, dentro da amostra). `py -3.12 -m scripts.impacto_rating` refaz.
CATRACA_ERRO_MEDIO = 0.0770
CATRACA_CORRELACAO = 0.9674
CATRACA_KAST_EXATOS = 247
JOGADOR_PARTIDAS = 430
KAST_COM_OFICIAL = 330
# Folgas: meio ponto na terceira casa do erro e na da correlação (o rating da
# página tem duas casas, e a média de 430 arredondamentos oscila nessa ordem).
FOLGA_ERRO = 0.0005
FOLGA_CORRELACAO = 0.0005
# nomes que a HLTV escreve diferente da demo (os mesmos de scripts/escada_validacao)
APELIDOS = {"sh1ro": "SH1R0", "mzinho": "Mzinho", "Techno": "Techno4K"}


@pytest.fixture(scope="module")
def medido():
    ins = insights(None)
    if len(ins) < 40:
        pytest.skip("sem data/processed/")
    return contra_a_hltv(ins)


def test_o_gabarito_do_rating_nao_encolheu(medido):
    assert medido["n"] == JOGADOR_PARTIDAS


def test_o_erro_medio_contra_a_hltv_nao_piora(medido):
    assert medido["erro_medio"] <= CATRACA_ERRO_MEDIO + FOLGA_ERRO, (
        f"erro médio {medido['erro_medio']:.4f} contra o patamar {CATRACA_ERRO_MEDIO}")


def test_a_correlacao_com_a_hltv_nao_piora(medido):
    assert medido["correlacao"] >= CATRACA_CORRELACAO - FOLGA_CORRELACAO, (
        f"correlação {medido['correlacao']:.4f} contra o patamar {CATRACA_CORRELACAO}")


def test_a_ordem_dos_jogadores_dentro_da_partida_acompanha_a_oficial():
    """O controle direto do que a média não vê: em cada partida, quem a HLTV põe
    acima tem de estar acima aqui (correlação de postos por partida)."""
    from scipy.stats import spearmanr
    oficial = json.loads((REFERENCIA / "hltv_ratings.json").read_text(encoding="utf-8"))["partidas"]
    ins = insights(None)
    rhos = []
    for partida, o in oficial.items():
        if not o.get("usar_na_calibracao") or partida not in ins:
            continue
        nosso = {p["name"]: p.get("rating") for p in ins[partida]["players"]}
        pares = [(nosso[n], r) for n, r in (o.get("jogadores") or {}).items() if r is not None and nosso.get(n) is not None]
        if len(pares) >= 8:
            rhos.append(spearmanr([a for a, _ in pares], [b for _, b in pares]).correlation)
    assert len(rhos) >= 40
    assert min(rhos) > 0.6, f"pior partida com correlação de postos {min(rhos):.2f}"
    assert sum(rhos) / len(rhos) > 0.9, sum(rhos) / len(rhos)


def test_o_kast_identico_ao_oficial_nao_cai():
    comp = json.loads((REFERENCIA / "hltv_componentes.json").read_text(encoding="utf-8"))["partidas"]
    ao_contrario = {b: a for a, b in APELIDOS.items()}
    exatos = com_oficial = 0
    for partida, v in comp.items():
        arq = PROCESSED / partida / "kast_summary.parquet"
        if not arq.exists():
            continue
        nosso = dict(pl.read_parquet(arq).select("name", "kast_rounds").iter_rows())
        for nome, o in v["jogadores"].items():
            if o.get("kast_rounds") is None:
                continue
            meu = nosso.get(nome, nosso.get(APELIDOS.get(nome, ""), nosso.get(ao_contrario.get(nome, ""))))
            if meu is None:
                continue
            com_oficial += 1
            exatos += int(meu == o["kast_rounds"])
    assert com_oficial == KAST_COM_OFICIAL, com_oficial
    assert exatos >= CATRACA_KAST_EXATOS, f"KAST idêntico caiu para {exatos} de {com_oficial}"


def test_controle_embaralhar_os_jogadores_derruba_a_catraca():
    """Se a catraca passasse com os ratings trocados entre os jogadores de cada
    partida, ela não estaria medindo nada -- era o que os testes antigos deixavam
    passar (a média não muda)."""
    import copy
    ins = copy.deepcopy(insights(None))
    for d in ins.values():
        r = [p.get("rating") for p in d["players"]]
        for p, novo in zip(d["players"], r[1:] + r[:1]):      # roda os ratings de um jogador
            p["rating"] = novo
    trocado = contra_a_hltv(ins)
    original = contra_a_hltv(insights(None))
    assert abs(trocado["media_nossa"] - original["media_nossa"]) < 1e-9   # a média não vê a troca
    assert trocado["erro_medio"] > CATRACA_ERRO_MEDIO + 0.1
    assert trocado["correlacao"] < CATRACA_CORRELACAO - 0.3
