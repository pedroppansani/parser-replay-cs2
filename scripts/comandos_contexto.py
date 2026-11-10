"""O contexto que o leitor de comandos (`dashboard/web/comandos/leitor.js`) recebe: os pontos do Pedro do mapa, os lugares da demo, os jogadores, as funções,
o relógio e os TEXTOS das perguntas (a frase da tela sai do Python, decisão 18).

Os pontos vêm de `data/reference/callouts_br.csv` (mapas de callouts do Pedro, C0b). Os lugares da demo vêm de `data/lugares/<mapa>.json` (o nome do jogo em
inglês; o leitor os entende "sem diferença de maiúscula, espaço e acento"), cada um com a primeira âncora do desenho (em unidades do jogo) como posição.
Os apelidos em português de um lugar da demo vêm da tabela da C0, sem os nomes que já são pontos do Pedro (esses são o ponto, não a área).
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

from metrics.lugares import rotulos, tabela_do_mapa, texto_do_lugar
from metrics.tactics import SEGUNDOS_DO_ROUND, funcoes_da_prancheta

RAIZ = Path(__file__).resolve().parent.parent
CALLOUTS = RAIZ / "data" / "reference" / "callouts_br.csv"
TABELA_C0 = RAIZ / "notas" / "investigacoes" / "2026-11-09-comandos-nomes-em-portugues.csv"

# A frase de cada pergunta e de cada opção (o leitor só preenche {os campos}).
TEXTOS = {
    "pergunta_quem": 'Quem faz "{trecho}"?',
    "pergunta_quem_lado": 'De qual time é "{ref}"?',
    "pergunta_quem_funcao": 'Não achei "{ref}" na tática. Quem é?',
    "pergunta_granada": 'Qual granada em "{trecho}"?',
    "pergunta_acao": 'Não entendi "{trecho}". O que o jogador faz?',
    "pergunta_qual": 'Qual "{nome}"?',
    "pergunta_onde": 'Em que lugar? ("{trecho}")',
    "pergunta_onde_desconhecido": 'Não achei o lugar "{trecho}" neste mapa. Qual destes?',
    "pergunta_quando": 'Quando começa "{trecho}"?',
    "pergunta_quando_segundos": "{n} segundos contados como?",
    "pergunta_horario_invalido": "O horário {horario} não existe no round.",
    "pergunta_espera": 'Quanto tempo espera em "{trecho}"?',
    "opcao_jogador": "{lado} {num}",
    "opcao_mover": "Mover até {lugar}",
    "opcao_segurar": "Segurar {lugar}",
    "opcao_relogio_n": "{n} s no relógio do round ({h})",
    "opcao_inicio_n": "{n} s depois do início do round",
    "granada_smoke": "Smoke", "granada_flash": "Flash", "granada_molotov": "Molotov", "granada_he": "HE",
}


def _norma(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"))


def _pontos(mapa: str, so_conferidos: bool) -> list[dict]:
    saida = []
    for r in csv.DictReader(open(CALLOUTS, encoding="utf-8-sig", newline=""), delimiter=";"):
        if r["mapa"] != mapa or (so_conferidos and r["conferido"] != "sim"):
            continue
        lugar = r["lugar_da_demo"].replace(" (mais perto)", "")
        saida.append({"id": f"{mapa}:{len(saida)}", "nome": r["nome"], "apelidos": [a.strip() for a in r["apelidos"].split(" / ") if a.strip()],
                      "qualificacao": r["qualificacao"], "vertical": r["posicao_vertical"], "tipo": r["tipo"], "x": int(r["x"]), "y": int(r["y"]),
                      "andar": r["andar"], "lugar": "" if lugar.startswith("(") else texto_do_lugar(lugar) if lugar else "", "conferido": r["conferido"] == "sim"})
    return saida


def _areas(mapa: str, pontos: list[dict]) -> list[dict]:
    tab = tabela_do_mapa(mapa)
    if not tab:
        return []
    radar = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    esc, ox, oy = radar["scale_px_per_unit"], radar["origin_x"], radar["origin_y"]
    nomes_de_ponto = {_norma(n) for p in pontos for n in [p["nome"]] + p["apelidos"]}
    apelidos: dict[str, list[str]] = {}
    for r in csv.DictReader(open(TABELA_C0, encoding="utf-8-sig", newline=""), delimiter=";"):
        if r["mapa"] == mapa and r["apelido_br"] not in ("", "?"):
            apelidos[r["nome_do_jogo"]] = [a.strip() for a in r["apelido_br"].split(" / ") if a.strip() and _norma(a) not in nomes_de_ponto]
    areas = []
    for andar, lugares in enumerate(rotulos(tab)):
        for ix, pts in lugares:
            if not pts or any(a["nome"] == tab["nomes"][ix] for a in areas):
                continue
            nome = tab["nomes"][ix]
            areas.append({"nome": nome, "texto": texto_do_lugar(nome), "apelidos": apelidos.get(nome, []), "x": round(ox + pts[0][0] / esc), "y": round(oy - pts[0][1] / esc),
                          "andar": "baixo" if andar else ("cima" if len(tab["andares"]) > 1 else "único")})
    return areas


def jogadores_padrao() -> list[dict]:
    return [{"lado": lado, "num": n} for lado in ("tr", "ct") for n in range(1, 6)]


def contexto(mapa: str, jogadores: list[dict] | None = None, so_conferidos: bool = False) -> dict:
    pontos = _pontos(mapa, so_conferidos)
    return {"mapa": mapa, "pontos": pontos, "areas": _areas(mapa, pontos), "jogadores": jogadores or jogadores_padrao(), "funcoes": funcoes_da_prancheta(),
            "segundos_do_round": int(SEGUNDOS_DO_ROUND), "textos": TEXTOS}
