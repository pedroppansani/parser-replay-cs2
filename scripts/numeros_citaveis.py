"""Os números que o projeto CITA, calculados dos dados e gravados num lugar só.

POR QUE EXISTE: número digitado à mão envelhece. A página dizia "Nove partidas
(1.870 jogador-rounds)" com 52 partidas no corpus. Todo texto que cita o
corpus, a validação ou uma contagem lê `data/processed/numeros_citaveis.json`
-- a página da partida, a landing e o README.

Cada bloco diz de onde saiu. O que depende de `data/interim/` (que não vai
para o git) é recalculado quando o interim existe; sem ele (clone limpo, CI) o
valor gravado é MANTIDO e o bloco diz que foi mantido.

Uso:
    py -3.12 -m scripts.numeros_citaveis          # recalcula e grava
    py -3.12 -m scripts.numeros_citaveis --ver    # só imprime
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl
from metrics.times import nome_canonico  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PROCESSED = RAIZ / "data" / "processed"
INTERIM = RAIZ / "data" / "interim"
SAIDA = PROCESSED / "numeros_citaveis.json"
ARMAS_SEM_MIRA = ["inferno", "planted_c4", "hegrenade"]


def corpus() -> dict:
    """Partidas, mapas e volume, do manifesto (versionado)."""
    partidas = json.loads((RAIZ / "data" / "manifest.json").read_text(encoding="utf-8"))["partidas"]
    por_origem: dict[str, int] = {}
    jogador_rounds = jogador_partidas = 0
    times = set()
    for p in partidas.values():
        por_origem[p.get("origem") or "desconhecida"] = por_origem.get(p.get("origem") or "desconhecida", 0) + 1
        n = sum(len((p.get("times") or {}).get(lado, {}).get("jogadores") or []) for lado in ("A", "B"))
        jogador_partidas += n
        jogador_rounds += n * int(p.get("rounds") or 0)
        if p.get("origem") == "profissional":
            # "Vitality" e "Team Vitality" são o mesmo time: nome canônico (metrics/times.py)
            times.update(nome_canonico(t["nome"]) for t in (p.get("times") or {}).values() if t.get("nome"))
    return {
        "fonte": "data/manifest.json",
        "partidas": len(partidas),
        "por_origem": dict(sorted(por_origem.items())),
        "mapas": sorted({p["mapa"] for p in partidas.values() if p.get("mapa")}),
        "times_profissionais": len(times),
        "jogador_partidas": jogador_partidas,
        "jogador_rounds": jogador_rounds,
    }


def convencao_de_angulos(anterior: dict | None) -> dict:
    """Erro mediano da mira do matador até a vítima no tick da kill, na
    convenção adotada (pitch positivo = olhar para baixo) e na invertida."""
    from metrics.geometry import add_aim_error_columns

    certos, invertidos, n_partidas = [], [], 0
    for d in sorted(INTERIM.glob("match_*")) if INTERIM.exists() else []:
        if not (d / "kills.parquet").exists():
            continue
        k = pl.read_parquet(d / "kills.parquet")
        if "attacker_pitch" not in k.columns:
            continue
        k = k.filter(pl.col("attacker_X").is_not_null() & pl.col("attacker_pitch").is_not_null()
                     & pl.col("victim_X").is_not_null() & (~pl.col("weapon").is_in(ARMAS_SEM_MIRA)))
        if k.height == 0:
            continue
        n_partidas += 1
        cols = dict(shooter_x="attacker_X", shooter_y="attacker_Y", shooter_z="attacker_Z",
                    shooter_yaw="attacker_yaw", target_x="victim_X", target_y="victim_Y", target_z="victim_Z")
        certos.append(add_aim_error_columns(k, shooter_pitch="attacker_pitch", **cols)["aim_error_deg"].to_numpy())
        inv = k.with_columns((-pl.col("attacker_pitch")).alias("_p"))
        invertidos.append(add_aim_error_columns(inv, shooter_pitch="_p", **cols)["aim_error_deg"].to_numpy())
    if not certos:
        return {**(anterior or {}), "mantido": "sem data/interim/ nesta máquina: valor da última medição"}
    c, i = np.concatenate(certos), np.concatenate(invertidos)
    # matador e vítima no mesmo ponto não têm direção: saem da conta
    ok = np.isfinite(c) & np.isfinite(i)
    c, i = c[ok], i[ok]
    return {
        "fonte": "data/interim/*/kills.parquet (metrics.geometry.add_aim_error_columns)",
        "erro_mediano_graus": round(float(np.median(c)), 2),
        "erro_mediano_invertida_graus": round(float(np.median(i)), 2),
        "kills": int(c.size), "partidas": n_partidas,
    }


def estilos() -> dict:
    nomes = json.loads((RAIZ / "clustering" / "cluster_names.json").read_text(encoding="utf-8"))
    grupos = [k for k in nomes if str(k).lstrip("-").isdigit()] if isinstance(nomes, dict) else nomes
    return {"fonte": "clustering/cluster_names.json", "grupos": len(grupos)}


def rating(anterior: dict | None) -> dict:
    """O rating contra o oficial da HLTV, com o método dito por extenso.

    `na_pagina` é o número que o site mostra, DENTRO da amostra (os pesos, a
    referência de escala, o modelo de round e a economia foram ajustados nas
    mesmas partidas). `fora_da_amostra` é o "deixa uma partida fora" gravado
    com os pesos -- hoje ele reajusta SÓ os pesos.
    """
    from scripts.impacto_rating import contra_a_hltv, insights

    h = contra_a_hltv(insights(None))
    pesos = json.loads((RAIZ / "metrics" / "rating_weights.json").read_text(encoding="utf-8"))["validacao"]
    return {
        "fonte": "data/processed/*/insights.json x data/reference/hltv_ratings.json; metrics/rating_weights.json",
        "jogador_partidas": h["n"],
        "na_pagina": {"erro_medio": round(h["erro_medio"], 3), "correlacao": round(h["correlacao"], 3),
                      "metodo": "dentro da amostra: tudo foi ajustado nestas mesmas partidas"},
        "fora_da_amostra": {"erro_medio": pesos["fora_da_amostra"]["erro_medio_absoluto"],
                            "correlacao": pesos["fora_da_amostra"]["correlacao"],
                            "partidas": pesos["partidas"],
                            "metodo": ("deixa uma partida fora, reajustando só os PESOS; o modelo de round, a "
                                       "referência de escala e a economia viram todas as partidas")},
    }


def escada(anterior: dict | None) -> dict:
    """Contagens exatas contra a HLTV (precisa do interim: kills por partida)."""
    try:
        from scripts.escada_validacao import TOLERANCIA_ADR, contagens, detalhado
        cont = contagens()
        det = detalhado()
    except Exception as erro:  # sem data/interim/ (clone limpo)
        return {**(anterior or {}), "mantido": f"sem data/interim/ nesta máquina ({type(erro).__name__}): valor da última medição"}
    n = cont.height
    kast = cont.drop_nulls("kast_oficial")
    out = {
        "fonte": "scripts/escada_validacao.py contra data/reference/hltv_placar.json, hltv_componentes.json e hltv_detalhado.json",
        "jogador_partidas": n,
        "partidas": cont["match_id"].n_unique(),
        "kills_exatos": int((cont["kills"] == cont["kills_oficial"]).sum()),
        "mortes_exatas": int((cont["mortes"] == cont["mortes_oficial"]).sum()),
        "adr_exatos": int(((cont["adr"] - cont["adr_oficial"]).abs() <= TOLERANCIA_ADR).sum()),
        "kast_exatos": int((kast["kast"] == kast["kast_oficial"]).sum()),
        "kast_com_oficial": kast.height,
    }
    if det.height:
        nomes = {"op_kills": "aberturas_feitas", "op_mortes": "aberturas_sofridas", "mk_rounds": "rounds_de_multikill",
                 "hs": "headshots", "clutches": "clutches"}
        out["series_inteiras"] = det["serie"].n_unique()
        for campo, g in det.group_by("campo", maintain_order=True):
            out[nomes[campo[0]]] = {"exatos": int((g["nosso"] == g["oficial"]).sum()), "de": g.height}
    return out


def arremessos() -> dict:
    """Metas dos arremessos no gabarito de demos, dentro e FORA da amostra.

    Dentro: as constantes calculadas com as 13 partidas, avaliadas nelas.
    Fora: para cada partida, as constantes calculadas SEM ela (tolerância,
    guarda do voo, faixa de postura, deslocamento do primeiro segmento) e a
    avaliação nela. As constantes medidas uma vez na primeira partida com demo
    (velocidade de cada botão, alturas de saída) ficam fixas nos dois casos.
    """
    import numpy as np

    import metrics.grenade_throws as gt
    from scripts.constantes_do_gabarito import calcula as constantes, carrega_gabarito
    from scripts.valida_rota_a import metas_da_partida

    todos, partidas = carrega_gabarito()
    por: dict[str, list[dict]] = {}
    for a in todos:
        por.setdefault(a["id"].split(":")[0], []).append(a)

    def resumo(metas: dict[str, dict]) -> dict:
        def faixa(campo):
            v = [m[campo][0] / m[campo][1] for m in metas.values() if m[campo][1]]
            return {"pior_partida": round(min(v), 4), "melhor_partida": round(max(v), 4),
                    "acertos": sum(m[campo][0] for m in metas.values()), "de": sum(m[campo][1] for m in metas.values())}
        return {"botao": faixa("botao"), "no_ar": faixa("no_ar"), "postura": faixa("postura"),
                "cobertura_do_botao": round(sum(m["botao"][1] for m in metas.values()) / sum(m["n"] for m in metas.values()), 4)}

    dentro = {p: metas_da_partida(arr) for p, arr in por.items()}
    nomes = ("TOLERANCIA_BOTAO", "LIMIAR_GUARDA_VOO", "FAIXA_POSTURA_NEUTRA", "DESLOCAMENTO_PRIMEIRO_SEGMENTO")
    guardado = {n: getattr(gt, n) for n in nomes}
    fora = {}
    try:
        for p, arr in por.items():
            k = constantes([a for a in todos if a["id"].split(":")[0] != p])
            gt.TOLERANCIA_BOTAO = float(k["tolerancia_botao"])
            gt.LIMIAR_GUARDA_VOO = float(k["limiar_guarda_voo"])
            gt.FAIXA_POSTURA_NEUTRA = tuple(float(x) for x in k["faixa_postura_neutra"])
            gt.DESLOCAMENTO_PRIMEIRO_SEGMENTO = np.array([0.0, 0.0, float(k["deslocamento_primeiro_segmento_z"])])
            fora[p] = metas_da_partida(arr)
    finally:
        for n, v in guardado.items():
            setattr(gt, n, v)
    return {
        "fonte": "tests/fixtures/gabarito_arremessos_*.json.gz (scripts/valida_rota_a.metas_da_partida)",
        "partidas_do_gabarito": len(por), "arremessos": len(todos),
        "dentro_da_amostra": resumo(dentro),
        "fora_da_amostra": {**resumo(fora), "metodo": ("deixa uma partida fora: tolerância, guarda do voo, faixa de "
                                                        "postura e deslocamento recalculados sem a partida avaliada")},
    }


def testes(anterior: dict | None) -> dict:
    """Quantos testes a suíte coleta (pytest --collect-only)."""
    import re
    import subprocess

    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
                       capture_output=True, text=True, cwd=RAIZ)
    m = re.search(r"([0-9]+) tests? collected", r.stdout + r.stderr)
    if not m:
        return {**(anterior or {}), "mantido": "pytest --collect-only não devolveu a contagem"}
    return {"fonte": "pytest --collect-only", "coletados": int(m.group(1))}


def calcula() -> dict:
    anterior = json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else {}
    return {
        "_leia_isto": ("Gerado por py -3.12 -m scripts.numeros_citaveis. Não editar à mão: a página, a "
                       "landing e o README leem daqui."),
        "corpus": corpus(),
        "convencao_de_angulos": convencao_de_angulos(anterior.get("convencao_de_angulos")),
        "estilos": estilos(),
        "rating": rating(anterior.get("rating")),
        "escada": escada(anterior.get("escada")),
        "arremessos": arremessos(),
        "testes": testes(anterior.get("testes")),
    }


# ---------------------------------------------------------------------------
# Os blocos de texto que citam os números (README e landing)
# ---------------------------------------------------------------------------

def _br(x: float, casas: int) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def _mil(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _pct(x: float, casas: int = 1) -> str:
    return _br(100 * x, 0 if x == 1 else casas) + "%"


def tres_numeros(d: dict) -> list[dict]:
    """Os três números validados da vitrine: valor, rótulo e a frase de contexto."""
    e, r, a = d["escada"], d["rating"], d["arremessos"]
    return [
        {"valor": f"{_mil(e['kills_exatos'])} de {_mil(e['jogador_partidas'])}",
         "rotulo": "placares idênticos aos da HLTV",
         "contexto": (f"Kills e mortes de {_mil(e['jogador_partidas'])} jogadores em {e['partidas']} mapas "
                      "profissionais batem com o placar oficial, um a um.")},
        {"valor": _br(r["fora_da_amostra"]["erro_medio"], 3),
         "rotulo": "erro médio do rating contra o oficial",
         "contexto": (f"Em {_mil(r['jogador_partidas'])} jogador-partidas (correlação "
                      f"{_br(r['fora_da_amostra']['correlacao'], 3)}), deixando uma partida fora a cada vez. "
                      "É uma implementação própria da metodologia publicada, não o número da HLTV.")},
        {"valor": _pct(a["fora_da_amostra"]["botao"]["pior_partida"]),
         "rotulo": "botão do arremesso certo, fora da amostra",
         "contexto": (f"A força de {_mil(a['arremessos'])} granadas inferida só da posição, conferida contra o "
                      f"que a demo grava em {a['partidas_do_gabarito']} partidas.")},
    ]


def blocos_de_texto(d: dict) -> dict[str, str]:
    """Os trechos do README que citam números, prontos em Markdown."""
    co, e, r, a, an = d["corpus"], d["escada"], d["rating"], d["arremessos"], d["convencao_de_angulos"]
    fo, de = a["fora_da_amostra"], a["dentro_da_amostra"]

    def faixa(x):
        return (_pct(x["pior_partida"]) if x["pior_partida"] == x["melhor_partida"]
                else f"{_pct(x['pior_partida'])} a {_pct(x['melhor_partida'])}")

    corpus = (f"{co['partidas']} partidas ({co['por_origem'].get('profissional', 0)} profissionais, de "
              f"{co['times_profissionais']} times, e {co['por_origem'].get('faceit', 0)} de FACEIT) em "
              f"{len(co['mapas'])} mapas")
    resumo = "\n".join(f"- **{n['valor']}** {n['rotulo']}. {n['contexto']}" for n in tres_numeros(d))
    validacao = "\n".join([
        "| O que é conferido | Resultado |",
        "|---|---|",
        f"| Kills e mortes por jogador | {_mil(e['kills_exatos'])} de {_mil(e['jogador_partidas'])} idênticos ({e['partidas']} mapas) |",
        f"| ADR | {e['adr_exatos']} de {e['jogador_partidas']} idênticos no arredondamento |",
        f"| KAST | {e['kast_exatos']} de {e['kast_com_oficial']} idênticos |",
        f"| Aberturas, rounds de multi-kill e headshots | {e['aberturas_feitas']['exatos']} de {e['aberturas_feitas']['de']} idênticos ({e['series_inteiras']} séries inteiras) |",
        f"| Clutches vencidos | {e['clutches']['exatos']} de {e['clutches']['de']} idênticos |",
        f"| Rating, na página (dentro da amostra) | erro médio {_br(r['na_pagina']['erro_medio'], 3)}, correlação {_br(r['na_pagina']['correlacao'], 3)} ({r['jogador_partidas']} jogador-partidas) |",
        f"| Rating, fora da amostra | erro médio {_br(r['fora_da_amostra']['erro_medio'], 3)}, correlação {_br(r['fora_da_amostra']['correlacao'], 3)} |",
        f"| Convenção de ângulos | mira a {_br(an['erro_mediano_graus'], 2)}° da vítima no tick da kill, contra {_br(an['erro_mediano_invertida_graus'], 2)}° na convenção invertida ({_mil(an['kills'])} kills) |",
    ])
    arremessos = "\n".join([
        f"| Arremessos ({a['partidas_do_gabarito']} demos, {_mil(a['arremessos'])} granadas) | Dentro da amostra | Fora da amostra |",
        "|---|---|---|",
        f"| Botão (curto, médio, longo), por partida | {faixa(de['botao'])} | {faixa(fo['botao'])} |",
        f"| No ar ou no chão, por partida | {faixa(de['no_ar'])} | {faixa(fo['no_ar'])} |",
        f"| Em pé ou agachado, por partida | {faixa(de['postura'])} | {faixa(fo['postura'])} |",
        f"| Arremessos com botão afirmado | {_pct(de['cobertura_do_botao'])} | {_pct(fo['cobertura_do_botao'])} |",
    ])
    testes = f"{_mil(d['testes']['coletados'])} testes"
    return {"corpus": corpus, "resumo": resumo, "validacao": validacao, "arremessos": arremessos, "testes": testes}


def _marcas(nome: str) -> tuple[str, str]:
    return f"<!-- numeros:inicio {nome} -->", f"<!-- numeros:fim {nome} -->"


def preenche(texto: str, d: dict) -> str:
    """Troca o conteúdo de cada bloco marcado do texto pelo gerado do JSON."""
    for nome, novo in blocos_de_texto(d).items():
        ini, fim = _marcas(nome)
        pos = 0
        while True:
            i = texto.find(ini, pos)
            if i < 0:
                break
            j = texto.index(fim, i)
            em_linha = "\n" not in novo
            meio = novo if em_linha else "\n" + novo + "\n"
            texto = texto[:i + len(ini)] + meio + texto[j:]
            pos = i + len(ini) + len(meio) + len(fim)
    return texto


def blocos_no_texto(texto: str) -> dict[str, list[str]]:
    """O que está escrito hoje em cada bloco marcado (para o teste)."""
    out: dict[str, list[str]] = {}
    for nome in ("corpus", "resumo", "validacao", "arremessos", "testes"):
        ini, fim = _marcas(nome)
        pos = 0
        while True:
            i = texto.find(ini, pos)
            if i < 0:
                break
            j = texto.index(fim, i)
            out.setdefault(nome, []).append(texto[i + len(ini):j].strip("\n"))
            pos = j + len(fim)
    return out


def carrega() -> dict:
    return json.loads(SAIDA.read_text(encoding="utf-8")) if SAIDA.exists() else calcula()


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    doc = calcula()
    if "--ver" not in sys.argv:
        SAIDA.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # os blocos marcados do README são preenchidos daqui: nunca à mão
        readme = RAIZ / "README.md"
        if readme.exists():
            readme.write_text(preenche(readme.read_text(encoding="utf-8"), doc), encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
