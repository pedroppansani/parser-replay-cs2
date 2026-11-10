"""C0b (Comandos na prancheta): os callouts do Pedro viram uma tabela de dados e imagens de conferência.

    py -3.12 -m pesquisa.comandos_c0b_callouts dados <pasta_das_imagens_do_pedro>     # grava data/reference/callouts_br.csv e preenche apelido_br da tabela da C0
    py -3.12 -m pesquisa.comandos_c0b_callouts conferencia <pasta_das_imagens_do_pedro> <pasta_de_saida>

As imagens do Pedro são material de terceiros e NÃO entram no repositório: só o nome e a posição que se tira delas. A leitura dos nomes (feita
olhando cada imagem) está em `pesquisa/callouts_br/<arquivo>.txt`, uma linha por rótulo: `x y texto` em pixels da imagem do Pedro (1024 x 1024);
"|" separa as linhas do mesmo rótulo e "@A"/"@B" é a letra vermelha do bombsite. O alinhamento de cada imagem com o radar do projeto (escala e
deslocamento, sem rotação) está em `pesquisa/callouts_br/alinhamento.json`.

Regras de leitura (Pedro): "A / B" no mesmo rótulo = apelidos do mesmo ponto; o que vai entre parênteses é qualificação; "↑" e "↓" no começo = em
cima / embaixo naquele ponto; o andar vem do nome do arquivo (`-cima`, `-baixo`); dúvida de leitura = "?" no nome, nunca chute.
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from metrics.lugares import lugar, rotulos, tabela_do_mapa, texto_do_lugar

RAIZ = Path(__file__).resolve().parent.parent
LEITURA = RAIZ / "pesquisa" / "callouts_br"
SAIDA_CSV = RAIZ / "data" / "reference" / "callouts_br.csv"
TABELA_C0 = RAIZ / "notas" / "investigacoes" / "2026-11-09-comandos-nomes-em-portugues.csv"
FONTE = "mapas de callouts do Pedro, 2026-11-09"
ARQUIVOS = [("de_ancient", "ancient"), ("de_anubis", "anubis"), ("de_cache", "cache"), ("de_dust2", "dust2"), ("de_inferno", "inferno"), ("de_mirage", "mirage"),
            ("de_overpass", "overpass"), ("de_train", "train"), ("de_nuke", "nuke-cima"), ("de_nuke", "nuke-baixo"), ("de_vertigo", "vertigo-cima"),
            ("de_vertigo", "vertigo-baixo")]
RAIO_BORDA_PX = 12            # raio (px do radar do projeto) em volta do ponto para dizer "na borda entre dois lugares"
# palavras que a imagem do Pedro quebra em duas linhas (a leitura as deixa em duas partes)
EMENDAS = {"Esquer dinha": "Esquerdinha", "Cami nhão": "Caminhão", "Campa nário": "Campanário", "BaseTR": "Base TR", "LigaCT": "Liga CT"}
# Decisões do Pedro sobre a leitura (2026-11-10): (arquivo, texto original) -> (nome, apelidos, qualificação) que valem no lugar do que a regra geral leria
AJUSTES = {
    **{(a, "Meio Falso (MF)"): ("Meio Falso", ["MF"], "") for a in ("mirage", "inferno", "vertigo-cima")},      # "(MF)" é apelido, não qualificação
    ("nuke-cima", "↓ Inferno(Hell)"): ("Inferno", ["Hell"], ""),                                              # "(Hell)" é apelido
    ("ancient", "Caixa do Quadrado/Jardim"): ("Caixa do Quadrado", ["Caixa do Jardim"], ""),                  # as duas valem
    ("train", "(Bomb) Antigo"): ("Antigo", ["Bomb Antigo"], ""),                                              # aceita "Bomb Antigo" e "Antigo"
    ("mirage", "Moddii"): ("Moddii", ["Mogi"], ""),                                                           # "Mogi" é apelido do Moddii (pedido do Pedro)
}
# observações por (arquivo, texto original): o que a leitura decidiu e quem decidiu
OBSERVACOES = {
    ("ancient", "Escanteio/ L"): "'L' fica como apelido (nome repetido: o leitor pergunta qual)",
    ("dust2", "L / Elevador"): "'L' fica como apelido (nome repetido: o leitor pergunta qual)",
    ("mirage", "L"): "dois 'L' (repetido: o leitor pergunta qual): um branco e grande (embaixo) e um cinza e pequeno (em cima, perto de Escada Rato)",
    ("mirage", "Palácio (ou Tapete A)"): "'ou Tapete A' é apelido do Palácio",
    **{(a, "Meio Falso (MF)"): "'MF' é apelido do Meio Falso (decisão do Pedro)" for a in ("mirage", "inferno", "vertigo-cima")},
    ("nuke-cima", "↓ Inferno(Hell)"): "'Hell' é apelido do Inferno (decisão do Pedro)",
    ("ancient", "Caixa do Quadrado/Jardim"): "valem 'Caixa do Quadrado' e 'Caixa do Jardim' (decisão do Pedro)",
    ("train", "(Bomb) Antigo"): "aceita 'Bomb Antigo' e 'Antigo' (decisão do Pedro)",
    ("mirage", "Moddii"): "'Mogi' é apelido do Moddii (pedido do Pedro; a imagem diz 'Moddii')",
}
# mapas que o Pedro já conferiu nas imagens (2026-11-10); os outros seguem `conferido = não` até ele avisar
CONFERIDOS = {"de_mirage", "de_dust2"}


def sem_acento(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def norma(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", sem_acento(s).lower())


def interpreta(linhas: list[str], arquivo: str) -> dict:
    """Um rótulo da leitura -> nome, apelidos, qualificação, vertical ('cima'/'baixo'/''), tipo, observações."""
    if linhas[0] in ("@A", "@B"):
        return {"tipo": "bombsite", "nome": linhas[0][1], "apelidos": [], "qualificacao": "", "vertical": "", "original": linhas[0], "obs": []}
    obs: list[str] = []
    texto = " ".join(l.strip() for l in linhas)
    original = texto
    texto = EMENDAS.get(texto, texto)
    partes = texto.split()
    if len(partes) >= 3 and all(len(p) == 1 for p in partes):          # letras espaçadas ("V a r a n d a")
        texto = EMENDAS.get("".join(partes), "".join(partes))
    vertical = ""
    if texto[:1] in "↑↓":
        vertical = "cima" if texto[0] == "↑" else "baixo"
        texto = texto[1:].strip()
    qual = ""
    if re.fullmatch(r"\((.*)\)", texto):
        texto = texto[1:-1]; obs.append("texto todo entre parênteses")
    elif (m := re.fullmatch(r"\((.*?)\)\s+(.+)", texto)):
        qual, texto = m.group(1), m.group(2)
    elif (m := re.fullmatch(r"(.*?)\s*\((.*)\)", texto)):
        texto, qual = m.group(1), m.group(2)
    nomes = [n.strip() for n in texto.split("/") if n.strip()]
    if qual.startswith("ou "):
        nomes.append(qual[3:].strip()); qual = ""
    if (arquivo, original) in AJUSTES:
        n0, apel, qual = AJUSTES[(arquivo, original)]
        nomes = [n0] + apel
    if (arquivo, original) in OBSERVACOES:
        obs.append(OBSERVACOES[(arquivo, original)])
    incerto = original.startswith("?")
    if incerto:
        obs.append("leitura incerta")
    return {"tipo": "lugar", "nome": nomes[0], "apelidos": nomes[1:], "qualificacao": qual, "vertical": vertical, "original": original, "obs": obs}


def le_arquivo(arquivo: str) -> list[dict]:
    saida = []
    for linha in (LEITURA / f"{arquivo}.txt").read_text(encoding="utf-8").splitlines():
        if not linha.strip() or linha.startswith("#"):
            continue
        x, y, resto = linha.split(" ", 2)
        d = interpreta(resto.split("|"), arquivo)
        d["px_pedro"] = (float(x), float(y))
        saida.append(d)
    return saida


# --- achar o centro exato do texto na imagem do Pedro (a leitura dá uma estimativa; o bloco de texto dá o centro) ------------------------------------
def blocos_de_texto(imagem: Path):
    import cv2
    im = cv2.imread(str(imagem)); hsv = cv2.cvtColor(im, cv2.COLOR_BGR2HSV)
    claro = ((im.min(axis=2) > 175) & (hsv[..., 1] < 60)).astype(np.uint8)
    verm = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 120) & (hsv[..., 2] > 140)).astype(np.uint8)
    m = cv2.dilate(claro | verm, cv2.getStructuringElement(cv2.MORPH_RECT, (13, 9)))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m)
    out = []
    for i in range(1, n):
        x, y, w, h, _ = st[i]
        if w <= 220 and h <= 100 and ((lab == i) & ((claro | verm) > 0)).sum() >= 40:
            out.append((x + w / 2, y + h / 2))
    return out


def ajusta_centro(rotulos_: list[dict], imagem: Path, maximo: float = 15.0) -> int:
    """Troca a estimativa pelo centro do bloco de texto mais perto (até `maximo` px). Devolve quantos foram ajustados."""
    if not imagem.exists():
        return 0
    blocos = blocos_de_texto(imagem); n = 0
    for r in rotulos_:
        x, y = r["px_pedro"]
        d, bx, by = min(((math.hypot(bx - x, by - y), bx, by) for bx, by in blocos), default=(1e9, 0, 0))
        if d <= maximo:
            r["px_pedro"] = (float(bx), float(by)); n += 1
    return n


def radar(mapa: str) -> dict:
    d = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    return {k: d[k] for k in ("scale_px_per_unit", "origin_x", "origin_y")}


def lugares_do_ponto(tab: dict | None, x: float, y: float, andar: int) -> tuple[str, list[str]]:
    """O nome de lugar da demo da célula do ponto (ou da mais perto, até 4 células) e os outros nomes num raio de RAIO_BORDA_PX (a borda)."""
    if not tab or andar >= len(tab["andares"]):
        return "", []
    amostras = [(x, y)] + [(x + RAIO_BORDA_PX * math.cos(a), y + RAIO_BORDA_PX * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
    nomes = [lugar(tab, px, py, andar) for px, py in amostras]
    prim = nomes[0]
    if prim is None:
        for r in range(1, 5):
            viz = [lugar(tab, x + r * tab["lado"] * math.cos(a), y + r * tab["lado"] * math.sin(a), andar) for a in np.linspace(0, 2 * math.pi, 16, endpoint=False)]
            viz = [v for v in viz if v]
            if viz:
                prim = Counter(viz).most_common(1)[0][0] + " (mais perto)"      # a célula do ponto não tem nome na demo: é o lugar mais perto
                break
        else:
            prim = ""
    base = prim.replace(" (mais perto)", "")
    return prim, sorted({n for n in nomes[1:] if n and n != base})


def monta(pasta_imagens: Path) -> list[dict]:
    alinh = json.loads((LEITURA / "alinhamento.json").read_text(encoding="utf-8"))
    linhas: list[dict] = []
    for mapa, arq in ARQUIVOS:
        a = alinh[f"{arq}.png"]; A = np.array(a["A"]); r = radar(mapa); tab = tabela_do_mapa(mapa)
        andar_nome = "baixo" if arq.endswith("-baixo") else ("cima" if arq.endswith("-cima") else "único")
        andar_ix = 1 if arq.endswith("-baixo") else 0
        rots = le_arquivo(arq); ajustados = ajusta_centro(rots, pasta_imagens / f"{arq}.png")
        for rr in rots:
            x, y = rr["px_pedro"]; xp, yp = A @ np.array([x, y, 1.0])
            X = r["origin_x"] + xp / r["scale_px_per_unit"]; Y = r["origin_y"] - yp / r["scale_px_per_unit"]
            prim, borda = lugares_do_ponto(tab, xp, yp, andar_ix)
            linhas.append({"mapa": mapa, "arquivo": arq, "andar": andar_nome, "nome": rr["nome"], "apelidos": rr["apelidos"], "qualificacao": rr["qualificacao"],
                           "vertical": rr["vertical"], "tipo": rr["tipo"], "texto_original": rr["original"].lstrip("?"), "x": round(X), "y": round(Y),
                           "px_x": round(float(xp), 1), "px_y": round(float(yp), 1), "lugar_da_demo": prim, "lugares_na_borda": borda,
                           "tem_tabela_da_demo": tab is not None, "obs": rr["obs"]})
        print(f"{arq}: {len(rots)} rótulos ({ajustados} com o centro ajustado pelo bloco de texto)")
    # nomes repetidos no mesmo mapa (os dois andares contam juntos); apelido que é nome de outro rótulo também conta
    por_mapa: dict = defaultdict(lambda: defaultdict(list))
    for i, l in enumerate(linhas):
        if l["tipo"] == "lugar":
            for n in [l["nome"]] + l["apelidos"]:
                por_mapa[l["mapa"]][norma(n) + ("|" + norma(l["qualificacao"]) if l["qualificacao"] and n == l["nome"] else "")].append(i)
    for l in linhas:
        l["repete_no_mapa"] = ""
        if l["tipo"] == "lugar":
            for n in [l["nome"]] + l["apelidos"]:
                chave = norma(n) + ("|" + norma(l["qualificacao"]) if l["qualificacao"] and n == l["nome"] else "")
                if len(set(por_mapa[l["mapa"]][chave])) > 1:
                    l["repete_no_mapa"] = f"{n} ({len(set(por_mapa[l['mapa']][chave]))}x)"; break
    return linhas


def mostra(l: dict) -> str:
    """Como o rótulo se escreve: seta, nome, (qualificação), e os apelidos."""
    s = {"cima": "↑ ", "baixo": "↓ ", "": ""}[l["vertical"]] + l["nome"] + (f" ({l['qualificacao']})" if l["qualificacao"] else "")
    return s + "".join(" / " + a for a in l["apelidos"])


def grava_dados(linhas: list[dict]) -> None:
    SAIDA_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(SAIDA_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["mapa", "andar", "nome", "apelidos", "qualificacao", "posicao_vertical", "tipo", "x", "y", "lugar_da_demo", "lugares_na_borda", "repete_no_mapa",
                    "texto_original", "observacao", "fonte", "conferido"])
        for l in linhas:
            w.writerow([l["mapa"], l["andar"], l["nome"], " / ".join(l["apelidos"]), l["qualificacao"], l["vertical"], l["tipo"], l["x"], l["y"],
                        l["lugar_da_demo"] if l["tem_tabela_da_demo"] else "(mapa sem tabela da demo)", " / ".join(l["lugares_na_borda"]), l["repete_no_mapa"],
                        l["texto_original"], "; ".join(l["obs"]), FONTE, "sim" if l["mapa"] in CONFERIDOS else "não"])


def preenche_apelido_br(linhas: list[dict]) -> tuple[int, int]:
    """Põe, na coluna apelido_br da tabela da C0, os nomes do Pedro que caem em cada lugar da demo (sem apagar o que já havia). Devolve (linhas alteradas, nomes postos)."""
    por_lugar: dict = defaultdict(list)
    for l in linhas:
        if l["tipo"] == "lugar" and l["lugar_da_demo"] and l["tem_tabela_da_demo"] and not l["lugar_da_demo"].endswith("(mais perto)"):
            por_lugar[(l["mapa"], l["lugar_da_demo"])].append(mostra(l))
    with open(TABELA_C0, encoding="utf-8-sig", newline="") as f:
        linhas_csv = list(csv.reader(f, delimiter=";"))
    cab = linhas_csv[0]; i_ap = cab.index("apelido_br"); alteradas = postos = 0
    for r in linhas_csv[1:]:
        novos = por_lugar.get((r[0], r[1]), [])
        antigos = [] if r[i_ap].strip() in ("", "?") else [a.strip() for a in r[i_ap].split(" / ")]
        ja = {norma(a) for a in antigos}; acresc = []
        for nome in novos:
            for pedaco in [p.strip() for p in nome.split(" / ")]:
                if norma(pedaco) not in ja:
                    ja.add(norma(pedaco)); acresc.append(pedaco)
        if acresc:
            r[i_ap] = " / ".join(antigos + acresc); alteradas += 1; postos += len(acresc)
    with open(TABELA_C0, "w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f, delimiter=";").writerows(linhas_csv)
    return alteradas, postos


# --- imagens de conferência: o radar DO PROJETO, os pontos do Pedro e o contorno das áreas da demo ----------------------------------------------------
def conferencia(linhas: list[dict], pasta_saida: Path) -> None:
    import base64, io
    import cv2
    from PIL import Image, ImageDraw, ImageFont
    pasta_saida.mkdir(parents=True, exist_ok=True)
    Z = 3
    f_nome = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 21)
    f_area = ImageFont.truetype("C:/Windows/Fonts/ariali.ttf", 18)
    f_tit = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 30)
    f_bomb = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 38)
    for mapa, arq in ARQUIVOS:
        sel = [l for l in linhas if l["arquivo"] == arq]
        baixo = arq.endswith("-baixo"); andar_ix = 1 if baixo else 0
        d = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
        if baixo:
            im = Image.open(io.BytesIO(base64.b64decode(d["layers"]["lower"].split(",", 1)[1]))).convert("RGBA")
        else:
            im = Image.open(RAIZ / "assets" / "radars" / f"{mapa}.png").convert("RGBA") if (RAIZ / "assets" / "radars" / f"{mapa}.png").exists() \
                else Image.open(io.BytesIO(base64.b64decode(d["image"].split(",", 1)[1]))).convert("RGBA")
        fundo = Image.new("RGBA", im.size, (22, 24, 28, 255)); fundo.alpha_composite(im)
        base = fundo.convert("RGB").resize((1024 * Z, 1024 * Z), Image.LANCZOS)
        tab = tabela_do_mapa(mapa)
        # contorno das áreas da demo (onde o nome do lugar muda de uma célula para a vizinha)
        arr = np.array(base)
        if tab and andar_ix < len(tab["andares"]):
            lado = tab["lado"]; n = 1024 // lado + 1; idx = -np.ones((n, n), int)
            for cy, rle in tab["andares"][andar_ix].items():
                for i in range(0, len(rle), 3):
                    idx[int(cy), rle[i]:rle[i] + rle[i + 2]] = rle[i + 1]
            grande = np.kron(idx, np.ones((lado * Z, lado * Z), int))[:1024 * Z, :1024 * Z]
            borda = np.zeros(grande.shape, bool)
            borda[:, 1:] |= grande[:, 1:] != grande[:, :-1]; borda[1:, :] |= grande[1:, :] != grande[:-1, :]
            borda &= grande >= 0
            arr[borda] = (255, 150, 40)
        img = Image.fromarray(arr); dr = ImageDraw.Draw(img)
        # nomes das áreas da demo (laranja, itálico) na primeira âncora de cada nome
        if tab and andar_ix < len(tab["andares"]):
            for ix, pts in rotulos(tab)[andar_ix]:
                if pts:
                    t = texto_do_lugar(tab["nomes"][ix]); x, y = pts[0][0] * Z, pts[0][1] * Z
                    dr.text((x, y), t, font=f_area, fill=(255, 170, 70), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        # os pontos do Pedro (ciano), com o nome ao lado; posição do texto escolhida para não cobrir outro
        colocados: list = []
        def cabe(b):
            return all(b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3] for o in colocados)
        for l in sorted(sel, key=lambda l: (l["tipo"] != "bombsite", -len(mostra(l)))):
            cx, cy = l["px_x"] * Z, l["px_y"] * Z
            if l["tipo"] == "bombsite":
                dr.text((cx, cy), l["nome"], font=f_bomb, fill=(255, 60, 60), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0))
                colocados.append((cx - 14, cy - 14, cx + 14, cy + 14)); continue
            txt = mostra(l) + ("?" if "leitura incerta" in l["obs"] else "")
            tb = dr.textbbox((0, 0), txt, font=f_nome, anchor="lt"); w, h = tb[2] - tb[0], tb[3] - tb[1]
            cands = [(0, -16), (0, 0)] + [(dx, dy) for dy in (-30, 30, -48, 48, -66, 66) for dx in (0, -w * .6, w * .6)] + [(w * .6 + 10, 0), (-w * .6 - 10, 0)]
            escolhido = None
            for dx, dy in cands:
                b = (cx + dx - w / 2 - 3, cy + dy - h / 2 - 3, cx + dx + w / 2 + 3, cy + dy + h / 2 + 3)
                if cabe(b):
                    escolhido = (dx, dy, b); break
            if escolhido is None:
                dx, dy = 0, 0; b = (cx - w / 2 - 3, cy - h / 2 - 3, cx + w / 2 + 3, cy + h / 2 + 3); escolhido = (dx, dy, b)
            dx, dy, b = escolhido; colocados.append(b)
            if abs(dx) + abs(dy) > 4:
                dr.line((cx, cy, cx + dx, cy + dy), fill=(0, 220, 255), width=1)
            dr.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(0, 220, 255), outline=(0, 0, 0))
            dr.text((cx + dx, cy + dy), txt, font=f_nome, fill=(255, 255, 255), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        # corta a margem vazia: a caixa do mapa e dos pontos, com folga
        ys, xs = np.nonzero(np.array(im)[..., 3] > (200 if baixo else 128))     # no andar de baixo só o que é opaco (o de cima aparece desbotado)
        xs_p = [l["px_x"] for l in sel]; ys_p = [l["px_y"] for l in sel]
        x0, x1 = min(xs.min(), min(xs_p) - 60) - 40, max(xs.max(), max(xs_p) + 60) + 40
        y0, y1 = min(ys.min(), min(ys_p) - 30) - 50, max(ys.max(), max(ys_p) + 30) + 40
        img = img.crop((int(max(0, x0) * Z), int(max(0, y0) * Z), int(min(1024, x1) * Z), int(min(1024, y1) * Z)))
        dt = ImageDraw.Draw(img)
        dt.text((16, 12), f"{mapa} · {'andar de baixo' if baixo else ('andar de cima' if arq.endswith('-cima') else 'um andar')} · {len(sel)} pontos", font=f_tit, fill=(235, 235, 235), stroke_width=2, stroke_fill=(0, 0, 0))
        dt.text((16, 52), "radar do projeto · ciano = ponto do Pedro · laranja = área da demo", font=f_nome, fill=(200, 200, 200), stroke_width=2, stroke_fill=(0, 0, 0))
        img.save(pasta_saida / f"{arq}-conferencia.png")
        print("conferência:", arq, len(sel), "pontos")


def main() -> None:
    modo = sys.argv[1]; pasta = Path(sys.argv[2])
    linhas = monta(pasta)
    if modo == "dados":
        grava_dados(linhas); alt, postos = preenche_apelido_br(linhas)
        print(f"{len(linhas)} pontos em {SAIDA_CSV}; apelido_br: {postos} nomes em {alt} lugares da demo")
    else:
        conferencia(linhas, Path(sys.argv[3]))


if __name__ == "__main__":
    main()
