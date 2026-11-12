"""O Round Swing por jogador em todas as partidas (RS1): `data/player_profiles/round_swing.json`.

    py -3.12 -m scripts.build_round_swing

Soma, entre as partidas, rounds, swing (p.p.) e soma dos quadrados de cada jogador (a razão das somas) e grava o número por round com o erro padrão e as marcas
"poucos rounds" (menos de 30) e "estável" (100 ou mais). Só lê os `insights.json`; não muda modelo, crédito nem rating.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from metrics.round_swing_jogador import MIN_ROUNDS_PARA_MOSTRAR, ROUNDS_ESTAVEL, agrega

RAIZ = Path(__file__).resolve().parent.parent
PROCESSED = RAIZ / "data" / "processed"
SAIDA = RAIZ / "data" / "player_profiles" / "round_swing.json"


def jogadores_do_corpus(processed: Path = PROCESSED) -> dict:
    blocos, nomes = [], {}
    for ins in sorted(processed.glob("match_*/insights.json")):
        d = json.loads(ins.read_text(encoding="utf-8"))
        for p in d["players"]:
            if p.get("round_swing") is None:
                continue
            blocos.append((int(p["steamid"]), p["round_swing"]))
            nomes.setdefault(int(p["steamid"]), Counter())[p["name"]] += 1
    agregado = agrega(blocos)
    return {str(sid): {"nome": nomes[sid].most_common(1)[0][0], **b} for sid, b in agregado.items()}


def main() -> None:
    jogadores = jogadores_do_corpus()
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "unidade": "pontos percentuais por round (Round Swing, implementação própria da metodologia do Rating 3.0 da HLTV; pode diferir do número deles)",
        "min_rounds_para_mostrar": MIN_ROUNDS_PARA_MOSTRAR, "rounds_estavel": ROUNDS_ESTAVEL, "jogadores": jogadores,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(jogadores)} jogadores em {SAIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
