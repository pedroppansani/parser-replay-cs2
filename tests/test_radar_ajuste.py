"""Radar dessaturado por mapa (design-B2b, entrega-sala-de-demo §4.1): a tabela, o aviso do build e a função
única do map_core.js que o replay e a prancheta usam."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.radar_ajuste import aviso, avisa, padrao, tabela

RAIZ = Path(__file__).resolve().parent.parent
WEB = RAIZ / "dashboard" / "web"


def test_a_tabela_do_map_core_e_a_que_o_gerador_mediu():
    """notas/design/radar_ajuste.json é a saída de `py -3.12 -m scripts.design.gera_radar_ajuste` (A13)."""
    medida = json.loads((RAIZ / "notas" / "design" / "radar_ajuste.json").read_text(encoding="utf-8"))
    assert tabela() == {m: tuple(v) for m, v in medida["ajuste"].items()}
    assert padrao() == tuple(medida["padrao"])
    # a tabela do documento (§4.1)
    assert tabela() == {"ancient": (0.65, 1.0), "anubis": (0.10, 0.80), "cache": (0.95, 0.80), "dust2": (0.90, 1.0),
                        "inferno": (1.0, 1.0), "mirage": (1.0, 1.0), "nuke": (0.45, 0.70), "overpass": (0.80, 0.85),
                        "train": (1.0, 1.0), "vertigo": (0.65, 1.0)}
    assert padrao() == (0.10, 0.70)


def test_todo_mapa_que_o_build_desenha_tem_par_na_tabela():
    from scripts.build_tactics_page import mapas_disponiveis
    manifesto = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    mapas = set(mapas_disponiveis()) | {v["mapa"] for v in manifesto.values()
                                        if (RAIZ / "assets" / "radars" / f"{v['mapa']}.json").exists()}
    sem = [m for m in sorted(mapas) if aviso(m)]
    assert not sem, sem


def test_mapa_sem_entrada_usa_o_padrao_e_o_build_avisa(capsys):
    """A15: radar fictício fora da tabela."""
    assert aviso("de_mirage") is None
    avisa("de_ficticio")
    err = capsys.readouterr().err
    assert "de_ficticio" in err and "0,10/0,70" in err and "gera_radar_ajuste" in err


def test_nada_de_filtro_por_quadro():
    """O processamento é uma vez na carga (getImageData/putImageData); ctx.filter por quadro está proibido."""
    for arq in ("map_core.js", "tactics.js", "template.html"):
        texto = (WEB / arq).read_text(encoding="utf-8")
        assert not re.search(r"\.filter\s*=", texto), arq
    assert "MapCore.radarProcessado(im, RAD.map)" in (WEB / "template.html").read_text(encoding="utf-8")
    assert "MapCore.radarProcessado(im, cfg.radar.map)" in (WEB / "tactics.js").read_text(encoding="utf-8")


# ------------------------------------------------------------------ no navegador
sync_api = pytest.importorskip("playwright.sync_api")

from tests.test_tactics_browser import abre, contexto, interno, navegador, pagina  # noqa: E402,F401


def test_radar_processado_aplica_a_formula_com_o_par_do_mapa(contexto, pagina):
    pg = abre(contexto, pagina)
    r = pg.evaluate("""async () => {
        const c = document.createElement('canvas'); c.width = 4; c.height = 1;
        const g = c.getContext('2d');
        const cores = [[200, 120, 40], [10, 200, 90], [255, 255, 255], [0, 0, 0]];
        cores.forEach((k, i) => { g.fillStyle = `rgb(${k})`; g.fillRect(i, 0, 1, 1); });
        const im = new Image(); im.src = c.toDataURL();
        await im.decode();
        const lido = (fonte) => { const t = document.createElement('canvas'); t.width = 4; t.height = 1;
            const tg = t.getContext('2d'); tg.drawImage(fonte, 0, 0); return Array.from(tg.getImageData(0, 0, 4, 1).data); };
        return { nuke: lido(MapCore.radarProcessado(im, 'de_nuke')), mirageEhAPropria: MapCore.radarProcessado(im, 'de_mirage') === im,
                 cache: MapCore.radarProcessado(im, 'de_nuke') === MapCore.radarProcessado(im, 'de_nuke'),
                 ficticio: MapCore.ajusteDoRadar('de_ficticio') };
    }""")
    s, b = 0.45, 0.70
    for i, (cr, cg, cb) in enumerate([(200, 120, 40), (10, 200, 90), (255, 255, 255), (0, 0, 0)]):
        lum = 0.2126 * cr + 0.7152 * cg + 0.0722 * cb
        esperado = [min(255, max(0, b * (lum + s * (x - lum)))) for x in (cr, cg, cb)]
        assert all(abs(r["nuke"][4 * i + j] - esperado[j]) <= 1 for j in range(3)), (i, r["nuke"][4 * i:4 * i + 3], esperado)
        assert r["nuke"][4 * i + 3] == 255
    assert r["mirageEhAPropria"]          # par 1,00/1,00: a imagem original, sem cópia
    assert r["cache"]                     # processado uma vez e reaproveitado
    assert r["ficticio"] == [0.10, 0.70]
    pg.close()
