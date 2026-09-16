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

from scripts.build_web_page import build_html

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"

# Nome bonito do mapa pro seletor e pro índice.
MAP_LABEL = {
    "de_ancient": "Ancient",
    "de_anubis": "Anubis",
    "de_dust2": "Dust II",
    "de_inferno": "Inferno",
    "de_mirage": "Mirage",
    "de_nuke": "Nuke",
    "de_overpass": "Overpass",
    "de_train": "Train",
    "de_vertigo": "Vertigo",
}


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

    # destaque do índice: quem foi o MVP pela fórmula já declarada em build_insights
    players = insights.get("players", [])
    mvp = max(players, key=lambda p: p.get("mvp_index", 0)) if players else None

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
        "label": f"{MAP_LABEL.get(map_name, map_name)} · {m.get('score_a')}-{m.get('score_b')} · {match_id}",
    }


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


def build_index(matches: list[dict], repo_url: str) -> str:
    cards = "\n".join(
        f"""      <a class="mcard" href="{m['file']}">
        <div class="mtop"><span class="mmap">{m['map_label']}</span>
          <span class="mscore">{m['score_a']}<em>–</em>{m['score_b']}</span></div>
        <div class="mrosters">{" · ".join(m['rosters'].get('A', []))}<br>
          <span class="vs">contra</span><br>{" · ".join(m['rosters'].get('B', []))}</div>
        <div class="mfoot"><span>{m['rounds']} rounds</span>
          <span>{m.get('extra') or ('MVP ' + (m['mvp'] or '?'))}</span></div>
        {"" if m['has_radar'] else '<div class="noradar">sem radar calibrado</div>'}
      </a>"""
        for m in matches
    )

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

  .grid {{ margin-top: 30px; display: grid;
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
  <header>
    <div class="eyebrow">CS2 · replay parser · métricas autorais</div>
    <h1>Uma partida,<br>round a round</h1>
    <p class="lead">
      Leitor de replay (.dem) de CS2 com métricas desenhadas a partir de decisões de jogo, não das
      que já vinham prontas. <b>Escolha uma partida abaixo</b> para abrir o replay no mapa, a leitura
      round a round e o perfil de cada jogador. Tudo processado localmente: o site é estático e só
      carrega o resultado.
    </p>
  </header>

  <div class="grid">
{cards}
  </div>

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

    (DOCS_DIR / "index.html").write_text(build_index(matches, repo_url), encoding="utf-8")

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
