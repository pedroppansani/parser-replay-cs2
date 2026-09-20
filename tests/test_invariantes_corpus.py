"""
Invariantes sobre o CORPUS INTEIRO: o que nunca pode acontecer em partida
nenhuma, por mais demos que entrem.

É barato e pega regressão em coisa que ninguém está olhando. Cada invariante
aqui corresponde a um bug que já aconteceu ou que aconteceria em silêncio:

- tempo negativo no timeline (decisão 8a) -- aconteceu, com morte no freeze time;
- atacante igual à vítima (decisão 8c) -- o demo preenche assim em morte por
  queda e bomba, e virava "+1 kill por se matar";
- KAST fora de 0-100 e nulo propagado -- não aconteceu, e é justamente o tipo de
  coisa que passa despercebida;
- warmup dentro das métricas (decisão 8b);
- média do rating longe da OFICIAL -- aconteceu depois de mexer no Round Swing;
- probabilidade de vitória que não vai de 0,5 ao resultado (decisão 19);
- IDENTIDADE: o jogador é o steamid, e nome é rótulo (metrics/identidade.py).

Os testes leem `data/processed/`, que é versionado. Sem ele, são pulados.
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
REFERENCIA = RAIZ / "data" / "reference"

# Distância máxima entre a NOSSA média e a média OFICIAL dos mesmos
# jogador-partidas. Não é folga para erro de escala: medido em 2026-09-20, a
# diferença é 0,0006 (nosso 1,0720 contra 1,0726 da HLTV em 430
# jogador-partidas). 0,02 dá margem para recalibração sem deixar passar um
# deslocamento de escala -- 1,105 já apareceu e era bug.
TOLERANCIA_MEDIA_RATING = 0.02


def _partidas() -> list[Path]:
    return sorted(d for d in PROCESSED.glob("match_*") if (d / "insights.json").exists())


def _pula_sem_corpus():
    if not _partidas():
        pytest.skip("sem data/processed")


@pytest.fixture(scope="module")
def partidas():
    _pula_sem_corpus()
    return _partidas()


def _concat(nome: str) -> pl.DataFrame:
    partes = [pl.read_parquet(d / f"{nome}.parquet").with_columns(pl.lit(d.name).alias("match_id"))
              for d in _partidas() if (d / f"{nome}.parquet").exists()]
    return pl.concat(partes, how="diagonal_relaxed") if partes else pl.DataFrame()


# --- Tempo e eventos --------------------------------------------------------

def test_nenhum_tempo_de_timeline_negativo(partidas):
    """A origem do tempo é o fim do freeze time (decisão 8a): antes disso o
    evento não pertence ao round."""
    ruins = []
    for d in partidas:
        bd = json.loads((d / "breakdown.json").read_text(encoding="utf-8"))
        for r in bd:
            for e in r.get("eventos", []) or []:
                if e.get("t") is not None and float(e["t"]) < 0:
                    ruins.append((d.name, r.get("round"), e.get("t")))
    assert not ruins, ruins[:5]


def test_nenhum_evento_com_atacante_igual_a_vitima(partidas):
    """O demo preenche o atacante com a própria vítima em morte por queda ou
    bomba; o projeto trata isso como "sem atacante" (decisão 8c)."""
    ruins = []
    for d in partidas:
        for arquivo, a, v in (("kast_per_round", None, None),):
            pass
        r = d / "replay.json"
        if not r.exists():
            continue
        dados = json.loads(r.read_text(encoding="utf-8"))
        for k in dados.get("kills", []) or []:
            if k.get("attacker_steamid") is not None and k.get("attacker_steamid") == k.get("victim_steamid"):
                ruins.append((d.name, k.get("round"), k.get("attacker_steamid")))
    assert not ruins, ruins[:5]


def test_nenhum_round_de_warmup_nas_metricas(partidas):
    """Round numerado a partir de 1 e sem buraco: warmup e round de faca já
    saíram no parsing (decisões 8b e 8f)."""
    ruins = []
    for d in partidas:
        rounds = pl.read_parquet(d / "rounds.parquet")["round_num"].to_list()
        if rounds != list(range(1, len(rounds) + 1)):
            ruins.append((d.name, rounds[:5], len(rounds)))
    assert not ruins, ruins


# --- Métricas ---------------------------------------------------------------

def test_kast_entre_zero_e_cem_sem_nulo(partidas):
    k = _concat("kast_summary")
    assert k.height, "sem KAST no corpus"
    assert k["kast_pct"].null_count() == 0
    fora = k.filter((pl.col("kast_pct") < 0) | (pl.col("kast_pct") > 100))
    assert fora.height == 0, fora.head()


def test_nenhuma_metrica_final_com_nulo_onde_nao_pode(partidas):
    """Colunas que são contagem ou taxa do jogador: nulo ali é métrica que não
    rodou, e o número sai plausível do mesmo jeito."""
    obrigatorias = {
        "adr_summary": ["adr", "total_damage", "rounds_played"],
        "kast_summary": ["kast_rounds", "rounds_played"],
        "player_roles": ["adr", "kast_pct", "first_contact_share", "awp_share"],
        "archetypes_summary": ["rounds_played", "sacrifice_index", "idx_carry"],
    }
    ruins = []
    for tabela, colunas in obrigatorias.items():
        df = _concat(tabela)
        for c in colunas:
            if c in df.columns and df[c].null_count():
                ruins.append((tabela, c, df[c].null_count()))
    assert not ruins, ruins


def test_media_do_rating_acompanha_a_media_oficial(partidas):
    """A âncora é a média OFICIAL dos mesmos jogador-partidas, não o 1,00.

    O invariante anterior exigia média 1,00 no corpus e falhava em 1,081 -- mas
    o errado era ele: o corpus não é uma amostra neutra de jogadores. São
    partidas de times de topo, e a HLTV dá 1,0726 a esses mesmos 430
    jogador-partidas (as 9 de FACEIT, que não têm rating oficial, sobem a média
    do corpus inteiro para 1,081 porque são pugs com o donk). Exigir 1,00 aqui
    seria pedir que a nossa escala DISCORDASSE da oficial.

    O que continua travado é o que importa: um deslocamento de escala nosso --
    referência refeita sem refazer os pesos, sub-rating fora de escala -- move
    esta diferença na hora.
    """
    oficiais_por_partida = json.loads(
        (REFERENCIA / "hltv_ratings.json").read_text(encoding="utf-8"))["partidas"]
    nossos, oficiais = [], []
    for d in partidas:
        info = oficiais_por_partida.get(d.name)
        if not info or not any(v is not None for v in info["jogadores"].values()):
            continue  # FACEIT: a HLTV não publica rating, não dá para comparar
        ins = json.loads((d / "insights.json").read_text(encoding="utf-8"))
        por_nome = {j["name"]: j.get("rating") for j in ins.get("players", [])}
        for nome, oficial in info["jogadores"].items():
            nosso = por_nome.get(nome)
            if nosso is not None and oficial is not None:
                nossos.append(nosso)
                oficiais.append(oficial)
    assert len(nossos) >= 400, f"gabarito de rating encolheu: {len(nossos)} jogador-partidas"
    media_nossa = sum(nossos) / len(nossos)
    media_oficial = sum(oficiais) / len(oficiais)
    assert abs(media_nossa - media_oficial) <= TOLERANCIA_MEDIA_RATING, (
        f"nossa média {media_nossa:.4f} contra {media_oficial:.4f} oficial "
        f"em {len(nossos)} jogador-partidas")


def test_probabilidade_de_vitoria_vai_de_meio_ao_resultado(partidas):
    """A curva começa em 0,5 (round isolado é neutro, decisão 19) e termina em
    1,0 para quem venceu a partida."""
    ruins = []
    for d in partidas:
        ins = json.loads((d / "insights.json").read_text(encoding="utf-8"))
        curva = (ins.get("win_probability") or {}).get("curve") or []
        if not curva:
            continue
        if abs(float(curva[0]["wp_a_antes"]) - 0.5) > 1e-6:
            ruins.append((d.name, "começo", curva[0]["wp_a_antes"]))
        fim = float(curva[-1]["wp_a_depois"])
        venceu_a = ins["match"]["score_a"] > ins["match"]["score_b"]
        if abs(fim - (1.0 if venceu_a else 0.0)) > 1e-6:
            ruins.append((d.name, "fim", fim, venceu_a))
    assert not ruins, ruins[:5]


# --- Identidade: o jogador é o steamid --------------------------------------

def _nicks_conhecidos() -> dict:
    arq = REFERENCIA / "nicks_conhecidos.json"
    return json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else {"varios_nicks": {}, "nomes_compartilhados": {}}


def test_cada_partida_tem_dez_steamids_distintos(partidas):
    ruins = []
    for d in partidas:
        ids = pl.read_parquet(d / "player_roles.parquet")["steamid"]
        if ids.n_unique() != 10 or ids.len() != 10:
            ruins.append((d.name, ids.len(), ids.n_unique()))
    assert not ruins, ruins


def test_steamid_com_mais_de_um_nick_precisa_estar_registrado(partidas):
    """Trocar de nick é normal; o que não pode é passar despercebido, porque
    todo relatório entre partidas depende de saber que é a mesma pessoa."""
    conhecidos = _nicks_conhecidos()["varios_nicks"]
    c = _concat("player_roles").select("steamid", "name")
    varios = (c.unique().group_by("steamid").agg(pl.col("name").unique().alias("nicks"))
              .filter(pl.col("nicks").list.len() > 1))
    novos = [(sid, nicks) for sid, nicks in varios.iter_rows() if str(sid) not in conhecidos]
    assert not novos, f"steamid com nicks novos (registre em data/reference/nicks_conhecidos.json): {novos}"


def test_nome_em_dois_steamids_precisa_estar_registrado(partidas):
    """O risco INVERSO, e o pior: dois jogadores diferentes com o mesmo nome de
    exibição não aparecem como duplicata -- aparecem como um jogador com
    estatística estranha. Qualquer agrupamento por nome os funde em silêncio."""
    conhecidos = _nicks_conhecidos().get("nomes_compartilhados", {})
    c = _concat("player_roles").select("steamid", "name")
    repetidos = (c.unique().group_by("name").agg(pl.col("steamid").unique().alias("ids"))
                 .filter(pl.col("ids").list.len() > 1))
    novos = [(nome, ids) for nome, ids in repetidos.iter_rows() if nome not in conhecidos]
    assert not novos, f"nome de exibição em mais de um steamid: {novos}"
