"""Material do round decisivo (fase 6, passo 6.3)."""
from __future__ import annotations

from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent


def test_a_secao_tem_ate_25_partidas_com_curva_regras_e_pergunta():
    from scripts.calibracao.material_decisivo import FIM, INICIO, MAX_PARTIDAS
    texto = (RAIZ / "MATERIAL_DE_CALIBRACAO.md").read_text(encoding="utf-8")
    if INICIO not in texto:
        pytest.skip("seção ainda não gerada")
    secao = texto[texto.index(INICIO):texto.index(FIM)]
    n = secao.count("\n### match_")
    assert 0 < n <= MAX_PARTIDAS
    assert secao.count("**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**") == n
    assert secao.count("Sua resposta: ____") == n
    for regra in ("**A:**", "**B:**", "**C:**", "**D:**"):
        assert secao.count(regra) == n, regra


def test_a_escolha_inclui_prorrogacao_virada_largo_e_apertado():
    from scripts.calibracao.material_decisivo import PROCESSED, _partida, escolhe
    arquivos = sorted(PROCESSED.glob("match_*/insights.json"))
    if not arquivos:
        pytest.skip("sem o processado")
    escolhidas, n_disc, _ = escolhe([_partida(f) for f in arquivos])
    assert len(escolhidas) <= 25 and len({p["id"] for p in escolhidas}) == len(escolhidas)
    assert any(p["rounds"] > 24 for p in escolhidas) and any(p["virada"] for p in escolhidas)
    assert any(p["dif"] >= 6 for p in escolhidas) and any(p["dif"] <= 3 for p in escolhidas)
