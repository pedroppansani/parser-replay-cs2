"""
Calibra e prepara a imagem de radar de um mapa para uso no painel.

O problema: uma imagem de radar não vem com a informação de como os pixels dela
correspondem às coordenadas do jogo. O awpy distribui essa tabela, mas o
download dos assets exige rede liberada — e mesmo com ela, um radar baixado de
outra fonte (recortado, redimensionado, com grade por cima) não bateria com a
tabela oficial.

A solução aqui não depende de tabela nenhuma: as posições reais dos jogadores
são o gabarito. Jogador só anda onde há chão, então a transformação correta é a
que faz a nuvem de posições da partida cair em cima da área caminhável do radar.
O script faz uma busca (grosseira e depois fina) por escala e deslocamento,
maximizando essa sobreposição, e reporta o quanto conseguiu encaixar — se a
cobertura vier baixa, a calibração não é confiável e o painel avisa em vez de
desenhar torto.

Também retrata a imagem para a paleta do painel: o radar original é verde
saturado sobre preto, o que brigaria com o resto da página.

Uso:
    python -m scripts.prepare_radar de_ancient assets/radars/de_ancient_raw.png --match match_01
"""
from __future__ import annotations

import argparse
import base64
import json
from io import BytesIO
from pathlib import Path

import numpy as np
import polars as pl
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RADAR_DIR = PROJECT_ROOT / "assets" / "radars"


def walkable_mask(img: Image.Image) -> np.ndarray:
    """Máscara do que é chão no radar.

    Pega o corpo esverdeado do mapa e também os blocos claros (objetos, caixas),
    mas ignora o preto do fundo e a grade fina de referência.
    """
    a = np.array(img.convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    green_body = (g > r + 6) & (g > b + 6) & (g > 32)
    light_block = (r > 90) & (g > 90) & (b > 90)
    return green_body | light_block


def fit_transform(mask: np.ndarray, pts: np.ndarray, weights: np.ndarray) -> dict:
    """Acha escala e deslocamento que colocam as posições sobre a área caminhável.

    Parametrização: px = (wx - ox) * s ; py = (oy - wy) * s  (y invertido, porque
    a imagem cresce para baixo e o mundo cresce para cima).
    """
    h, w = mask.shape
    wx, wy = pts[:, 0], pts[:, 1]

    def coverage(s: float, ox: float, oy: float) -> float:
        px = ((wx - ox) * s).astype(np.int32)
        py = ((oy - wy) * s).astype(np.int32)
        inside = (px >= 0) & (px < w) & (py >= 0) & (py < h)
        if not inside.any():
            return 0.0
        hit = np.zeros(len(px), dtype=bool)
        hit[inside] = mask[py[inside], px[inside]]
        return float((weights * hit).sum() / weights.sum())

    best = {"score": -1.0}

    # etapa grosseira: varre escalas plausíveis e desloca a nuvem pela imagem
    span_x, span_y = wx.max() - wx.min(), wy.max() - wy.min()
    for s in np.linspace(0.6 * w / max(span_x, span_y), 1.25 * w / max(span_x, span_y), 24):
        for ox in np.linspace(wx.min() - span_x * 0.35, wx.min() + span_x * 0.2, 26):
            for oy in np.linspace(wy.max() - span_y * 0.2, wy.max() + span_y * 0.35, 26):
                sc = coverage(s, ox, oy)
                if sc > best["score"]:
                    best = {"score": sc, "s": float(s), "ox": float(ox), "oy": float(oy)}

    # etapa fina: refina em torno do melhor candidato, duas vezes
    for shrink in (0.12, 0.03):
        s0, ox0, oy0 = best["s"], best["ox"], best["oy"]
        for s in np.linspace(s0 * (1 - shrink), s0 * (1 + shrink), 15):
            for ox in np.linspace(ox0 - span_x * shrink, ox0 + span_x * shrink, 17):
                for oy in np.linspace(oy0 - span_y * shrink, oy0 + span_y * shrink, 17):
                    sc = coverage(s, ox, oy)
                    if sc > best["score"]:
                        best = {"score": sc, "s": float(s), "ox": float(ox), "oy": float(oy)}

    return best


def recolor(img: Image.Image) -> Image.Image:
    """Retrata o radar para a paleta do painel.

    O original é verde saturado sobre preto. Vira um azul-ardósia escuro,
    dessaturado, que convive com os acentos azul/laranja do resto da página sem
    puxar a atenção para si — o radar é o palco, não o assunto.
    """
    a = np.array(img.convert("RGB")).astype(np.float32) / 255.0
    lum = a.max(axis=2)

    out = np.zeros_like(a)
    floor = np.array([0.086, 0.106, 0.133])  # fundo fora do mapa
    low = np.array([0.161, 0.196, 0.239])  # chão
    high = np.array([0.478, 0.541, 0.612])  # objetos e bordas claras

    t = np.clip((lum - 0.10) / 0.55, 0, 1)[..., None]
    body = low + (high - low) * t
    is_map = (lum > 0.12)[..., None]
    out = np.where(is_map, body, floor)

    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def build(map_name: str, source: Path, match_id: str, crop: int = 0) -> Path:
    img = Image.open(source)
    if crop:
        img = img.crop((crop, crop, img.width - crop, img.height - crop))

    mask = walkable_mask(img)

    heat = pl.read_parquet(PROJECT_ROOT / "data" / "processed" / match_id / "heatmap_bins.parquet")
    pts = np.stack([heat["x"].to_numpy(), heat["y"].to_numpy()], axis=1).astype(np.float64)
    weights = heat["samples"].to_numpy().astype(np.float64)

    fit = fit_transform(mask, pts, weights)

    styled = recolor(img)
    buf = BytesIO()
    styled.save(buf, format="PNG", optimize=True)
    data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    RADAR_DIR.mkdir(parents=True, exist_ok=True)
    styled.save(RADAR_DIR / f"{map_name}.png")

    meta = {
        "map": map_name,
        "width": img.width,
        "height": img.height,
        "scale_px_per_unit": fit["s"],
        "origin_x": fit["ox"],
        "origin_y": fit["oy"],
        "coverage": fit["score"],
        "image": data_uri,
    }
    out = RADAR_DIR / f"{map_name}.json"
    out.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")

    print(f"{map_name}: {img.width}x{img.height}px")
    print(f"  escala   {fit['s']:.5f} px por unidade de jogo")
    print(f"  origem   x={fit['ox']:.1f}  y={fit['oy']:.1f}")
    print(f"  cobertura {100 * fit['score']:.1f}% das posições caem em chão do radar")
    print(f"  {len(data_uri) / 1024:.0f} KB embutidos")
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Calibra e prepara um radar de mapa para o painel.")
    p.add_argument("map_name", type=str, help="Nome do mapa, ex: de_ancient")
    p.add_argument("source", type=Path, help="Imagem do radar")
    p.add_argument("--match", type=str, required=True, help="Partida usada como gabarito de calibração")
    p.add_argument("--crop", type=int, default=0, help="Pixels a recortar de cada borda (réguas/moldura)")
    args = p.parse_args()
    build(args.map_name, args.source, args.match, args.crop)


if __name__ == "__main__":
    main()
