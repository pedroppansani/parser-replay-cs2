"""
Monta o site estático de demonstração em `docs/` (a pasta que o GitHub Pages
serve): uma página por partida processada, mais um índice para escolher.

Por que uma página por partida, em vez de um app que troca os dados sem
recarregar: cada página é um HTML autocontido, com os dados dela embutidos. Não
precisa de servidor, não precisa de fetch, não quebra se alguém salvar o arquivo
e abrir offline — e é o mesmo artefato que o `build_web_page.py` já gerava. A
troca de partida é navegação entre páginas, e o seletor do cabeçalho faz isso.

O custo é carregar ~900KB ao trocar de partida. Para um site de portfólio com
poucas partidas isso é irrelevante perto de ter que manter dois caminhos de
renderização.

Uso:
    python -m scripts.build_site
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import polars as pl

from scripts.build_tactics_page import arquivo_da_pagina, mapas_disponiveis
from scripts.build_tactics_page import build_html as build_prancheta
from scripts.build_web_page import build_html

from metrics.constantes import NOME_DO_MAPA

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"

# Nome bonito do mapa pro seletor e pro índice (metrics/constantes.py).
MAP_LABEL = NOME_DO_MAPA


def match_summary(match_id: str) -> dict | None:
    """Dados de vitrine de uma partida: mapa, placar, times, nº de rounds.

    Lê do que já foi calculado (insights.json), não recalcula nada -- se a
    partida não tiver passado pela cadeia completa, ela simplesmente não entra
    no site em vez de entrar pela metade.
    """
    base = PROCESSED_DIR / match_id
    insights_path = base / "insights.json"
    meta_path = base / "match_meta.json"
    if not insights_path.exists() or not meta_path.exists():
        return None

    insights = json.loads(insights_path.read_text(encoding="utf-8"))
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    m = insights.get("match", {})
    map_name = meta.get("map_name", "?")

    # o MVP é o do card da partida (maior rating, metrics/match_highlights.py),
    # casado por steamid -- a landing não tem critério próprio
    card = insights.get("mvp_card") or {}
    mvp = next((p for p in insights.get("players", []) if p.get("steamid") == card.get("steamid")), None)

    return {
        "id": match_id,
        "file": f"{match_id}.html",
        "map": map_name,
        "map_label": MAP_LABEL.get(map_name, map_name),
        "rounds": m.get("rounds", meta.get("n_rounds")),
        "score_a": m.get("score_a"),
        "score_b": m.get("score_b"),
        "rosters": m.get("rosters", {}),
        "mvp": mvp["name"] if mvp else None,
        "mvp_adr": round(mvp["adr"], 1) if mvp else None,
        "has_radar": (PROJECT_ROOT / "assets" / "radars" / f"{map_name}.json").exists(),
        # para a escolha da partida de exemplo da landing
        "tem_round_decisivo": bool(insights.get("decisive_round")),
        "origem": _origem(match_id),
        "label": f"{MAP_LABEL.get(map_name, map_name)} · {m.get('score_a')}-{m.get('score_b')} · {match_id}",
    }


def _origem(match_id: str) -> str | None:
    manifesto = PROJECT_ROOT / "data" / "manifest.json"
    if not manifesto.exists():
        return None
    return (json.loads(manifesto.read_text(encoding="utf-8")).get("partidas", {}).get(match_id) or {}).get("origem")


def partida_de_exemplo(matches: list[dict]) -> dict | None:
    """A partida do botão "Ver uma partida" da landing.

    Critério declarado, para a escolha não ser gosto: entre as partidas
    PROFISSIONAIS com radar e com round decisivo (um jogo apertado tem mais o
    que mostrar: o round que virou a partida, a curva de probabilidade), a de
    placar mais apertado; no empate, a de mais rounds e depois o menor id. Sem
    nenhuma assim, a primeira com radar; sem radar, a primeira.
    """
    if not matches:
        return None

    def aperto(m):
        return (abs((m.get("score_a") or 0) - (m.get("score_b") or 0)), -(m.get("rounds") or 0), m["id"])

    boas = [m for m in matches if m.get("origem") == "profissional" and m.get("has_radar") and m.get("tem_round_decisivo")]
    if boas:
        return min(boas, key=aperto)
    com_radar = [m for m in matches if m.get("has_radar")]
    return (com_radar or matches)[0]


def utility_highlight(match_id: str) -> str | None:
    """Uma frase de utility pro cartão do índice, se a partida tiver a métrica."""
    path = PROCESSED_DIR / match_id / "grenades_summary.parquet"
    if not path.exists():
        return None
    gren = pl.read_parquet(path).sort("enemy_blind_seconds", descending=True)
    if gren.height == 0 or gren["enemy_blind_seconds"][0] == 0:
        return None
    top = gren.row(0, named=True)
    return f"{top['name']} impôs {top['enemy_blind_seconds']:.0f}s de cegueira"


def build_index(matches: list[dict], repo_url: str, pranchetas: list[dict] | None = None,
                numeros: dict | None = None, imagem: str | None = None) -> str:
    """A landing. `numeros` é o documento de numeros_citaveis.json (os três
    números do topo vêm dele, nunca escritos aqui); `imagem` é o arquivo da
    captura do replay ao lado da página, se houver."""
    from html import escape as e

    # todo texto que vem do dado (nicks, mapa, frase do destaque) é escapado:
    # um nick com `<` não pode virar marcação na landing
    cards = "\n".join(
        f"""      <a class="mcard" data-mapa="{e(str(m.get('map', '')))}" href="{e(m['file'])}">
        <div class="mtop"><span class="mmap">{e(str(m['map_label']))}</span>
          <span class="mscore">{m['score_a']}<em>–</em>{m['score_b']}</span></div>
        <div class="mrosters">{" · ".join(e(n) for n in m['rosters'].get('A', []))}<br>
          <span class="vs">contra</span><br>{" · ".join(e(n) for n in m['rosters'].get('B', []))}</div>
        <div class="mfoot"><span>{m['rounds']} rounds</span>
          <span>{e(m.get('extra') or ('MVP ' + (m['mvp'] or '?')))}</span></div>
        {"" if m['has_radar'] else '<div class="noradar">sem radar calibrado</div>'}
      </a>"""
        for m in matches
    )

    links = " · ".join(f'<a href="{e(p["file"])}">{e(p["label"])}</a>' for p in (pranchetas or []))
    bloco_prancheta = (f"""
  <section class="box">
    <h2>Prancheta tática</h2>
    <p>Monte uma jogada no mapa vazio: peças, passos e granadas. Clique onde a granada deve cair e a
      prancheta mostra os arremessos reais do corpus que caem ali, com o comando de console que os
      reproduz. {links}</p>
  </section>
""" if links else "")

    # --- topo: o que é, três números validados, uma imagem e três caminhos ---
    from scripts.numeros_citaveis import blocos_de_texto, tres_numeros

    exemplo = partida_de_exemplo(matches)
    tres = "".join(
        f"""      <div class="num"><b>{e(n['valor'])}</b><span>{e(n['rotulo'])}</span><p>{e(n['contexto'])}</p></div>\n"""
        for n in (tres_numeros(numeros) if numeros else []))
    corpus = e(blocos_de_texto(numeros)["corpus"]) if numeros else ""
    prancheta_do_exemplo = next((p for p in (pranchetas or []) if exemplo and p.get("mapa") == exemplo.get("map")),
                                (pranchetas or [None])[0])
    botoes = "".join([
        f'<a class="btn principal" id="btn-partida" href="{e(exemplo["file"])}">Ver uma partida</a>' if exemplo else "",
        f'<a class="btn" id="btn-prancheta" href="{e(prancheta_do_exemplo["file"])}">Prancheta</a>' if prancheta_do_exemplo else "",
        f'<a class="btn" id="btn-github" href="{e(repo_url)}">GitHub</a>',
    ])
    figura = (f'<img class="hero-img" src="{e(imagem)}" alt="Replay de uma partida no radar, com a direção do olhar '
              f'de cada jogador" loading="lazy">' if imagem else "")
    mapas = sorted({(m.get("map"), m.get("map_label")) for m in matches if m.get("map")}, key=lambda x: str(x[1]))
    filtro = "".join(f'<button type="button" data-filtro="{e(str(k))}">{e(str(rot))}</button>' for k, rot in mapas)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CS2 Replay Stats — demonstração</title>
<meta name="description" content="Parser de replay de CS2 com métricas autorais: utility por efeito, crosshair placement validado contra os dados e função de jogador derivada de limiar explícito.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400..800&family=DM+Mono:wght@400;500&family=Figtree:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --paper: #eef1f5; --paper-2: #e7ebf1; --card: #fff; --ink: #0f1620; --ink-2: #4c5a6b;
    --dim: #7d8a99; --line: #dde3eb; --ct: #2a78d6; --t: #eb6834; --aqua: #1baf7a;
    --display: "Bricolage Grotesque", Georgia, sans-serif;
    --body: "Figtree", system-ui, sans-serif;
    --mono: "DM Mono", ui-monospace, Menlo, monospace;
    --r: 10px;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--paper); color: var(--ink); font-family: var(--body);
    -webkit-font-smoothing: antialiased; }}
  .shell {{ max-width: 1120px; margin: 0 auto; padding: 0 20px 64px; }}
  header {{ padding: 56px 0 8px; }}
  .eyebrow {{ font-family: var(--mono); font-size: 11px; letter-spacing: 0.14em;
    text-transform: uppercase; color: var(--dim); }}
  h1 {{ font-family: var(--display); font-size: clamp(34px, 6vw, 58px); line-height: 1.02;
    letter-spacing: -0.03em; margin: 12px 0 0; font-weight: 800; }}
  .lead {{ max-width: 62ch; font-size: 16px; line-height: 1.6; color: var(--ink-2); margin: 16px 0 0; }}
  .lead b {{ color: var(--ink); font-weight: 600; }}

  .hero {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 28px; align-items: center; }}
  .hero-img {{ width: 100%; height: auto; border-radius: var(--r); border: 1px solid var(--line);
    box-shadow: 0 10px 30px rgba(15, 22, 32, .10); display: block; }}
  .botoes {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 22px; }}
  .btn {{ display: inline-block; padding: 10px 18px; border-radius: 999px; border: 1px solid var(--line);
    background: var(--card); color: var(--ink); text-decoration: none; font-weight: 600; font-size: 15px; }}
  .btn:hover {{ border-color: var(--ct); }}
  .btn.principal {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
  .corpus {{ font-family: var(--mono); font-size: 12px; color: var(--dim); margin: 16px 0 0; }}
  .nums {{ margin-top: 30px; display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr)); gap: 14px; }}
  .num {{ background: var(--card); border: 1px solid var(--line); border-radius: var(--r); padding: 18px 20px; }}
  .num b {{ display: block; font-family: var(--display); font-size: 30px; letter-spacing: -0.02em; line-height: 1.1; }}
  .num span {{ display: block; font-weight: 600; font-size: 14px; margin-top: 6px; }}
  .num p {{ margin: 8px 0 0; font-size: 13px; line-height: 1.5; color: var(--ink-2); }}
  .filtro {{ margin-top: 34px; display: flex; flex-wrap: wrap; gap: 8px; }}
  .filtro button {{ font: inherit; font-size: 13px; padding: 6px 13px; border-radius: 999px; cursor: pointer;
    border: 1px solid var(--line); background: var(--card); color: var(--ink-2); }}
  .filtro button[aria-pressed="true"] {{ background: var(--ink); color: #fff; border-color: var(--ink); }}
  .mcard[hidden] {{ display: none; }}
  @media (max-width: 760px) {{ .hero {{ grid-template-columns: 1fr; }} }}

  .grid {{ margin-top: 14px; display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 290px), 1fr)); gap: 14px; }}
  .mcard {{ display: block; text-decoration: none; color: inherit; background: var(--card);
    border: 1px solid var(--line); border-radius: var(--r); padding: 16px;
    transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease; }}
  .mcard:hover {{ transform: translateY(-2px); border-color: var(--ct);
    box-shadow: 0 6px 22px rgba(15,22,32,0.09); }}
  .mtop {{ display: flex; align-items: baseline; justify-content: space-between; gap: 10px; }}
  .mmap {{ font-family: var(--display); font-weight: 700; font-size: 21px; letter-spacing: -0.02em; }}
  .mscore {{ font-family: var(--mono); font-size: 19px; font-weight: 500; }}
  .mscore em {{ font-style: normal; color: var(--dim); padding: 0 2px; }}
  .mrosters {{ margin-top: 10px; font-family: var(--mono); font-size: 11px; color: var(--ink-2);
    line-height: 1.75; }}
  .mrosters .vs {{ color: var(--dim); }}
  .mfoot {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--line);
    display: flex; justify-content: space-between; gap: 8px;
    font-family: var(--mono); font-size: 10.5px; color: var(--dim); }}
  .noradar {{ margin-top: 8px; font-family: var(--mono); font-size: 10px; color: var(--dim);
    font-style: italic; }}

  .box {{ margin-top: 34px; background: var(--card); border: 1px solid var(--line);
    border-radius: var(--r); padding: 20px 22px; }}
  .box h2 {{ font-family: var(--display); font-size: 22px; letter-spacing: -0.02em; margin: 0 0 8px; }}
  .box p {{ font-size: 13.5px; line-height: 1.6; color: var(--ink-2); margin: 0 0 10px; max-width: 70ch; }}
  .box b {{ color: var(--ink); font-weight: 600; }}
  pre {{ margin: 0; padding: 13px 14px; background: var(--ink); color: #e6edf5; border-radius: 8px;
    overflow-x: auto; font-family: var(--mono); font-size: 11.5px; line-height: 1.75; }}
  .why {{ font-size: 12px; color: var(--dim); margin-top: 10px; }}
  footer {{ margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line);
    font-size: 12px; color: var(--dim); line-height: 1.6; }}
  footer a {{ color: var(--ct); }}
</style>
</head>
<body>
<div class="shell">
  <header class="hero">
    <div class="hero-txt">
      <div class="eyebrow">CS2 · replay parser · métricas autorais</div>
      <h1>Uma partida,<br>round a round</h1>
      <p class="lead">
        Lê o replay (.dem) de uma partida de CS2 e mostra o que aconteceu: o mapa round a round, o
        round que decidiu o jogo e o que cada jogador fez. <b>Cada número é conferido contra dado
        oficial</b>, e o que não se sustenta fica sem afirmação.
      </p>
      <div class="botoes">{botoes}</div>
      <p class="corpus" id="corpus">{corpus}</p>
    </div>
    {figura}
  </header>

  <section class="nums" id="tres-numeros">
{tres}  </section>

  <div class="filtro" id="filtro" role="group" aria-label="Filtrar as partidas por mapa">
    <button type="button" data-filtro="" aria-pressed="true">Todos os mapas</button>{filtro}
  </div>
  <div class="grid" id="partidas">
{cards}
  </div>
{bloco_prancheta}
  <section class="box">
    <h2>Adicionar a sua própria demo</h2>
    <p>
      O parsing não roda no navegador — um .dem tem 200-300MB e o parser é nativo (Rust, via awpy).
      A demo é processada na sua máquina e o que vai pro site é só o resultado: alguns KB de
      métricas por partida.
    </p>
    <pre>git clone {repo_url}
cd "01 - Parser de Replay CS2"
pip install -r requirements.txt

# jogue o .dem (ou a pasta que o FACEIT entrega) em demos/ e rode:
python -m scripts.process_all_demos
python -m scripts.build_site

# abra docs/index.html</pre>
    <p class="why">
      A partida nova aparece sozinha nesta lista e no seletor do cabeçalho de cada página. É a mesma
      razão de o site ser estático: parsear .dem a cada acesso derrubaria qualquer hospedagem
      gratuita, e os arquivos originais expiram no FACEIT em 30 dias.
    </p>
  </section>

  <footer>
    Parsing com <a href="https://awpy.rtfd.io/">awpy</a> sobre demoparser2; métricas em Polars.
    Mapas sem radar calibrado aparecem em coordenadas de jogo — a leitura é a mesma, sem a imagem de
    fundo. Código e metodologia em <a href="{repo_url}">{repo_url}</a>.
  </footer>
</div>
<script>
  // filtro por mapa: esconde os cards dos outros mapas
  (function () {{
    var botoes = document.querySelectorAll("#filtro button");
    Array.prototype.forEach.call(botoes, function (b) {{
      b.addEventListener("click", function () {{
        var alvo = b.getAttribute("data-filtro");
        Array.prototype.forEach.call(botoes, function (x) {{ x.setAttribute("aria-pressed", String(x === b)); }});
        Array.prototype.forEach.call(document.querySelectorAll("#partidas .mcard"), function (c) {{
          c.hidden = !!alvo && c.getAttribute("data-mapa") !== alvo;
        }});
      }});
    }});
  }})();
</script>
</body>
</html>
"""


def build(repo_url: str) -> Path:
    if not PROCESSED_DIR.exists():
        raise SystemExit("Nenhuma partida processada. Rode scripts/process_all_demos.py primeiro.")

    matches: list[dict] = []
    for match_dir in sorted(PROCESSED_DIR.iterdir()):
        if not match_dir.is_dir():
            continue
        summary = match_summary(match_dir.name)
        if summary is None:
            print(f"[pular] {match_dir.name}: cadeia incompleta (falta insights.json ou meta)")
            continue
        summary["extra"] = utility_highlight(match_dir.name)
        matches.append(summary)

    if not matches:
        raise SystemExit("Nenhuma partida com a cadeia completa. Rode scripts/process_all_demos.py.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for old in DOCS_DIR.glob("*.html"):
        old.unlink()

    # o seletor precisa da lista inteira em toda página, e de saber onde está
    nav = [{"id": m["id"], "file": m["file"], "label": m["label"]} for m in matches]

    for m in matches:
        site = {"matches": nav, "current": m["id"], "repo": repo_url}
        html = build_html(m["id"], site=site)
        (DOCS_DIR / m["file"]).write_text(html, encoding="utf-8")
        print(f"  {m['file']}  ({len(html) / 1024:.0f} KB)  {m['map_label']} {m['score_a']}-{m['score_b']}")

    # prancheta tática: uma página por mapa com radar e biblioteca de arremessos
    pranchetas = []
    for mapa in mapas_disponiveis():
        html = build_prancheta(mapa, MAP_LABEL)
        (DOCS_DIR / arquivo_da_pagina(mapa)).write_text(html, encoding="utf-8")
        pranchetas.append({"mapa": mapa, "file": arquivo_da_pagina(mapa), "label": MAP_LABEL.get(mapa, mapa)})
        print(f"  {arquivo_da_pagina(mapa)}  ({len(html) / 1024:.0f} KB)  prancheta")

    # os números do topo vêm de numeros_citaveis.json; a imagem do replay é a
    # captura versionada do README (scripts/capturas_readme.py), copiada para o site
    from scripts.numeros_citaveis import carrega as numeros_citaveis
    captura = PROJECT_ROOT / "assets" / "readme" / "replay.png"
    imagem = None
    if captura.exists():
        shutil.copyfile(captura, DOCS_DIR / "replay.png")
        imagem = "replay.png"
    (DOCS_DIR / "index.html").write_text(
        build_index(matches, repo_url, pranchetas, numeros=numeros_citaveis(), imagem=imagem), encoding="utf-8")

    # o GitHub Pages passa o conteúdo pelo Jekyll por padrão, que ignora arquivos
    # e pastas começando com underscore; .nojekyll desliga isso
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\nSite em {DOCS_DIR} · {len(matches)} partida(s) · abra docs/index.html")
    return DOCS_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o site estático de demonstração em docs/.")
    parser.add_argument(
        "--repo",
        default="https://github.com/pedroppansani/parser-replay-cs2",
        help="URL do repositório, usada nas instruções da página",
    )
    args = parser.parse_args()
    build(args.repo)


if __name__ == "__main__":
    main()
