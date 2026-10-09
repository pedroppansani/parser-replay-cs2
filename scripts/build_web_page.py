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


def _manifesto_da_partida(match_id: str) -> dict:
    manifesto = PROJECT_ROOT / "data" / "manifest.json"
    if not manifesto.exists():
        return {}
    return json.loads(manifesto.read_text(encoding="utf-8")).get("partidas", {}).get(match_id) or {}


def _le_json(caminho: Path) -> dict:
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _nome_do_mapa(base: Path, match_id: str) -> str:
    from metrics.constantes import NOME_DO_MAPA
    mapa = _le_json(base / "match_meta.json").get("map_name") or ""
    return NOME_DO_MAPA.get(mapa, mapa.removeprefix("de_").capitalize()) or match_id


def _nome_do_lado(linha: dict, lado: str, nicks: list[str] | None = None) -> str:
    """O nome de um lado: o canônico do time (profissionais) ou "Time de <nick>" (FACEIT)."""
    from metrics.times import nome_canonico, nome_do_lado_faceit
    info = (linha.get("times") or {}).get(lado) or {}
    if linha.get("origem") == "profissional" and info.get("nome"):
        return nome_canonico(info["nome"])
    return nome_do_lado_faceit(nicks or info.get("jogadores") or []) or f"Lado {lado}"


def cabecalho_da_partida(match_id: str, base: Path | None = None) -> dict | None:
    """Tudo que o placar do cabeçalho mostra, pronto: nome, pontos, quem venceu e de que lado começou.

    O nome do lado é o canônico do time nas partidas profissionais e "Time de <nick>" na FACEIT
    (metrics.times.nome_do_lado_faceit), com os nicks DA PARTIDA. Sem placar no payload, devolve None
    e a página cai no título só com o mapa. Os rótulos "começou CT/TR" e "venceu" são do JS.
    """
    from leitura.narrativa import linha_do_decisor
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    payload = _le_json(base / "web_payload.json")
    m = payload.get("match") or {}
    if m.get("score_a") is None or m.get("score_b") is None:
        return None
    linha = _manifesto_da_partida(match_id)
    times = linha.get("times") or {}
    lados = {}
    for lado, pts in (("A", m["score_a"]), ("B", m["score_b"])):
        info = times.get(lado) or {}
        nome = _nome_do_lado(linha, lado, (m.get("rosters") or {}).get(lado))
        lados[lado] = {"nome": nome, "pontos": pts, "comecou": "tr" if (info.get("comecou_de") or ("t" if lado == "A" else "ct")) == "t" else "ct"}
    venceu = "A" if m["score_a"] > m["score_b"] else "B" if m["score_b"] > m["score_a"] else None
    decisivo = (payload.get("decisive_round") or {}).get("round")
    mvp = (payload.get("mvp_card") or {}).get("name")
    return {"lados": lados, "venceu": venceu, "decisor": linha_do_decisor(decisivo, mvp), "round_decisivo": decisivo,
            "mapa": _nome_do_mapa(base, match_id)}


def com_os_nomes_dos_lados(payload_texto: str, cabecalho: dict | None) -> str:
    """Troca "Time A"/"Time B" nas frases prontas (`narrative`) pelo nome do lado no cabeçalho.

    As frases saem de leitura/narrativa.py falando de "Time A" e "Time B" (o identificador interno);
    a página mostra o nome do lado ("MOUZ", "Time de donk666"). Só o TEXTO muda, nenhum número.
    """
    if not cabecalho:
        return payload_texto
    import re
    dados = json.loads(payload_texto)
    nomes = {k: v["nome"] for k, v in cabecalho["lados"].items()}
    narrativa = dados.get("narrative")
    if not isinstance(narrativa, dict):
        return payload_texto
    for chave, valor in narrativa.items():
        if isinstance(valor, str):
            narrativa[chave] = re.sub(r"(?<!\w)Time ([AB])(?!\w)", lambda m: nomes[m.group(1)], valor)
    return json.dumps(dados, ensure_ascii=False, separators=(",", ":"))


def _cabecalho_para_a_pagina(c: dict | None) -> dict | None:
    """O que o JS recebe do cabeçalho: sem os pontos nem o round (a página os lê do payload, que já os traz;
    um segundo caminho para o mesmo número é onde os dois discordariam)."""
    if not c:
        return None
    return {"lados": {k: {"nome": v["nome"], "comecou": v["comecou"]} for k, v in c["lados"].items()},
            "venceu": c["venceu"], "decisor": c["decisor"]}


def cabecalho_html(match_id: str, base: Path, site: dict | None) -> dict[str, str]:
    """Migalhas, placar (h1) e linha do decisor em HTML pronto, para a página não mudar de altura depois
    de carregar (CLS, A12). A mesma estrutura que o JS montava; nome de time e de jogador é escapado.
    Os rótulos "venceu" e "começou CT/TR" são os mesmos do JS (COMECOU no template)."""
    import html as _h
    c = cabecalho_da_partida(match_id, base)
    payload = _le_json(base / "web_payload.json")
    m = payload.get("match") or {}
    mapa = _nome_do_mapa(base, match_id)
    origem = origem_da_partida(match_id)
    partes = []
    if site:                      # "Partidas" só no site; o arquivo solto não tem para onde voltar
        partes.append('<a id="c-partidas" href="index.html">Partidas</a><em>/</em>')
    partes.append(f'<span id="c-map">{_h.escape(mapa)}</span><em>/</em>')
    if origem:
        partes.append(f'<span id="c-origem">{_h.escape(origem)}</span><em>/</em>')
    partes.append(f'<span id="c-rounds">{m.get("rounds", "")} rounds</span>')
    migalhas = "".join(partes)
    if not c:
        return {"migalhas": migalhas, "placar": _h.escape(mapa), "decisor": ""}
    comecou = {"ct": "começou CT", "tr": "começou TR"}

    def lado(k: str, cls: str) -> str:
        info, venceu = c["lados"][k], c["venceu"] == k
        nome = f'<span class="nome" title="{_h.escape(info["nome"])}">{_h.escape(info["nome"])}</span>'
        pts = f'<span class="pts">{info["pontos"]}</span>'
        miolo = nome + pts if cls == "a" else pts + nome
        tag_venceu = '<span class="tag-venceu">venceu</span>' if venceu else ""
        tag = f'<span class="tag comecou {info["comecou"]}">{comecou[info["comecou"]]}</span>'
        return f'<span class="lado {cls} {"venceu" if venceu else "perdeu"}">{miolo}{tag_venceu}{tag}</span>'

    placar = lado("A", "a") + '<span class="x" aria-hidden="true">×</span>' + lado("B", "b")
    return {"migalhas": migalhas, "placar": placar, "decisor": _h.escape(c["decisor"])}


def titulo_da_pagina(match_id: str, base: Path | None = None) -> str:
    """O <title> por partida: "A 17 × 19 B · Dust II · Parser de Replay CS2"; sem placar, só o mapa."""
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    c = cabecalho_da_partida(match_id, base)
    mapa = _nome_do_mapa(base, match_id)
    if not c:
        return mapa
    a, b = c["lados"]["A"], c["lados"]["B"]
    evento = _evento_se_o_titulo_repete(match_id, c)
    return f"{a['nome']} {a['pontos']} × {b['pontos']} {b['nome']} · {mapa}{' · ' + evento if evento else ''} · Parser de Replay CS2"


def _evento_se_o_titulo_repete(match_id: str, c: dict) -> str | None:
    """O <title> é único por partida: se outra partida do corpus tem o mesmo mapa, os mesmos lados e o
    mesmo placar (Vitality 13 × 10 FURIA em Overpass, em dois eventos), o evento entra para desempatar."""
    manifesto = PROJECT_ROOT / "data" / "manifest.json"
    if not manifesto.exists():
        return None
    partidas = json.loads(manifesto.read_text(encoding="utf-8")).get("partidas", {})
    minha = partidas.get(match_id) or {}
    chave = lambda linha, lado: (_nome_do_lado(linha, lado), (linha.get("placar") or {}).get(lado))  # noqa: E731
    mesma = lambda linha: (linha.get("mapa"), chave(linha, "A"), chave(linha, "B"))  # noqa: E731
    if not any(k != match_id and mesma(v) == mesma(minha) for k, v in partidas.items()):
        return None
    return origem_da_partida(match_id)


def descricao_da_pagina(match_id: str, base: Path | None = None) -> str:
    """A meta description: "MOUZ venceu Falcons por 19 a 17 em Dust II (evento). Decidida no round 24."."""
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    c = cabecalho_da_partida(match_id, base)
    if not c:
        return f"{_nome_do_mapa(base, match_id)}: replay no radar, placar round a round e a leitura da partida."
    a, b = c["lados"]["A"], c["lados"]["B"]
    origem = origem_da_partida(match_id)
    onde = f"{c['mapa']} ({origem})" if origem else c["mapa"]
    if c["venceu"]:
        v, p = (a, b) if c["venceu"] == "A" else (b, a)
        frase = f"{v['nome']} venceu {p['nome']} por {v['pontos']} a {p['pontos']} em {onde}."
    else:
        frase = f"{a['nome']} e {b['nome']} empataram em {a['pontos']} a {b['pontos']} em {onde}."
    if c["round_decisivo"]:
        frase += f" Decidida no round {c['round_decisivo']}."
    return frase


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
        f"<b>Limites.</b> {_milhar(co['partidas'])} partidas ({_milhar(co['jogador_rounds'])} jogador-rounds): "
        f"{_milhar(co['por_origem']['profissional'])} profissionais e {_milhar(co['por_origem']['faceit'])} da FACEIT. "
        f"Os {es['grupos']} jeitos de jogar têm separação fraca: "
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


# "método" ao lado do erro do rating: a seção do README que conta como o rating foi conferido
REPO = "https://github.com/pedroppansani/parser-replay-cs2"
METODO_DO_RATING = "README.md#como-sei-que-os-números-estão-certos"


def erro_do_rating(c: dict) -> str:
    """O erro típico do rating contra o oficial, como a página escreve ("0,079"): o da validação
    "deixa uma partida fora, completa" (numeros_citaveis.json), nunca um número fixo no template."""
    return _br(c["rating"]["fora_da_amostra"]["erro_medio"], 3)


def _vice_dentro_do_erro(mvp: dict | None, citaveis: dict) -> bool:
    """O 2º maior rating está a menos de um erro típico do MVP? (`margem` do card é a margem de ruído, não a
    diferença entre os dois.)"""
    if not mvp or mvp.get("vice_rating") is None:
        return False
    return (mvp["rating"] - mvp["vice_rating"]) < citaveis["rating"]["fora_da_amostra"]["erro_medio"]


def dados_da_pagina(match_id: str, base: Path | None = None, repo: str | None = None) -> dict:
    from metrics.impacto import resumo_dos_grupos
    from scripts.numeros_citaveis import carrega
    base = base or PROJECT_ROOT / "data" / "processed" / match_id
    from metrics.round_na_prancheta import TOLERANCIA_U
    citaveis = carrega()
    payload = _le_json(base / "web_payload.json")
    return {"origem": origem_da_partida(match_id), "rodape_html": rodape_html(citaveis),
            "erro_rating": erro_do_rating(citaveis),
            # "a diferença é menor que o erro típico" (§7.2): decidido aqui, para a página não comparar números
            "vice_dentro_do_erro": _vice_dentro_do_erro(payload.get("mvp_card"), citaveis),
            "metodo_rating": f"{(repo or REPO).rstrip('/')}/blob/main/{METODO_DO_RATING}",
            "resumo_dos_grupos": resumo_dos_grupos(payload.get("player_profile") or [],
                                                   (payload.get("rating_info") or {}).get("modo_degradado")),
            "cabecalho": _cabecalho_para_a_pagina(cabecalho_da_partida(match_id, base)), "mapa": _nome_do_mapa(base, match_id),
            # "Abrir round na prancheta" (fase 9): a tolerância medida do caminho
            "round_na_prancheta": {"tolerancia_u": TOLERANCIA_U}}


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
    payload = texto_seguro(com_os_nomes_dos_lados((base / "web_payload.json").read_text(encoding="utf-8"),
                                                  cabecalho_da_partida(match_id, base)))
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
        from scripts.radar_ajuste import avisa
        avisa(map_name)   # mapa sem par em RADAR_AJUSTE (§4.1): a página usa o padrão, o build avisa
        radar = json.loads(radar_path.read_text(encoding="utf-8"))
        # A impressão da calibração vai pronta para a página: é a mesma função que
        # valida um arquivo de anotações exportado, então as duas pontas nunca
        # discordam sobre qual calibração um traço usou.
        radar["calibracao"] = impressao_da_calibracao(radar)
        # o `||` mantém o `null` do template como fallback quando o mapa não tem radar
        radar_js = js(radar) + " ||"
    html = html.replace("/*__RADAR__*/", radar_js)
    # Botão "Criar tática": só quando o mapa desta partida tem prancheta. O link
    # é relativo e funciona igual em dashboard/web/ e em docs/, que têm as duas
    # páginas lado a lado.
    from scripts.build_tactics_page import arquivo_da_pagina, mapas_disponiveis
    prancheta = arquivo_da_pagina(map_name) if map_name in mapas_disponiveis() else None
    html = html.replace("/*__PRANCHETA__*/null", js(prancheta))
    import html as _html
    html = html.replace("/*__PAGINA__*/null", js(dados_da_pagina(match_id, base, (site or {}).get("repo"))))
    titulo = titulo_da_pagina(match_id, base)
    html = html.replace("<!--__TITULO__-->", _html.escape(titulo))
    cab = cabecalho_html(match_id, base, site)
    html = (html.replace("<!--__MIGALHAS__-->", cab["migalhas"]).replace("<!--__PLACAR__-->", cab["placar"])
            .replace("<!--__DECISOR__-->", cab["decisor"]))
    if site:
        # a barra de troca de partida já sai visível no site (o JS só enche o seletor): aparecer depois da
        # carga empurrava o placar e as abas para baixo
        html = html.replace('<div class="demobar" id="demobar" hidden>', '<div class="demobar" id="demobar">')
        if site.get("jogadores"):
            j = site["jogadores"]
            html = html.replace('<a href="jogadores.html" id="link-jogadores" hidden></a>',
                                f'<a href="jogadores.html" id="link-jogadores" title="{_html.escape(j["aviso"])}">'
                                f'{_html.escape(j["texto"])}</a>')
    from scripts.meta_da_pagina import meta_tags, url_do_site
    html = html.replace("<!--__META__-->", meta_tags(
        titulo, descricao_da_pagina(match_id, base), url_do_site((site or {}).get("repo")), f"{match_id}.html"))
    html = html.replace("/*__SITE__*/", js(site) + " ||" if site else "")
    from scripts.design_head import aplica
    return aplica(html)  # tokens e fontes da direção "Sala de demo" (decisão 44)


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
