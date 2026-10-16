"""A marca "(tendência)" da função dominante no cabeçalho da aba Perfil, com o motivo na dica.

Resposta do Pedro ao cartão 2 (decisão 39, 2026-10-16): a função continua aparecendo e ganha a MESMA
marca da decisão 39 quando a chance ao acaso passa do alfa, além do caso já coberto pela fase 12
(reamostragem instável). O texto e a regra são de `metrics.structural_roles.marca_da_funcao`; aqui só
se aplica ao bloco `perfil` que `leitura.perfil_erros` monta (o cabeçalho `funcoes` de cada jogador).
Nenhum rótulo muda: só o texto da marca e a dica (`dica`, o `title` da etiqueta na página).
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

ROTULO_DO_LADO = {"CT": "ct", "TR": "t"}


def marca_da_partida(base: Path) -> dict:
    """{(steamid, lado): {"funcao", "dica"}} a partir do que está gravado na pasta da partida."""
    from metrics.player_roles import awpers_do_time
    from metrics.structural_roles import estabilidade_da_funcao, marca_da_funcao

    resumo, por_round = base / "structural_roles_summary.parquet", base / "structural_roles.parquet"
    if not resumo.exists() or not por_round.exists():
        return {}
    traits = base / "player_traits.parquet"
    awpers = awpers_do_time(pl.read_parquet(traits)) if traits.exists() else set()
    return marca_da_funcao(pl.read_parquet(resumo), estabilidade_da_funcao(pl.read_parquet(por_round), awpers))


def aplica(perfil: dict | None, payload: dict, marca: dict) -> dict | None:
    """Põe a marca e a dica nas funções do cabeçalho de cada jogador. A etiqueta sem marca não muda."""
    from metrics.player_roles import rotulo_exibido
    from metrics.structural_roles import FUNCOES

    if not perfil:
        return perfil
    sid_por_nome = {p["name"]: int(p["steamid"]) for p in payload.get("player_profile") or []}
    for j in perfil.get("jogadores") or []:
        sid = sid_por_nome.get(j.get("name"))
        for f in j.get("funcoes") or []:
            m = marca.get((sid, ROTULO_DO_LADO.get(f.get("lado"))))
            nome = FUNCOES.get(m["funcao"], (m["funcao"],))[0] if m else None
            # só a etiqueta da própria função (o empate e o "sem função definida" não têm marca)
            if not m or f.get("texto") not in (nome, rotulo_exibido(nome, True)):
                continue
            f.update({"texto": rotulo_exibido(nome, True),
                      "tendencia": True, "neutro": True, "dica": m["dica"]})
    return perfil
