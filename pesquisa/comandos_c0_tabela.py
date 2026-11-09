"""C0 (Comandos na prancheta): gera o RASCUNHO da tabela de nomes de lugar em português, uma linha por lugar (os 171 nomes das tabelas dos 7 mapas).

    py -3.12 -m pesquisa.comandos_c0_tabela <analise.json> <saida.csv>

Serve só para a primeira versão: se a saída já existe, o script para (a tabela é editada à mão pelo Pedro; não se gera de novo por cima).
Colunas: tradução das palavras (mecânica, palavra por palavra, sem apelido), apelido usado no Brasil (só onde há certeza; o resto é "?"),
quantos pedaços separados o nome tem no mapa e em quantos andares (mais de um = o comando precisa perguntar "qual?").
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

from metrics.lugares import texto_do_lugar

PALAVRAS = {
    "A": "A", "B": "B", "ADMIN": "Administração", "ALLEY": "Beco", "APARTMENTS": "Apartamentos", "ARCH": "Arco", "BACK": "Fundo", "BALCONY": "Sacada",
    "BANANA": "Banana", "BOMBSITE": "Bomb", "BRICKS": "Tijolos", "BRIDGE": "Ponte", "CANAL": "Canal", "CATWALK": "Passarela", "CONNECTOR": "Conector",
    "CONSTRUCTION": "Construção", "CONTROL": "Controle", "CRANE": "Guindaste", "CT": "CT", "DECK": "Deck", "DECON": "?", "DOORS": "Portas",
    "ENTRANCE": "Entrada", "EXTENDED": "Estendido", "FOUNTAIN": "Fonte", "GARAGE": "Garagem", "GRAVEYARD": "Cemitério", "HALL": "Salão", "HEAVEN": "Céu",
    "HELL": "Inferno", "HOLE": "Buraco", "HOUSE": "Casa", "HUT": "Cabana", "INTERIOR": "Interior", "JUNGLE": "Selva", "KITCHEN": "Cozinha",
    "LADDER": "Escada de mão", "LIBRARY": "Biblioteca", "LOBBY": "Saguão", "LOCKER": "Armários", "LONG": "Longo", "LOWER": "Baixo", "MAIN": "Principal",
    "MID": "Mid", "MIDDLE": "Meio", "MINI": "Mini", "NEST": "Ninho", "OBSERVATION": "Observação", "OF": "de", "OUTSIDE": "Lado de fora",
    "PALACE": "Palácio", "PARK": "Parque", "PIPE": "Cano", "PIT": "Fosso", "PLAYGROUND": "Parquinho", "QUAD": "?", "RAFTERS": "Vigas", "RAMP": "Rampa",
    "RESTROOM": "Banheiro", "ROOF": "Telhado", "ROOM": "Sala", "RUINS": "Ruínas", "SCAFFOLDING": "Andaime", "SECOND": "Segundo", "SECRET": "Secreto",
    "SHOP": "Loja", "SHORT": "Curto", "SIDE": "Lateral", "SILO": "Silo", "SNIPERS": "Snipers", "SPAWN": "Spawn", "SQUEAKY": "?", "STAIRS": "Escadas",
    "STORAGE": "Depósito", "STREET": "Rua", "T": "TR", "TOP": "Topo", "TROPHY": "Troféu", "TRUCK": "Caminhão", "TUNNEL": "Túnel", "TUNNELS": "Túneis",
    "UNDER": "Sob", "UNDERPASS": "Passagem inferior", "UPPER": "Alto", "UPSTAIRS": "Andar de cima", "VENDING": "Máquina de venda", "VENTS": "Dutos",
    "WALKWAY": "Passagem", "WATER": "Água",
}
# Só o que o Brasil diz com certeza (meu conhecimento, o Pedro confere): letra do bombsite, spawn, meio. O resto fica "?".
APELIDOS = {"BombsiteA": "A / bomb A / site A", "BombsiteB": "B / bomb B / site B", "CTSpawn": "spawn CT / base CT", "TSpawn": "spawn TR / base TR",
            "Middle": "meio / mid"}


def traduz(nome: str) -> str:
    return " ".join(PALAVRAS.get(p, "?") for p in texto_do_lugar(nome).split())


def main() -> None:
    saida = Path(sys.argv[2])
    if saida.exists():
        raise SystemExit(f"{saida} já existe: a tabela é editada à mão, não gero por cima.")
    res = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["nomes"]
    with open(saida, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["mapa", "nome_do_jogo", "texto_no_mapa", "traducao_das_palavras", "apelido_br", "pedacos_no_mapa", "andares", "ticks_no_corpus", "status"])
        for m in res:
            for l in m["lugares"]:
                w.writerow([m["mapa"], l["nome"], l["texto"], traduz(l["nome"]), APELIDOS.get(l["nome"], "?"), l["pedacos"], l["andares"], l["ticks"],
                            "rascunho, o Pedro confere"])


if __name__ == "__main__":
    main()
