"""Módulos que mudaram de lugar na auditoria (item 5.6, 2026-10-03): origem -> destino.

Um lugar só para a tabela. A conferência do CLAUDE.md antigo
(scripts/confere_claude_md.py) aplica estas trocas ao texto velho antes de
procurá-lo nas notas -- as notas passaram a citar os caminhos novos.
"""
from __future__ import annotations

import re

RENOMEADOS = {
    "scripts.narrative": "leitura.narrativa",
    "scripts.build_insights": "leitura.insights",
    "scripts.constantes_do_gabarito": "metrics.gabarito",
    "scripts.valida_paleta": "metrics.paleta",
    **{f"scripts.{m}": f"scripts.calibracao.{m}" for m in (
        "calibration_report", "material_calibracao", "valida_rating", "valida_modelo_de_round",
        "varre_trade", "tabela_funcoes")},
    **{f"scripts.{m}": f"pesquisa.{m}" for m in (
        "investiga_cauda_rota_a", "investiga_faceit", "investiga_props_arremesso", "prototipo_rota_a",
        "verifica_rota_a", "valida_rota_a", "piora_rota_a", "compara_lido_inferido", "casos_repick",
        "proposta_grupos", "proposta_pisos", "debug_timeline", "show_derived_angles", "show_map_areas",
        "igl_candidatos")},
    "pesquisa.confere_claude_md": "scripts.confere_claude_md",
    "pesquisa.divide_claude_md": "scripts.divide_claude_md",
    "dashboard.app": "legado.app",
    "dashboard.theme": "legado.theme",
}


def atualiza(texto: str) -> str:
    """O texto com os nomes antigos trocados pelos novos (forma pontuada e caminho .py)."""
    for origem, destino in sorted(RENOMEADOS.items(), key=lambda kv: -len(kv[0])):
        texto = re.sub(rf"\b{re.escape(origem)}\b", destino, texto)
        texto = re.sub(rf"\b{re.escape(origem.replace('.', '/'))}\.py\b", destino.replace(".", "/") + ".py", texto)
    return texto
