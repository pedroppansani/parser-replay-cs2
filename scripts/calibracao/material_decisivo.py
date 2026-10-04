"""Seção "Round decisivo" do MATERIAL_DE_CALIBRACAO.md (fase 6, passo 6.3).

Para cada partida escolhida: a curva da chance de vitória em texto (um bloco por
round), os três maiores rounds com o que aconteceu neles, o que cada regra
candidata diria (metrics/decisivo_candidatas.py) e a pergunta para o Pedro.

ESCOLHA DAS PARTIDAS. O passo pede todas as partidas em que as candidatas
discordam, mais uma amostra das que concordam, até 25 no total. As candidatas
discordam em 41 das 52, então não cabem todas: entram 21 discordâncias e 4
concordâncias. As discordâncias são escolhidas em rodízio pelo TIPO de
desacordo (quais regras dão round e se apontam o mesmo), para que cada tipo
apareça; dentro do tipo, a ordem cobre prorrogação, virada, placar largo e
apertado antes de repetir. Tudo determinístico (ordem do id da partida).

Uso (regrava só esta seção, entre os marcadores):
    py -3.12 -m scripts.calibracao.material_decisivo
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from metrics.decisivo_candidatas import K_PROEMINENCIA_DO_MATERIAL, todas  # noqa: E402
from metrics.formatting import format_money, format_pct  # noqa: E402
from metrics.win_probability import MR12, MR15  # noqa: E402

PROCESSED = RAIZ / "data" / "processed"
SAIDA = RAIZ / "MATERIAL_DE_CALIBRACAO.md"
INICIO, FIM = "<!-- decisivo:inicio -->", "<!-- decisivo:fim -->"
MAX_PARTIDAS = 25            # limite do passo 6.3
N_CONCORDANTES = 4           # amostra das que concordam
LARGURA_DA_BARRA = 20        # caracteres da barra de chance em texto


def _partida(f: Path) -> dict:
    d = json.loads(f.read_text(encoding="utf-8"))
    m = d["match"]
    vencedor = "A" if m["score_a"] > m["score_b"] else "B"
    curva = sorted(d["win_probability"]["curve"], key=lambda r: r["round"])
    regras = todas(curva, vencedor, MR15 if m.get("formato") == "MR15" else MR12)
    chance_v = [r["wp_a_antes"] if vencedor == "A" else 1 - r["wp_a_antes"] for r in curva]
    bd = PROCESSED / f.parent.name / "breakdown.json"
    return {
        "id": f.parent.name, "d": d, "m": m, "vencedor": vencedor, "curva": curva, "regras": regras,
        "breakdown": {b["round"]: b for b in json.loads(bd.read_text(encoding="utf-8"))} if bd.exists() else {},
        "rounds": len(curva), "dif": abs(m["score_a"] - m["score_b"]),
        "virada": min(chance_v) < 0.5,
        "rounds_escolhidos": tuple(r["round"] for r in regras.values()),
    }


def tipo_de_desacordo(p: dict) -> tuple:
    """Quais regras dão round e quais coincidem: (A?, B?, C?, D?, classes de igualdade)."""
    rs = p["rounds_escolhidos"]
    tem = tuple(r is not None for r in rs)
    classes = tuple(sorted({rs.index(r) for r in rs if r is not None}))
    return tem + classes


def escolhe(partidas: list[dict]) -> list[dict]:
    discordam = [p for p in partidas if len(set(p["rounds_escolhidos"])) > 1]
    concordam = [p for p in partidas if len(set(p["rounds_escolhidos"])) == 1]

    def chave(p):   # prorrogação, virada, largo, apertado primeiro; depois o id
        return (-(p["rounds"] > 24), -p["virada"], -(p["dif"] >= 6), -(p["dif"] <= 3), p["id"])

    por_tipo = defaultdict(list)
    for p in sorted(discordam, key=chave):
        por_tipo[tipo_de_desacordo(p)].append(p)
    escolhidas, tipos = [], sorted(por_tipo, key=str)
    while len(escolhidas) < MAX_PARTIDAS - N_CONCORDANTES and any(por_tipo.values()):
        for t in tipos:
            if por_tipo[t] and len(escolhidas) < MAX_PARTIDAS - N_CONCORDANTES:
                escolhidas.append(por_tipo[t].pop(0))
    # amostra das concordantes: um de cada perfil que existir (prorrogação, virada, largo, apertado)
    perfis = [lambda p: p["rounds"] > 24, lambda p: p["virada"], lambda p: p["dif"] >= 6, lambda p: p["dif"] <= 3]
    amostra = []
    for perfil in perfis:
        cand = [p for p in sorted(concordam, key=lambda p: p["id"]) if perfil(p) and p not in amostra]
        if cand and len(amostra) < N_CONCORDANTES:
            amostra.append(cand[0])
    for p in sorted(concordam, key=lambda p: p["id"]):
        if len(amostra) >= N_CONCORDANTES:
            break
        if p not in amostra:
            amostra.append(p)
    return sorted(escolhidas + amostra, key=lambda p: p["id"]), len(discordam), len(concordam)


def _barra(chance: float) -> str:
    n = round(chance * LARGURA_DA_BARRA)
    return "#" * n + "." * (LARGURA_DA_BARRA - n)


def _bloco_da_curva(p: dict) -> list[str]:
    linhas = ["```", f"round  placar   chance do vencedor ({'Time ' + p['vencedor']}) depois do round   |ΔP|"]
    for r in p["curva"]:
        c = r["wp_a_depois"] if p["vencedor"] == "A" else 1 - r["wp_a_depois"]
        linhas.append(f"R{r['round']:<4}  {r['score_a']:>2}-{r['score_b']:<2}   {_barra(c)} {format_pct(c):>4}   "
                      f"{format_pct(r['wpa_abs']):>4}  vence {r['winner_team']}")
    return linhas + ["```"]


def _round_em_detalhe(p: dict, r: dict) -> str:
    sc = {x["round"]: x for x in p["d"]["rounds_scored"]}.get(r["round"], {})
    b = p["breakdown"].get(r["round"], {})
    antes_a = r["score_a"] - (r["winner_team"] == "A")
    antes_b = r["score_b"] - (r["winner_team"] == "B")
    partes = [f"**R{r['round']}** ({format_pct(r['wpa_abs'])}): {antes_a}-{antes_b} → {r['score_a']}-{r['score_b']}, "
              f"vence o Time {r['winner_team']}"]
    if b.get("equip_value_winner") is not None:
        partes.append(f"compra: quem venceu {format_money(b['equip_value_winner'])}, "
                      f"quem perdeu {format_money(b['equip_value'])}")
    if sc.get("clutch_player"):
        partes.append(f"clutch de {sc['clutch_player']} contra {sc['clutch_against']}")
    if sc.get("multikill_player"):
        partes.append(f"{sc['multikill_count']}K de {sc['multikill_player']}")
    if sc.get("bomb_planted"):
        partes.append("bomba plantada")
    texto = "; ".join(partes) + "."
    if b.get("eco_text"):
        texto += f" Frase do round: \"{b['eco_text']}\""
    return texto


def secao() -> list[str]:
    partidas = [_partida(f) for f in sorted(PROCESSED.glob("match_*/insights.json"))]
    escolhidas, n_disc, n_conc = escolhe(partidas)
    out = [INICIO, "## 6. Round decisivo (fase 6)", "",
           "Gerado por `py -3.12 -m scripts.calibracao.material_decisivo` (regras em "
           "`metrics/decisivo_candidatas.py`, diagnóstico em `notas/investigacoes/2026-10-04-piso-do-decisivo.md`).",
           "",
           "**As regras candidatas:**",
           "- **A, piso absoluto (a de hoje):** o maior salto da chance de vitória, se passar de 1,5x o round "
           "mais barato do formato (12% no MR12).",
           f"- **B, proeminência:** o maior salto tem de valer pelo menos k vezes o round típico da partida "
           f"(a mediana dos saltos dela). Aqui k = {K_PROEMINENCIA_DO_MATERIAL} (a mediana no corpus) só para "
           "mostrar; o k de verdade sai das suas respostas.".replace(".68", ",68"),
           "- **C, virada definitiva:** o round depois do qual o vencedor nunca mais teve menos de 50% de chance, "
           "se antes dele esteve abaixo. Sem virada, não há round decisivo.",
           "- **D, combinação:** C quando houve virada; senão, B.",
           "- **Empate no topo** (A, B): o 1º e o 2º maiores saltos que a frase da página escreve com a mesma "
           "porcentagem.",
           "",
           f"As candidatas discordam em {n_disc} das {n_disc + n_conc} partidas, mais do que as {MAX_PARTIDAS} que "
           f"cabem aqui: entram {len(escolhidas) - min(N_CONCORDANTES, n_conc)} discordâncias, escolhidas em "
           f"rodízio pelo tipo de desacordo, e {min(N_CONCORDANTES, n_conc)} partidas em que as quatro concordam.",
           "",
           "| partida | mapa | placar | virada | A | B | C | D |",
           "|---|---|---|---|---|---|---|---|"]
    for p in escolhidas:
        rr = ["—" if x["round"] is None else f"R{x['round']}" + (" (empate)" if x["empate"] else "")
              for x in p["regras"].values()]
        out.append(f"| {p['id']} | {p['m']['map']} | {p['m']['score_a']}-{p['m']['score_b']} | "
                   f"{'sim' if p['virada'] else 'não'} | " + " | ".join(rr) + " |")
    out.append("")
    for p in escolhidas:
        out += [f"### {p['id']} — {p['m']['map']}, {p['m']['score_a']}-{p['m']['score_b']} ({p['rounds']} rounds)", ""]
        out += _bloco_da_curva(p)
        out += ["", "Os três maiores saltos:", ""]
        for r in sorted(p["curva"], key=lambda r: (-r["wpa_abs"], r["round"]))[:3]:
            out.append("- " + _round_em_detalhe(p, r))
        out += ["", "O que cada regra diria:", ""]
        for nome, x in p["regras"].items():
            alvo = "nenhum round" if x["round"] is None else f"R{x['round']}" + (" (empate no topo)" if x["empate"] else "")
            out.append(f"- **{nome}:** {alvo} — {x['porque']}.")
        out += ["", "**Esta partida teve round decisivo? Qual? Ou foi construída ao longo do jogo?**", "",
                "Sua resposta: ____", ""]
    out.append(FIM)
    return out


def grava() -> None:
    texto = SAIDA.read_text(encoding="utf-8")
    bloco = "\n".join(secao())
    if INICIO in texto and FIM in texto:
        ini, fim = texto.index(INICIO), texto.index(FIM) + len(FIM)
        texto = texto[:ini] + bloco + texto[fim:]
    else:
        texto = texto.rstrip("\n") + "\n\n" + bloco + "\n"
    SAIDA.write_text(texto, encoding="utf-8")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    grava()
    print(f"seção do round decisivo gravada em {SAIDA.relative_to(RAIZ).as_posix()}")


if __name__ == "__main__":
    main()
