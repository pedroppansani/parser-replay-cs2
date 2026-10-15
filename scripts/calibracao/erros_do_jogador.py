"""Seção 7 do MATERIAL_DE_CALIBRACAO.md: "Erros na aba Perfil" (fase 12, item 12.4).

    py -3.12 -m scripts.calibracao.erros_do_jogador            # reescreve a seção 7 no material
    py -3.12 -m scripts.calibracao.erros_do_jogador --tabela   # só a tabela de ocorrências por tipo

Lê as ocorrências gravadas (`data/processed/<partida>/erros_do_jogador.parquet`, de
metrics/erros.build) e, para as varreduras das constantes, recalcula cada partida
com outro valor (metrics/erros.ocorrencias aceita as constantes como argumento).

Para cada constante nova: o valor proposto com a origem, o histograma no corpus e
quantas ocorrências cada tipo teria no valor mais baixo e no mais alto de uma faixa
razoável. Para cada tipo: 10 exemplos sorteados com semente fixa, no máximo 2 por
partida, com o link do replay naquele instante e as duas perguntas do Pedro.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

import polars as pl

from metrics import erros as E

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
MATERIAL = RAIZ / "MATERIAL_DE_CALIBRACAO.md"
TITULO_DA_SECAO = "## 7. Erros na aba Perfil"

# Sorteio dos exemplos: semente fixa (decisão 28) e no máximo 2 por partida (pedido 12.4).
SEMENTE_DOS_EXEMPLOS = 20261013
EXEMPLOS_POR_TIPO = 10
MAX_EXEMPLOS_POR_PARTIDA = 2

# Faixas razoáveis de cada constante (o mais baixo e o mais alto que ainda fazem sentido de jogo).
FAIXAS = {
    "dist_troca": ("DIST_TROCA", 400.0, 800.0, "unidades"),
    "s_duelo": ("S_DUELO", 1.0, 4.0, "s"),
    "seg_aliado": ("SEG_CEGUEIRA_ALIADO", 5.0, 20.0, "s"),
    "seg_uma": ("SEG_CEGUEIRA_ALIADO_UMA", 2.0, 4.0, "s"),
    "dano_aliado": ("DANO_UTILIDADE_ALIADO", 25.0, 100.0, "de dano"),
}
VALOR_ATUAL = {"dist_troca": E.DIST_TROCA, "s_duelo": E.S_DUELO, "seg_aliado": E.SEG_CEGUEIRA_ALIADO,
               "seg_uma": E.SEG_CEGUEIRA_ALIADO_UMA, "dano_aliado": E.DANO_UTILIDADE_ALIADO}


def partidas() -> list[str]:
    return sorted(d.name for d in PROCESSED.glob("match_*") if (d / E.ARQUIVO).exists())


def corpus() -> pl.DataFrame:
    return pl.concat([pl.read_parquet(PROCESSED / m / E.ARQUIVO) for m in partidas()], how="vertical")


def tabela_por_tipo(oc: pl.DataFrame) -> list[str]:
    """Antes dos filtros, depois dos filtros e por nível, um tipo por linha."""
    linhas = ["| tipo | antes dos filtros | depois dos filtros | explícito | depende da tática | saiu pelos filtros (motivo: n) |",
              "|---|---|---|---|---|---|"]
    for t in E.TIPOS:
        o = oc.filter(pl.col("tipo") == t)
        dep = o.filter(pl.col("filtro").is_null())
        fora = (o.filter(pl.col("filtro").is_not_null()).group_by("filtro", maintain_order=True).len()
                .sort(["len", "filtro"], descending=[True, False]))
        motivos = "; ".join(f"{r[0]}: {r[1]}" for r in fora.iter_rows()) or "—"
        linhas.append(f"| {E.TITULOS[t]} | {o.height} | {dep.height} | "
                      f"{dep.filter(pl.col('nivel') == E.EXPLICITO).height} | "
                      f"{dep.filter(pl.col('nivel') == E.DEPENDE).height} | {motivos} |")
    linhas.append("| Utilidade no bolso | não criado | — | — | — | o inventário na hora da morte não existe no dado (decisão 46) |")
    return linhas


def histograma(valores: list[float], cortes: list[float], unidade: str, marca: float | None = None) -> list[str]:
    """Histograma em texto, com a marca do valor proposto."""
    if not valores:
        return ["```", "(sem dados)", "```"]
    cont = [0] * (len(cortes) - 1)
    acima = 0
    for v in valores:
        if v >= cortes[-1]:
            acima += 1
            continue
        for i in range(len(cortes) - 1):
            if cortes[i] <= v < cortes[i + 1]:
                cont[i] += 1
                break
    maior = max(cont + [acima]) or 1
    out = ["```"]
    for i, c in enumerate(cont):
        rot = f"{cortes[i]:>7g}-{cortes[i + 1]:<7g}"
        seta = "   <- proposto" if marca is not None and cortes[i] <= marca < cortes[i + 1] else ""
        out.append(f"  {rot} {c:6d} {'#' * round(40 * c / maior)}{seta}")
    out.append(f"  {'>= ' + format(cortes[-1], 'g'):<15} {acima:6d} {'#' * round(40 * acima / maior)}")
    out.append(f"  ({len(valores)} valores, em {unidade})")
    out.append("```")
    return out


def _medidas(cache: dict) -> dict[str, list[float]]:
    """As distribuições do corpus que sustentam cada constante."""
    dist_vizinho, s_desde_dano, cegueira_soma, cegueira_uma, dano_soma = [], [], [], [], []
    for m, p in cache.items():
        ix = E._Indice(p)
        for k, rn, t, v, a in E._mortes_de_aliado(ix):
            pos_v = {"X": k["victim_X"], "Y": k["victim_Y"], "Z": k["victim_Z"]}
            for r in ix.aliados_vivos(rn, v, t):
                d = E.distancia(r, pos_v, p.corte_de_andar)
                if d != float("inf"):
                    dist_vizinho.append(d)
                if d <= E.DIST_TROCA:
                    ultimo = None
                    for x in ix.dano:
                        if int(x["round_num"]) == rn and x["tick"] <= t and (
                                (x["attacker_steamid"] is not None and int(x["attacker_steamid"]) == int(r["steamid"]))
                                or (x["victim_steamid"] is not None and int(x["victim_steamid"]) == int(r["steamid"]))) \
                                and ix.time(x["attacker_steamid"]) != ix.time(x["victim_steamid"]):
                            ultimo = x["tick"]
                    if ultimo is not None:
                        s_desde_dano.append((t - ultimo) / p.tickrate)
        fl = E.flash_no_time(p, _ix=ix)
        soma: dict = {}
        for o in fl:
            if o["filtro"] in (None, E.FILTRO_ABAIXO_DO_LIMIAR):
                cegueira_uma.append(o["valor"])
                soma[o["steamid"]] = soma.get(o["steamid"], 0.0) + o["valor"]
        for sid in p.team_of:
            cegueira_soma.append(soma.get(sid, 0.0))
        du = E.dano_de_utilidade_no_time(p, _ix=ix)
        sd: dict = {}
        for o in du:
            if o["filtro"] in (None, E.FILTRO_ABAIXO_DO_LIMIAR):
                sd[o["steamid"]] = sd.get(o["steamid"], 0.0) + o["valor"]
        for sid in p.team_of:
            dano_soma.append(sd.get(sid, 0.0))
    return {"dist_troca": dist_vizinho, "s_duelo": s_desde_dano, "seg_aliado": cegueira_soma,
            "seg_uma": cegueira_uma, "dano_aliado": dano_soma}


def _percentil(v: list[float], q: float) -> float:
    s = sorted(v)
    if not s:
        return float("nan")
    i = min(len(s) - 1, max(0, round(q * (len(s) - 1))))
    return s[i]


def _contagens(cache: dict, **const) -> dict[str, int]:
    tot = {t: 0 for t in E.TIPOS}
    for p in cache.values():
        o = E.ocorrencias(p, **const)
        for t, n in o.filter(pl.col("filtro").is_null()).group_by("tipo", maintain_order=True).len().iter_rows():
            tot[t] += n
    return tot


ORIGEM = {
    "dist_troca": ("o raio de apoio do projeto (RAIO_COMPANHEIRO = 600 do perfil e das funções: \"o alcance em que "
                   "uma troca ainda acontece\"). O histograma é a distância de cada aliado vivo a quem morreu, na hora "
                   "da morte, no mesmo andar."),
    "s_duelo": ("tempo de um duelo de rifle (reação de ~0,25 s mais 0,3 a 1 s para matar), com folga. O histograma é, "
                "para cada aliado a até DIST_TROCA de quem morreu, o tempo desde o último dano que ele deu ou levou de "
                "um inimigo antes da morte."),
    "seg_aliado": ("o percentil 90 da soma de cegueira imposta ao próprio time por jogador-partida no corpus (fora "
                   "eco e pós-plant perdido)."),
    "seg_uma": ("o percentil 90 da cegueira nos aliados por flash no corpus (uma flash cheia cega de 2 a 5 s; perto "
                "do topo é a flash que estourou na cara do aliado). O histograma é a cegueira nos aliados por flash."),
    "dano_aliado": ("o percentil 95 do dano de HE e molotov no próprio time por jogador-partida no corpus (fora eco e "
                    "pós-plant perdido)."),
}
CORTES = {
    "dist_troca": [0, 100, 200, 300, 400, 500, 600, 700, 800, 1000, 1200, 1500, 2000, 3000],
    "s_duelo": [0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 7, 10, 15],
    "seg_aliado": [0, 0.01, 2, 4, 6, 8, 10, 12, 15, 20, 30],
    "seg_uma": [0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 5],
    "dano_aliado": [0, 0.01, 10, 25, 40, 50, 60, 80, 100, 150],
}


def secao_constantes(cache: dict) -> list[str]:
    med = _medidas(cache)
    base = _contagens(cache)
    out = ["### 7.1 As constantes novas", "",
           "Valor proposto, origem, histograma no corpus e quantas ocorrências (depois dos filtros) cada tipo teria "
           "no valor mais baixo e no mais alto da faixa. As outras constantes ficam no valor proposto em cada varredura.",
           ""]
    for chave, (nome, baixo, alto, unidade) in FAIXAS.items():
        v = med[chave]
        out += [f"#### `{nome}` = {_g(VALOR_ATUAL[chave])} {unidade}", "",
                f"Origem: {ORIGEM[chave]}", "",
                f"Mediana {_fmt(_percentil(v, 0.5), 1)}, p75 {_fmt(_percentil(v, 0.75), 1)}, "
                f"p90 {_fmt(_percentil(v, 0.90), 1)}, p95 {_fmt(_percentil(v, 0.95), 1)}.", ""]
        out += histograma(v, CORTES[chave], unidade, VALOR_ATUAL[chave])
        c_baixo = _contagens(cache, **{chave: baixo})
        c_alto = _contagens(cache, **{chave: alto})
        out += ["", f"| tipo | {nome} = {_g(baixo)} | proposto ({_g(VALOR_ATUAL[chave])}) | {nome} = {_g(alto)} |",
                "|---|---|---|---|"]
        for t in E.TIPOS:
            out.append(f"| {E.TITULOS[t]} | {c_baixo[t]} | {base[t]} | {c_alto[t]} |")
        out.append("")
    out += ["#### `MIN_GRANADAS_NO_BOLSO`: não criada", "",
            "O tipo \"Utilidade no bolso\" exige o inventário na hora da morte. O parser lê o inventário só no fim do "
            "freeze time (`PROPS_DA_COMPRA` em `parsing/parser.py`, a tabela `compra`); na hora da morte não há o que "
            "ler. Pela regra do pedido, o tipo não foi criado e nada foi estimado (decisão 46).", ""]
    return out


# --- 7.1b Quantos pontos a melhorar cada jogador teria (fase 12b) ------------------------------------------

PERCENTIS_COMPARADOS = (50, 75, 90)                # o em uso (E.PERCENTIL_PONTO_A_MELHORAR) é um deles
DIST_TROCA_COMPARADAS = (400.0, E.DIST_TROCA, 800.0)             # um menor, o atual e um maior
ROTULO_LADO = E.ROTULO_DO_LADO


def _linhas_de_contagem(oc: pl.DataFrame) -> list[dict]:
    """Um registro por (partida, jogador, lado) do corpus: função do lado e contagem de cada tipo (só o que
    passou nos filtros). Mesmo formato que o ajuste da régua (scripts/fit_erros_reference)."""
    conta: dict = {}
    for m, sid, lado, tipo, n in (oc.filter(pl.col("filtro").is_null())
                                  .group_by(["match_id", "steamid", "side", "tipo"], maintain_order=True)
                                  .len().iter_rows()):
        conta[(m, int(sid), lado, tipo)] = n
    linhas = []
    for m in partidas():
        resumo = pl.read_parquet(PROCESSED / m / "structural_roles_summary.parquet")
        for r in resumo.sort(["steamid", "side"]).iter_rows(named=True):
            sid, lado = int(r["steamid"]), r["side"]
            linhas.append({"partida": m, "steamid": sid, "lado": lado, "funcao": r["funcao"], "valores": {},
                           "contagens": {t: conta.get((m, sid, lado, t), 0) for t in E.TIPOS}})
    return linhas


def _pontos_por_jogador(linhas: list[dict], ref: dict, q: float) -> tuple[dict, dict]:
    """({(partida, jogador): quantos pontos a melhorar}, {tipo: quantos pares (tipo, lado)}), com a regra da
    página: acima do percentil `q` da célula (ou do lado, se a célula é pequena) e pelo menos 2 ocorrências."""
    por_jogador: dict = {}
    por_tipo = {t: 0 for t in E.TIPOS}
    for x in linhas:
        por_jogador.setdefault((x["partida"], x["steamid"]), 0)
        for t in E.TIPOS:
            celula, _ = E.escolhe_celula(ref, "erros", t, x["lado"], x["funcao"])
            if E.acima_do_normal(x["contagens"][t], celula, percentil=q):
                por_jogador[(x["partida"], x["steamid"])] += 1
                por_tipo[t] += 1
    return por_jogador, por_tipo


def _resumo_de_pontos(por_jogador: dict) -> tuple[int, int, float, list[int]]:
    """(jogador-partidas, com pelo menos 1, média por jogador-partida, quantos com 0, 1, 2, 3 ou mais)."""
    n = len(por_jogador)
    vs = list(por_jogador.values())
    faixas = [sum(v == k for v in vs) for k in (0, 1, 2)] + [sum(v >= 3 for v in vs)]
    return n, sum(v >= 1 for v in vs), (sum(vs) / n if n else 0.0), faixas


def secao_quantos_pontos(oc: pl.DataFrame, cache: dict | None) -> list[str]:
    from scripts.fit_erros_reference import ajusta

    linhas = _linhas_de_contagem(oc)
    ref = ajusta(linhas)
    out = ["### 7.1b Quantos pontos a melhorar cada jogador teria", "",
           "Uma ocorrência só vira \"ponto a melhorar\" quando a contagem do jogador num lado fica ACIMA do "
           f"percentil {E.PERCENTIL_PONTO_A_MELHORAR} da referência (os jogador-lados do corpus com a mesma função "
           f"no mesmo lado; com menos de {E.MIN_REF_LADO_FUNCAO} deles, todos os jogador-lados daquele lado) e tem pelo "
           f"menos {E.MIN_OCORRENCIAS_PARA_PONTO} ocorrências. Um jogador-lado é um jogador numa partida, num dos "
           f"lados ({len(linhas)} no corpus). A tela mostra no máximo {E.MAX_PONTOS_A_MELHORAR} por jogador; as "
           "contagens abaixo são as brutas, sem esse corte.", "",
           "#### Distribuição da contagem por jogador-lado, por tipo e lado", "",
           "| tipo | lado | jogador-lados | média | mediana | p75 | p90 | máximo | com 0 |", "|---|---|---|---|---|---|---|---|---|"]
    for t in E.TIPOS:
        for lado in E.LADOS:
            v = sorted(x["contagens"][t] for x in linhas if x["lado"] == lado)
            out.append(f"| {E.TITULOS[t]} | {ROTULO_LADO[lado]} | {len(v)} | {_fmt(sum(v) / len(v), 2)} | "
                       f"{_fmt(_percentil(v, 0.5), 1)} | {_fmt(_percentil(v, 0.75), 1)} | {_fmt(_percentil(v, 0.9), 1)} | "
                       f"{max(v)} | {_fmt(100 * sum(1 for a in v if a == 0) / len(v), 0)}% |")
    out += ["", "#### Pontos a melhorar por jogador-partida, por percentil", "",
            "| percentil | jogador-partidas | com pelo menos 1 | % | média | com 0 | com 1 | com 2 | com 3 ou mais |",
            "|---|---|---|---|---|---|---|---|---|"]
    por_tipo_de = {}
    for q in PERCENTIS_COMPARADOS:
        pj, por_tipo_de[q] = _pontos_por_jogador(linhas, ref, q)
        n, com, media, f = _resumo_de_pontos(pj)
        marca = " (em uso)" if q == E.PERCENTIL_PONTO_A_MELHORAR else ""
        out.append(f"| {q}{marca} | {n} | {com} | {_fmt(100 * com / n, 0)}% | {_fmt(media, 2)} | {f[0]} | {f[1]} | "
                   f"{f[2]} | {f[3]} |")
    out += ["", "Pares (tipo, lado) que viram ponto a melhorar, por tipo:", "",
            "| tipo | " + " | ".join(f"p{q}" for q in PERCENTIS_COMPARADOS) + " |",
            "|---|" + "---|" * len(PERCENTIS_COMPARADOS)]
    for t in E.TIPOS:
        out.append(f"| {E.TITULOS[t]} | " + " | ".join(str(por_tipo_de[q][t]) for q in PERCENTIS_COMPARADOS) + " |")
    out.append("")
    if cache:
        out += ["#### O efeito de `DIST_TROCA` em \"não trocou\" e \"possível bait\"", "",
                "Cada linha recalcula as ocorrências do corpus com outro `DIST_TROCA` (o atual está marcado) e "
                f"refaz a referência com elas. Ponto a melhorar com o percentil {E.PERCENTIL_PONTO_A_MELHORAR}. "
                "O valor da constante NÃO muda agora: depende da sua calibração.", "",
                "| `DIST_TROCA` | tipo | ocorrências no corpus | média por jogador-lado | jogador-partidas com pelo "
                "menos 1 ponto a melhorar | % |", "|---|---|---|---|---|---|"]
        for d in DIST_TROCA_COMPARADAS:
            oc_d = pl.concat([E.ocorrencias(p, dist_troca=d) for p in cache.values()], how="vertical")
            lin = _linhas_de_contagem(oc_d)
            ref_d = ajusta(lin)
            marca = " (atual)" if d == E.DIST_TROCA else ""
            for t in (E.NAO_TROCOU, E.POSSIVEL_BAIT):
                total = sum(x["contagens"][t] for x in lin)
                pj = {}
                for x in lin:
                    pj.setdefault((x["partida"], x["steamid"]), 0)
                    celula, _ = E.escolhe_celula(ref_d, "erros", t, x["lado"], x["funcao"])
                    if E.acima_do_normal(x["contagens"][t], celula):
                        pj[(x["partida"], x["steamid"])] += 1
                com = sum(v >= 1 for v in pj.values())
                out.append(f"| {_g(d)}{marca} | {E.TITULOS[t]} | {total} | {_fmt(total / len(lin), 2)} | {com} | "
                           f"{_fmt(100 * com / len(pj), 0)}% |")
        out.append("")
    return out


def _g(x: float) -> str:
    """Número curto com vírgula decimal (4,8; 600)."""
    return format(x, "g").replace(".", ",")


def _relogio(seg: float | None) -> str:
    if seg is None:
        return "—"
    s = max(0, int(round(seg)))
    return f"{s // 60}:{s % 60:02d}"


def link_do_replay(match_id: str, round_num: int, segundos: float | None) -> str:
    """O link direto para o replay naquele instante (a página abre 3 s antes, como ao clicar num evento)."""
    t = "" if segundos is None else f"&t={segundos:g}"
    return f"docs/{match_id}.html#replay?round={round_num}{t}"


def exemplos(oc: pl.DataFrame, tipo: str) -> list[dict]:
    """Até 10 ocorrências do tipo, sorteadas com semente fixa, no máximo 2 por partida."""
    o = oc.filter((pl.col("tipo") == tipo) & pl.col("filtro").is_null()).to_dicts()
    rng = random.Random(f"{SEMENTE_DOS_EXEMPLOS}-{tipo}")
    rng.shuffle(o)
    por_partida: dict[str, int] = {}
    escolhidos = []
    for x in o:
        if por_partida.get(x["match_id"], 0) >= MAX_EXEMPLOS_POR_PARTIDA:
            continue
        por_partida[x["match_id"]] = por_partida.get(x["match_id"], 0) + 1
        escolhidos.append(x)
        if len(escolhidos) == EXEMPLOS_POR_TIPO:
            break
    return sorted(escolhidos, key=lambda x: (x["match_id"], x["round_num"], x["tick"], x["steamid"]))


def _fmt(v, casas: int = 0) -> str:
    if v is None:
        return "—"
    return f"{v:.{casas}f}".replace(".", ",")


def secao_exemplos(oc: pl.DataFrame) -> list[str]:
    out = ["### 7.2 Dez exemplos por tipo", "",
           f"Sorteados com semente fixa ({SEMENTE_DOS_EXEMPLOS}), no máximo {MAX_EXEMPLOS_POR_PARTIDA} por partida, "
           "só entre as ocorrências que passaram nos filtros. O relógio é o tempo decorrido desde o fim do freeze "
           "time. O link abre o replay naquele round, 3 s antes do instante (gere o site com "
           "`py -3.12 -m scripts.build_site`). Distâncias em unidades do jogo, no mesmo andar; \"—\" quando não se "
           "aplica ou estão em andares diferentes. ΔWPA em pontos de chance de vitória da partida, pela estimativa "
           "do modelo (negativo = o time perdeu chance).", "",
           "**Regra de publicação:** o tipo só aparece no site com pelo menos 8 dos 10 confirmados: \"sim\" quando "
           "o nível é explícito, ou \"depende da tática\" quando o nível é depende.", ""]
    for t in E.TIPOS:
        ex = exemplos(oc, t)
        out += [f"#### {E.TITULOS[t]}", "", f"Frase de como melhorar: \"{E.COMO_MELHORAR[t]}\"", "",
                "**A frase serve?** sim / reescrever: ____", ""]
        if not ex:
            out += ["(nenhuma ocorrência no corpus)", ""]
            continue
        out += ["| # | partida | round | relógio | jogador | aliado | matador | dist. ao aliado | dist. jogador–matador "
                "| dist. aliado–matador | situação | valor | ΔWPA | nível | motivo | replay | É erro mesmo? | A frase serve? |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for i, x in enumerate(ex, 1):
            situ = f"{x['vivos_time']} contra {x['vivos_adversario']}"
            valor = "—" if x["valor"] is None else _fmt(x["valor"], 1)
            dw = "—" if x["dwpa"] is None else _fmt(100 * x["dwpa"], 1)
            nome = lambda s: (s or "—").replace("|", "\\|")  # noqa: E731
            out.append(
                f"| {i} | {x['match_id']} | {x['round_num']} | {_relogio(x['segundos'])} | {nome(x['name'])} | "
                f"{nome(x['aliado'])} | {nome(x['matador'])} | {_fmt(x['dist_aliado'])} | "
                f"{_fmt(x['dist_matador_jogador'])} | {_fmt(x['dist_matador_aliado'])} | {situ} | {valor} | {dw} | "
                f"{E.ROTULO_DO_NIVEL[x['nivel']]} | {x['motivo']} | "
                f"[abrir]({link_do_replay(x['match_id'], x['round_num'], x['segundos'])}) | "
                "sim / não / depende da tática | sim / reescrever |")
        out.append("")
    return out


NOTA_FASE15 = (
    '**Mudança da fase 15 (decisão 46).** "Flash no time" e "dano de utilidade no time" eram somas da partida (CT e TR juntos); passam a ser POR LADO, com '
    'o mesmo limiar (`SEG_CEGUEIRA_ALIADO` 27 s e `DANO_UTILIDADE_ALIADO` 20) aplicado a cada lado. Ocorrências que seguem na tela (depois dos filtros), no'
    ' corpus de 52 jogos: flash no time 880 antes, 530 depois; dano de utilidade no time 32 antes, 28 depois (o total detectado não muda: 3091 e 195). Na fase'
    ' 17 os exemplos de "flash no time" e "dano de utilidade no time" foram conferidos contra as regras de hoje: os que seguem sendo ocorrência ficaram, e só os que deixaram de ser foram sorteados de novo (marcados "(substituído na fase 17)" na coluna motivo).'
    '')


def secao(oc: pl.DataFrame, cache: dict | None) -> list[str]:
    n = len(partidas())
    out = [TITULO_DA_SECAO, "",
           "Gerado por `py -3.12 -m scripts.calibracao.erros_do_jogador` (fase 12, decisão 46). Os tipos de erro de "
           f"`metrics/erros.py` sobre as {n} partidas do corpus. Nenhum tipo aparece no site até você confirmar os "
           "exemplos: `TIPOS_DE_ERRO_VALIDADOS` começa vazia. Para ver a aba com todos os tipos marcados "
           "\"em validação\": `py -3.12 -m scripts.build_site --mostrar-erros-nao-validados` (gera em `preview/`, "
           "fora do git e nunca publicado).", "",
           "### 7.0 Ocorrências por tipo no corpus", ""]
    out += tabela_por_tipo(oc)
    out += ["", NOTA_FASE15]
    out += ["", "Ordem dos níveis (a primeira regra que se aplica decide): 1) round de eco ou pistola do time, ou time "
            "guardando arma (evento depois do plant num round que o time perdeu): fora; 2) morreu isolado sendo "
            "lurker: depende; 3) primeira morte sem troca sendo entry: depende; 4) morreu isolado ou primeira morte do "
            "AWPer no duelo de abertura: depende; 5) função só tendência: o motivo diz que a função não é firme; "
            "6) não trocou, possível bait, perdeu a troca, flash no time e dano de utilidade no time: explícito; "
            "7) o resto: depende. Por isso \"morreu isolado\" e \"primeira morte sem troca\" saem sempre como "
            "\"depende da tática\" (só o motivo muda).", ""]
    if cache:
        out += secao_constantes(cache)
    out += secao_quantos_pontos(oc, cache)
    out += secao_exemplos(oc)
    out += ["### 7.3 Sua resposta", "",
            "Para cada tipo: quantos dos 10 exemplos você confirma, e se a frase de como melhorar serve. O tipo com 8 "
            "ou mais confirmados entra em `TIPOS_DE_ERRO_VALIDADOS` (`metrics/erros.py`) num item à parte; os "
            "reprovados ficam fora da tela, e eu trago uma proposta de ajuste com os números.", ""]
    return out


def grava(linhas: list[str], material: Path = MATERIAL) -> None:
    """Troca a seção 7 do material (ou a acrescenta no fim), sem tocar nas outras."""
    texto = material.read_text(encoding="utf-8")
    novo = "\n".join(linhas).rstrip() + "\n"
    i = texto.find(TITULO_DA_SECAO)
    if i < 0:
        texto = texto.rstrip() + "\n\n" + novo
    else:
        j = texto.find("\n## ", i + len(TITULO_DA_SECAO))
        texto = texto[:i] + novo + ("" if j < 0 else "\n" + texto[j + 1:])
    material.write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    oc = corpus()
    if "--tabela" in argv:
        print("\n".join(tabela_por_tipo(oc)))
        return 0
    cache = {m: E.carrega_partida(m) for m in partidas()}
    grava(secao(oc, cache))
    print(f"seção 7 gravada em {MATERIAL.name} ({oc.height} ocorrências em {len(cache)} partidas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
