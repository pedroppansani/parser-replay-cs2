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

from scripts.build_tactics_page import arquivo_da_pagina, mapas_disponiveis
from scripts.build_tactics_page import build_html as build_prancheta
from scripts.build_web_page import build_html

from metrics.constantes import NOME_DO_MAPA
from scripts.meta_da_pagina import meta_tags, url_do_site

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"

# Link para a página jogadores.html, na landing e no cabeçalho das partidas, com
# o aviso de que ela é a visão do corpus e não de uma partida (decisão 30).
LINK_JOGADORES = {"texto": "Jogadores no corpus",
                  "aviso": "Visão do corpus: os números somam todas as partidas de cada jogador, não uma partida."}

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
        # card da landing (design-C): nomes dos lados, quem venceu e a linha do decisor saem do mesmo
        # Python do cabeçalho da partida (scripts/build_web_page.cabecalho_da_partida)
        **_dados_do_card(match_id),
    }


def _dados_do_card(match_id: str) -> dict:
    from scripts.build_web_page import _manifesto_da_partida, cabecalho_da_partida, origem_da_partida
    c = cabecalho_da_partida(match_id) or {}
    linha = _manifesto_da_partida(match_id)
    return {
        "lados": c.get("lados"),
        "venceu": c.get("venceu"),
        "decisor": c.get("decisor"),
        "evento": origem_da_partida(match_id) if linha.get("origem") == "profissional" else None,
        "data": linha.get("data") or "",
    }


def ordem_da_grade(matches: list[dict]) -> list[dict]:
    """Profissionais primeiro; dentro de cada origem, as mais recentes antes; empate pelo id (estável)."""
    recentes = sorted(matches, key=lambda m: m.get("id") or "")
    recentes = sorted(recentes, key=lambda m: m.get("data") or "", reverse=True)
    return sorted(recentes, key=lambda m: m.get("origem") != "profissional")


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


def legenda_da_captura(matches: list[dict]) -> str | None:
    """Que round a imagem do topo mostra: o quadro fixo de scripts/capturas_readme.py na partida de exemplo."""
    from scripts.capturas_readme import ROUND
    m = partida_de_exemplo(matches)
    if not m or not m.get("lados"):
        return None
    a, b = m["lados"]["A"]["nome"], m["lados"]["B"]["nome"]
    return f"Replay do round {ROUND} de {a} × {b}, em {m['map_label']}."


# Textos do topo da landing (entrega-sala-de-demo §7.1): linguagem comum, sem jargão.
ROTULO_DO_TOPO = "Projeto de portfólio · Python e JavaScript · site estático"
TITULO_DO_TOPO = "Lê gravações de partidas de Counter-Strike 2 e mostra o que decidiu cada jogo"
FRASE_DO_TOPO = ("Cada partida vira uma página: o replay no mapa, o round que virou o jogo e o que cada jogador fez. "
                 "Os números são conferidos contra a estatística oficial, e quando o dado não sustenta uma afirmação "
                 "a página diz que não sabe.")
TITULO_DA_PAGINA = "Parser de Replay CS2 · partidas lidas round a round"
ROTULO_ORIGEM = {"profissional": "Profissionais", "faceit": "FACEIT"}


def _card(m: dict) -> str:
    from html import escape as e
    lados = m.get("lados") or {}
    venceu = m.get("venceu")

    def linha(k: str, pts) -> str:
        nome = (lados.get(k) or {}).get("nome") or f"Lado {k}"
        tag = ' <span class="tag-venceu">venceu</span>' if venceu == k else ""
        return (f'<span class="cp-linha{"" if venceu == k else " perdeu"}"><span class="nome" title="{e(nome)}">'
                f'{e(nome)}{tag}</span><span class="num">{pts}</span></span>')

    topo_esq = e(str(m["map_label"])) + (" · FACEIT" if m.get("origem") == "faceit" else "")
    rounds = f'<span class="num">{m["rounds"]}</span> rounds' + (" · prorrogação" if (m.get("rounds") or 0) > 24 else "")
    topo_dir = (e(m["evento"]) + " · " if m.get("evento") else "") + rounds
    return (f'      <a class="mcard cp" data-mapa="{e(str(m.get("map", "")))}" data-origem="{e(str(m.get("origem") or ""))}" '
            f'href="{e(m["file"])}">\n'
            f'        <span class="cp-topo"><span>{topo_esq}</span><span>{topo_dir}</span></span>\n'
            f'        {linha("A", m["score_a"])}\n        {linha("B", m["score_b"])}\n'
            f'        <span class="cp-frase">{e(m.get("decisor") or "")}</span>\n'
            + ("" if m["has_radar"] else '        <span class="noradar">sem radar calibrado</span>\n')
            + "      </a>")


def build_index(matches: list[dict], repo_url: str, pranchetas: list[dict] | None = None,
                numeros: dict | None = None, imagem: str | None = None,
                imagem_tamanho: tuple[int, int] | None = None, legenda: str | None = None) -> str:
    """A landing (entrega-sala-de-demo §7.1). `numeros` é o documento de numeros_citaveis.json (os três
    números do topo vêm dele, nunca escritos aqui); `imagem` é o arquivo da captura do replay ao lado da
    página, com `imagem_tamanho` (largura, altura) para não empurrar o layout e `legenda` dizendo qual round é.
    Ordem no HTML = ordem do celular: texto, números, imagem; no desktop a imagem vai para a direita por CSS."""
    from collections import Counter
    from html import escape as e

    from scripts.numeros_citaveis import blocos_de_texto, tres_numeros

    # todo texto que vem do dado (nicks, mapa, frase do decisor) é escapado: um nick com `<` não vira marcação
    grade = ordem_da_grade(matches)
    cards = "\n".join(_card(m) for m in grade)

    exemplo = partida_de_exemplo(matches)
    tres = "".join(
        f"""        <div class="num-item"><dt><b class="num">{e(n['valor'])}</b>{e(n['rotulo'])}</dt><dd>{e(n['contexto'])}</dd></div>\n"""
        for n in (tres_numeros(numeros) if numeros else []))
    corpus = e(blocos_de_texto(numeros)["corpus"]) if numeros else ""
    prancheta_do_exemplo = next((p for p in (pranchetas or []) if exemplo and p.get("mapa") == exemplo.get("map")),
                                (pranchetas or [None])[0])
    botoes = "".join([
        f'<a class="btn principal" id="btn-partida" href="{e(exemplo["file"])}">Ver uma partida</a>' if exemplo else "",
        f'<a class="btn" id="btn-prancheta" href="{e(prancheta_do_exemplo["file"])}">Prancheta tática</a>' if prancheta_do_exemplo else "",
        f'<a class="btn fantasma" id="btn-github" href="{e(repo_url)}">Código no GitHub ↗</a>',
    ])
    tam = (f' width="{imagem_tamanho[0]}" height="{imagem_tamanho[1]}"' if imagem_tamanho else "")
    cap = f"<figcaption>{e(legenda)}</figcaption>" if legenda else ""
    figura = (f"""    <figure class="figura">
      <div class="moldura"><img src="{e(imagem)}"{tam} loading="lazy" decoding="async"
        alt="Replay de uma partida no radar, com a direção do olhar de cada jogador"></div>
      {cap}
    </figure>""" if imagem else "")

    # filtros: origem (Profissionais por padrão) e mapa, com a contagem de cada um
    por_origem = Counter(m.get("origem") for m in grade)
    origem_padrao = "profissional" if por_origem.get("profissional") else ""
    chips_origem = "".join(
        f'<button type="button" class="chip" data-valor="{v}" aria-pressed="{str(v == origem_padrao).lower()}">'
        f'{rot} <span class="num">{n}</span></button>'
        for v, rot, n in [("profissional", "Profissionais", por_origem.get("profissional", 0)),
                          ("faceit", "FACEIT", por_origem.get("faceit", 0)), ("", "Todas", len(grade))] if n)
    por_mapa = Counter(m.get("map") for m in grade if m.get("map"))
    rotulo_mapa = {m.get("map"): m.get("map_label") for m in grade}
    chips_mapa = '<button type="button" class="chip" data-valor="" aria-pressed="true">Todos os mapas</button>' + "".join(
        f'<button type="button" class="chip" data-valor="{e(str(k))}" aria-pressed="false">{e(str(rotulo_mapa[k]))} '
        f'<span class="num">{n}</span></button>'
        for k, n in sorted(por_mapa.items(), key=lambda kv: (-kv[1], str(rotulo_mapa[kv[0]]))))

    links = " · ".join(f'<a href="{e(p["file"])}">{e(p["label"])}</a>' for p in (pranchetas or []))
    bloco_prancheta = (f"""
  <section class="box" aria-labelledby="h-prancheta">
    <h2 id="h-prancheta">Prancheta tática</h2>
    <p>Monte uma jogada no mapa vazio: peças, passos e granadas. Clique onde a granada deve cair e a
      prancheta mostra os arremessos reais do corpus que caem ali, com o comando de console que os
      reproduz. {links}</p>
  </section>
""" if links else "")
    link_prancheta = (f'<a href="{e(prancheta_do_exemplo["file"])}">Prancheta</a>' if prancheta_do_exemplo else "")

    from scripts.design_head import aplica  # tokens e fontes (decisão 44)
    return aplica(f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_DA_PAGINA)}</title>
{meta_tags(TITULO_DA_PAGINA, FRASE_DO_TOPO, url_do_site(repo_url))}
<!--__FONTES__-->
<style>
  /* Os tokens (cores, fontes, espaços) vêm de dashboard/web/tokens.css, injetado no build. */
  /*__TOKENS__*/
  * {{ box-sizing: border-box; }}
  :where(button, a[href], select, input, textarea, summary, [tabindex]):focus-visible {{
    outline: 2px solid var(--foco); outline-offset: 2px;
  }}
  body {{ margin: 0; background: var(--fundo); color: var(--tinta); font-family: var(--f-texto);
    -webkit-font-smoothing: antialiased; }}
  .shell {{ max-width: 1280px; margin: 0 auto; padding: 0 16px 64px; }}
  .num {{ font-family: var(--f-num); font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }}

  /* topo do site: marca e quatro links (§7) */
  .site-topo {{ display: flex; align-items: center; justify-content: space-between; gap: 4px 16px; flex-wrap: nowrap;
    border-bottom: 1px solid var(--linha); margin: 0 -16px; padding: 0 16px; }}
  .marca {{ display: inline-flex; align-items: center; min-height: var(--toque); min-width: var(--toque); flex: none;
    font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em; color: var(--tinta); text-decoration: none; }}
  .marca b {{ color: var(--tr-texto); margin-left: 0.3em; }}
  .site-nav {{ display: flex; flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; }}
  .site-nav::-webkit-scrollbar {{ display: none; }}
  .site-nav a {{ display: inline-flex; align-items: center; min-height: var(--toque); padding: 0 10px; flex: none;
    color: var(--tinta-2); text-decoration: none; font-size: var(--t-sm); }}
  .site-nav a[aria-current] {{ color: var(--tinta); box-shadow: inset 0 -2px 0 var(--tinta); }}
  .site-nav a:hover {{ color: var(--tinta); }}
  @media (max-width: 640px) {{ .marca .marca-longa {{ display: none; }} .marca b {{ margin-left: 0; }} .site-nav a {{ padding: 0 7px; }} }}

  /* topo da landing: texto, números, imagem (ordem do celular); no desktop a imagem vai para a direita */
  .heroi {{ display: grid; gap: 24px; padding: 28px 0 8px; }}
  @media (min-width: 960px) {{
    .heroi {{ grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr); grid-template-areas: "texto figura" "numeros figura";
      align-items: start; gap: 24px 40px; padding-top: 48px; }}
    .heroi > .heroi-texto {{ grid-area: texto; }} .heroi > .numeros-heroi {{ grid-area: numeros; }} .heroi > .figura {{ grid-area: figura; }}
  }}
  .rot {{ font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-weight: 700; font-size: var(--t-xs);
    letter-spacing: 0.1em; text-transform: uppercase; color: var(--apagado); margin: 0; }}
  .heroi h1 {{ margin: 10px 0 14px; font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-weight: 700;
    font-size: clamp(2rem, 6.4vw, 3.4rem); line-height: 1.02; letter-spacing: -0.01em; text-wrap: balance; }}
  .lead {{ color: var(--tinta-2); font-size: 1.0625rem; line-height: 1.55; max-width: 52ch; margin: 0 0 22px; }}
  .caminhos {{ display: flex; flex-wrap: wrap; gap: 10px; }}
  .btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 0.45em; min-height: var(--toque);
    padding: 0 18px; border-radius: var(--r-sm); border: 1px solid var(--borda); background: var(--superficie);
    color: var(--tinta); font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-weight: 700;
    font-size: var(--t-sm); letter-spacing: 0.08em; text-transform: uppercase; text-decoration: none; white-space: nowrap; }}
  .btn:hover {{ background: var(--superficie-2); border-color: var(--tinta-2); }}
  .btn.principal {{ background: var(--tinta); color: var(--fundo); border-color: var(--tinta); }}
  .btn.fantasma {{ background: none; border-color: transparent; text-decoration: underline; text-underline-offset: 4px; }}
  .tres {{ display: grid; margin: 0; border: 1px solid var(--borda); border-radius: var(--r-md); background: var(--superficie); }}
  @media (min-width: 760px) {{ .tres {{ grid-template-columns: repeat(3, 1fr); }} }}
  .tres > div {{ padding: 16px; border-top: 1px solid var(--linha); }}
  .tres > div:first-child {{ border-top: 0; }}
  @media (min-width: 760px) {{ .tres > div {{ border-top: 0; border-left: 1px solid var(--linha); }} .tres > div:first-child {{ border-left: 0; }} }}
  .tres dt {{ font-weight: 600; }}
  .tres dt .num {{ display: block; font-size: 2.1rem; line-height: 1.1; font-weight: 600; margin-bottom: 4px; white-space: nowrap; }}
  /* em três colunas a célula fica estreita: o número diminui para "410 de 410" caber numa linha */
  @media (min-width: 760px) {{ .tres dt .num {{ font-size: clamp(1.4rem, 2.2vw, 2.1rem); }} }}
  .tres dd {{ margin: 6px 0 0; color: var(--tinta-2); font-size: var(--t-sm); line-height: 1.5; }}
  .corpus {{ margin: 12px 0 0; color: var(--tinta-2); font-size: var(--t-sm); }}
  .corpus a {{ color: var(--tinta); }}
  .figura {{ margin: 0; }}
  .figura .moldura {{ border: 1px solid var(--borda); border-radius: var(--r-md); overflow: hidden; background: var(--radar); }}
  .figura img {{ display: block; width: 100%; height: auto; }}
  .figura figcaption {{ font-size: var(--t-sm); color: var(--tinta-2); margin-top: 8px; }}

  /* grade de partidas */
  .grade-topo {{ display: flex; flex-wrap: wrap; align-items: end; justify-content: space-between; gap: 12px 24px; margin: 48px 0 12px; }}
  .grade-topo h2 {{ margin: 0; font-family: var(--f-cond); font-stretch: var(--larg-condensada); text-transform: uppercase;
    font-size: 1.5rem; letter-spacing: 0.02em; }}
  .grade-topo h2 .num {{ color: var(--apagado); font-size: 0.8em; }}
  .filtros {{ display: grid; gap: 8px; min-width: 0; max-width: 100%; }}
  @media (min-width: 960px) {{ .filtros {{ grid-auto-flow: column; }} }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .filtro-mapas {{ flex-wrap: nowrap; overflow-x: auto; scrollbar-width: thin; padding-bottom: 2px; }}
  @media (min-width: 760px) {{ .filtro-mapas {{ flex-wrap: wrap; overflow: visible; }} }}
  .chip {{ flex: none; min-height: var(--toque); padding: 0 14px; border-radius: var(--r-sm); cursor: pointer; font: inherit;
    font-size: var(--t-sm); border: 1px solid var(--borda); background: var(--superficie); color: var(--tinta-2); }}
  .chip:hover {{ color: var(--tinta); border-color: var(--tinta-2); }}
  .chip[aria-pressed="true"] {{ background: var(--tinta); color: var(--fundo); border-color: var(--tinta); }}
  .chip .num {{ font-size: var(--t-xs); margin-left: 4px; }}
  .grid {{ display: grid; gap: 10px; }}
  @media (min-width: 640px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
  @media (min-width: 1024px) {{ .grid {{ grid-template-columns: repeat(3, 1fr); }} }}
  .cp {{ display: grid; gap: 8px; padding: 14px 14px 12px; text-decoration: none; color: var(--tinta); min-width: 0;
    background: var(--superficie); border: 1px solid var(--linha); border-left: 3px solid var(--borda); border-radius: var(--r-md); }}
  .cp:hover {{ background: var(--superficie-2); border-left-color: var(--tinta); }}
  .cp[hidden] {{ display: none; }}
  .cp-topo {{ display: flex; justify-content: space-between; gap: 8px; font-size: var(--t-sm); color: var(--tinta-2); }}
  .cp-linha {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: baseline; gap: 8px; }}
  .cp-linha .nome {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 600; }}
  .cp-linha .num {{ font-size: 1.2rem; font-weight: 600; }}
  .cp-linha.perdeu {{ color: var(--tinta-2); }} .cp-linha.perdeu .nome, .cp-linha.perdeu .num {{ font-weight: 400; }}
  .tag-venceu {{ font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.08em; font-size: var(--t-xs); padding: 2px 5px; margin-left: 4px; border: 1.5px solid var(--vitoria);
    border-radius: var(--r-sm); color: var(--vitoria); vertical-align: 2px; }}
  .cp-frase {{ font-size: var(--t-sm); color: var(--tinta-2); border-top: 1px solid var(--linha); padding-top: 8px; }}
  .noradar {{ font-size: var(--t-xs); color: var(--apagado); font-style: italic; }}
  .vazio {{ padding: 24px 16px; border: 1px dashed var(--borda); border-radius: var(--r-md); color: var(--tinta-2);
    display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }}
  .vazio[hidden] {{ display: none; }}

  .box {{ margin-top: 34px; background: var(--superficie); border: 1px solid var(--linha); border-radius: var(--r-md); padding: 20px 22px; }}
  .box h2 {{ font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-size: 22px; letter-spacing: -0.02em; margin: 0 0 8px; }}
  .box p {{ font-size: var(--t-sm); line-height: 1.6; color: var(--tinta-2); margin: 0 0 10px; max-width: 70ch; }}
  .box p a {{ color: var(--tinta); }}
  pre {{ margin: 0; padding: 13px 14px; background: var(--superficie-2); color: var(--tinta); border-radius: var(--r-md);
    overflow-x: auto; font-family: var(--f-codigo); font-size: 12px; line-height: 1.75; }}
  .why {{ font-size: var(--t-xs); color: var(--apagado); margin-top: 10px; }}
  footer {{ margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--linha); font-size: var(--t-sm);
    color: var(--tinta-2); line-height: 1.6; }}
  footer h2 {{ font-family: var(--f-cond); font-stretch: var(--larg-condensada); font-size: 1rem; text-transform: uppercase;
    letter-spacing: 0.06em; margin: 0 0 6px; color: var(--tinta); }}
  footer p {{ margin: 0; }}
  footer a {{ color: var(--tinta); text-decoration: underline; text-underline-offset: 3px; }}
</style>
</head>
<body>
<div class="shell">
  <header class="site-topo">
    <a class="marca" href="index.html" aria-label="Parser de Replay CS2, início"><span class="marca-longa">Parser de Replay</span><b>CS2</b></a>
    <nav class="site-nav" aria-label="Principal">
      <a href="index.html" aria-current="page">Partidas</a>
      <a href="jogadores.html">Jogadores</a>
      {link_prancheta}
      <a href="{e(repo_url)}">GitHub</a>
    </nav>
  </header>

  <main>
  <section class="heroi" aria-labelledby="h-heroi">
    <div class="heroi-texto">
      <p class="rot">{e(ROTULO_DO_TOPO)}</p>
      <h1 id="h-heroi">{e(TITULO_DO_TOPO)}</h1>
      <p class="lead">{e(FRASE_DO_TOPO)}</p>
      <div class="caminhos botoes">{botoes}</div>
    </div>
    <section class="numeros-heroi" aria-label="Três números validados">
      <dl class="tres nums" id="tres-numeros">
{tres}      </dl>
      <p class="corpus" id="corpus">{corpus}</p>
      <p class="corpus"><a id="link-jogadores" href="jogadores.html" title="{e(LINK_JOGADORES["aviso"])}">{e(LINK_JOGADORES["texto"])}</a> · {e(LINK_JOGADORES["aviso"])}</p>
    </section>
{figura}
  </section>

  <section aria-labelledby="h-grade">
    <div class="grade-topo">
      <h2 id="h-grade">Partidas <span class="num" id="grade-contagem">{len(grade)}</span></h2>
      <div class="filtros">
        <div class="chips" id="filtro-origem" role="group" aria-label="Filtrar as partidas por origem">{chips_origem}</div>
        <div class="chips filtro-mapas filtro" id="filtro" role="group" aria-label="Filtrar as partidas por mapa">{chips_mapa}</div>
      </div>
    </div>
    <div class="grid" id="partidas">
{cards}
    </div>
    <p class="vazio" id="vazio" hidden>Nenhuma partida com esse filtro.
      <button type="button" class="btn" id="mostra-todos">Mostrar todos os mapas</button></p>
  </section>
{bloco_prancheta}
  <section class="box" aria-labelledby="h-demo">
    <h2 id="h-demo">Adicionar a sua própria demo</h2>
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
  </main>

  <footer>
    <h2>Como os números são conferidos</h2>
    <p>Placar, kills, ADR e KAST batem com a estatística oficial partida a partida; o rating e o botão do arremesso
    são medidos fora da amostra. O método inteiro, com as tabelas, está no
    <a href="{e(repo_url)}#como-sei-que-os-números-estão-certos">README</a>. Parsing com
    <a href="https://awpy.rtfd.io/">awpy</a> sobre demoparser2; métricas em Polars.</p>
  </footer>
</div>
<script>
  // filtros da grade: origem e mapa; vazio mostra o aviso e o botão que limpa o mapa
  (function () {{
    var estado = {{ origem: "{origem_padrao}", mapa: "" }};
    var cards = document.querySelectorAll("#partidas .mcard");
    function aplica() {{
      var n = 0;
      Array.prototype.forEach.call(cards, function (c) {{
        var mostra = (!estado.origem || c.getAttribute("data-origem") === estado.origem) &&
                     (!estado.mapa || c.getAttribute("data-mapa") === estado.mapa);
        c.hidden = !mostra;
        if (mostra) n++;
      }});
      document.getElementById("grade-contagem").textContent = n;
      document.getElementById("vazio").hidden = n > 0;
    }}
    function liga(grupo, chave) {{
      var botoes = document.querySelectorAll("#" + grupo + " button");
      Array.prototype.forEach.call(botoes, function (b) {{
        b.addEventListener("click", function () {{
          estado[chave] = b.getAttribute("data-valor");
          Array.prototype.forEach.call(botoes, function (x) {{ x.setAttribute("aria-pressed", String(x === b)); }});
          aplica();
        }});
      }});
    }}
    liga("filtro-origem", "origem");
    liga("filtro", "mapa");
    document.getElementById("mostra-todos").addEventListener("click", function () {{
      document.querySelector('#filtro button[data-valor=""]').click();
    }});
    aplica();
  }})();
</script>
</body>
</html>
""")


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
        matches.append(summary)

    if not matches:
        raise SystemExit("Nenhuma partida com a cadeia completa. Rode scripts/process_all_demos.py.")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for old in DOCS_DIR.glob("*.html"):
        old.unlink()

    # o seletor precisa da lista inteira em toda página, e de saber onde está
    nav = [{"id": m["id"], "file": m["file"], "label": m["label"]} for m in matches]

    for m in matches:
        site = {"matches": nav, "current": m["id"], "repo": repo_url, "jogadores": LINK_JOGADORES}
        html = build_html(m["id"], site=site)
        (DOCS_DIR / m["file"]).write_text(html, encoding="utf-8")
        print(f"  {m['file']}  ({len(html) / 1024:.0f} KB)  {m['map_label']} {m['score_a']}-{m['score_b']}")

    # prancheta tática: uma página por mapa com radar e biblioteca de arremessos
    pranchetas = []
    for mapa in mapas_disponiveis():
        html = build_prancheta(mapa, MAP_LABEL, site=url_do_site(repo_url))
        (DOCS_DIR / arquivo_da_pagina(mapa)).write_text(html, encoding="utf-8")
        pranchetas.append({"mapa": mapa, "file": arquivo_da_pagina(mapa), "label": MAP_LABEL.get(mapa, mapa)})
        print(f"  {arquivo_da_pagina(mapa)}  ({len(html) / 1024:.0f} KB)  prancheta")

    # visão agregada por jogador no corpus (fase 7): página separada da partida
    from scripts.build_jogadores import ARQUIVO as ARQUIVO_JOGADORES, build_html as build_jogadores
    pagina_jogadores = build_jogadores(url_do_site(repo_url))
    (DOCS_DIR / ARQUIVO_JOGADORES).write_text(pagina_jogadores, encoding="utf-8")
    print(f"  {ARQUIVO_JOGADORES}  ({len(pagina_jogadores) / 1024:.0f} KB)  jogadores no corpus")

    # os números do topo vêm de numeros_citaveis.json; a imagem do replay é a
    # captura versionada do README (scripts/capturas_readme.py), copiada para o site
    from scripts.numeros_citaveis import carrega as numeros_citaveis
    captura = PROJECT_ROOT / "assets" / "readme" / "replay.png"
    imagem, tamanho, legenda = None, None, None
    if captura.exists():
        # a PNG continua sendo a og:image; na página vai uma WebP com largura e altura declaradas (não empurra
        # o layout, CLS) e carregada sem pressa (lazy): o que conta nos primeiros segundos são os números
        shutil.copyfile(captura, DOCS_DIR / "replay.png")
        from PIL import Image
        with Image.open(captura) as im:
            im.convert("RGB").save(DOCS_DIR / "replay.webp", "WEBP", quality=82, method=6)
            tamanho = im.size
        imagem = "replay.webp"
        legenda = legenda_da_captura(matches)
    (DOCS_DIR / "index.html").write_text(
        build_index(matches, repo_url, pranchetas, numeros=numeros_citaveis(), imagem=imagem,
                    imagem_tamanho=tamanho, legenda=legenda), encoding="utf-8")

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
