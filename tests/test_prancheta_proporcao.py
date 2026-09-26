"""
GUARDA TEMPORÁRIA -- remover na ETAPA 2 da prancheta.

Hoje `redimensiona()` em dashboard/web/tactics.js FORÇA o canvas da prancheta a
ser quadrado, e a conversão ponteiro -> pixel (MapCore.eventoParaPixel) usa a
escala da LARGURA para os dois eixos. Os dois só estão certos juntos porque os
radares com prancheta são quadrados -- coincidência dos dados, não garantia do
código. Um radar retangular deixaria o mapa esticado e o clique fora do lugar.

Na etapa 2, o redimensionamento da prancheta passa para a reprojeção
compartilhada (MapCore.caixaDoMapa, que preserva a proporção), e este arquivo
deixa de ter motivo: apague-o junto.
"""
from __future__ import annotations

import json

from scripts.build_tactics_page import RADARS_DIR, mapas_disponiveis


def test_todo_mapa_com_prancheta_tem_radar_quadrado():
    """Falha se um radar não quadrado entrar em mapas_disponiveis()."""
    for mapa in mapas_disponiveis():
        radar = json.loads((RADARS_DIR / f"{mapa}.json").read_text(encoding="utf-8"))
        assert radar["width"] == radar["height"], (
            f"{mapa}: radar {radar['width']}x{radar['height']} não é quadrado, e a prancheta "
            "ainda força canvas quadrado (tactics.js, redimensiona). Troque pela reprojeção "
            "compartilhada com MapCore.caixaDoMapa antes de publicar este mapa (etapa 2)."
        )
