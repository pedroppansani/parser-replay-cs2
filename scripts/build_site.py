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

from scripts.build_tactics_page import arquivo_da_biblioteca, arquivo_da_pagina, biblioteca_js, mapas_disponiveis
from scripts.build_tactics_page import build_html as build_prancheta
from scripts.build_web_page import build_html

from metrics.constantes import NOME_DO_MAPA
from scripts.meta_da_pagina import MARCA, meta_tags, url_do_site

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"
# Pré-visualização da aba Perfil com TODOS os tipos de erro marcados "em validação" (fase 12, 12.4):
# vai para preview/, que está no .gitignore e nunca é publicada (o Pages publica só docs/).
PREVIEW_DIR = PROJECT_ROOT / "preview"

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
    """A partida de exemplo da landing: desde a v2-3 é o PRIMEIRO card da grade, em destaque (o botão principal
    "Explorar partidas" leva à lista; plano v2-0, dúvida 2, opção A).

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


# Textos da landing (entrega-v2-goatdemo §5.2 e §5.7, aceitos pelo Pedro no plano v2-0, dúvidas 1, 2 e 9). Saem
# daqui, prontos, como a decisão 18 manda: o HTML não escreve frase própria. Nenhum número de corpus aqui (37): os
# três números e a linha do corpus vêm de numeros_citaveis.json.
TEXTOS_DA_LANDING = {
    "titulo": "Cada round, explicado.",
    "og_frase": "Replay de partidas de CS2",        # a linha de baixo da imagem de compartilhamento (protótipo)
    "subtitulo": ("Veja a partida de CS2 como uma jogada: onde cada um estava, o que cada granada fez e por que o "
                  "round virou."),
    "explorar": "Explorar partidas",
    "adicionar": "Adicionar demo",
    "em_breve": "Em breve",
    "em_breve_frase": "Envio de demo próprio. Por enquanto, explore as partidas do corpus.",
    "numeros": "Três números validados",
    "partidas": "Partidas",
    "exemplo": "Para começar: a profissional decidida num round, de placar mais apertado",
    "vazio": "Nenhuma partida com esse filtro.",
    "mostrar_todos": "Mostrar todos os mapas",
    "dialogo_titulo": "Adicionar demo",
    "fechar": "Fechar",
    "dialogo_aviso": "O envio de demo próprio ainda não está disponível.",
    "dialogo_frase": ("Hoje as partidas são processadas no computador do autor, em Python, e o site mostra o resultado. "
                      "Para sugerir uma partida, abra uma issue no GitHub com o link da demo."),
    "dialogo_issue": "Abrir uma issue no GitHub",
    "rodape_marca": f"{MARCA}",
    "rodape_projeto": "Projeto de portfólio, sem fins comerciais.",
    "rodape_metodo": "Como os números são conferidos",
    "rodape_github": "Código no GitHub",
    "rodape_terceiros": ("Os mapas e os pontos das laterais vêm dos radares do jogo, e os agentes desta página são derivados "
                         "de gravações do jogo: pertencem à Valve, e o projeto não tem ligação com ela. "
                         "Fontes Geist e Geist Mono (SIL OFL 1.1)."),
    "agente": {"tr": "Agente TR com fuzil", "ct": "Agente CT com fuzil"},
    "pular": "Pular para o conteúdo",
}
TITULO_DO_TOPO = TEXTOS_DA_LANDING["titulo"]
FRASE_DO_TOPO = TEXTOS_DA_LANDING["subtitulo"]
TITULO_DA_PAGINA = f"Partidas lidas round a round · {MARCA}"
ROTULO_ORIGEM = {"profissional": "Profissionais", "faceit": "FACEIT"}
# Tema da landing (decisão 48, entrega-v2-goatdemo §5.2): claro; as outras páginas seguem no escuro até a v2-4/v2-5.
TEMA_DA_LANDING = "claro"
# Laterais em pontos a partir de 1440 px (§5.2 item 4): Mirage à esquerda, Dust II à direita (as duas do protótipo)
LATERAIS = (("e", "de_mirage"), ("d", "de_dust2"))
AGENTE_DIR = Path(__file__).resolve().parent.parent / "dashboard" / "web" / "agente"


def copia_agente(saida: Path) -> None:
    """Os dois .js do agente em `<saida>/agente/` (o tocador baixa só o sorteado). Os quadros fixos vão no HTML."""
    (saida / "agente").mkdir(parents=True, exist_ok=True)
    for js in sorted(AGENTE_DIR.glob("agente-*.js")):
        shutil.copyfile(js, saida / "agente" / js.name)


def _quadro_do_agente(lado: str, escondido: bool) -> str:
    """O quadro fixo do agente em SVG (gerado junto com o .js, ver o manifesto), em linha: aparece sem JavaScript."""
    svg = (AGENTE_DIR / f"agente-{lado}-quadro.svg").read_text(encoding="utf-8").strip()
    estilo = ' style="display:none"' if escondido else ""
    return svg.replace('<svg xmlns="http://www.w3.org/2000/svg"',
                       f'<svg aria-hidden="true" focusable="false" class="q-{lado}"{estilo}', 1)


def _titulo_pixelado() -> str:
    svg = (AGENTE_DIR.parent / "landing" / "titulo-pixel.svg").read_text(encoding="utf-8").strip()
    return svg.replace('<svg xmlns="http://www.w3.org/2000/svg"', '<svg class="pix"', 1)


def _lateral(lado: str, mapa: str) -> str:
    """Um mapa em pontos (máscara gerada no build a partir do radar do .json, scripts/design/gera_pontos)."""
    from html import escape as e

    from scripts.design.gera_pontos import data_uri
    if not (PROJECT_ROOT / "assets" / "radars" / f"{mapa}.json").exists():
        return ""
    return (f'<div class="lateral {lado}" aria-hidden="true" style="--m:url({data_uri(mapa)})"><div class="pts"><i></i><u></u>'
            f'</div><span>{e(MAP_LABEL.get(mapa, mapa))}</span></div>')


def _card(m: dict, exemplo: bool = False) -> str:
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
    # a partida de exemplo (critério declarado em partida_de_exemplo) é o primeiro card, em destaque (dúvida 2, A)
    destaque = (f' data-exemplo="1"', f'        <span class="cp-exemplo">{e(TEXTOS_DA_LANDING["exemplo"])}</span>\n') if exemplo else ("", "")
    return (f'      <a class="mcard cp" data-mapa="{e(str(m.get("map", "")))}" data-origem="{e(str(m.get("origem") or ""))}" '
            f'href="{e(m["file"])}"{destaque[0]}>\n'
            + destaque[1] +
            f'        <span class="cp-topo"><span>{topo_esq}</span><span>{topo_dir}</span></span>\n'
            f'        {linha("A", m["score_a"])}\n        {linha("B", m["score_b"])}\n'
            f'        <span class="cp-frase">{e(m.get("decisor") or "")}</span>\n'
            + ("" if m["has_radar"] else '        <span class="noradar">sem radar calibrado</span>\n')
            + "      </a>")


def gera_imagens_og(saida: Path, matches: list[dict]) -> None:
    """As imagens de compartilhamento 1200x630 em `<saida>/og/` (v2-6, decisão 48): uma por partida (os times e o
    placar do cabeçalho, o mapa, o evento e a linha do decisor: só o que o card da landing já mostra) e a da landing
    (título e frase de TEXTOS_DA_LANDING, mapa da lateral direita). Pillow, sem navegador; mesmos bytes a cada build."""
    from scripts.design.gera_og import imagem_da_landing, imagem_da_partida
    from scripts.meta_da_pagina import IMAGEM_OG, imagem_da_partida as caminho
    pasta = saida / "og"
    pasta.mkdir(exist_ok=True)
    for velha in pasta.glob("*.png"):
        velha.unlink()
    for m in matches:
        lados = m.get("lados") or {}
        nomes = tuple((lados.get(k) or {}).get("nome") or f"Lado {k}" for k in "AB")
        local = m.get("evento") or ("FACEIT" if m.get("origem") == "faceit" else "")
        linhas = [" · ".join(x for x in (str(m["map_label"]), local) if x), m.get("decisor") or ""]
        (saida / caminho(m["id"])).write_bytes(
            imagem_da_partida(m.get("map"), nomes, (m["score_a"], m["score_b"]), m.get("venceu"), linhas))
    T = TEXTOS_DA_LANDING
    (saida / IMAGEM_OG).write_bytes(imagem_da_landing(LATERAIS[-1][1], T["titulo"], T["og_frase"]))
    print(f"  og/  ({len(matches) + 1} imagens de compartilhamento)")


def build_index(matches: list[dict], repo_url: str, pranchetas: list[dict] | None = None,
                numeros: dict | None = None, imagem: str | None = None) -> str:
    """A landing (entrega-v2-goatdemo §5.2). `numeros` é o documento de numeros_citaveis.json (os três números e a
    linha do corpus vêm dele, nunca escritos aqui). `imagem` não é mais usada (a og:image é a da landing,
    `scripts/meta_da_pagina.IMAGEM_OG`, desde a v2-6). Ordem no HTML = ordem do celular: título, botões, agente,
    números, partidas, rodapé."""
    from collections import Counter
    from html import escape as e

    from scripts.design_head import aplica, topo_do_site, v2_js  # tokens, fontes e a navbar (decisão 48)
    from scripts.numeros_citaveis import blocos_de_texto, tres_numeros
    T = TEXTOS_DA_LANDING

    # todo texto que vem do dado (nicks, mapa, frase do decisor) é escapado: um nick com `<` não vira marcação
    exemplo = partida_de_exemplo(matches)
    grade = ordem_da_grade(matches)
    if exemplo is not None:
        grade = [exemplo] + [m for m in grade if m is not exemplo]
    cards = "\n".join(_card(m, exemplo=m is exemplo) for m in grade)

    tres = "".join(
        f"""        <div class="num-item"><dt><b class="num">{e(n['valor'])}</b>{e(n['rotulo'])}</dt><dd>{e(n['contexto'])}</dd></div>\n"""
        for n in (tres_numeros(numeros) if numeros else []))
    corpus = e(blocos_de_texto(numeros)["corpus"]) if numeros else ""
    prancheta_do_exemplo = next((p for p in (pranchetas or []) if exemplo and p.get("mapa") == exemplo.get("map")),
                                (pranchetas or [None])[0])

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

    laterais = "".join(_lateral(lado, mapa) for lado, mapa in LATERAIS)
    agente_js = (AGENTE_DIR.parent / "agente.js").read_text(encoding="utf-8")
    rotulos_do_agente = T["agente"]

    return aplica(f"""<!DOCTYPE html>
<html lang="pt-BR" data-tema="{TEMA_DA_LANDING}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(TITULO_DA_PAGINA)}</title>
{meta_tags(TITULO_DA_PAGINA, FRASE_DO_TOPO, url_do_site(repo_url))}
<!--__FONTES__-->
<style>
  /* Os tokens (cores, fontes, espaços) vêm de dashboard/web/tokens.css; a navbar, de dashboard/web/v2.css. */
  /*__TOKENS__*/
  /*__V2__*/
  * {{ box-sizing: border-box; }}
  :where(button, a[href], select, input, textarea, summary, [tabindex]):focus-visible {{
    outline: 2px solid var(--foco); outline-offset: 2px;
  }}
  body {{ margin: 0; background: var(--fundo); color: var(--tinta); font: 400 var(--t-base)/1.55 var(--f-texto);
    -webkit-font-smoothing: antialiased; }}
  h1, h2, p, figure, dl, dd {{ margin: 0; }}
  .sr {{ position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }}
  .shell {{ max-width: 1212px; margin: 0 auto; padding: 0 16px; }}
  main {{ outline: none; }}
  .num {{ font-family: var(--f-num); font-variant-numeric: tabular-nums; }}

  /* topo: título pixelado, subtítulo, as duas ações e o agente à direita (2 colunas em >= 761 px) */
  .heroi {{ display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr); gap: 32px; align-items: center;
    padding: 40px 0 16px; }}
  .heroi-texto {{ display: grid; gap: 20px; justify-items: start; }}
  .pix {{ display: block; width: 100%; max-width: 620px; height: auto; color: var(--tinta); }}
  .sub {{ color: var(--tinta-2); font-size: var(--t-lg); max-width: 44ch; }}
  .acoes {{ display: flex; flex-wrap: wrap; gap: 12px; }}
  .btn {{ display: inline-flex; align-items: center; justify-content: center; gap: 8px; min-height: var(--toque);
    padding: 0 20px; border-radius: var(--r-ctl); border: 1px solid var(--borda); background: transparent;
    color: var(--tinta); font: inherit; font-weight: 500; cursor: pointer; text-decoration: none; white-space: nowrap; }}
  .btn:hover {{ background: var(--superficie-2); }}
  .btn.prim {{ background: var(--acao); color: var(--acao-ink); border-color: var(--acao); }}
  .btn.prim:hover {{ opacity: 0.88; }}
  .tag {{ display: inline-flex; align-items: center; min-height: 24px; padding: 0 10px; border-radius: var(--r-ctl);
    border: 1px dashed var(--borda); color: var(--tinta-2); font-size: var(--t-xs); font-weight: 500; white-space: nowrap; }}
  .em-breve {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; color: var(--tinta-2); font-size: var(--t-sm); }}
  /* o agente (§6.2): caixa fixa 251/264 com qualquer lado (CLS 0); sem JS, o quadro fixo do TR */
  .agente {{ position: relative; justify-self: center; width: min(100%, 300px); aspect-ratio: 251 / 264; margin: 0;
    color: var(--tinta); }}
  .agente svg, .agente canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; display: block; }}
  .agente canvas {{ opacity: 0; }}
  .agente.pronto canvas {{ opacity: 1; }} .agente.pronto svg {{ opacity: 0; }}
  .agente .corte {{ position: absolute; left: 4%; right: 4%; bottom: -6px; height: 3px; border-radius: 2px; background: var(--ct); }}
  .agente[data-lado="tr"] .corte {{ background: var(--tr); }}
  @media (max-width: 760px) {{
    .heroi {{ grid-template-columns: minmax(0, 1fr); padding-top: 24px; }}
    .agente {{ width: min(70%, 240px); }}
  }}

  /* três números (mono 34 px), 3 colunas em >= 761 px */
  .numeros-heroi {{ padding: 24px 0 8px; }}
  .tres {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
  .tres > div {{ display: grid; align-content: start; gap: 4px; padding: 20px; background: var(--superficie);
    border: 1px solid var(--linha); border-radius: var(--r-card); }}
  .tres dt {{ font-weight: var(--peso-forte); }}
  .tres dt .num {{ display: block; font-size: 34px; line-height: 1.1; font-weight: 500; white-space: nowrap; }}
  .tres dd {{ color: var(--tinta-2); font-size: var(--t-sm); }}
  .corpus {{ margin-top: 12px; color: var(--apagado); font-size: var(--t-sm); }}
  @media (max-width: 760px) {{ .tres {{ grid-template-columns: minmax(0, 1fr); }} }}

  /* partidas: filtros em pílula e cards de 16 px (1/2/3 colunas) */
  .grade-topo {{ display: grid; gap: 12px; padding: 32px 0 16px; }}
  .grade-topo h2 {{ font-size: var(--t-xl); font-weight: var(--peso-forte); letter-spacing: -0.01em; }}
  .grade-topo h2 .num {{ color: var(--apagado); font-weight: 400; }}
  .filtros {{ display: grid; gap: 12px; min-width: 0; }}
  .chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .filtro-mapas {{ flex-wrap: nowrap; overflow-x: auto; padding: 4px 2px 6px; scrollbar-width: thin; }}
  @media (min-width: 761px) {{ .filtro-mapas {{ flex-wrap: wrap; overflow: visible; }} }}
  .chip {{ display: inline-flex; align-items: center; gap: 8px; flex: none; min-height: var(--toque); padding: 0 16px;
    border-radius: var(--r-ctl); border: 1px solid var(--borda); background: var(--superficie); color: var(--tinta);
    font: inherit; font-size: var(--t-sm); font-weight: 500; cursor: pointer; white-space: nowrap; }}
  .chip .num {{ color: var(--apagado); }}
  .chip[aria-pressed="true"] {{ background: var(--acao); color: var(--acao-ink); border-color: var(--acao); }}
  .chip[aria-pressed="true"] .num {{ color: inherit; }}
  .grid {{ display: grid; gap: 16px; grid-template-columns: minmax(0, 1fr); }}
  @media (min-width: 640px) {{ .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
  @media (min-width: 1024px) {{ .grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }} }}
  .cp {{ display: grid; gap: 10px; align-content: start; min-width: 0; padding: 20px; color: var(--tinta); text-decoration: none;
    background: var(--superficie); border: 1px solid var(--linha); border-radius: var(--r-card); }}
  .cp:hover {{ border-color: var(--borda); }}
  .cp[hidden] {{ display: none; }}
  .cp[data-exemplo] {{ border-color: var(--tinta); }}
  .cp-exemplo {{ font-size: var(--t-xs); font-weight: 500; color: var(--tinta-2); }}
  .cp-topo {{ display: flex; justify-content: space-between; gap: 8px; color: var(--apagado); font-size: var(--t-sm); }}
  .cp-linha {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 8px; }}
  .cp-linha .nome {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500; }}
  .cp-linha .num {{ font-size: var(--t-lg); font-weight: 500; }}
  .cp-linha.perdeu {{ color: var(--tinta-2); }} .cp-linha.perdeu .nome {{ font-weight: 400; }}
  .tag-venceu {{ font-size: var(--t-xs); font-weight: var(--peso-forte); text-transform: uppercase; letter-spacing: 0.06em;
    background: var(--tinta); color: var(--fundo); border-radius: var(--r-ctl); padding: 2px 8px; margin-left: 6px; }}
  .cp-frase {{ color: var(--tinta-2); font-size: var(--t-sm); }}
  .noradar {{ font-size: var(--t-xs); color: var(--apagado); font-style: italic; }}
  .vazio {{ display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding: 24px 16px; color: var(--tinta-2);
    border: 1px dashed var(--borda); border-radius: var(--r-card); }}
  .vazio[hidden] {{ display: none; }}

  /* rodapé de terceiros */
  .rodape {{ display: grid; gap: 8px; margin-top: 48px; padding: 32px 0 48px; border-top: 1px solid var(--linha);
    color: var(--tinta-2); font-size: var(--t-sm); }}
  .rodape b {{ color: var(--tinta); font-weight: var(--peso-forte); }}
  .rodape a {{ color: inherit; text-underline-offset: 3px; }}

  /* "Adicionar demo" (§5.7): diálogo honesto, "em breve" */
  dialog {{ width: min(520px, calc(100vw - 32px)); max-height: calc(100vh - 32px); overflow: auto; padding: 0;
    border: 1px solid var(--borda); border-radius: var(--r-card); background: var(--superficie); color: var(--tinta); }}
  dialog::backdrop {{ background: color-mix(in srgb, var(--fundo-mapa) 60%, transparent); }}
  .dlg {{ display: grid; gap: 16px; padding: 24px; }}
  .dlg-cab {{ display: flex; justify-content: space-between; align-items: center; gap: 12px; }}
  .dlg-cab h2 {{ font-size: var(--t-lg); font-weight: var(--peso-forte); }}
  .fechar {{ min-width: var(--toque); min-height: var(--toque); border-radius: var(--r-ctl); border: 1px solid var(--borda);
    background: transparent; color: var(--tinta); font: inherit; font-size: var(--t-lg); cursor: pointer; }}
  .painel-honesto {{ display: grid; gap: 8px; justify-items: start; padding: 16px; border: 1px solid var(--borda);
    border-radius: var(--r-card); background: var(--superficie-2); color: var(--tinta-2); }}
  .painel-honesto b {{ color: var(--tinta); }}
  .painel-honesto .acoes {{ margin-top: 8px; }}

  /* laterais em pontos (>= 1440 px), decorativas, sem empurrar nada */
  .lateral {{ display: none; }}
  @media (min-width: 1440px) {{
    .tem-laterais {{ position: relative; overflow-x: clip; --lw: clamp(104px, calc((100vw - 1180px) / 2 - 32px), 300px); }}
    .lateral {{ display: grid; position: absolute; top: 96px; height: 480px; width: var(--lw); pointer-events: none;
      justify-items: center; align-content: center; gap: 10px; }}
    .lateral.e {{ left: 16px; }} .lateral.d {{ right: 16px; }}
    .lateral .pts {{ position: relative; width: 100%; aspect-ratio: 1; }}
    .lateral i, .lateral u {{ position: absolute; inset: 0; -webkit-mask: var(--m) center / 100% 100% no-repeat;
      mask: var(--m) center / 100% 100% no-repeat; }}
    .lateral i {{ background: var(--borda); opacity: 0.55; }}
    .lateral u {{ background: linear-gradient(100deg, transparent 42%, var(--tinta-2) 50%, transparent 58%) 0 0 / 300% 100%;
      animation: varre 9s linear infinite; }}
    .lateral span {{ font-size: var(--t-xs); color: var(--apagado); }}
  }}
  @keyframes varre {{ from {{ background-position: 100% 0; }} to {{ background-position: -100% 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .lateral u {{ animation: none; }} }}
</style>
</head>
<body>
<a class="pular" href="#conteudo">{e(T["pular"])}</a>
<div class="tem-laterais">
  {laterais}
<div class="shell">
  {topo_do_site("partidas", prancheta_do_exemplo["file"] if prancheta_do_exemplo else None, repo_url)}

  <main id="conteudo" tabindex="-1">
  <section class="heroi" aria-labelledby="h-heroi">
    <div class="heroi-texto">
      <h1 id="h-heroi"><span class="sr">{e(T["titulo"])}</span>{_titulo_pixelado()}</h1>
      <p class="sub">{e(T["subtitulo"])}</p>
      <div class="acoes"><a class="btn prim" id="btn-explorar" href="#partidas">{e(T["explorar"])}</a><button class="btn" type="button" id="btn-demo" data-abre-demo>{e(T["adicionar"])}</button></div>
      <p class="em-breve"><span class="tag">{e(T["em_breve"])}</span> {e(T["em_breve_frase"])}</p>
    </div>
    <figure class="agente" id="agente" data-lado="tr" data-base="agente/" role="img" aria-label="{e(rotulos_do_agente["tr"])}">{_quadro_do_agente("tr", False)}{_quadro_do_agente("ct", True)}<canvas aria-hidden="true"></canvas><span class="corte" aria-hidden="true"></span></figure>
    <script>
      // sorteio do lado, antes do primeiro desenho (§6.2): ?agente=ct|tr força; sem JS fica o TR
      (function () {{ var f = document.getElementById("agente"), q = new URLSearchParams(location.search).get("agente"),
        l = (q === "ct" || q === "tr") ? q : (Math.random() < 0.5 ? "ct" : "tr");
        f.dataset.lado = l;
        if (l === "ct") {{ f.querySelector(".q-tr").style.display = "none"; f.querySelector(".q-ct").style.display = "";
          f.setAttribute("aria-label", "{e(rotulos_do_agente["ct"])}"); }} }})();
    </script>
  </section>

  <section class="numeros-heroi" aria-label="{e(T["numeros"])}">
    <dl class="tres nums" id="tres-numeros">
{tres}    </dl>
    <p class="corpus" id="corpus">{corpus}</p>
  </section>

  <section aria-labelledby="h-grade">
    <div class="grade-topo">
      <h2 id="h-grade">{e(T["partidas"])} <span class="num" id="grade-contagem">{len(grade)}</span></h2>
      <div class="filtros">
        <div class="chips" id="filtro-origem" role="group" aria-label="Filtrar as partidas por origem">{chips_origem}</div>
        <div class="chips filtro-mapas filtro" id="filtro" role="group" aria-label="Filtrar as partidas por mapa">{chips_mapa}</div>
      </div>
    </div>
    <div class="grid" id="partidas">
{cards}
    </div>
    <p class="vazio" id="vazio" hidden>{e(T["vazio"])}
      <button type="button" class="btn" id="mostra-todos">{e(T["mostrar_todos"])}</button></p>
  </section>
  </main>

  <footer class="rodape">
    <b>{e(T["rodape_marca"])}</b>
    <p>{e(T["rodape_projeto"])} <a href="{e(repo_url)}#como-sei-que-os-números-estão-certos">{e(T["rodape_metodo"])}</a> ·
      <a id="link-github" href="{e(repo_url)}">{e(T["rodape_github"])}</a></p>
    <p>{e(T["rodape_terceiros"])}</p>
  </footer>
</div>
</div>
<dialog id="dlg-demo" aria-labelledby="dlg-t">
  <div class="dlg">
    <div class="dlg-cab"><h2 id="dlg-t">{e(T["dialogo_titulo"])}</h2><button class="fechar" type="button" aria-label="{e(T["fechar"])}">×</button></div>
    <div class="painel-honesto">
      <span class="tag">{e(T["em_breve"])}</span>
      <p><b>{e(T["dialogo_aviso"])}</b></p>
      <p>{e(T["dialogo_frase"])}</p>
      <div class="acoes"><a class="btn prim" href="#partidas" data-fecha>{e(T["explorar"])}</a><a class="btn" id="link-issue" href="{e(repo_url)}/issues">{e(T["dialogo_issue"])}</a></div>
    </div>
  </div>
</dialog>
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
<script>
{v2_js()}
</script>
<script>
{agente_js}
</script>
</body>
</html>
""")


def build(repo_url: str, preview: bool = False) -> Path:
    """Gera o site em docs/; com `preview`, em preview/, com os tipos de erro não validados à mostra."""
    saida = PREVIEW_DIR if preview else DOCS_DIR
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

    saida.mkdir(parents=True, exist_ok=True)
    # as fontes Geist e Geist Mono (decisão 48) ficam em fontes/, ao lado das páginas
    from scripts.design_head import copia_fontes
    copia_fontes(saida)
    for old in saida.glob("*.html"):
        old.unlink()

    # o seletor precisa da lista inteira em toda página, e de saber onde está
    nav = [{"id": m["id"], "file": m["file"], "label": m["label"]} for m in matches]

    for m in matches:
        site = {"matches": nav, "current": m["id"], "repo": repo_url, "jogadores": LINK_JOGADORES}
        html = build_html(m["id"], site=site, preview=preview)
        (saida / m["file"]).write_text(html, encoding="utf-8")
        print(f"  {m['file']}  ({len(html) / 1024:.0f} KB)  {m['map_label']} {m['score_a']}-{m['score_b']}")

    # prancheta tática: uma página por mapa com radar e biblioteca de arremessos
    pranchetas = []
    # grupos (fase 13): o supabase-js fixado é conferido pelo sha256 em todo build, e só vai para docs/ (ao lado
    # das páginas, carregado ao abrir um grupo) quando o grupo está ligado e configurado (scripts/grupos_config.py)
    from scripts.grupos_config import ARQUIVO_SUPABASE_JS, confere_biblioteca
    from scripts.grupos_config import configuracao as config_do_grupo
    biblioteca = confere_biblioteca()
    com_grupo = False
    for mapa in mapas_disponiveis():
        grupo = config_do_grupo(url_do_site(repo_url), arquivo_da_pagina(mapa))
        com_grupo = com_grupo or grupo is not None
        html = build_prancheta(mapa, MAP_LABEL, site=url_do_site(repo_url), grupo=grupo, biblioteca_externa=True)
        (saida / arquivo_da_pagina(mapa)).write_text(html, encoding="utf-8")
        # a biblioteca de arremessos num arquivo próprio, carregado depois de a tela montar (cartão 20)
        bib = biblioteca_js(mapa)
        if bib is not None:
            (saida / arquivo_da_biblioteca(mapa)).parent.mkdir(exist_ok=True)
            (saida / arquivo_da_biblioteca(mapa)).write_text(bib, encoding="utf-8")
        pranchetas.append({"mapa": mapa, "file": arquivo_da_pagina(mapa), "label": MAP_LABEL.get(mapa, mapa)})
        print(f"  {arquivo_da_pagina(mapa)}  ({len(html) / 1024:.0f} KB)  prancheta")

    if com_grupo:
        (saida / "vendor").mkdir(exist_ok=True)
        shutil.copyfile(biblioteca, saida / "vendor" / ARQUIVO_SUPABASE_JS)
        confere_biblioteca(saida / "vendor" / ARQUIVO_SUPABASE_JS)
        print(f"  vendor/{ARQUIVO_SUPABASE_JS}  (grupos ligados; sha256 conferido)")

    # visão agregada por jogador no corpus (fase 7): página separada da partida
    from scripts.build_jogadores import ARQUIVO as ARQUIVO_JOGADORES, build_html as build_jogadores
    pagina_jogadores = build_jogadores(url_do_site(repo_url))
    (saida / ARQUIVO_JOGADORES).write_text(pagina_jogadores, encoding="utf-8")
    print(f"  {ARQUIVO_JOGADORES}  ({len(pagina_jogadores) / 1024:.0f} KB)  jogadores no corpus")

    # os números do topo vêm de numeros_citaveis.json; a og:image é a imagem de compartilhamento (v2-6), não mais a
    # captura do replay
    from scripts.numeros_citaveis import carrega as numeros_citaveis
    for velha in ("replay.png", "replay.webp"):
        (saida / velha).unlink(missing_ok=True)
    gera_imagens_og(saida, matches)
    # o agente da landing (decisão 48): os dois .js em agente/, ao lado das páginas; só o sorteado é baixado
    copia_agente(saida)
    (saida / "index.html").write_text(build_index(matches, repo_url, pranchetas, numeros=numeros_citaveis()),
                                      encoding="utf-8")

    # o GitHub Pages passa o conteúdo pelo Jekyll por padrão, que ignora arquivos
    # e pastas começando com underscore; .nojekyll desliga isso
    (saida / ".nojekyll").write_text("", encoding="utf-8")

    print(f"\nSite em {saida} · {len(matches)} partida(s) · abra {saida.name}/index.html")
    return saida


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera o site estático de demonstração em docs/.")
    parser.add_argument(
        "--repo",
        default="https://github.com/pedroppansani/parser-replay-cs2",
        help="URL do repositório, usada nas instruções da página",
    )
    parser.add_argument(
        "--mostrar-erros-nao-validados", action="store_true",
        help="gera em preview/ (fora do git, nunca publicado) a aba Perfil com todos os tipos de erro em validação",
    )
    args = parser.parse_args()
    build(args.repo, preview=args.mostrar_erros_nao_validados)


if __name__ == "__main__":
    main()
