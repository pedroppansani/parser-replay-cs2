"""A aba Perfil nova (fase 12): o bloco da página, com todas as frases prontas (decisão 18).

Responde, para cada jogador desta partida, nesta ordem:
1. onde ele mais custou rounds ao time (até 3 pontos a melhorar, dos tipos de metrics/erros.py);
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

# O endereço de "como é conferido": a seção 7 do material de calibração, no repositório.
REPO = "https://github.com/pedroppansani/parser-replay-cs2"
COMO_E_CONFERIDO = "MATERIAL_DE_CALIBRACAO.md#7-erros-na-aba-perfil"

TEXTOS = {
    "eyebrow": "Onde errou e como melhorar",
    "seletor": "Jogador",
    "melhorar": "Pontos a melhorar",
    "fortes": "Pontos fortes",
    "comparar": "Comparar com",
    "ninguem": "— ninguém —",
    "detalhes": "Detalhes",
    "detalhes_resumo": "o perfil completo desta partida: taxas, função por round, jeito de jogar e quem joga em cada grupo",
    "detalhes_erros": "Aconteceu uma vez (abaixo do mínimo de 2 para virar ponto a melhorar)",
    "em_validacao": "Em validação: os tipos de erro aparecem depois de conferidos",
    "como_e_conferido": "como é conferido",
    "rotulo_em_validacao": "em validação",
    "aviso_preview": ("Pré-visualização: nenhum destes tipos de erro foi conferido ainda. Todos estão em validação e "
                      "esta página não é publicada."),
    "nenhum_erro": "Nenhum erro se repetiu nesta partida",
    "fortes_vazio": "Nenhuma métrica ficou acima da referência da função nesta partida",
    "comparar_texto": ("Só jogadores desta partida, de qualquer time; ao lado de cada um, a contagem ou o valor dele "
                       "nesta partida. A referência é a mediana anônima do corpus."),
    "col_ponto": "Ponto",
    "col_referencia": "referência",
    "rounds_do_chip": "rounds",
}


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


def _referencia(ref: dict | None, grupo: str, chave: str, funcao: str | None) -> tuple[float | None, str | None]:
    """(valor, de quem): a mediana da função; sem régua própria da função, a do corpus inteiro."""
    tabela = ((ref or {}).get(grupo) or {}).get(chave) or {}
    if funcao and tabela.get(funcao) is not None:
        return tabela[funcao], f"de quem joga {_nome_da_funcao(funcao)}"
    if tabela.get(E.TODAS) is not None:
        return tabela[E.TODAS], "do corpus"
    return None, None


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


def _chips(ocs: list[dict]) -> list[dict]:
    """Um chip por ocorrência: abre o Replay naquele round e naquele tempo (round e segundos desde o freeze)."""
    out = []
    for o in sorted(ocs, key=lambda x: (x["round_num"], x["tick"])):
        t = o["segundos"]
        out.append({"round": int(o["round_num"]), "t": None if t is None else float(t),
                    "rotulo": str(int(o["round_num"])),
                    "titulo": f"Abrir o replay no round {int(o['round_num'])}, {relogio(t)} depois do fim do freeze"})
    return out


def _ponto_a_melhorar(tipo: str, ocs: list[dict], rounds: int, ref: dict | None, funcao: str | None,
                      em_validacao: bool) -> dict:
    niveis = Counter(o["nivel"] for o in ocs)
    nivel = E.EXPLICITO if niveis.get(E.EXPLICITO, 0) >= niveis.get(E.DEPENDE, 0) else E.DEPENDE
    motivos = Counter(o["motivo"] for o in ocs if o["nivel"] == nivel)
    motivo = sorted(motivos.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    pontos, custo = _custo([o["dwpa"] for o in ocs])
    mediana, de_quem = _referencia(ref, "erros", tipo, funcao)
    referencia = (f"a mediana {de_quem} é {_br(mediana, 1).removesuffix(',0')}" if mediana is not None else "")
    frase = (E.COMO_MELHORAR[tipo] if nivel == E.EXPLICITO
             else f"{motivo[0].upper()}{motivo[1:]}. {E.CONFERIR_COM_O_TIME}")
    return {"tipo": tipo, "titulo": E.TITULOS[tipo], "contagem": _contagem(len(ocs), rounds),
            "referencia": referencia, "nivel": nivel, "nivel_rotulo": E.ROTULO_DO_NIVEL[nivel],
            "motivo": motivo, "frase": frase, "custo": custo, "_pontos": pontos,
            "em_validacao": em_validacao, "chips": _chips(ocs)}


def _pontos_fortes(perfil: dict, ref: dict | None, funcao: str | None) -> tuple[list[dict], dict]:
    """(até MAX_PONTOS_FORTES pontos fortes, {chave: valor e bruto formatados} de todas as métricas)."""
    candidatos, valores = [], {}
    for chave, formato, unidade in E.METRICAS_DE_PONTO_FORTE:
        v, n, d = perfil.get(chave), perfil.get(f"{chave}_n"), perfil.get(f"{chave}_d")
        bruto = ""
        if d:
            bruto = (f"{round(n)} de {round(d)} {unidade}" if formato == "pct"
                     else f"em {round(d)} {unidade}")
        valores[chave] = {"valor": formata(v, formato), "bruto": bruto}
        if v is None or perfil.get(f"{chave}_fraco") or not d:
            continue
        r, de_quem = _referencia(ref, "metricas", chave, funcao)
        if r is None or r <= 0 or v < r * (1 + E.MARGEM_PONTO_FORTE):
            continue
        candidatos.append(((v - r) / r, chave, {
            "chave": chave, "rotulo": _rotulo_da_metrica(chave), "valor": formata(v, formato), "bruto": bruto,
            "referencia": f"a mediana {de_quem} é {formata(r, formato)}"}))
    candidatos.sort(key=lambda c: (-c[0], c[1]))
    return [c[2] for c in candidatos[:E.MAX_PONTOS_FORTES]], valores


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
        partes.append(f"o que mais custou foi {m['titulo'].lower()} ({m['contagem'].split(' em ')[0]})")
    if fortes:
        f = fortes[0]
        partes.append(f"o ponto mais forte foi {f['rotulo'][0].lower()}{f['rotulo'][1:]} ({f['valor']}, "
                      f"{f['referencia']})")
    return "; ".join(partes) + "."


def bloco(payload: dict, ocorrencias: pl.DataFrame | None, *, cabecalho: dict | None = None,
          tendencia: dict | None = None, referencia: dict | None = None,
          validados: frozenset[str] | set[str] | None = None, preview: bool = False,
          repo: str | None = None) -> dict:
    """O bloco `perfil` da página. `validados` (padrão: metrics.erros.TIPOS_DE_ERRO_VALIDADOS) diz que
    tipos vão para a tela; `preview` mostra todos, marcados "em validação"."""
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
        funcao = E.funcao_principal(funcoes.get(sid, []))
        ocs = por_jogador.get(sid, [])
        por_tipo = {t: [o for o in ocs if o["tipo"] == t] for t in na_tela}
        melhorar, uma_vez = [], []
        for t in na_tela:
            if len(por_tipo[t]) >= E.MIN_OCORRENCIAS_PARA_PONTO:
                melhorar.append(_ponto_a_melhorar(t, por_tipo[t], rounds, referencia, funcao, preview))
            elif por_tipo[t]:
                uma_vez.append({"titulo": E.TITULOS[t], "contagem": _contagem(len(por_tipo[t]), rounds),
                                "chips": _chips(por_tipo[t])})
        # explícitos antes; dentro do nível, o maior custo; empate pela ordem fixa dos tipos
        ordem = {t: i for i, t in enumerate(E.TIPOS)}
        melhorar.sort(key=lambda m: (m["nivel"] != E.EXPLICITO, -m["_pontos"], ordem[m["tipo"]]))
        melhorar = melhorar[:E.MAX_PONTOS_A_MELHORAR]
        if rating_deg:
            for m in melhorar:
                m["custo"] = ""
        for m in melhorar:
            m.pop("_pontos", None)
        fortes, valores = _pontos_fortes(p, referencia, funcao)
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
        "link_como_e_conferido": f"{(repo or REPO).rstrip('/')}/blob/main/{COMO_E_CONFERIDO}",
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
    return bloco(payload, oc, cabecalho=cabecalho, tendencia=tendencia_da_partida(base),
                 referencia=E.carrega_referencia(), validados=validados, preview=preview, repo=repo)
