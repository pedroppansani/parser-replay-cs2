"""PC0: os exemplos do Pedro na Mirage, com o caminho do `.nav` desenhado sobre o radar e o tempo de cada opção.

    py -3.12 -m scripts.pc0.exemplos PASTA_DOS_NAV_JSON PASTA_DE_SAIDA

Pares: Base TR -> Meio (12,0 s reais contra 8,0 s da reta), CT -> L, Janela Mercado -> L e Janelão -> L. Para cada um: a reta, o caminho pelo grafo (com o fio puxado), o tempo real da C3 (se o par tem
amostra), a lista das quedas (centro a centro, mais de 40 u para baixo) e um PNG no radar. Sem nada inventado: o desenho é o caminho do grafo, e onde não há caminho o par diz isso."""
from __future__ import annotations

import base64
import io
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.build_tactics_page import RADARS_DIR
from scripts.build_tempos import nos_de_pontos
from scripts.comandos_contexto import contexto
from scripts.build_tempos import rastros
from scripts.pc0.compara_tempos import V, z_dos_nos
from scripts.pc0.grafo_corpus import GrafoCorpus
from scripts.pc0.grafo_nav import Grafo

MAPA = "de_mirage"
PARES = [("Base TR", "Meio"), ("CT", "L"), ("Janela Mercado", "L"), ("Janelão", "L")]


def nos_por_nome(pontos: list[dict]) -> dict[str, list[dict]]:
    """O nó de cada nome do Pedro (um nome pode ter mais de um ponto: o nó é o do grupo)."""
    nos = {n["chave"]: n for n in nos_de_pontos(pontos)}
    saida: dict[str, list[dict]] = {}
    for p in pontos:
        chaves = [k for k in nos if str(int(p["id"].split(":")[1])) in k.split("+")]
        saida.setdefault(p["nome"], []).extend(nos[k] for k in chaves)
    return saida


def radar() -> tuple[Image.Image, dict]:
    d = json.loads((RADARS_DIR / f"{MAPA}.json").read_text(encoding="utf-8"))
    img = Image.open(io.BytesIO(base64.b64decode(d["image"].split(",", 1)[1]))).convert("RGBA")
    return img, d


def px(d: dict, x: float, y: float) -> tuple[float, float]:
    return (x - d["origin_x"]) * d["scale_px_per_unit"], (d["origin_y"] - y) * d["scale_px_per_unit"]


def caminho_pontos(g: Grafo, p, q):
    """Os pontos do caminho com o fio puxado (o mesmo de `comprimento_entre_pontos`), para desenhar."""
    a, b = g.area_do_ponto(*p), g.area_do_ponto(*q)
    r = g.caminho(a, b) if a is not None and b is not None else None
    if r is None:
        return None
    rota, _ = r
    pts = [(p[0], p[1], g.cent[a][2])] + [g.cent[i] for i in rota[1:-1]] + [(q[0], q[1], g.cent[b][2])]
    fora, i = [pts[0]], 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1 and not g.visivel(rota, pts[i], pts[j]):
            j -= 1
        fora.append(pts[j])
        i = j
    quedas = [(g.cent[rota[k]], g.cent[rota[k + 1]]) for k in range(len(rota) - 1) if g.cent[rota[k + 1]][2] - g.cent[rota[k]][2] < -40]
    return rota, fora, quedas


def main(pasta: Path, saida: Path) -> None:
    saida.mkdir(parents=True, exist_ok=True)
    ctx = contexto(MAPA, so_conferidos=True)
    nos = nos_por_nome(ctx["pontos"])
    t = json.loads(Path(f"data/tempos/{MAPA}.json").read_text(encoding="utf-8"))
    pares = {(a, b): (p25, med, p75, casos, partidas) for a, b, p25, med, p75, casos, partidas in t["pontos"]}
    zn = z_dos_nos(t["nos"], MAPA)
    g = Grafo(pasta / f"{MAPA}.json")
    base, d = radar()
    gc = GrafoCorpus(rastros(MAPA))
    relato = []
    for na, nb in PARES:
        if na not in nos or nb not in nos:
            relato.append({"par": f"{na} -> {nb}", "erro": "nome não está nos pontos do Pedro"})
            continue
        a, b = nos[na][0], nos[nb][0]
        pa, pb = (a["x"], a["y"], zn.get(a["chave"])), (b["x"], b["y"], zn.get(b["chave"]))
        reta = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
        r = caminho_pontos(g, pa, pb)
        real = pares.get((a["chave"], b["chave"]))
        item = {"par": f"{na} -> {nb}", "reta_u": round(reta), "reta_s": round(reta / V, 1), "real": real}
        img = base.copy()
        dr = ImageDraw.Draw(img, "RGBA")
        dr.line([px(d, pa[0], pa[1]), px(d, pb[0], pb[1])], fill=(255, 255, 255, 150), width=2)
        if r is None:
            item["caminho"] = "sem caminho no grafo"
        else:
            rota, pts, quedas = r
            comp = sum(math.dist(pts[k], pts[k + 1]) for k in range(len(pts) - 1))
            item.update({"caminho_u": round(comp), "caminho_s": round(comp / V, 1), "areas": len(rota), "quedas": len(quedas), "quedas_dz": [round(q1[2] - q0[2]) for q0, q1 in quedas]})
            dr.line([px(d, x, y) for x, y, _ in pts], fill=(255, 190, 40, 255), width=4)
            for q0, q1 in quedas:
                x1, y1 = px(d, *q0[:2])
                dr.ellipse([x1 - 7, y1 - 7, x1 + 7, y1 + 7], outline=(255, 60, 60, 255), width=3)
        rc = gc.comprimento_entre_pontos(pa, pb)
        if rc is None:
            item["corpus"] = "sem caminho no grafo do corpus"
        else:
            rota_c, comp_c = rc
            item["corpus_u"], item["corpus_s"] = round(comp_c), round(comp_c / V, 1)
            dr.line([px(d, *gc.centro[c][:2]) for c in rota_c], fill=(255, 80, 220, 255), width=3)
        for (xx, yy), cor in ((px(d, pa[0], pa[1]), (80, 200, 255, 255)), (px(d, pb[0], pb[1]), (120, 255, 120, 255))):
            dr.ellipse([xx - 8, yy - 8, xx + 8, yy + 8], fill=cor, outline=(0, 0, 0, 255), width=2)
        txt = f"{na} -> {nb}: reta {item['reta_s']} s"
        if r is not None:
            txt += f"  nav {item['caminho_s']} s"
        if rc is not None:
            txt += f"  corpus {item['corpus_s']} s"
        txt += f"  real {real[1]} s ({real[3]} casos)" if real else "  real: sem amostra"
        dr.rectangle([0, 0, 1024, 30], fill=(0, 0, 0, 200))
        dr.text((8, 8), txt, fill=(255, 255, 255, 255))
        img.convert("RGB").save(saida / f"{na.replace(' ', '_')}_para_{nb.replace(' ', '_')}.png")
        relato.append(item)
    (saida / "exemplos.json").write_text(json.dumps(relato, ensure_ascii=False, indent=1), encoding="utf-8")
    for it in relato:
        print(it)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
