"""O validador da paleta por tema (decisões 44 e 48): claro, escuro e mapa, linha a linha."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from metrics.paleta import (FUNDOS, TEMAS, TOKENS_DO_MAPA, avalia, contraste, le_tokens, regras,
                            relatorio)

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"


@pytest.mark.parametrize("tema", ["claro", "escuro", "mapa"])
def test_a_saida_de_cada_tema_e_a_fixada_caractere_por_caractere(tema):
    linhas, falhas = relatorio(tema)
    esperado = (FIXTURES / f"paleta_{tema}_saida.txt").read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert falhas == 0
    # a primeira linha só diz de onde os tokens foram lidos; o resto é igual
    assert linhas[1:] == esperado[1:]
    assert esperado[0].startswith("tokens lidos de tokens.css: ")
    assert linhas[0].split(": ")[-1] == esperado[0].split(": ")[-1]


def test_o_claro_da_os_contrastes_da_entrega_v2():
    """O pior contraste de cada cor do claro é o da tabela §2.1 da entrega (medida no paleta_v3 do design)."""
    da_entrega = {"tinta": 18.16, "tinta-2": 7.17, "apagado": 4.89, "borda": 3.38, "ct": 4.05, "ct-texto": 5.35,
                  "tr": 3.27, "tr-texto": 8.52, "decisivo": 5.99, "aviso": 4.71, "erro": 5.87, "acao-ink": 19.80}
    tk = le_tokens(tema="claro")
    paleta, _, _ = regras("claro")
    pior = {nome: round(min(contraste(tk[nome], tk[f]) for f in fundos), 2) for nome, _, fundos in paleta}
    assert {n: pior[n] for n in da_entrega} == da_entrega


def test_o_escuro_e_o_de_hoje_e_o_mapa_e_igual_nos_dois_temas():
    """v2-1: o escuro é o da Sala de demo (as páginas não mudam de cor); o canvas lê os *-mapa, com os valores
    escuros de hoje (plano v2-0 §4.3), os mesmos nos dois temas."""
    proto = (RAIZ / "notas" / "design" / "prototipo" / "tokens.css").read_text(encoding="utf-8")
    hoje = dict(re.findall(r"^\s*--([a-z0-9-]+):\s*(#[0-9a-f]{6});", proto, re.M))
    escuro, claro = le_tokens(tema="escuro"), le_tokens(tema="claro")
    assert {k: escuro[k] for k in hoje} == hoje
    assert {n: escuro[n] for n in TOKENS_DO_MAPA} == {n: claro[n] for n in TOKENS_DO_MAPA}
    for mapa, de_hoje in (("tinta-mapa", "tinta"), ("tinta-2-mapa", "tinta-2"), ("apagado-mapa", "apagado"),
                          ("foco-mapa", "foco"), ("fundo-mapa", "fundo"), ("ct-mapa", "ct"), ("tr-mapa", "tr"),
                          ("aviso-mapa", "aviso")):
        assert escuro[mapa] == hoje[de_hoje], mapa


@pytest.mark.parametrize("tema", TEMAS)
def test_toda_cor_do_tema_tem_papel_e_todo_fundo_existe(tema):
    tk = le_tokens(tema=tema)
    usados = set()
    for t in (tema, "mapa"):
        paleta, grupos, pares = regras(t)
        usados |= {n for nome, _, fundos in paleta for n in (nome, *fundos)}
        usados |= {n for g in grupos.values() for n in g} | {n for p in pares for n in p}
    assert usados <= set(tk), usados - set(tk)
    assert set(FUNDOS) <= set(tk)
    # nenhuma cor sobra sem papel declarado (linha e contorno são decoração; acao é fundo do acao-ink)
    sem_papel = set(tk) - usados - {"linha", "contorno"}
    assert not sem_papel, sem_papel


def test_tema_desconhecido_e_recusado():
    with pytest.raises(ValueError):
        le_tokens(tema="mapa")


def test_candidato_reprovado_aparece_como_falha():
    for tema in TEMAS:
        tk = le_tokens(tema=tema)
        ruim = {**tk, "decisivo": tk["tr"]}              # o mesmo laranja do TR: o ΔE entre os dois vira 0
        _, falhas = avalia(ruim, "x", tema)
        assert falhas >= 1, tema
    escuro = le_tokens(tema="escuro")
    _, falhas = avalia(escuro, "x", "mapa", outro={**escuro, "tinta-mapa": "#0a0a0a"})
    assert falhas >= 1                                   # o mapa diferente entre os temas reprova
