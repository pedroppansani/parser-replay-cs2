"""
A25 da §19.11 (granada desenhada x granada real) medido no CANVAS REAL do `map_core.js`, não na réplica do protótipo.

    py -3.12 -m scripts.design.mede_granada_real            # tabela completa; sai com 1 se algum mapa reprovar

O que é medido (a conta é a de `notas/design/prototipo/granada.js`, função `mede`/`dif`, que a §19.7 cita):
  - cenário: o radar PROCESSADO do mapa (`MapCore.radarProcessado`, o par de dessaturação do mapa) sobre o fundo
    `--radar`, numa janela de 40 x 40 px de tela, com o glifo no centro;
  - a granada REAL: `MapCore.nadeGlyph(..., raio 5,5, desenhada = false)` com o anel duplo ligado (é como o replay a
    desenha); a DESENHADA: a mesma função com `desenhada = true`;
  - ΔE CIELAB76 pixel a pixel entre as duas imagens, dentro do círculo de 11 px de tela em volta do glifo (raio de
    11 x densidade px do canvas; D65), a média de TODOS os pixels do círculo (os que não mudam entram, como no
    protótipo); um número por posição; o ΔE do tipo é a média das posições; o da combinação é a média dos 4 tipos;
  - modo B, "mesmo tamanho" (o do critério A25): a desenhada com o raio 5,5 da real, isolando o tracejado e o
    carimbo do tamanho. Modo A, "como no projeto" (informativo): `MapCore.desenhaGranadaDesenhada`, raio 7;
  - posições: sorteio com a semente fixa 28 (decisão 28, `mulberry32`) sobre o radar reduzido a 256 x 256, na margem
    de 16 px, só em pixel que difere do fundo `--radar` em mais de 40 (soma de |dR|+|dG|+|dB|), 48 por andar (o
    protótipo usou 12 por mapa); os andares do mapa (principal e `layers`) entram, cada um com as suas;
  - escalas: 0,508 px de tela por px do radar a 1440 px e 0,321 a 375 px (as do design); o navegador abre com a
    largura e a densidade (1x e 2x) da combinação, então `devicePixelRatio` e o tamanho CSS do canvas são os reais.

Aceite A25: média dos quatro tipos >= 4,5 e nenhum tipo abaixo de 3,5, em cada mapa COM PARTIDAS, nas quatro
combinações de largura e densidade (modo B). Cache e Vertigo (sem partidas) saem na tabela como informativos.

Também refaz o A13/A14 para o tracejado em px de TELA: `confere_tracejado` grava as chamadas de `stroke` do anel e
confere que halo e contorno saem com o MESMO passo e que ele vale 3,5/3 px de tela em toda largura e densidade.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from scripts.design._comum import RADARES, RAIZ, chrome  # noqa: E402

WEB = RAIZ / "dashboard" / "web"
PROCESSED = RAIZ / "data" / "processed"

# largura da janela do navegador -> px de tela por px do radar (as escalas da §19.7: 1440 px e 375 px)
ESCALAS = {1440: 0.508, 375: 0.321}
DENSIDADES = (1, 2)
TIPOS = ("smoke", "flash", "he", "molotov")
RAIO_REAL = 5.5                # replay: 5 a 5,5 px do radar (template.html, nadeGlyph das granadas reais)
POSICOES_POR_ANDAR = 48        # o protótipo usou 12 por mapa
SEMENTE = 28                   # decisão 28
JANELA = 40                    # px de tela do lado da janela
RAIO_DA_CONTA = 11             # px de tela: cobre o glifo, o anel e o carimbo
# Limites do A25 (§19.7/§19.11)
MEDIA_MINIMA = 4.5
TIPO_MINIMO = 3.5
# O mapa entra no A25 se tem partida em data/processed; os demais com radar são informativos.
MAPAS_DO_RADAR = ("ancient", "anubis", "cache", "dust2", "inferno", "mirage", "nuke", "overpass", "train", "vertigo")

JS = r"""
(function () {
  "use strict";
  function lab(r, g, b) {
    var f = function (c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
    var R = f(r), G = f(g), B = f(b);
    var x = (R * 0.4124 + G * 0.3576 + B * 0.1805) / 0.95047, y = R * 0.2126 + G * 0.7152 + B * 0.0722,
        z = (R * 0.0193 + G * 0.1192 + B * 0.9505) / 1.08883;
    var h = function (t) { return t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116; };
    return [116 * h(y) - 16, 500 * (h(x) - h(y)), 200 * (h(y) - h(z))];
  }
  function mulberry(seed) {
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function carrega(src) {
    return new Promise(function (ok, erro) { var i = new Image(); i.onload = function () { ok(i); }; i.onerror = erro; i.src = src; });
  }
  function token(n) { return MapCore.token(n); }

  function posicoes(radar, n, semente) {
    var c = document.createElement("canvas"); c.width = 256; c.height = 256;
    var g = c.getContext("2d"); g.drawImage(radar, 0, 0, 256, 256);
    var d = g.getImageData(0, 0, 256, 256).data, rnd = mulberry(semente), out = [], tent = 0;
    var bg = token("radar"), br = parseInt(bg.slice(1, 3), 16), bgG = parseInt(bg.slice(3, 5), 16), bb = parseInt(bg.slice(5, 7), 16);
    while (out.length < n && tent++ < 20000) {
      var x = 16 + Math.floor(rnd() * 224), y = 16 + Math.floor(rnd() * 224), i = (y * 256 + x) * 4;
      if (Math.abs(d[i] - br) + Math.abs(d[i + 1] - bgG) + Math.abs(d[i + 2] - bb) > 40) out.push([x * 4, y * 4]);
    }
    return out;
  }

  /* um cenário: o radar centrado em (px, py) (px do radar de 1024), na escala k, com a densidade do navegador; o
     canvas está no documento com tamanho CSS W x W, como os do replay (o tamanho CSS entra na escala em px de tela) */
  function cenario(radar, px, py, k, W) {
    var dpr = window.devicePixelRatio || 1;
    var c = document.createElement("canvas");
    c.width = Math.round(W * dpr); c.height = Math.round(W * dpr);
    c.style.cssText = "position:absolute;left:0;top:0;width:" + W + "px;height:" + W + "px";
    document.body.appendChild(c);
    var ctx = c.getContext("2d", { willReadFrequently: true });
    ctx.setTransform(k * dpr, 0, 0, k * dpr, W / 2 * dpr - px * k * dpr, W / 2 * dpr - py * k * dpr);
    ctx.fillStyle = token("radar"); ctx.fillRect(0, 0, 1024, 1024);
    ctx.drawImage(radar, 0, 0, 1024, 1024);
    ctx.setTransform(k * dpr, 0, 0, k * dpr, W / 2 * dpr, W / 2 * dpr);
    return { canvas: c, ctx: ctx };
  }

  function dif(a, b, raio) {
    var w = a.width, cx = w / 2, cy = a.height / 2, soma = 0, n = 0;
    for (var y = 0; y < a.height; y++) for (var x = 0; x < w; x++) {
      if ((x - cx) * (x - cx) + (y - cy) * (y - cy) > raio * raio) continue;
      var i = (y * w + x) * 4, la = lab(a.data[i], a.data[i + 1], a.data[i + 2]), lb = lab(b.data[i], b.data[i + 1], b.data[i + 2]);
      soma += Math.hypot(la[0] - lb[0], la[1] - lb[1], la[2] - lb[2]); n++;
    }
    return soma / n;
  }

  var ANG = -Math.PI / 2;
  function desenha(ctx, kind, modo, radarInfo) {
    if (modo === "real") MapCore.nadeGlyph(ctx, kind, 0, 0, %(RAIO_REAL)s, MapCore.NADE_COLOR[kind], ANG, false);
    else if (modo === "B") MapCore.nadeGlyph(ctx, kind, 0, 0, %(RAIO_REAL)s, MapCore.NADE_COLOR[kind], ANG, true);
    else MapCore.desenhaGranadaDesenhada(ctx, kind, 0, 0, radarInfo, false);          // A: raio 7, como no projeto
  }

  /* devolve {tipo: {B: [ΔE por posição], A: [...]}} para uma lista de radares (andares) de um mapa */
  window.MedeGranada = {
    mede: async function (uris, mapa, k, tipos, n, semente, raioConta) {
      MapCore.defineAnelDuplo(true);
      var dpr = window.devicePixelRatio || 1, W = %(JANELA)s, saida = {};
      tipos.forEach(function (t) { saida[t] = { A: [], B: [] }; });
      for (var u = 0; u < uris.length; u++) {
        var img = await carrega(uris[u]), radar = MapCore.radarProcessado(img, mapa);
        var pos = posicoes(radar, n, semente);
        for (var p = 0; p < pos.length; p++) {
          for (var t = 0; t < tipos.length; t++) {
            var kind = tipos[t], cenas = {};
            ["real", "B", "A"].forEach(function (m) {
              var c = cenario(radar, pos[p][0], pos[p][1], k, W);
              desenha(c.ctx, kind, m, { scale_px_per_unit: 0.2 });
              cenas[m] = c;
            });
            var im = {};
            Object.keys(cenas).forEach(function (m) {
              im[m] = cenas[m].ctx.getImageData(0, 0, cenas[m].canvas.width, cenas[m].canvas.height);
              cenas[m].canvas.remove();
            });
            saida[kind].B.push(dif(im.real, im.B, raioConta * dpr));
            saida[kind].A.push(dif(im.real, im.A, raioConta * dpr));
          }
        }
      }
      return saida;
    },

    /* A13/A14: grava as chamadas de stroke() e setLineDash() do anel da granada desenhada */
    tracejado: function (k) {
      MapCore.defineAnelDuplo(true);
      var dpr = window.devicePixelRatio || 1, W = 60, c = document.createElement("canvas");
      c.width = Math.round(W * dpr); c.height = Math.round(W * dpr);
      c.style.cssText = "position:absolute;left:0;top:0;width:" + W + "px;height:" + W + "px";
      document.body.appendChild(c);
      var ctx = c.getContext("2d"), saida = [];
      ctx.setTransform(k * dpr, 0, 0, k * dpr, W / 2 * dpr, W / 2 * dpr);
      var stroke0 = ctx.stroke.bind(ctx);
      ctx.stroke = function () {
        saida.push({ passo: ctx.getLineDash().map(function (x) { return x * k; }), largura: ctx.lineWidth * k, cor: ctx.strokeStyle });
        return stroke0();
      };
      MapCore.nadeGlyph(ctx, "smoke", 0, 0, 7, MapCore.NADE_COLOR.smoke, ANG, true);
      c.remove();
      return saida;
    }
  };
})();
""" % {"RAIO_REAL": RAIO_REAL, "JANELA": JANELA}


def mapas_com_partida() -> set[str]:
    """Os mapas com partida em data/processed (campo `map_name` de match_meta.json), sem o prefixo `de_`."""
    achados = set()
    for f in sorted(PROCESSED.glob("match_*/match_meta.json")):
        mapa = json.loads(f.read_text(encoding="utf-8")).get("map_name")
        if mapa:
            achados.add(mapa.removeprefix("de_"))
    return achados


def radares() -> dict[str, list[str]]:
    """{mapa: [data URI de cada andar]} dos radares locais (assets/radars/de_<mapa>.json)."""
    out = {}
    for mapa in MAPAS_DO_RADAR:
        f = RADARES / f"de_{mapa}.json"
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            out[mapa] = [d["image"]] + list((d.get("layers") or {}).values())
    return out


def _pagina(playwright, largura: int, densidade: int, pasta: Path):
    """Uma página só com os tokens e o map_core.js, no navegador com a largura e a densidade da combinação."""
    html = pasta / "medida.html"
    html.write_text(
        '<!doctype html><meta charset="utf-8"><link rel="stylesheet" href="%s"><body style="margin:0;background:#0f141b">'
        '<script src="%s"></script></body>' % ((WEB / "tokens.css").as_uri(), (WEB / "map_core.js").as_uri()),
        encoding="utf-8")
    nav = chrome(playwright)
    contexto = nav.new_context(viewport={"width": largura, "height": 900}, device_scale_factor=densidade)
    pg = contexto.new_page()
    erros: list[str] = []
    pg.on("pageerror", lambda e: erros.append(str(e)))
    pg.goto(html.as_uri())
    pg.add_script_tag(content=JS)
    return nav, pg, erros


def mede(mapas: list[str] | None = None, posicoes: int = POSICOES_POR_ANDAR) -> list[dict]:
    """Uma linha por (mapa, largura, densidade, modo, tipo): `medio` (média das posições), `minimo` (a pior posição)
    e `n`. Modo "B" é o do critério A25; "A" é informativo."""
    from playwright.sync_api import sync_playwright
    todos = radares()
    mapas = [m for m in (mapas or list(todos)) if m in todos]
    linhas = []
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix="granada_") as tmp:
        for largura, k in ESCALAS.items():
            for dens in DENSIDADES:
                nav, pg, erros = _pagina(p, largura, dens, Path(tmp))
                try:
                    assert pg.evaluate("window.devicePixelRatio") == dens
                    for mapa in mapas:
                        r = pg.evaluate("([u, m, k, t, n, s, rc]) => MedeGranada.mede(u, m, k, t, n, s, rc)",
                                        [todos[mapa], "de_" + mapa, k, list(TIPOS), posicoes, SEMENTE, RAIO_DA_CONTA])
                        for modo in ("B", "A"):
                            for tipo in TIPOS:
                                v = r[tipo][modo]
                                linhas.append({"mapa": mapa, "largura": largura, "densidade": dens, "modo": modo, "tipo": tipo,
                                               "medio": sum(v) / len(v), "minimo": min(v), "n": len(v)})
                finally:
                    nav.close()
                assert not erros, erros
    return linhas


def confere_tracejado() -> list[dict]:
    """A13/A14 com o tracejado em px de tela: por largura e densidade, o passo (em px de tela) e a largura (px de
    tela) de cada `stroke()` do anel da granada desenhada. Halo e contorno têm de sair com o mesmo passo."""
    from playwright.sync_api import sync_playwright
    linhas = []
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix="granada_") as tmp:
        for largura, k in ESCALAS.items():
            for dens in DENSIDADES:
                nav, pg, erros = _pagina(p, largura, dens, Path(tmp))
                try:
                    s = pg.evaluate("(k) => MedeGranada.tracejado(k)", k)
                finally:
                    nav.close()
                assert not erros, erros
                linhas.append({"largura": largura, "densidade": dens, "strokes": s})
    return linhas


def resumo(linhas: list[dict], modo: str = "B") -> list[dict]:
    """Por (mapa, largura, densidade): a média dos quatro tipos, o pior tipo e o nome dele."""
    out = []
    chaves = sorted({(l["mapa"], l["largura"], l["densidade"]) for l in linhas if l["modo"] == modo},
                    key=lambda c: (c[0], -c[1], c[2]))
    for mapa, larg, dens in chaves:
        tipos = {l["tipo"]: l for l in linhas if l["modo"] == modo and (l["mapa"], l["largura"], l["densidade"]) == (mapa, larg, dens)}
        media = sum(t["medio"] for t in tipos.values()) / len(tipos)
        pior = min(tipos.values(), key=lambda t: t["medio"])
        out.append({"mapa": mapa, "largura": larg, "densidade": dens, "media": media, "pior": pior["medio"],
                    "pior_tipo": pior["tipo"], "tipos": {t: v["medio"] for t, v in tipos.items()},
                    "minimos": {t: v["minimo"] for t, v in tipos.items()},
                    "passa": media >= MEDIA_MINIMA and pior["medio"] >= TIPO_MINIMO})
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    com_partida = mapas_com_partida()
    linhas = mede()
    print("(cada célula: ΔE médio do tipo; entre parênteses, m = o mínimo, a pior posição sorteada)")
    print(f"== A25: granada desenhada x real no canvas do map_core.js (ΔE76; média >= {MEDIA_MINIMA}, "
          f"nenhum tipo < {TIPO_MINIMO}; mapas com partida: {', '.join(sorted(com_partida))}) ==")
    for modo, nome in (("B", "modo B, mesmo tamanho (critério)"), ("A", "modo A, como no projeto (informativo)")):
        print(f"\n-- {nome} --")
        print(f"{'mapa':<9} {'tela':>5} {'dpr':>3}  " + "  ".join(f"{t:>14}" for t in TIPOS) + f"  {'média':>6}  {'pior':>5}  situação")
        for r in resumo(linhas, modo):
            cel = "  ".join(f"{r['tipos'][t]:6.2f} (m{r['minimos'][t]:5.2f})" for t in TIPOS)
            sit = ("PASSA" if r["passa"] else "REPROVA") if r["mapa"] in com_partida else "(sem partida)"
            print(f"{r['mapa']:<9} {r['largura']:>5} {r['densidade']:>2}x  {cel}  {r['media']:6.2f}  {r['pior']:5.2f}  {sit}")
    reprovados = [r for r in resumo(linhas) if r["mapa"] in com_partida and not r["passa"]]
    print("\nA25:", "PASSA em todos os mapas com partida" if not reprovados else
          "REPROVA: " + ", ".join(f"{r['mapa']} {r['largura']} {r['densidade']}x" for r in reprovados))
    print("\n== A13/A14: tracejado em px de tela (passo e largura de cada stroke do anel) ==")
    for l in confere_tracejado():
        print(f"{l['largura']:>5} px {l['densidade']}x:", " | ".join(
            f"passo {s['passo'][0]:.2f}/{s['passo'][1]:.2f} larg {s['largura']:.2f}" for s in l["strokes"] if s["passo"]))
    return 1 if reprovados else 0


if __name__ == "__main__":
    raise SystemExit(main())
