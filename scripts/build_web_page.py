"""
Injeta o payload da partida no template e gera a página final, autocontida.

Uso:
    python -m scripts.build_web_page match_01
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from metrics.annotations import impressao_da_calibracao

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PROJECT_ROOT / "dashboard" / "web" / "template.html"


def titulo_da_pagina(match_id: str) -> str:
    """Título da aba, por partida: mapa, placar e times; sem dado, só o mapa.

    Os times vêm do manifesto e só entram quando a partida é profissional (em
    FACEIT o "time" é um nome gerado, `team_<nick>`, que não diz nada).
    """
    base = PROJECT_ROOT / "data" / "processed" / match_id
    mapa = json.loads((base / "match_meta.json").read_text(encoding="utf-8")).get("map_name") or ""
    nome = mapa.removeprefix("de_").capitalize() or match_id
    partes = [nome]
    try:
        m = json.loads((base / "web_payload.json").read_text(encoding="utf-8")).get("match") or {}
        if m.get("score_a") is not None and m.get("score_b") is not None:
            partes[0] = f"{nome} {m['score_a']}–{m['score_b']}"
    except (OSError, ValueError):
        pass
    manifesto = PROJECT_ROOT / "data" / "manifest.json"
    if manifesto.exists():
        linha = json.loads(manifesto.read_text(encoding="utf-8")).get("partidas", {}).get(match_id) or {}
        times = linha.get("times") or {}
        if linha.get("origem") == "profissional" and times.get("A", {}).get("nome") and times.get("B", {}).get("nome"):
            from metrics.times import nome_canonico
            partes.append(f"{nome_canonico(times['A']['nome'])} x {nome_canonico(times['B']['nome'])}")
    return " · ".join(partes)


def _br(x: float, casas: int = 2) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _milhar(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def rodape_html(c: dict) -> str:
    """Metodologia e limites, com os números do corpus LIDOS de
    numeros_citaveis.json (nunca escritos à mão)."""
    co, an, es = c["corpus"], c["convencao_de_angulos"], c["estilos"]
    return (
        "<b>Metodologia.</b> Parsing com awpy sobre demoparser2, métricas próprias em Polars. A convenção "
        "de ângulos do CS2 foi validada contra os dados, não assumida: no tick de cada kill a mira do "
        f"atacante fica a {_br(an['erro_mediano_graus'])}° da vítima na convenção adotada, contra "
        f"{_br(an['erro_mediano_invertida_graus'])}° na invertida ({_milhar(an['kills'])} kills).<br>"
        f"<b>Limites.</b> {_milhar(co['partidas'])} partidas ({_milhar(co['jogador_rounds'])} jogador-rounds), "
        f"todas de nível profissional e não do autor. Os {es['grupos']} jeitos de jogar têm separação fraca: "
        "os grupos existem e são distintos na média, mas a fronteira entre eles não é nítida — e isso não "
        "melhorou ao processar mais partidas, o que sugere que estilo de jogo é um contínuo e não um conjunto "
        "de caixas. Os índices de papel são fórmulas declaradas aqui, não padrões da indústria."
    )


def origem_da_partida(match_id: str) -> str | None:
    """De onde é a partida, para o cabeçalho: "FACEIT" ou o nome do evento."""
    manifesto = PROJECT_ROOT / "data" / "manifest.json"
    if not manifesto.exists():
        return None
    linha = json.loads(manifesto.read_text(encoding="utf-8")).get("partidas", {}).get(match_id) or {}
    if linha.get("origem") == "faceit":
        return "FACEIT"
    if linha.get("evento"):
        return " ".join(p.upper() if p in ("iem", "pgl", "blast", "esl") else p.capitalize()
                        for p in str(linha["evento"]).split("-"))
    return None


def titulo_da_partida(base: Path) -> str | None:
    """O h1 da página da partida: mapa e placar ("Mirage 13–9"). Cada partida
    tem o seu -- o "Uma partida, round a round" é o da landing (auditoria 5.2)."""
    from metrics.constantes import NOME_DO_MAPA
    try:
        mapa = json.loads((base / "match_meta.json").read_text(encoding="utf-8")).get("map_name") or ""
        m = json.loads((base / "web_payload.json").read_text(encoding="utf-8")).get("match") or {}
    except (OSError, ValueError):
        return None
    nome = NOME_DO_MAPA.get(mapa, mapa.removeprefix("de_").capitalize())
    if not nome:
        return None
    if m.get("score_a") is None or m.get("score_b") is None:
        return nome
    return f"{nome} {m['score_a']}–{m['score_b']}"


def dados_da_pagina(match_id: str, base: Path | None = None) -> dict:
    from scripts.numeros_citaveis import carrega
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    return {"origem": origem_da_partida(match_id), "rodape_html": rodape_html(carrega()),
            "titulo": titulo_da_partida(base)}


def build_html(match_id: str, site: dict | None = None, base: Path | None = None) -> str:
    """Devolve o HTML final da partida, com os dados já embutidos.

    `site` é a lista de partidas do site multi-demo (ver scripts/build_site.py).
    Sem ele, a barra de troca de partida fica escondida e o arquivo é um HTML
    solto que funciona offline — que é o modo original da página.
    """
    from scripts.json_em_script import js, texto_seguro

    # `base` troca a pasta dos dados da partida (os testes montam uma partida
    # sintética); o padrão é data/processed/<partida>
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    # todo JSON que entra num <script> passa pela injeção segura: um nome de
    # jogador com `</script>` fecharia o script no meio do dado
    payload = texto_seguro((base / "web_payload.json").read_text(encoding="utf-8"))
    replay = texto_seguro((base / "replay.json").read_text(encoding="utf-8"))
    breakdown_path = base / "breakdown.json"
    breakdown = texto_seguro(breakdown_path.read_text(encoding="utf-8")) if breakdown_path.exists() else "[]"
    # A camada de desenho vive em arquivo separado no repositorio (o template ja
    # esta grande demais) e e injetada aqui, para a pagina continuar sendo um
    # arquivo unico que abre offline.
    # O núcleo compartilhado do mapa (map_core.js) vai antes: a anotação e o
    # replay usam o MapCore.
    map_core = (TEMPLATE.parent / "map_core.js").read_text(encoding="utf-8")
    annotations = (TEMPLATE.parent / "annotations.js").read_text(encoding="utf-8")
    annotations_css = (TEMPLATE.parent / "annotations.css").read_text(encoding="utf-8")

    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("/*__DATA__*/", payload)
        .replace("/*__REPLAY__*/", replay)
        .replace("/*__BREAKDOWN__*/", breakdown)
        .replace("/*__MAP_CORE__*/", map_core)
        .replace("/*__ANNOTATIONS__*/", annotations)
        .replace("/*__ANNOTATIONS_CSS__*/", annotations_css)
    )

    map_name = json.loads((base / "match_meta.json").read_text(encoding="utf-8"))["map_name"]
    radar_path = PROJECT_ROOT / "assets" / "radars" / f"{map_name}.json"
    radar_js = ""
    if radar_path.exists():
        radar = json.loads(radar_path.read_text(encoding="utf-8"))
        # A impressão da calibração vai pronta para a página: é a mesma função que
        # valida um arquivo de anotações exportado, então as duas pontas nunca
        # discordam sobre qual calibração um traço usou.
        radar["calibracao"] = impressao_da_calibracao(radar)
        # o `||` mantém o `null` do template como fallback quando o mapa não tem radar
        radar_js = js(radar, compacto=False) + " ||"
    html = html.replace("/*__RADAR__*/", radar_js)
    # Botão "Criar tática": só quando o mapa desta partida tem prancheta. O link
    # é relativo e funciona igual em dashboard/web/ e em docs/, que têm as duas
    # páginas lado a lado.
    from scripts.build_tactics_page import arquivo_da_pagina, mapas_disponiveis
    prancheta = arquivo_da_pagina(map_name) if map_name in mapas_disponiveis() else None
    html = html.replace("/*__PRANCHETA__*/null", js(prancheta))
    import html as _html
    html = html.replace("/*__PAGINA__*/null", js(dados_da_pagina(match_id, base), compacto=False))
    html = html.replace("<!--__TITULO__-->", _html.escape(titulo_da_pagina(match_id)))
    from scripts.meta_da_pagina import meta_tags, url_do_site
    titulo = titulo_da_pagina(match_id)
    html = html.replace("<!--__META__-->", meta_tags(
        titulo, f"{titulo}: replay no radar, placar round a round e a leitura da partida.",
        url_do_site((site or {}).get("repo")), f"{match_id}.html"))
    html = html.replace("/*__SITE__*/", js(site, compacto=False) + " ||" if site else "")
    return html


def build(match_id: str) -> Path:
    out = PROJECT_ROOT / "dashboard" / "web" / f"{match_id}.html"
    out.write_text(build_html(match_id), encoding="utf-8")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera a página web autocontida da partida.")
    parser.add_argument("match_id", type=str)
    args = parser.parse_args()
    out = build(args.match_id)
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
