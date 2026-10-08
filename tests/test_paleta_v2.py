"""O validador da paleta v2 (decisão 44): a saída é a da §9.2 da entrega, linha a linha."""
from __future__ import annotations

from pathlib import Path

from metrics.paleta import FUNDOS, GRUPOS, PALETA, avalia, le_tokens

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "tests" / "fixtures" / "paleta_v2_saida.txt"


def test_a_saida_e_a_do_documento_de_entrega_caractere_por_caractere():
    linhas, falhas = avalia(le_tokens(), "tokens.css")
    esperado = FIXTURE.read_text(encoding="utf-8").rstrip("\n").split("\n")
    assert falhas == 0
    # a primeira linha só diz de onde os tokens foram lidos; o resto é igual
    assert linhas[1:] == esperado[1:]
    assert esperado[0] == "tokens lidos de tokens.css: 23" and linhas[0].endswith(": 23")


def test_toda_cor_da_paleta_e_todo_fundo_existem_nos_tokens_e_nao_ha_cor_fora_dela():
    tk = le_tokens()
    usados = {nome for nome, _, fundos in PALETA for nome in (nome, *fundos)} | {n for g in GRUPOS.values() for n in g}
    assert usados <= set(tk), usados - set(tk)
    assert set(FUNDOS) <= set(tk)
    # os 23 tokens de cor: nenhum sobra sem papel declarado (linha, contorno e foco têm papel de marca/decoração)
    sem_papel = set(tk) - usados - {"linha", "contorno"}
    assert not sem_papel, sem_papel


def test_candidato_reprovado_aparece_como_falha():
    tk = le_tokens()
    ruim = {**tk, "decisivo": tk["tr"]}              # o mesmo dourado do TR: o ΔE entre os dois vira 0
    _, falhas = avalia(ruim, "x")
    assert falhas >= 1
