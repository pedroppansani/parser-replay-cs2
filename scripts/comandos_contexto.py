"""O contexto que o leitor de comandos (`dashboard/web/comandos/leitor.js`) recebe: os pontos do Pedro do mapa, os lugares da demo, os jogadores, as funções,
o relógio e os TEXTOS das perguntas (a frase da tela sai do Python, decisão 18).

Os pontos vêm de `data/reference/callouts_br.csv` (mapas de callouts do Pedro, C0b). Os lugares da demo vêm de `data/lugares/<mapa>.json` (o nome do jogo em
inglês; o leitor os entende "sem diferença de maiúscula, espaço e acento"), cada um com a primeira âncora do desenho (em unidades do jogo) como posição.
Os apelidos em português de um lugar da demo vêm da tabela da C0, sem os nomes que já são pontos do Pedro (esses são o ponto, não a área).
"""
from __future__ import annotations

import csv
import json
import re
import unicodedata
from pathlib import Path

from metrics.lugares import rotulos, tabela_do_mapa, texto_do_lugar
from metrics.tactics import SEGUNDOS_DO_ROUND, funcoes_da_prancheta

RAIZ = Path(__file__).resolve().parent.parent
CALLOUTS = RAIZ / "data" / "reference" / "callouts_br.csv"
TABELA_C0 = RAIZ / "notas" / "investigacoes" / "2026-11-09-comandos-nomes-em-portugues.csv"

# A frase de cada pergunta e de cada opção (o leitor só preenche {os campos}).
TEXTOS = {
    "pergunta_quem": 'Quem faz "{trecho}"?',
    "pergunta_quem_lado": 'De qual time é "{ref}"?',
    "pergunta_quem_funcao": 'Não achei "{ref}" na tática. Quem é?',
    "pergunta_granada": 'Qual granada em "{trecho}"?',
    "pergunta_acao": 'Não entendi "{trecho}". O que o jogador faz?',
    "pergunta_qual": 'Qual "{nome}"?',
    "pergunta_onde": 'Em que lugar? ("{trecho}")',
    "pergunta_onde_desconhecido": 'Não achei o lugar "{trecho}" neste mapa. Qual destes?',
    "pergunta_quando": 'Quando começa "{trecho}"?',
    "pergunta_quando_segundos": "{n} segundos contados como?",
    "pergunta_horario_invalido": "O horário {horario} não existe no round.",
    "pergunta_espera": 'Quanto tempo espera em "{trecho}"?',
    "opcao_jogador": "{lado} {num}",
    "opcao_mover": "Mover até {lugar}",
    "opcao_segurar": "Segurar {lugar}",
    "opcao_relogio_n": "{n} s no relógio do round ({h})",
    "opcao_inicio_n": "{n} s depois do início do round",
    "granada_smoke": "Smoke", "granada_flash": "Flash", "granada_molotov": "Molotov", "granada_he": "HE",
    # a aba Comandos da prancheta (C2)
    "ui_aba": "Comandos",
    "ui_titulo": "Comandos",
    "ui_dica": "Escreva o que cada jogador faz. Nada muda no mapa até você aplicar.",
    "ui_exemplo": "Ex.: tr 2 joga smoke no B aos 1:30 e depois corre até o meio",
    "ui_rotulo": "O que acontece, em uma frase",
    "ui_entender": "Entender",
    "ui_aplicar": "Aplicar",
    "ui_corrigir": "Corrigir",
    "ui_confirmar": "Confirmar",
    "ui_entendi": "O que entendi",
    "ui_vazio": "Escreva uma frase e toque em Entender.",
    "ui_horario": "ex.: 1:20 ou 40 s do início",
    "ui_sem_nomes": "Os nomes de lugar deste mapa ainda não foram conferidos: valem os nomes do jogo, em inglês.",
    "ui_sem_nenhum": "Este mapa ainda não tem nomes de lugar conferidos, então não há onde mandar o jogador.",
    "ui_corrija": "Corrija a frase e toque em Entender de novo.",
    "ui_round": "Neste round as fichas têm o nome do jogador: ainda não dá para mandar por número (TR 2). Comece uma tática nova para usar os comandos.",
    "linha_lancar": "{quem} · {granada} em {alvo} · {quando}",
    "linha_mover": "{quem} · {modo} até {alvo} · {quando}",
    "linha_segurar": "{quem} · segura {alvo} · {quando}",
    "linha_esperar": "{quem} · espera {n} s · {quando}",
    "linha_incompleta": "{quem} · ainda falta dizer o que faz",
    "aviso_origem": "Ainda não busco o arremesso real: a granada sai de onde o jogador está nesse horário.",
    "chegada_real_pontos": "chega entre {h1} e {h2}, por volta de {h} (tempo real entre os pontos: {n} casos em {p} partidas)",
    "chegada_real_areas": "chega entre {h1} e {h2}, por volta de {h} (tempo real entre as áreas da demo: {n} casos em {p} partidas)",
    "chegada_fator": "chega por volta de {h} (estimado: linha reta corrigida pelo desvio medido no mapa, {f}×)",
    "chegada_reta": "chega por volta de {h} (estimado: linha reta, sem correção: poucos dados neste mapa)",
    "ui_carregando_tempos": "Carregando os tempos reais de corrida…",
    "aviso_tempos_falhou": "Os tempos reais não carregaram: os tempos abaixo são estimados em linha reta. Recarregue a página para tentar de novo.",
    "q_relogio": "aos {h}", "q_inicio": "aos {n} s do início", "q_depois": "depois", "q_junto": "ao mesmo tempo", "q_sem": "sem horário",
    "quem_vazio": "quem?", "onde_vazio": "onde?",
    "aviso_duracao_imposta": "Você pediu {n} s de corrida. O site não confere esse tempo: usa a corrida estimada.",
    "aviso_ordem_invertida": "O horário desta ação vem antes do da anterior, mas a frase diz “depois”.",
    "aviso_depende_do_deslocamento": "O horário desta ação é fixo: não espera o jogador chegar.",
    "aviso_palavra_sobrando": "Não entendi: {trechos}.",
    "pergunta_chegada": "{quem} muda de andar para ir a {alvo}. Não estimei o tempo por causa da troca de andar. Quando chega?",
    "ok_aplicado": "Aplicado ({n} operações). Desfazer volta tudo de uma vez.",
    "erro_sem_peca": "{quem} ainda não está no mapa. Ponha a ficha no mapa e aplique de novo.",
    "erro_sem_horario": "{quem}: não sei de que horário esta ação parte. Corrija a frase.",
    "erro_inicio": "{quem}: a frase põe uma ação depois de outra, mas a anterior não tem horário. Corrija a frase.",
}


def _norma(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn"))


def _pontos(mapa: str, so_conferidos: bool) -> list[dict]:
    saida = []
    for r in csv.DictReader(open(CALLOUTS, encoding="utf-8-sig", newline=""), delimiter=";"):
        if r["mapa"] != mapa or (so_conferidos and r["conferido"] != "sim"):
            continue
        lugar = r["lugar_da_demo"].replace(" (mais perto)", "")
        saida.append({"id": f"{mapa}:{len(saida)}", "nome": r["nome"], "apelidos": [a.strip() for a in r["apelidos"].split(" / ") if a.strip()],
                      "qualificacao": r["qualificacao"], "vertical": r["posicao_vertical"], "tipo": r["tipo"], "x": int(r["x"]), "y": int(r["y"]),
                      "andar": r["andar"], "lugar": "" if lugar.startswith("(") else texto_do_lugar(lugar) if lugar else "", "conferido": r["conferido"] == "sim"})
    return saida


def _areas(mapa: str, pontos: list[dict]) -> list[dict]:
    tab = tabela_do_mapa(mapa)
    if not tab:
        return []
    radar = json.loads((RAIZ / "assets" / "radars" / f"{mapa}.json").read_text(encoding="utf-8"))
    esc, ox, oy = radar["scale_px_per_unit"], radar["origin_x"], radar["origin_y"]
    # nomes de TODO ponto do Pedro do mapa (conferido ou não): um nome de ponto não conferido não pode entrar pela tabela de apelidos das áreas
    nomes_de_ponto = {_norma(n) for p in _pontos(mapa, False) for n in [p["nome"], p["nome"] + p["qualificacao"]] + p["apelidos"]}
    apelidos: dict[str, list[str]] = {}
    for r in csv.DictReader(open(TABELA_C0, encoding="utf-8-sig", newline=""), delimiter=";"):
        if r["mapa"] == mapa and r["apelido_br"] not in ("", "?"):
            apelidos[r["nome_do_jogo"]] = [a.strip() for a in r["apelido_br"].split(" / ") if a.strip() and _norma(a) not in nomes_de_ponto]
    areas = []
    for andar, lugares in enumerate(rotulos(tab)):
        for ix, pts in lugares:
            if not pts or any(a["nome"] == tab["nomes"][ix] for a in areas):
                continue
            nome = tab["nomes"][ix]
            areas.append({"nome": nome, "texto": texto_do_lugar(nome), "apelidos": apelidos.get(nome, []), "x": round(ox + pts[0][0] / esc), "y": round(oy - pts[0][1] / esc),
                          "andar": "baixo" if andar else ("cima" if len(tab["andares"]) > 1 else "único")})
    return areas


def jogadores_padrao() -> list[dict]:
    return [{"lado": lado, "num": n} for lado in ("tr", "ct") for n in range(1, 6)]


def contexto(mapa: str, jogadores: list[dict] | None = None, so_conferidos: bool = False) -> dict:
    pontos = _pontos(mapa, so_conferidos)
    return {"mapa": mapa, "pontos": pontos, "areas": _areas(mapa, pontos), "jogadores": jogadores or jogadores_padrao(), "funcoes": funcoes_da_prancheta(),
            "segundos_do_round": int(SEGUNDOS_DO_ROUND), "textos": TEXTOS}
