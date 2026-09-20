"""
Versão do código que produziu cada partida (parsing/versao.py) e o relatório do
que está velho (scripts/manifest.py).

O que estes testes protegem: o relatório de versões só serve se ele estiver
CERTO quando a versão subir -- e isso não dá para conferir no dia a dia, porque
hoje todas as partidas estão na mesma versão. Aqui a subida de versão é
simulada.
"""
from __future__ import annotations

import pytest

from parsing import versao as v
from scripts import manifest


def _linha(versao_registrada: dict | None, demo_existe: bool) -> dict:
    """Uma linha de manifesto com só o que o relatório olha."""
    return {"versao": versao_registrada, "demos": [{"existe": demo_existe}]}


def _manifesto(partidas: dict) -> dict:
    return {"partidas": partidas}


# --- situacao ---------------------------------------------------------------

def test_partida_sem_versao_registrada_e_desconhecida_e_nao_velha():
    """"Não sei" não é "está velho".

    Se as duas virassem a mesma coisa, o relatório mandaria reprocessar o corpus
    inteiro por precaução -- o que é o mesmo que não relatar nada.
    """
    s = v.situacao(None)
    assert s["desconhecida"] is True
    assert "antes de o projeto registrar" in s["motivo"]


def test_partida_na_versao_de_agora_esta_em_dia():
    s = v.situacao(v.versoes())
    assert s == {"parser_velho": False, "metricas_velhas": False,
                 "desconhecida": False, "motivo": None}


def test_versao_velha_diz_qual_subiu_e_de_quanto_para_quanto():
    """O motivo é lido por gente que vai decidir se reprocessa; "desatualizada"
    sozinho não ajuda a decidir nada."""
    registrado = {**v.versoes(), "parser": v.VERSAO_DO_PARSER - 1}
    s = v.situacao(registrado)
    assert s["parser_velho"] is True and s["metricas_velhas"] is False
    assert f"parser {v.VERSAO_DO_PARSER - 1} -> {v.VERSAO_DO_PARSER}" in s["motivo"]

    registrado = {**v.versoes(), "metricas": v.VERSAO_DAS_METRICAS - 1}
    s = v.situacao(registrado)
    assert s["metricas_velhas"] is True and s["parser_velho"] is False
    assert "métricas" in s["motivo"]


def test_versoes_traz_o_commit_para_nao_depender_de_memoria():
    """A versão declarada à mão não pega quem esqueceu de subi-la; o commit sim."""
    x = v.versoes()
    assert x["parser"] == v.VERSAO_DO_PARSER
    assert x["metricas"] == v.VERSAO_DAS_METRICAS
    assert set(x) >= {"parser", "metricas", "commit", "sujo", "awpy", "demoparser2"}


# --- o relatório ------------------------------------------------------------

def test_metrica_velha_com_demo_apagada_ainda_da_para_refazer():
    """Mudança só de métrica se refaz com --from-interim: não precisa da demo.

    Este é o caso comum do projeto (as demos são apagadas depois do
    processamento), e tratá-lo como perdido assustaria à toa.
    """
    m = _manifesto({"match_01": _linha({**v.versoes(), "metricas": v.VERSAO_DAS_METRICAS - 1}, False)})
    d = manifest.desatualizadas(m)
    assert [x[0] for x in d["so_metricas"]] == ["match_01"]
    assert d["sem_demo"] == [] and d["precisa_reparsear"] == []


def test_parser_velho_sem_demo_e_a_categoria_que_nao_tem_conserto():
    """Parser velho + demo apagada = a partida NÃO pode ser refeita.

    É a informação mais cara do relatório: ela tem que aparecer ANTES de alguém
    subir VERSAO_DO_PARSER, não depois.
    """
    m = _manifesto({
        "match_01": _linha({**v.versoes(), "parser": v.VERSAO_DO_PARSER - 1}, False),
        "match_02": _linha({**v.versoes(), "parser": v.VERSAO_DO_PARSER - 1}, True),
    })
    d = manifest.desatualizadas(m)
    assert [x[0] for x in d["sem_demo"]] == ["match_01"]
    assert [x[0] for x in d["precisa_reparsear"]] == ["match_02"]


def test_partida_em_dia_nao_aparece_em_lista_nenhuma_de_trabalho():
    m = _manifesto({"match_01": _linha(v.versoes(), False)})
    d = manifest.desatualizadas(m)
    assert d["em_dia"] == ["match_01"]
    assert not (d["so_metricas"] or d["precisa_reparsear"] or d["sem_demo"] or d["desconhecida"])


# --- demo que mudou de lugar ------------------------------------------------

def test_demo_so_e_reconhecida_por_hash_nunca_so_pelo_nome(tmp_path, monkeypatch):
    """Nome de arquivo não identifica demo.

    Achar "vitality-vs-magic-m2-dust2.dem" noutra pasta e aceitar sem conferir
    abriria a porta para parsear um arquivo diferente achando que é o mesmo --
    e o número sairia plausível.
    """
    demos = tmp_path / "demos" / "outra pasta"
    demos.mkdir(parents=True)
    arquivo = demos / "partida.dem"
    arquivo.write_bytes(b"conteudo da demo")
    monkeypatch.setattr(manifest, "PROJECT_ROOT", tmp_path)

    certo = manifest.sha256_do_arquivo(arquivo)
    assert manifest.procura_pelo_nome("partida.dem", certo) == arquivo
    assert manifest.procura_pelo_nome("partida.dem", "0" * 64) is None
    # sem hash gravado não há como conferir, então não adivinha
    assert manifest.procura_pelo_nome("partida.dem", None) is None


@pytest.mark.parametrize("campo", ["parser", "metricas"])
def test_o_historico_de_versoes_fica_no_modulo_e_nao_na_cabeca_de_ninguem(campo):
    """Subir a versão sem escrever o que mudou transforma o número em enfeite."""
    fonte = (v.RAIZ / "parsing" / "versao.py").read_text(encoding="utf-8")
    atual = getattr(v, "VERSAO_DO_PARSER" if campo == "parser" else "VERSAO_DAS_METRICAS")
    assert f"# {atual} (" in fonte, (
        f"versão {atual} não tem linha de histórico em parsing/versao.py")
