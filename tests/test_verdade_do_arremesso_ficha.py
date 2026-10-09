"""Rota B: a ficha do arremesso real mostra de onde veio cada afirmação
("lido" da demo ou "inferido" pela rotina do jogo). Playwright + Chrome, com os
fixtures de test_tactics_browser.py."""
from __future__ import annotations

import json

import pytest

sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import (clica,   # noqa: E402,F401  (fixtures)
    abre, contexto, interno, navegador, no_mapa, pagina,
)


def test_ficha_do_arremesso_real_mostra_a_fonte(contexto, pagina):
    pg = abre(contexto, pagina)
    assert interno(pg, "I.descreveFontes({botao: 'lido', postura: 'lido', no_ar: 'lido', origem: 'lido'})") == \
        "lido da demo: botão, postura, no ar, saída"
    assert interno(pg, "I.descreveFontes({botao: 'inferido', postura: 'lido', no_ar: 'inferido', origem: 'lido'})") == \
        "lido da demo: postura, saída · inferido pela rotina do jogo: botão, no ar"
    assert interno(pg, "I.descreveFontes(undefined)") == ""
    clica(pg, '[data-arma="smoke"]')
    pg.click('[data-ferramenta="buscar"]')
    pg.mouse.click(*no_mapa(pg, 0.48, 0.52))
    pg.locator(".pr-lista li").first.click()
    (g,) = interno(pg, "Object.values(S.estado.granadas)")
    esperado = interno(pg, f"I.descreveFontes({json.dumps(g['arremesso'].get('fontes'))})")
    assert esperado and pg.locator("#pr-fonte").text_content() == esperado
    assert pg._erros == []
