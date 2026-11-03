"""A `compara_capturas` guarda de onde vieram as referências e AVISA quando são de outra máquina (cartão 19).

Regra do Pedro (2026-11-03): o mesmo código dá o mesmo PNG na mesma máquina, mas o texto e as bordas do radar mudam entre
Windows e Linux. Comparar com referências de outra máquina não prova nada: a ferramenta avisa em vez de só acusar diferença.
Sem navegador: só as funções de origem e a comparação de PNG de teste.
"""
from __future__ import annotations

import json

import pytest
from PIL import Image

from scripts import compara_capturas as cc

PC = {"sistema": "Windows 11 (AMD64)", "familia": "Windows", "navegador": "Chrome do sistema", "versao": "142.0.7444.60"}
LINUX = {"sistema": "Linux 6.8 (x86_64)", "familia": "Linux", "navegador": "Chromium do Playwright", "versao": "143.0.7499.4"}


def test_a_mesma_maquina_nao_tem_motivo_de_aviso():
    assert cc.motivos_de_outra_maquina(dict(PC), dict(PC)) == []


def test_so_a_versao_menor_do_navegador_nao_conta_como_outra_maquina():
    atual = dict(PC, versao="142.0.9999.1")
    assert cc.motivos_de_outra_maquina(dict(PC), atual) == []


@pytest.mark.parametrize("campo,valor,trecho", [
    ("familia", "Linux", "sistema"),
    ("navegador", "Chromium do Playwright", "navegador"),
    ("versao", "143.0.1.1", "versão do navegador"),
])
def test_cada_diferenca_de_maquina_vira_um_motivo(campo, valor, trecho):
    motivos = cc.motivos_de_outra_maquina(dict(PC), dict(PC, **{campo: valor}))
    assert len(motivos) == 1 and trecho in motivos[0]


def test_referencia_sem_origem_conta_como_outra_maquina():
    motivos = cc.motivos_de_outra_maquina(None, dict(PC))
    assert len(motivos) == 1 and "origem.json" in motivos[0]


def _quadros(pasta, cor):
    for q in ("replay_mirage_r6", cc.QUADRO_PRANCHETA):
        Image.new("RGB", (8, 8), cor).save(pasta / f"{q}_depois.png")


def test_grava_as_referencias_com_a_origem_e_le_de_volta(tmp_path, monkeypatch):
    monkeypatch.setattr(cc, "NAVEGADOR_ATUAL", {"nome": "Chrome do sistema", "versao": "142.0.1"})
    saida, ref = tmp_path / "saida", tmp_path / "ref"
    saida.mkdir()
    _quadros(saida, (10, 20, 30))
    cc.grava_referencias(saida, ref, ["replay_mirage_r6", cc.QUADRO_PRANCHETA])
    origem = cc.le_origem(ref)
    assert origem["navegador"] == "Chrome do sistema" and origem["versao"] == "142.0.1" and origem["sistema"]
    assert {f.name for f in ref.iterdir()} == {"replay_mirage_r6_depois.png", f"{cc.QUADRO_PRANCHETA}_depois.png", "origem.json"}


def test_na_mesma_maquina_compara_de_verdade_e_na_outra_so_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(cc, "NAVEGADOR_ATUAL", {"nome": "Chrome do sistema", "versao": "142.0.1"})
    nomes = ["replay_mirage_r6", cc.QUADRO_PRANCHETA]
    saida, ref = tmp_path / "saida", tmp_path / "ref"
    saida.mkdir()
    _quadros(saida, (10, 20, 30))
    cc.grava_referencias(saida, ref, nomes)

    mesma = "\n".join(cc.compara_com_referencias(saida, ref, nomes))
    assert "mesma máquina" in mesma and mesma.count("idêntico às referências") == 2 and "AVISO" not in mesma

    Image.new("RGB", (8, 8), (11, 20, 30)).save(saida / "replay_mirage_r6_depois.png")
    mudou = "\n".join(cc.compara_com_referencias(saida, ref, nomes))
    assert "DIFERENTE das referências" in mudou and mudou.count("idêntico às referências") == 1

    origem = json.loads((ref / cc.ARQUIVO_DE_ORIGEM).read_text(encoding="utf-8"))
    origem.update(familia="Linux", sistema="Linux 6.8 (x86_64)", navegador="Chromium do Playwright")
    (ref / cc.ARQUIVO_DE_ORIGEM).write_text(json.dumps(origem), encoding="utf-8")
    outra = "\n".join(cc.compara_com_referencias(saida, ref, nomes))
    assert "AVISO" in outra and "OUTRA máquina" in outra and "NÃO são comparáveis" in outra
    # de outra máquina a ferramenta não compara nada: nem "idêntico" nem "DIFERENTE"
    assert "idêntico às referências" not in outra and "DIFERENTE" not in outra


@pytest.mark.parametrize("cor", [(11, 20, 30), (10, 21, 30), (10, 20, 31)])
def test_um_degrau_em_qualquer_canal_nao_escapa_da_comparacao(cor):
    """REGRESSÃO: a diferença convertida para cinza arredondava 1 degrau só no vermelho ou no azul para zero (idêntico, falso)."""
    a, b = Image.new("RGB", (4, 4), (10, 20, 30)), Image.new("RGB", (4, 4), cor)
    assert cc.mascara_de_diferenca(a, b).getbbox() == (0, 0, 4, 4)
    assert cc.mascara_de_diferenca(a, a.copy()).getbbox() is None
