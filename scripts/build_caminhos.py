"""PC1: monta o grafo de caminhos de cada mapa (decisão 70) e grava `data/caminhos/<mapa>.json`.

    py -3.12 -m scripts.build_caminhos [mapa ...]

Junta (1) o grafo das TRAJETÓRIAS do corpus (`data/interim`, células de 64 u; só os mapas que têm partida) e (2) a malha do jogo já DERIVADA (`data/caminhos/malha/<mapa>.json`, de `scripts/gera_malha.py`):
o build e o CI só leem o arquivo derivado, nunca o `.nav`. Une os dois com pontes célula <-> área onde o centro da célula está dentro da área, na mesma altura. Nos mapas de dois andares
(`metrics.map_areas.floor_split_z`) as ligações do corpus que cruzam o andar não entram: ENTRE ANDARES a malha vem primeiro.

Formato (compacto, como a biblioteca de arremessos e os tempos; o site entrega `docs/caminhos/<mapa>.js`):
  {"versao": 1, "mapa", "gerado_em", "credito", "origem": {"malha": {...}|null, "corpus": {...}|null}, "celula_u", "faixa_z_u", "andar_z": float|null,
   "nc": células, "na": áreas, "p": [x, y, z, ...] (int, um por nó: as células e depois as áreas), "e": [de em delta, para, ...] (ligações dirigidas, em ordem),
   "poli": [[x, y, z, ...] por área], "z_pontos": {chave do nó da C3: z}, "z_areas": {nome da área da demo: z}}"""
from __future__ import annotations

import datetime
import json
import math
import sys
from pathlib import Path

from scripts.caminhos.corpus import CELULA_U, FAIXA_Z_U, MIN_LIGACOES, MIN_VISITAS, celulas_e_ligacoes, z_dos_nos

RAIZ = Path(__file__).resolve().parent.parent
PASTA = RAIZ / "data" / "caminhos"
VERSAO = 1
PONTE_DZ_U = 110.0      # a célula só liga à área se estiver a menos disso dela, em altura


def arquivo_dos_caminhos(mapa: str) -> Path:
    return PASTA / f"{mapa}.json"


def _contem(poli: list[tuple], x: float, y: float) -> bool:
    pos = neg = False
    for k in range(len(poli)):
        ax, ay = poli[k]
        bx, by = poli[(k + 1) % len(poli)]
        s = (bx - ax) * (y - ay) - (by - ay) * (x - ax)
        if s > 1e-6:
            pos = True
        elif s < -1e-6:
            neg = True
    return not (pos and neg)


def monta(mapa: str, malha: dict | None, rastros: list[dict] | None, z_pontos: dict, z_areas: dict, split: float | None) -> dict:
    """O grafo do mapa; `malha` é o arquivo derivado (ou None), `rastros` os do corpus (ou None)."""
    celulas, centro, lig_c = ([], {}, set())
    if rastros:
        celulas, centro, lig_c = celulas_e_ligacoes(rastros)
    idx = {c: k for k, c in enumerate(celulas)}
    nc = len(celulas)
    p = [int(round(v)) for c in celulas for v in centro[c]]
    arestas: set[tuple[int, int]] = set()
    for a, b in lig_c:
        za, zb = centro[a][2], centro[b][2]
        if split is not None and (za < split) != (zb < split):      # entre andares a malha vem primeiro: o corpus não cruza
            continue
        arestas.add((idx[a], idx[b]))
    poli: list[list[int]] = []
    na = 0
    if malha:
        poli = malha["areas"]["poli"]
        na = len(poli)
        zs = []
        for q in poli:
            p += [int(round(sum(q[0::3]) / (len(q) // 3))), int(round(sum(q[1::3]) / (len(q) // 3))), int(round(sum(q[2::3]) / (len(q) // 3)))]
            zs.append(p[-1])
        lig = malha["lig"]
        for k in range(0, len(lig), 2):
            arestas.add((nc + lig[k], nc + lig[k + 1]))
        # pontes célula <-> área: o centro da célula dentro do polígono da área, a menos de PONTE_DZ_U de altura
        grade: dict[tuple[int, int], list[int]] = {}
        cantos = [[(q[3 * k], q[3 * k + 1]) for k in range(len(q) // 3)] for q in poli]
        for a, c in enumerate(cantos):
            for gx in range(int(min(v[0] for v in c) // 128), int(max(v[0] for v in c) // 128) + 1):
                for gy in range(int(min(v[1] for v in c) // 128), int(max(v[1] for v in c) // 128) + 1):
                    grade.setdefault((gx, gy), []).append(a)
        for ci, cel in enumerate(celulas):
            x, y, z = centro[cel]
            for a in grade.get((int(x // 128), int(y // 128)), []):
                if abs(zs[a] - z) < PONTE_DZ_U and _contem(cantos[a], x, y):
                    arestas.add((ci, nc + a))
                    arestas.add((nc + a, ci))
    e, ant = [], 0
    for a, b in sorted(arestas):
        e += [a - ant, b]
        ant = a
    return {"versao": VERSAO, "mapa": mapa, "gerado_em": datetime.date.today().isoformat(),
            "credito": (malha or {}).get("credito") or "Trajetórias do corpus do projeto.",
            "origem": {"malha": (malha or {}).get("origem"), "corpus": {"rastros": len(rastros or []), "partidas": len({r["partida"] for r in rastros or []}), "min_visitas": MIN_VISITAS, "min_ligacoes": MIN_LIGACOES} if rastros else None},
            "celula_u": CELULA_U, "faixa_z_u": FAIXA_Z_U, "andar_z": split, "nc": nc, "na": na, "p": p, "e": e, "poli": poli,
            "z_pontos": z_pontos, "z_areas": z_areas}


def grafo_do_mapa(mapa: str) -> dict | None:
    from metrics.map_areas import floor_split_z
    from scripts.build_tempos import rastros
    from scripts.comandos_contexto import contexto
    arq = PASTA / "malha" / f"{mapa}.json"
    malha = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else None
    rs = rastros(mapa) or None
    if malha is None and rs is None:
        return None
    tempos = RAIZ / "data" / "tempos" / f"{mapa}.json"
    z_pontos: dict = {}
    if tempos.exists() and rs:
        nos = json.loads(tempos.read_text(encoding="utf-8"))["nos"]
        z_pontos = {k: round(v) for k, v in z_dos_nos(nos, mapa, rs).items() if v is not None}
    z_areas: dict = {}
    if rs:
        ctx = contexto(mapa, so_conferidos=False)
        areas = [[a["nome"], a["x"], a["y"], a["andar"] if a["andar"] in ("cima", "baixo") else ""] for a in ctx["areas"]]
        z_areas = {k: round(v) for k, v in z_dos_nos(areas, mapa, rs).items() if v is not None}
    return monta(mapa, malha, rs, z_pontos, z_areas, floor_split_z(mapa))


PASTA_NO_SITE = "caminhos"
ARQUIVO_DO_MODULO = "comandos/caminho.js"      # a busca do caminho (pura), a mesma para a prancheta e o Reescrever (PC2 e PC3)


def arquivo_no_site(mapa: str) -> str:
    return f"{PASTA_NO_SITE}/{mapa}.js"


def caminhos_js(mapa: str) -> str | None:
    """O arquivo do site com o grafo do mapa: chama `window.__recebeCaminhos(...)`, que quem usa deixa pronta antes de carregá-lo (como o contexto dos comandos do real). None sem dado."""
    arq = arquivo_dos_caminhos(mapa)
    if not arq.exists():
        return None
    return "window.__recebeCaminhos && window.__recebeCaminhos(" + arq.read_text(encoding="utf-8") + ");\n"


def escreve(destino: Path) -> list[str]:
    """Escreve o módulo e os grafos ao lado das páginas (a raiz do site, ou a pasta de um teste); devolve os caminhos escritos. Nenhuma página os pede ainda (PC2)."""
    import shutil
    escritos = []
    (destino / ARQUIVO_DO_MODULO).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(RAIZ / "dashboard" / "web" / "comandos" / "caminho.js", destino / ARQUIVO_DO_MODULO)
    escritos.append(ARQUIVO_DO_MODULO)
    for arq in sorted(PASTA.glob("*.json")):
        js = caminhos_js(arq.stem)
        if js is not None:
            f = destino / arquivo_no_site(arq.stem)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(js, encoding="utf-8")
            escritos.append(arquivo_no_site(arq.stem))
    return escritos


def main(mapas: list[str]) -> int:
    from scripts.build_tactics_page import mapas_disponiveis
    PASTA.mkdir(parents=True, exist_ok=True)
    for mapa in mapas or sorted(set(mapas_disponiveis()) | {f.stem for f in (PASTA / "malha").glob("*.json")}):
        g = grafo_do_mapa(mapa)
        if g is None:
            print(f"{mapa}: sem malha e sem partida")
            continue
        texto = json.dumps(g, separators=(",", ":"), ensure_ascii=False)
        arquivo_dos_caminhos(mapa).write_text(texto, encoding="utf-8")
        print(f"{mapa}: {g['nc']} células, {g['na']} áreas, {len(g['e']) // 2} ligações, {len(texto) / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
