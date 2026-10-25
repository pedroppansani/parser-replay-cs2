"""As fontes do próprio site carregam com a página aberta como arquivo (decisão 48; plano v2-0 §4.1).

A landing, uma partida e a prancheta, gravadas numa pasta com `fontes/` ao lado (como o build faz em docs/),
abrem em `file://` com a CSP de `scripts/csp.py` (`font-src 'self'`): a Geist e a Geist Mono chegam a `loaded`
e não há nenhuma violação de CSP. Sem Chrome, o teste é pulado.
"""
from __future__ import annotations

import pytest

pytest.importorskip("playwright.sync_api")

from scripts.design_head import FONTES, copia_fontes  # noqa: E402
from tests.test_csp import _abre, _paginas, _sem_violacao  # noqa: E402
from tests.test_tactics_browser import contexto, navegador  # noqa: E402,F401

ESTADO_DAS_FONTES = """async (familias) => {
  await document.fonts.ready;
  // a fonte só é baixada quando algo a usa: pede as duas, como o texto e os números da página pedem
  for (const f of familias) await document.fonts.load('16px "' + f + '"');
  const faces = Array.from(document.fonts).filter((f) => familias.includes(f.family.replace(/"/g, '')));
  return faces.map((f) => [f.family.replace(/"/g, ''), f.status]);
}"""


def test_geist_e_geist_mono_carregam_em_file_sem_violacao_de_csp(contexto, tmp_path):
    paginas = _paginas()
    destino = {"prancheta": "#pr-mapa", "partida": "[role=tab][data-tab]", "landing": "#partidas"}
    assert "prancheta" in paginas
    copia_fontes(tmp_path)
    familias = [f for f, _ in FONTES]
    vistas = []
    for nome, seletor in destino.items():
        if nome not in paginas:          # partida e landing dependem de data/processed (pulado sem o dado)
            continue
        arq = tmp_path / f"{nome}.html"
        arq.write_text(paginas[nome], encoding="utf-8")
        pg, consoles, erros = _abre(contexto, arq, seletor)
        estado = pg.evaluate(ESTADO_DAS_FONTES, familias)
        assert sorted(estado) == sorted([f, "loaded"] for f in familias), (nome, estado)
        _sem_violacao(pg, consoles, erros, nome)
        vistas.append(nome)
        pg.close()
    assert "prancheta" in vistas


def test_sem_a_pasta_fontes_a_pagina_cai_no_fallback_sem_quebrar(contexto, tmp_path):
    """Um HTML solto, copiado sem `fontes/`, não carrega a Geist (erro), mas abre sem violação de CSP."""
    arq = tmp_path / "prancheta.html"
    arq.write_text(_paginas()["prancheta"], encoding="utf-8")
    pg, consoles, erros = _abre(contexto, arq, "#pr-mapa")
    estado = pg.evaluate("""async () => { try { await document.fonts.load('16px "Geist"'); } catch (e) {}
        return Array.from(document.fonts).filter((f) => f.family.replace(/"/g, '') === 'Geist').map((f) => f.status); }""")
    assert estado == ["error"]
    _sem_violacao(pg, [c for c in consoles if "ERR_FILE_NOT_FOUND" not in c], erros, "prancheta sem fontes")
    pg.close()
