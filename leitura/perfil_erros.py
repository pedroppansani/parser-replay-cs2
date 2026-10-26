"""A aba Perfil nova (fase 12): o bloco da página, com todas as frases prontas (decisão 18).

Responde, para cada jogador desta partida, nesta ordem:
1. onde ele mais custou rounds ao time (até 3 pontos a melhorar, dos tipos de metrics/erros/__init__.py);
2. o que ele fez bem (até 2 pontos fortes, das métricas que já existem no perfil);
3. como ele se compara com outro jogador DESTA partida nesses pontos (decisão 30).

Só aparecem na tela os tipos de erro em `metrics.erros.TIPOS_DE_ERRO_VALIDADOS` (vazia até o Pedro
conferir os exemplos do material de calibração). Com ela vazia, a seção "Pontos a melhorar" diz que
os tipos estão em validação. A pré-visualização (`--mostrar-erros-nao-validados` do build, só em
`preview/`) mostra todos os tipos, cada um marcado "em validação".

O JS só monta o HTML: nenhum texto daqui é escrito no template, e todo texto passa por esc() lá.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import polars as pl

from metrics import erros as E
from metrics.impacto import ROTULOS as ROTULOS_DE_IMPACTO
from metrics.player_profile import ROTULOS_DAS_TAXAS
from metrics.structural_roles import FUNCOES
from metrics.tactics import relogio as relogio_do_jogo

# O endereço de "como é conferido": a "Metodologia" no rodapé da própria página (v2-4, pedido do Pedro: um
# lugar DO SITE, sem link externo nem e-mail; o site não tem página de método própria).
COMO_E_CONFERIDO = "#foot"

TEXTOS = {
    "eyebrow": "Onde errou e como melhorar",
    "seletor": "Jogador",
    "melhorar": "Pontos a melhorar",
    "fortes": "Pontos fortes",
    "comparar": "Comparar com",
    "ninguem": "— ninguém —",
    "detalhes": "Detalhes",
    "detalhes_resumo": "o perfil completo desta partida: taxas, função por round, jeito de jogar e quem joga em cada grupo",
    "detalhes_erros": "Erros que não viraram ponto a melhorar",
    "uma_vez": "aconteceu uma vez, abaixo do mínimo de 2 para virar ponto a melhorar",
    "normal_funcao": "dentro do normal para a função",
    "normal_lado": "dentro do normal para os jogadores de {lado}",
    # texto do estado vazio da v2 (entrega-v2-goatdemo §5.4, aceito pelo Pedro, dúvida 8 do plano v2-0)
    "em_validacao": ("Ainda estamos conferindo estas leituras com partidas reais. Elas aparecem aqui quando "
                     "estiverem validadas."),
    "como_e_conferido": "Como é conferido",
    "rotulo_em_validacao": "em validação",
    "aviso_preview": ("Pré-visualização: nenhum destes tipos de erro foi conferido ainda. Todos estão em validação e "
                      "esta página não é publicada."),
    "nenhum_erro": "Nada acima do normal para a função nesta partida",
    "fortes_vazio": "Nenhuma métrica ficou acima da referência da função nesta partida",
    "comparar_texto": ("Só jogadores desta partida, de qualquer time; ao lado de cada um, a contagem ou o valor dele "
                       "nesta partida. A referência é a mediana anônima do corpus."),
    "col_ponto": "Ponto",
    "col_referencia": "referência",
    "rounds_do_chip": "rounds",
    # fase 15 (§19.9): rótulos dos cards novos; nenhum texto fixo no template (decisão 18)
    "rot_como_melhorar": "Como melhorar",
    "rot_conferir": "Antes de mudar algo",
    "rot_rounds": "Rounds (abrem o Replay)",
    "ja_aberto": "já aberto",
    "nivel_explicito": "explícito",
    "nivel_depende": "depende da tática",
    "rotulo_dentro_do_normal": "dentro do normal para a função",
    "sem_taxas": "Sem taxas com amostra suficiente nesta partida.",
    "escondido_degradado": "Escondido: dado degradado.",
}

# A taxa só é destacada, e só é "dentro do normal", pela diferença absoluta para a mediana da régua do corpus
# (pontos de taxa). É o MARGEM_DESTAQUE do template da aba, lido aqui para a etiqueta sair do Python.
MARGEM_DESTAQUE = 0.15
# Quando o dado não traz o plant do round, o relógio do chip é o do round (1:55 descendo).
SEGUNDOS_ANTES_DO_REPLAY = 3        # o Replay abre 3 s antes do instante (decisão 46, "Replay com tempo")


def _br(x: float, casas: int) -> str:
    return f"{x:.{casas}f}".replace(".", ",")


def formata(valor: float | None, formato: str) -> str:
    """Como a página escreve o número (o mesmo jeito da aba Jogadores: porcentagem inteira, vírgula)."""
    if valor is None:
        return "—"
    if formato == "pct":
        return f"{round(100 * valor)}%"
    return _br(valor, 2 if formato == "num2" else 1)


def relogio(segundos: float | None) -> str:
    if segundos is None:
        return "—"
    s = max(0, int(round(segundos)))
    return f"{s // 60}:{s % 60:02d}"


def _rotulo_da_metrica(chave: str) -> str:
    return ROTULOS_DAS_TAXAS.get(chave) or ROTULOS_DE_IMPACTO.get(chave, (chave,))[0]


def _nome_da_funcao(f: str | None) -> str | None:
    if f not in FUNCOES:
        return None
    rot = FUNCOES[f][0]
    return rot if rot == "AWPer" else rot.lower()     # AWPer é nome próprio da função


def _origem(escopo: str | None, lado: str, funcao: str | None) -> str:
    """De quem é a referência (decisão 46, fase 12b): a célula (lado, função), ou, com poucos jogador-lados
    nela, o lado inteiro. Nunca os dois lados juntos."""
    rot = E.ROTULO_DO_LADO[lado]
    nome = _nome_da_funcao(funcao)
    if escopo == "funcao" and nome:
        return f"quem joga {nome} no {rot}"
    if nome:
        plural = nome if nome.endswith("s") else f"{nome}s"
        return f"todos os jogadores de {rot} (poucos {plural} no corpus)"
    return f"todos os jogadores de {rot} (sem função definida neste lado)"


def _referencia(ref: dict | None, grupo: str, chave: str, lado: str,
                funcao: str | None) -> tuple[dict | None, str | None]:
    """(entrada da régua, de quem): a da célula (lado, função), ou a do lado inteiro quando a célula é pequena."""
    celula, escopo = E.escolhe_celula(ref, grupo, chave, lado, funcao)
    return (celula, _origem(escopo, lado, funcao)) if celula is not None else (None, None)


def _no_lado(lado: str | None) -> str:
    """"no TR" / "no CT": o card diz o lado do erro."""
    return f"no {E.ROTULO_DO_LADO[lado]}" if lado else ""


def _contagem(n: int, rounds: int) -> str:
    vezes = "vez" if n == 1 else "vezes"
    return f"{n} {vezes} em {rounds} rounds"


def _custo(dwpas: list[float | None]) -> tuple[float, str]:
    """(custo em pontos, frase). Custo = a soma das quedas da chance de vitória (ΔWPA), em pontos."""
    medidos = [d for d in dwpas if d is not None]
    if not medidos:
        return 0.0, "sem custo estimado: o modelo de vitória não mede este tipo de erro"
    pontos = -100.0 * sum(medidos)
    if pontos < 1:
        return pontos, "custou menos de 1 ponto de chance de vitória, pela estimativa do modelo"
    n = round(pontos)
    return pontos, f"custou cerca de {n} {'ponto' if n == 1 else 'pontos'} de chance de vitória, pela estimativa do modelo"


def _chips(ocs: list[dict], lado: str | None = None) -> list[dict]:
    """Um chip por ocorrência: abre o Replay naquele round e naquele tempo (round e segundos desde o freeze).
    Todo erro é de um lado só (fase 15): o chip leva o lado e o relógio do round ("R12 · 1:14"), o mesmo
    que o Replay mostra no instante."""
    out = []
    for o in sorted(ocs, key=lambda x: (x["round_num"], x["tick"])):
        t = o["segundos"]
        rn = int(o["round_num"])
        lado_o = o.get("side") or lado or ""
        hora = o.get("relogio") or (relogio_do_jogo(t) if t is not None else "")
        texto = f"R{rn} · {hora}" if hora else f"R{rn}"
        out.append({"round": rn, "t": None if t is None else float(t),
                    "lado": lado_o, "lado_rotulo": _no_lado(lado_o), "relogio": hora,
                    "rotulo": f"R{rn}", "texto": texto,
                    "titulo": f"Round {rn}{', ' + hora if hora else ''}: abre o Replay {SEGUNDOS_ANTES_DO_REPLAY} s antes do instante"})
    return out


def _ponto_a_melhorar(tipo: str, ocs: list[dict], rounds: int, ref: dict | None, funcao: str | None,
                      em_validacao: bool, lado: str | None = None) -> dict:
    niveis = Counter(o["nivel"] for o in ocs)
    nivel = E.EXPLICITO if niveis.get(E.EXPLICITO, 0) >= niveis.get(E.DEPENDE, 0) else E.DEPENDE
    motivos = Counter(o["motivo"] for o in ocs if o["nivel"] == nivel)
    motivo = sorted(motivos.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    pontos, custo = _custo([o["dwpa"] for o in ocs])
    referencia, limite = "", None
    if lado:
        celula, de_quem = _referencia(ref, "erros", tipo, lado, funcao)
        mediana = E.percentil_do_histograma(celula["hist"], 50) if celula else None
        limite = E.percentil_do_histograma(celula["hist"], E.PERCENTIL_PONTO_A_MELHORAR) if celula else None
        if mediana is not None:
            referencia = (f"referência: {de_quem}; a mediana é {_br(mediana, 1).removesuffix(',0')}; "
                          f"o normal vai até {_br(limite, 1).removesuffix(',0')}")
    frase = (E.COMO_MELHORAR[tipo] if nivel == E.EXPLICITO
             else f"{motivo[0].upper()}{motivo[1:]}. {E.CONFERIR_COM_O_TIME}")
    return {"tipo": tipo, "titulo": E.TITULOS[tipo], "lado": lado or "", "lado_rotulo": _no_lado(lado),
            "limite": limite if limite is not None else -1.0,
            "contagem": _contagem(len(ocs), rounds),
            "referencia": referencia, "nivel": nivel, "nivel_rotulo": E.ROTULO_DO_NIVEL[nivel],
            "motivo": motivo, "frase": frase, "custo": custo, "_pontos": pontos,
            "em_validacao": em_validacao, "chips": _chips(ocs, lado)}


def dentro_do_normal(perfil: dict, chave: str) -> bool:
    """A taxa está dentro da faixa da régua do corpus: tem denominador, amostra suficiente, régua e fica a
    menos de `MARGEM_DESTAQUE` da mediana (a conta do `celula` do template, que passa a vir do Python)."""
    v, ref = perfil.get(chave), perfil.get(f"{chave}_ref")
    return bool(perfil.get(f"{chave}_d")) and not perfil.get(f"{chave}_fraco") and v is not None         and ref is not None and abs(v - ref) < MARGEM_DESTAQUE


def _bruto(n, d, formato: str, unidade: str) -> str:
    if not d:
        return ""
    return f"{round(n)} de {round(d)} {unidade}" if formato == "pct" else f"em {round(d)} {unidade}"


def _pontos_fortes(perfil: dict, por_lado: dict, funcoes: dict, ref: dict | None) -> tuple[list[dict], dict]:
    """(até MAX_PONTOS_FORTES pontos fortes, {chave: valor e bruto formatados} de todas as métricas).

    `valores` é o da partida inteira (a tabela de comparar); o ponto forte é por LADO: `por_lado` é
    {lado: {chave: (valor, n, d)}} (metrics.erros.metricas_por_lado) e `funcoes` {lado: função}. A
    referência é a da célula (lado, função), ou a do lado inteiro (decisão 46, fase 12b)."""
    candidatos, valores = [], {}
    for chave, formato, unidade in E.METRICAS_DE_PONTO_FORTE:
        v, n, d = perfil.get(chave), perfil.get(f"{chave}_n"), perfil.get(f"{chave}_d")
        valores[chave] = {"valor": formata(v, formato), "bruto": _bruto(n, d, formato, unidade)}
    for lado in E.LADOS:
        for chave, formato, unidade in E.METRICAS_DE_PONTO_FORTE:
            v, n, d = (por_lado.get(lado) or {}).get(chave, (None, 0, 0))
            if v is None or not d or E.amostra_fraca(chave, d):
                continue
            celula, de_quem = _referencia(ref, "metricas", chave, lado, funcoes.get(lado))
            r = celula["mediana"] if celula else None
            if r is None or r <= 0 or v < r * (1 + E.MARGEM_PONTO_FORTE):
                continue
            rotulo = _rotulo_da_metrica(chave)
            candidatos.append(((v - r) / r, chave, lado, {
                "chave": chave, "rotulo": rotulo, "lado": lado,
                "lado_rotulo": "" if rotulo.endswith(("(TR)", "(CT)")) else _no_lado(lado),
                "valor": formata(v, formato), "bruto": _bruto(n, d, formato, unidade),
                "referencia": f"referência: {de_quem}; a mediana é {formata(r, formato)}"}))
    candidatos.sort(key=lambda c: (-c[0], c[1], c[2]))
    return [c[3] for c in candidatos[:E.MAX_PONTOS_FORTES]], valores


def _funcoes_do_jogador(linhas: list[dict], tendencia: dict) -> list[dict]:
    out = []
    for lado, rot in (("ct", "CT"), ("t", "TR")):
        r = next((x for x in linhas if x.get("side") == lado), None)
        if r is None:
            continue
        if r.get("texto_empate"):
            out.append({"lado": rot, "texto": r["texto_empate"], "tendencia": False, "neutro": True})
        elif r.get("funcao"):
            t = bool(tendencia.get((int(r["steamid"]), lado)))
            nome = FUNCOES.get(r["funcao"], (r["funcao"],))[0]
            out.append({"lado": rot, "texto": f"{nome} (tendência)" if t else nome, "tendencia": t, "neutro": t})
        else:
            out.append({"lado": rot, "texto": "sem função definida", "tendencia": False, "neutro": True})
    return out


def _resumo(nome: str, rounds: int, fortes: list[dict], melhorar: list[dict]) -> str:
    partes = [f"{nome} jogou {rounds} rounds nesta partida"]
    if melhorar:
        m = melhorar[0]
        partes.append(f"o que mais custou foi {m['titulo'].lower()} {m['lado_rotulo']} "
                      f"({m['contagem'].split(' em ')[0]})".replace("  ", " "))
    if fortes:
        f = fortes[0]
        partes.append(f"o ponto mais forte foi {f['rotulo'][0].lower()}{f['rotulo'][1:]}"
                      f"{' ' + f['lado_rotulo'] if f.get('lado_rotulo') else ''} ({f['valor']}, "
                      f"{f['referencia']})")
    return "; ".join(partes) + "."


def bloco(payload: dict, ocorrencias: pl.DataFrame | None, *, cabecalho: dict | None = None,
          tendencia: dict | None = None, referencia: dict | None = None,
          validados: frozenset[str] | set[str] | None = None, preview: bool = False,
          repo: str | None = None, metricas_lado: dict | None = None) -> dict:
    """O bloco `perfil` da página. `validados` (padrão: metrics.erros.TIPOS_DE_ERRO_VALIDADOS) diz que
    tipos vão para a tela; `preview` mostra todos, marcados "em validação". `metricas_lado` é
    {steamid: {lado: {chave: (valor, n, d)}}}, as métricas de ponto forte só com os rounds de cada lado."""
    validados = E.TIPOS_DE_ERRO_VALIDADOS if validados is None else frozenset(validados)
    na_tela = [t for t in E.TIPOS if preview or t in validados]
    tendencia = tendencia or {}
    perfis = {int(p["steamid"]): p for p in payload.get("player_profile") or []}
    players = {int(p["steamid"]): p for p in payload.get("players") or []}
    funcoes: dict[int, list[dict]] = {}
    for r in payload.get("structural_roles") or []:
        funcoes.setdefault(int(r["steamid"]), []).append(r)
    lados = (cabecalho or {}).get("lados") or {}
    por_jogador = E.por_jogador(ocorrencias) if ocorrencias is not None else {}
    degradado = []
    if ocorrencias is None:
        degradado.append("sem a tabela de erros desta partida")
    rating_deg = (payload.get("rating_info") or {}).get("modo_degradado") or []
    if rating_deg:
        degradado.append("o custo em chance de vitória usa o modelo do rating, que está degradado nesta partida")

    jogadores = []
    for sid in sorted(perfis, key=lambda s: ((players.get(s) or {}).get("team") or "", perfis[s]["name"].lower(), s)):
        p = perfis[sid]
        pl_ = players.get(sid) or {}
        rounds = int(p.get("rounds_jogados") or 0)
        # por lado: a função (None se empatada ou ausente) e os rounds jogados naquele lado
        funcao_do_lado, rounds_do_lado = {}, {}
        for r in funcoes.get(sid, []):
            rounds_do_lado[r["side"]] = int(r.get("rounds_no_lado") or 0)
            funcao_do_lado[r["side"]] = None if r.get("texto_empate") else r.get("funcao")
        ocs = por_jogador.get(sid, [])
        por_tipo = {t: [o for o in ocs if o["tipo"] == t] for t in na_tela}
        melhorar, uma_vez = [], []
        for t in na_tela:
            for lado_ in E.LADOS:                       # um ponto a melhorar é um par (tipo, lado)
                dele = [o for o in por_tipo[t] if o["side"] == lado_]
                if not dele:
                    continue
                celula, escopo = E.escolhe_celula(referencia, "erros", t, lado_, funcao_do_lado.get(lado_))
                if E.acima_do_normal(len(dele), celula):
                    melhorar.append(_ponto_a_melhorar(t, dele, rounds_do_lado.get(lado_, rounds), referencia,
                                                      funcao_do_lado.get(lado_), preview, lado_))
                else:
                    # Detalhes: abaixo do mínimo de ocorrências, ou dentro do normal para a referência
                    motivo = (TEXTOS["uma_vez"] if len(dele) < E.MIN_OCORRENCIAS_PARA_PONTO
                              else TEXTOS["normal_funcao"] if escopo != "lado"
                              else TEXTOS["normal_lado"].format(lado=E.ROTULO_DO_LADO[lado_]))
                    uma_vez.append({"titulo": E.TITULOS[t], "lado_rotulo": _no_lado(lado_),
                                    "contagem": _contagem(len(dele), rounds_do_lado.get(lado_, rounds)),
                                    "motivo": motivo, "chips": _chips(dele, lado_)})
        # explícitos antes; dentro do nível, o maior custo; empate pela ordem fixa dos tipos
        ordem = {t: i for i, t in enumerate(E.TIPOS)}
        melhorar.sort(key=lambda m: (m["nivel"] != E.EXPLICITO, -m["_pontos"], ordem[m["tipo"]]))
        melhorar = melhorar[:E.MAX_PONTOS_A_MELHORAR]
        if rating_deg:
            for m in melhorar:
                m["custo"] = ""
        for m in melhorar:
            m.pop("_pontos", None)
        # pontos fortes por (lado, função), na prévia e no publicado (decisão 46, FORTES_POR_LADO_PUBLICADOS)
        fortes, valores = _pontos_fortes(p, (metricas_lado or {}).get(sid, {}), funcao_do_lado, referencia)
        time = pl_.get("team")
        lado = lados.get(time) or {}
        jogadores.append({
            "name": p["name"], "team": time, "time_nome": lado.get("nome") or "",
            "comecou": lado.get("comecou") or "",
            "comecou_rotulo": {"ct": "começou CT", "tr": "começou TR"}.get(lado.get("comecou"), ""),
            "funcoes": _funcoes_do_jogador(funcoes.get(sid, []), tendencia),
            "resumo": _resumo(p["name"], rounds, fortes, melhorar),
            "melhorar": melhorar,
            "melhorar_vazio": TEXTOS["nenhum_erro"] if na_tela and not melhorar else "",
            "uma_vez": uma_vez,
            "dentro_do_normal": {c: dentro_do_normal(p, c) for c in ROTULOS_DAS_TAXAS},
            "fortes": fortes,
            "contagens": {t: len(por_tipo[t]) for t in na_tela},
            "valores": valores,
        })
    # o jogador aberto por padrão: o maior rating (desempate pelo nome, decisão 28)
    padrao = ""
    if perfis:
        padrao = sorted(perfis.values(), key=lambda p: (
            -((players.get(int(p["steamid"])) or {}).get("rating") or 0.0), p["name"].lower()))[0]["name"]
    estado = "preview" if preview else ("normal" if na_tela else "em_validacao")
    return {
        "textos": TEXTOS,
        "estado": estado,
        "link_como_e_conferido": COMO_E_CONFERIDO,
        "degradado": ("▲ " + "; ".join(degradado)) if degradado else "",
        "padrao": padrao,
        "tipos": [{"id": t, "titulo": E.TITULOS[t]} for t in na_tela],
        "metricas": [{"chave": c, "rotulo": _rotulo_da_metrica(c)} for c, _, _ in E.METRICAS_DE_PONTO_FORTE],
        "jogadores": jogadores,
    }


def tendencia_da_partida(base: Path) -> dict:
    """{(steamid, lado): função só tendência?}, da reamostragem da decisão 39 (structural_roles)."""
    from metrics.player_roles import awpers_do_time
    from metrics.structural_roles import estabilidade_da_funcao
    caminho = base / "structural_roles.parquet"
    if not caminho.exists():
        return {}
    traits = base / "player_traits.parquet"
    awpers = awpers_do_time(pl.read_parquet(traits)) if traits.exists() else set()
    return {(int(r["steamid"]), r["side"]): bool(r["tendencia"])
            for r in estabilidade_da_funcao(pl.read_parquet(caminho), awpers).iter_rows(named=True)}


def bloco_da_partida(base: Path, payload: dict, cabecalho: dict | None, *, preview: bool = False,
                     repo: str | None = None, validados=None) -> dict:
    """O bloco a partir da pasta processada da partida (o que o build chama)."""
    caminho = base / E.ARQUIVO
    oc = pl.read_parquet(caminho) if caminho.exists() else None
    metricas: dict = {}
    if (base / "player_profile_rounds.parquet").exists() and (base / "impacto_per_round.parquet").exists():
        por_lado = E.metricas_por_lado(pl.read_parquet(base / "player_profile_rounds.parquet"),
                                       pl.read_parquet(base / "impacto_per_round.parquet"))
        for (sid, lado), valores in por_lado.items():
            metricas.setdefault(sid, {})[lado] = valores
    return bloco(payload, oc, cabecalho=cabecalho, tendencia=tendencia_da_partida(base),
                 referencia=E.carrega_referencia(), validados=validados, preview=preview, repo=repo,
                 metricas_lado=metricas)
