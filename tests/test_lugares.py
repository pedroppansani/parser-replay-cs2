"""Nome do lugar do roteiro da prancheta (fase 8, item 8.5): metrics/lugares.py."""
from __future__ import annotations

import json
from pathlib import Path

from metrics.lugares import LIMITE_BYTES, MIN_ACERTO, MIN_PARTIDAS, grade, lugar, tabela_compacta
from scripts.build_lugares import escolhe

RAIZ = Path(__file__).resolve().parents[1]


def test_a_tabela_compacta_devolve_o_lugar_de_cada_celula_e_nada_fora_delas():
    pontos = [(1.0, 1.0, 0, "A"), (2.0, 2.0, 0, "A"), (3.0, 1.0, 0, "B"),       # célula (0,0): A vence
              (9.0, 1.0, 0, "B"), (17.0, 1.0, 0, "B"), (25.0, 1.0, 0, "A"),
              (1.0, 9.0, 1, "Baixo")]
    g = grade(pontos, 8)
    assert g[(0, 0, 0)] == "A" and g[(0, 1, 0)] == "B" and g[(0, 2, 0)] == "B" and g[(0, 3, 0)] == "A"
    tab = tabela_compacta(g, 8)
    for (n, cx, cy), nome in g.items():
        assert lugar(tab, cx * 8 + 4, cy * 8 + 4, n) == nome
    assert lugar(tab, 100, 100, 0) is None          # célula sem tick: sem nome
    assert lugar(tab, 1, 1, 5) is None              # andar que não existe
    assert lugar(None, 1, 1, 0) is None
    # empate de contagem: ordem alfabética, sempre o mesmo
    assert grade([(1, 1, 0, "Z"), (2, 2, 0, "M")], 8)[(0, 0, 0)] == "M"


def test_a_escolha_e_o_maior_acerto_que_cabe_no_limite():
    linhas = [{"lado": 4, "bytes": LIMITE_BYTES + 1, "acerto": 0.99},
              {"lado": 8, "bytes": 10, "acerto": 0.9601},
              {"lado": 16, "bytes": 5, "acerto": 0.9604},     # empata em 3 casas: fica a célula maior
              {"lado": 32, "bytes": 2, "acerto": 0.90}]
    assert escolhe(linhas)["lado"] == 16
    assert escolhe([{"lado": 8, "bytes": 1, "acerto": None}]) is None


def test_as_tabelas_gravadas_cabem_no_limite_e_dizem_de_onde_vieram():
    pasta = RAIZ / "data" / "lugares"
    arquivos = sorted(pasta.glob("*.json"))
    assert arquivos, "data/lugares vazio (scripts/build_lugares.py)"
    for a in arquivos:
        assert a.stat().st_size <= LIMITE_BYTES, a.name
        doc = json.loads(a.read_text(encoding="utf-8"))
        o = doc["origem"]
        assert o["partidas"] >= MIN_PARTIDAS and MIN_ACERTO <= o["acerto_fora_da_amostra"] <= 1
        assert o["fonte"] == "campo place dos ticks do corpus"
        assert doc["lado"] in (4, 8, 16, 32) and doc["nomes"] == sorted(doc["nomes"])


def test_a_prancheta_leva_a_tabela_do_mapa_e_nada_quando_nao_ha():
    from scripts.build_tactics_page import build_html
    html = build_html("de_mirage")
    assert "/*__LUGARES__*/" not in html
    tab = json.loads((RAIZ / "data" / "lugares" / "de_mirage.json").read_text(encoding="utf-8"))
    assert json.dumps(tab["nomes"][0], ensure_ascii=False) in html
    assert "lugares: null" in build_html("de_train")         # 1 partida: sem tabela, sem nome
