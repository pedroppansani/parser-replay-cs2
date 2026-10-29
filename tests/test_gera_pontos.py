"""Os pontos das laterais da landing (entrega-v2-goatdemo §9): a máscara sai do radar do .json (o PNG não existe no
CI), é determinística e pequena."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from scripts.design.gera_pontos import RADARS, mascara


# os mapas com partida no corpus (v2-6: o carregamento e a imagem de compartilhamento usam todos)
@pytest.mark.parametrize("mapa", ["de_ancient", "de_anubis", "de_dust2", "de_inferno", "de_mirage", "de_nuke",
                                  "de_overpass", "de_train"])
def test_a_mascara_e_deterministica_pequena_e_so_alfa(mapa):
    if not (RADARS / f"{mapa}.json").exists():
        pytest.skip("sem o radar")
    a, b = mascara.__wrapped__(mapa), mascara.__wrapped__(mapa)    # sem o cache: gera de novo
    assert a == b and len(a) < 4000
    im = Image.open(io.BytesIO(a))
    assert im.size == (512, 512) and im.mode == "RGBA"
    alfa = im.getchannel("A")
    assert 0 < sum(1 for v in alfa.getdata() if v > 128) < 512 * 512 // 2      # pontos, não um quadrado cheio
