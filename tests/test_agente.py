"""O agente da landing (entrega-v2-goatdemo §6, decisão 48): os .js batem com o manifesto (sha256), o gerador
nunca é importado, e no navegador só o agente sorteado é baixado (N2) e sem JS aparece o quadro fixo do TR (N6)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"
MANIFESTO = json.loads((WEB / "agentes.manifesto.json").read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("lado", ["tr", "ct"])
def test_os_js_e_os_quadros_batem_com_o_manifesto(lado):
    a = MANIFESTO["agentes"][lado]
    assert _sha(WEB / a["arquivo"]) == a["sha256"]
    assert _sha(WEB / a["quadro_fixo"]) == a["quadro_fixo_sha256"]
    # o nome dentro do arquivo é o que o tocador procura (agente.js: CHAVE)
    assert f'(window.AGENTES=window.AGENTES||{{}})["{a["nome_no_arquivo"]}"]=' in (WEB / a["arquivo"]).read_text(encoding="utf-8")


def test_o_corte_de_privacidade_e_o_do_plano():
    assert MANIFESTO["agentes"]["tr"]["corte_de_privacidade_y"] == 590
    assert MANIFESTO["agentes"]["ct"]["corte_de_privacidade_y"] == 545
    gerador = (RAIZ / "scripts" / "converte_agente.py").read_text(encoding="utf-8")
    assert 'CORTE_MAXIMO_Y = {"tr": 590, "ct": 545}' in gerador


def test_nenhum_teste_importa_o_gerador_do_agente():
    """converte_agente importa onnxruntime, cv2 e rembg (fora do requirements): importá-lo quebraria o CI."""
    padrao = re.compile(r"^\s*(from|import)\s+(scripts\.)?converte_agente\b|import_module\([^)]*converte_agente", re.M)
    achados = [t.name for t in (RAIZ / "tests").glob("*.py") if padrao.search(t.read_text(encoding="utf-8"))]
    assert not achados, achados
    build = (RAIZ / "scripts" / "build_site.py").read_text(encoding="utf-8")
    assert "converte_agente" not in build
