"""Divide o CLAUDE.md antigo em uma nota por decisão (reestruturação, 2026-10-02).

Rodado UMA vez. Fica no repositório como registro de como as notas nasceram: o
texto de cada decisão foi copiado INTEIRO do CLAUDE.md da revisão `ANTIGO`; o
que este script acrescenta é o cabeçalho (ID, título, status, data, resumo) e,
onde o texto antigo afirma algo que deixou de valer, o bloco "O que vale hoje".

A conferência de que nada se perdeu é `scripts/confere_claude_md.py`.

Uso:
    py -3.12 -m scripts.divide_claude_md
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ANTIGO = "f923fe9"                       # o main antes da reestruturação
NOTAS = RAIZ / "notas"
CITAVEIS = "`data/processed/numeros_citaveis.json`"

# ID -> (slug, status, resumo de 1 a 2 linhas, o que vale hoje ou None)
V = "vigente"
META: dict[str, tuple[str, str, str, str | None]] = {
    "1": ("peek-hold-liquido", V, "Peek ou hold pelo deslocamento LÍQUIDO; jiggle (sair e voltar) é hold.", None),
    "2": ("peek-hold-posicao", V, "Peek/hold usa a posição medida, não a flag `is_scoped`.", None),
    "3": ("awp-no-trade", V, "Tiro de AWP que erra sem custar a vida é `no_trade`, fora da conversão.", None),
    "4": ("crosshair-contato", V, "Crosshair placement só é cobrado nas amostras antes de contato real (1 s).", None),
    "5": ("angulos-por-moda", V, "Ângulos de pré-fire saem dos dados por moda circular; nunca bins fixos.", None),
    "6": ("desvio-de-setup", V, "Desvio de setup é contra o padrão do próprio time, não contra um setup certo.", None),
    "7": ("cluster-por-round", V, "Clustering é por (jogador, round), não por jogador.", None),
    "7a": ("perfil-por-jogador", V, "O perfil por jogador é a leitura; taxa sempre com bruto, referência e marca de amostra fraca.", None),
    "7c": ("longe-do-time", V, "\"Longe do time\" exige piso absoluto e nenhum companheiro no raio de apoio.", None),
    "7b": ("features-comportamento", V, "Features do clustering são só comportamento; resultado (kills, dano) fica fora.",
           "A silhueta de 0,216 e os 56% são do corpus de 9 partidas. Hoje, com 52: silhueta 0,195 "
           "(`data/global_clusters/model_meta.json`)."),
    "7d": ("duas-camadas", V, "Função estrutural (o trabalho) e traço comportamental (como executa) não se misturam.",
           "O texto diz que `structural_roles` substituiu o `player_roles.py`. Os dois existem hoje: "
           "`structural_roles` dá a função por lado e round; `player_roles` dá os rótulos da aba Estilos "
           "(`TRAIT_SPECS`, decisão 31) e o \"AWPer do time\" (decisão 28)."),
    "7h": ("trader", V, "Trader é o segundo homem do entry; proximidade sozinha fica abaixo do piso.", None),
    "7e": ("funcoes-de-ct", V, "Âncora, rotativo e coringa saem de dispersão do início × distância ao contato.", None),
    "7f": ("posicao-de-setup", V, "Posição inicial é a de setup (10 s depois do freeze), não o tick do freeze.", None),
    "7g": ("igl-manual", V, "IGL nunca é atribuído automaticamente; vem de `roles_manual.json`.", None),
    "8": ("kmeans-nao-nomeia", V, "O KMeans não nomeia grupos; o nome é do Pedro (`cluster_names.json`).", None),
    "8a": ("tempo-desde-o-freeze", V, "O tempo do timeline conta do fim do freeze; negativo é erro.", None),
    "8b": ("mortes-do-freeze", V, "Mortes e eventos do freeze time e do intervalo não pertencem a round nenhum.", None),
    "8f": ("round-de-faca", V, "Round de faca sai no parse e os rounds são renumerados.", None),
    "8g": ("kast-morte-vingada", V, "O T do KAST é de quem teve a morte vingada (janela de 5 s).",
           "As contagens de KAST idêntico citadas no texto (24 de 30, 230 de 310) são das épocas em que "
           f"foram medidas. A atual está em {CITAVEIS} (bloco `escada`)."),
    "8h": ("cegueira-reconstruida", V, "Cegueira é reconstruída de `flash_duration` nas demos sem `player_blind`.", None),
    "8i": ("economia-do-corpus", V, "Economia do rating estimada no corpus, por arma mais cara e colete.", None),
    "8j": ("dano-no-mesmo-tick", V, "`dmg_health_real` é recalculado: vários acertos no tick não passam da vida.", None),
    "8c": ("sem-atacante", V, "Sem atacante o texto não nomeia ninguém; abertura é o primeiro duelo ganho.", None),
    "8d": ("navegacao-por-tick", V, "O replay navega por tick; fora da janela exportada, não navega.", None),
    "8e": ("dinheiro", V, "Dinheiro só por `format_money` (`3.750$`).", None),
    "9": ("convencao-de-angulos", V, "Pitch positivo olha para baixo; o teste roda a convenção invertida como controle.",
          f"Os 1,76° e 6,52° são do corpus de 9 partidas. O valor atual está em {CITAVEIS} "
          "(bloco `convencao_de_angulos`)."),
    "10": ("paleta", V, "Paleta validada para daltonismo e contraste; não trocar cor sem `valida_paleta`.", None),
    "11": ("kmeans-global", V, "O KMeans é ajustado uma vez no corpus (`global_model.json`), não por partida.", None),
    "12": ("ancora-e-lurk-por-area", V, "Âncora e lurk são medidos por área do mapa (A/Mid/B), não por distância.", None),
    "13": ("entry-e-acao", V, "Entry é quem dá o primeiro contato do time, não quem chega cedo.", None),
    "15": ("carrega-piano", V, "Carrega piano é produto de esforço por benefício, em três formas.", None),
    "15a": ("eixo-piano-baiter", V, "Carrega piano e baiter são as pontas de um eixo; rótulo só além de ±0,5.", None),
    "15c": ("traco-dentro-da-funcao", V, "Traço comportamental é comparado dentro da função estrutural.", None),
    "15d": ("repick", V, "Repick é jiggle mais evento no ângulo; o desfecho é campo à parte.", None),
    "15e": ("eixo-por-populacao", V, "Cada braço do eixo piano/baiter é comparado com a população da função.", None),
    "15f": ("funcao-do-round-no-pipeline", V, "O pipeline passa a função do round aos papéis comportamentais (regressão corrigida).", None),
    "15b": ("repick-por-briga", V, "Repick classifica cada briga; a junção inclui o tick da briga.", None),
    "16": ("escala-dos-papeis", V, "A escala dos papéis é do corpus (`archetype_reference.json`).", None),
    "17": ("empate-no-contato", V, "Empate no primeiro contato não é abertura de ninguém.", None),
    "18": ("frases-em-python", V, "Frases dos cards saem do Python; papel sem sustentação devolve vazio.", None),
    "14": ("spawn-fora-da-particao", V, "Spawn não é área de jogo; passagem rápida não conta como rotação.", None),
    "19": ("round-decisivo", V, "Round decisivo é a maior variação da probabilidade de vitória (modelo neutro 0,5).", None),
    "19e": ("prorrogacao", V, "A prorrogação é modelada: o alvo sobe 4 a cada uma, até 5.", None),
    "19a": ("decisivo-e-impressionante", V, "Decisivo e impressionante são dois cards; o segundo tem pesos expostos.", None),
    "19b": ("sem-round-decisivo", V, "Partida sem round decisivo é resultado; piso de 1,5× o round mais barato.", None),
    "19c": ("formato-pela-troca-de-lado", V, "MR12 ou MR15 sai da troca de lado na demo.", None),
    "19d": ("economia-e-leitura", V, "Economia é leitura ao lado do round decisivo, nunca peso.", None),
    "20": ("tres-blocos", V, "A aba de leitura tem três blocos fixos; o MVP mostra os componentes.", None),
    "20a": ("destaque-negativo", V, "Destaque negativo só com número e referência.", None),
    "20b": ("bottom-frag", V, "Bottom frag exige distância destacada (MAD); mochila exige vitória.", None),
    "20d": ("empate-do-destaque", V, "No empate do topo vence o destaque negativo.", None),
    "20c": ("comparabilidade", V, "Pontuação de função é \"quanto acima do normal\"; concentração ponderada.", None),
    "21": ("ancoragem", "substituída por 21c", "Soltura por ancoragem geométrica.",
           "Onde a demo traz `grenade_thrown`, o tick é o do evento (decisão 21c) e a ancoragem vira validação. "
           "A ancoragem continua sendo a FONTE do tick só nas demos sem o evento (FACEIT), e a investigação de "
           "2026-10-02 mostrou que ali ela acerta o tick em 41% "
           "([investigação](../investigacoes/2026-10-02-faceit-tick-pelo-projetil.md))."),
    "21c": ("tick-oficial", V, "Com `grenade_thrown`, o tick do evento é a soltura; postura pela altura de saída.",
            "O texto diz que só a match_23 tem o `.dem`. Hoje são 13 partidas com a demo e com as tabelas da "
            "rota B no interim (`RECUPERACAO_DEMOS.md`)."),
    "21a": ("arremesso", V, "Botão, \"no ar\" e postura: lidos da demo onde há `.dem`, inferidos pela rotina do jogo onde não há.", None),
    "21b": ("console-no-jogo", V, "O comando de console só é dado como exato depois de conferido no jogo.", None),
    "22": ("rating-proprio", V, "O rating é implementação própria da metodologia do Rating 3.0; nunca \"o da HLTV\".",
           "O texto diz que os pesos são provisórios. Estão AJUSTADOS por regressão contra os ratings oficiais "
           "(`metrics/rating_weights.json`, decisão 22l); `PESOS_PROVISORIOS` é só o plano B sem o arquivo."),
    "22a": ("swing-parametrico", V, "O Round Swing usa regressão logística, não contagem por estado.",
            "AUC 0,897 e Brier 0,129 são do corpus de 9 partidas. O modelo atual está em "
            "`metrics/rating_reference.json` (`modelo_de_round`)."),
    "22b": ("swing-por-desvio", V, "O Round Swing é centrado em 1,00 e escalado pelo desvio.",
            "A média negativa (-0,043) vinha da regra de corte do round perdido, retirada na decisão 22k "
            "(média hoje -0,01). A normalização por desvio continua."),
    "22c": ("faceit-nao-calibra", V, "Partidas de FACEIT não servem para calibrar contra a HLTV.",
            "\"As 9 demos do corpus\" era o corpus inteiro na época. Hoje são 52 partidas, 43 profissionais; "
            "a regra vale para as 9 de FACEIT."),
    "22e": ("rating-na-aba", V, "O rating vai na aba Jogadores, com o modelo de round global.", None),
    "22f": ("swing-soma-zero", V, "O Swing soma zero por evento e inclui o fim do round.",
            "A regra do round perdido citada no fim foi retirada (decisão 22k); a média hoje é -0,01."),
    "22g": ("escada", V, "Escada de validação: contagem exata antes de olhar o rating.",
            f"As contagens atuais estão em {CITAVEIS} (bloco `escada`)."),
    "22l": ("detalhes-do-rating", V, "Escala alinhada, cálculo por lado, kill assistida e morte trocada.",
            f"O erro e a correlação atuais estão em {CITAVEIS} (bloco `rating`)."),
    "22k": ("swing-sem-corte", V, "O Swing é variação de probabilidade pura; soma zero é teste de integridade.",
            "A pendência do fim (média ~1,105 e teste `xfail`) foi resolvida pela recalibração da decisão 22l: "
            "o teste não tem mais a marca, e a média é 1,0720 contra 1,0726 da HLTV (decisão 26)."),
    "22j": ("detailed-stats", V, "Degrau 4: aberturas, multi-kills e headshots exatos; clutch é 1vX com X ≥ 1.",
            f"As contagens atuais estão em {CITAVEIS} (bloco `escada`)."),
    "22h": ("swing-oficial-soma-zero", V, "O Swing oficial soma zero; as exceções são mortes sem matador inimigo.",
            "A correção que \"esperava a decisão do Pedro\" foi feita na decisão 22k (sem a regra de corte)."),
    "22i": ("media-ou-desvio", V, "Dividir pela média ou padronizar dá o mesmo rating com pesos ajustados.",
            "O defeito de escala citado (calibração por partida, site pelo corpus) foi alinhado na decisão 22l."),
    "25": ("identidade-steamid", V, "Identidade é o steamid; o nome é rótulo (`metrics/identidade.py`).", None),
    "26": ("invariantes", V, "Dez invariantes sobre o corpus inteiro (`test_invariantes_corpus.py`).", None),
    "27": ("versoes", V, "Cada partida grava a versão do parser (lida do interim) e das métricas, e o commit.",
           "\"51 das 52 sem o .dem\" é de 2026-09-20. Hoje 13 partidas têm a demo e o parser 2; 39 não têm "
           "(`py -3.12 -m scripts.manifest --versoes`)."),
    "28": ("determinismo", V, "Processamento determinístico: `group_by`/`unique` com ordem; empate de função por 1 round.", None),
    "29": ("lurker", V, "Lurker: sem os rounds de AWP, relativo à função, mínimo de 8 rounds.",
           "O piso de 1,5× foi trocado por 1,284 (decisão 31)."),
    "30": ("tres-niveis", V, "Página da partida: números só dela; régua anônima do corpus; sem seletor.", None),
    "23": ("anotacao", V, "Anotação em coordenada de jogo; um ponto de redimensionamento; sem texto no template.", None),
    "24": ("saida-fora-do-git", V, "Saída gerada (`docs/`) não vai para o repositório; o Pages é artefato do CI.", None),
    "31": ("pisos-de-funcao", V, "Registro dos pisos de função e de onde veio cada um.", None),
    "32": ("prancheta", V, "A tática é um log de operações; desfazer é `anula`/`reativa`; interação por máquina de estados.", None),
    "33": ("map-core", V, "Um núcleo só para o mapa (`map_core.js`); extração aceita por pixel idêntico.", None),
    "34": ("direcao-do-olhar", V, "θ = −yaw; ângulo interpola linear pelo caminho curto.", None),
    "35": ("reproducao-pura", V, "A reprodução da prancheta é função pura do tempo.", None),
    "36": ("preservacao-de-dados", V, "Nenhum `.dem`, interim ou backup é apagado sem lista confirmada e cópia por sha256.", None),
    "37": ("pagina-e-dado", V, "Número de corpus vem de `numeros_citaveis.json`; texto do dado passa por `esc()`; CI testa antes de publicar.", None),
}

# As narrativas da 21a viram investigações; a nota fica com a regra e os links.
INVESTIGACOES_21A = [
    ("**Investigação do grupo de ~784 u/s", "2026-09-27-grupo-de-784-e-jump-throw",
     "O grupo de ~784 u/s e o jump-throw",
     "De onde vem o grupo extra de velocidade: a soltura no ar herda a velocidade vertical da decolagem menos 0,1 s "
     "de gravidade, não a do instante."),
    ("**Rota A aprovada e PARADA nas metas", "2026-09-27-rota-a",
     "Rota A: inferir botão, \"no ar\" e postura pela rotina do jogo",
     "Do protótipo ao main: metas, a cauda vertical, a obstrução refutada, a janela do jump-throw, a definição de "
     "piora, a validação fora da amostra, a guarda do voo e o estado final."),
    ("**ROTA B (2026-09-28)", "2026-09-28-rota-b",
     "Rota B: a verdade do arremesso lida da demo",
     "O parser 2 grava a força, a velocidade e o ponto de nascimento de cada granada e o movimento do jogador; "
     "lido contra inferido é o teste permanente da rota A."),
    ("**INVESTIGAÇÃO FACEIT (2026-10-02)", "2026-10-02-faceit-tick-pelo-projetil",
     "FACEIT: o tick da soltura pelo projétil",
     "Sem `grenade_thrown`, a ancoragem acerta o tick em 41%; o evento é reconstruível do projétil. Regra pronta "
     "e desligada à espera de aprovação."),
]

REGRA_21A = """## Regra em vigor

- **Fonte por campo.** Botão, postura, "no ar" e ponto de saída de cada arremesso declaram a fonte:
  `lido` (a demo grava, nas partidas com `.dem` e parser 2) ou `inferido` (a rotina do jogo medida no
  gabarito, nas demais). Nunca se misturam em silêncio.
- **Inferido (rota A).** Velocidade relativa ao jogador com herança 1,25; três botões (202,5 / 438,7 /
  675,0 u/s); pitch remapeado por trechos; no pulo, vz fixa de 6 a 13 ticks depois da decolagem e vz real
  de 19 em diante; estado vertical ambíguo, janelas sem gabarito, vetor incoerente com o voo e velocidade
  fora da tolerância ficam NEUTROS, com o motivo. Tolerância, guarda do voo e faixa de postura são
  calculadas do gabarito (`metrics/gabarito_constantes.json`), nunca digitadas.
- **Lido (rota B).** A força é a da granada que saiu (último tick gravado antes do nascimento do
  projétil), nunca a da arma no tick da soltura. Botão = o mais próximo da força lida; agachamento
  parcial não é afirmado.
- **Piora.** Um arremesso que tinha botão dentro da tolerância e troca de botão, ou fica neutro sem
  regra explícita. Mudança na biblioteca só entra com piora 0 (`py -3.12 -m pesquisa.piora_rota_a`).
- **Teste permanente.** Lido contra inferido nas partidas com demo, nas metas da rota A
  (`tests/test_verdade_do_arremesso.py`).
- **Demos sem `grenade_thrown` (FACEIT).** O tick ainda vem da ancoragem; a regra do tick pelo projétil
  está pronta e DESLIGADA (`TICK_PELO_PROJETIL_SEM_EVENTO`), à espera do Pedro.

Os números atuais (metas dentro e fora da amostra, cobertura) estão em
`data/processed/numeros_citaveis.json`, bloco `arremessos`.

## Como se chegou aqui

"""

CABECALHO_GERAL = {
    "contexto": ("Contexto do projeto, ambiente, estrutura e convenções",
                 "As seções gerais do CLAUDE.md como estavam antes da reestruturação de 2026-10-02. A versão "
                 "atual e curta está no `CLAUDE.md`. Onde este texto cita contagens (testes, partidas), valem "
                 "as de `data/processed/numeros_citaveis.json`."),
    "calibracao": ("Pontos de calibração que pertencem ao Pedro",
                   "A lista completa, com o histórico de cada ponto. O `CLAUDE.md` traz a lista curta e aponta "
                   "para cá."),
    "limitacoes": ("Limitações conhecidas e como validar",
                   "Como estavam no CLAUDE.md antes da reestruturação. **O que vale hoje:** o corpus tem 52 "
                   "partidas (não 9) e a silhueta do agrupamento é 0,195 "
                   "(`data/global_clusters/model_meta.json`); a contagem de testes está em "
                   "`data/processed/numeros_citaveis.json`. As demos disponíveis hoje são 13, de partidas "
                   "profissionais."),
}


def antigo() -> str:
    r = subprocess.run(["git", "show", f"{ANTIGO}:CLAUDE.md"], capture_output=True, cwd=RAIZ, check=True)
    return r.stdout.decode("utf-8").replace("\r\n", "\n")


def blocos(texto: str) -> tuple[dict[str, str], dict[str, str]]:
    """({ID: bloco inteiro da decisão}, {seção geral: texto})."""
    linhas = texto.split("\n")
    ini_dec = next(i for i, l in enumerate(linhas) if l.startswith("## Decisões de design"))
    ini_cal = next(i for i, l in enumerate(linhas) if l.startswith("## Pontos de calibração"))
    ini_lim = next(i for i, l in enumerate(linhas) if l.startswith("## Limitações conhecidas"))
    decs: dict[str, list[str]] = {}
    atual = None
    preambulo = []
    for l in linhas[ini_dec + 1:ini_cal]:
        m = re.match(r"^(\d+[a-z]?)\. \*\*", l)
        if m:
            atual = m.group(1)
            decs[atual] = []
        if atual is None:
            preambulo.append(l)
        else:
            decs[atual].append(l)
    gerais = {
        "contexto": "\n".join(linhas[:ini_dec + 1] + preambulo).strip("\n"),
        "calibracao": "\n".join(linhas[ini_cal:ini_lim]).strip("\n"),
        "limitacoes": "\n".join(linhas[ini_lim:]).strip("\n"),
    }
    return {k: "\n".join(v).strip("\n") for k, v in decs.items()}, gerais


def titulo_de(bloco: str) -> str:
    m = re.match(r"^\d+[a-z]?\. \*\*(.+?)\*\*", bloco, re.S)
    t = re.sub(r"\s+", " ", m.group(1)).strip() if m else bloco.split("\n")[0]
    return t.rstrip(".:")


def data_de(ident: str, bloco: str) -> str:
    """A primeira data escrita no bloco; sem data, o dia em que a decisão entrou no arquivo."""
    m = re.search(r"20\d\d-\d\d-\d\d", bloco)
    if m:
        return m.group(0)
    cabeca = bloco.split("\n")[0][:60]
    r = subprocess.run(["git", "log", "--format=%ad", "--date=short", "-S", cabeca, ANTIGO, "--", "CLAUDE.md"],
                       capture_output=True, text=True, cwd=RAIZ, encoding="utf-8")
    datas = [d for d in r.stdout.split("\n") if d]
    return (datas[-1] + " (entrada no arquivo; o texto não traz data)") if datas else "sem data registrada"


def nota(ident: str, bloco: str) -> str:
    slug, status, resumo, hoje = META[ident]
    partes = [f"# Decisão {ident}: {titulo_de(bloco)}", "",
              f"- **ID:** {ident}", f"- **Status:** {status}", f"- **Data:** {data_de(ident, bloco)}",
              f"- **Resumo:** {resumo}", ""]
    if hoje:
        partes += ["## O que vale hoje", "", hoje, ""]
    if ident == "21a":
        corte = bloco.index(INVESTIGACOES_21A[0][0])
        partes += [REGRA_21A.rstrip("\n"), ""]
        partes += [f"- [{t}](../investigacoes/{s}.md): {r}" for _, s, t, r in INVESTIGACOES_21A]
        partes += ["", "## Texto original (a parte que define a regra de base)", "", bloco[:corte].rstrip()]
    else:
        partes += ["## Texto", "", bloco]
    return "\n".join(partes).rstrip("\n") + "\n"


def investigacoes(bloco: str) -> dict[str, str]:
    out = {}
    cortes = [bloco.index(m[0]) for m in INVESTIGACOES_21A] + [len(bloco)]
    for k, (_, slug, titulo, resumo) in enumerate(INVESTIGACOES_21A):
        corpo = bloco[cortes[k]:cortes[k + 1]].rstrip()
        data = slug[:10]
        out[slug] = "\n".join([
            f"# {titulo}", "", f"- **Data:** {data}", "- **Decisão:** [21a](../decisoes/21a-arremesso.md)",
            f"- **Resumo:** {resumo}", "",
            "> Narrativa da investigação, como foi registrada na época. A regra que vale hoje está na decisão.",
            "", corpo, ""])
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    decs, gerais = blocos(antigo())
    faltam = sorted(set(decs) - set(META))
    sobram = sorted(set(META) - set(decs))
    assert not faltam and not sobram, (faltam, sobram)
    (NOTAS / "decisoes").mkdir(parents=True, exist_ok=True)
    (NOTAS / "investigacoes").mkdir(parents=True, exist_ok=True)
    for ident, bloco in decs.items():
        (NOTAS / "decisoes" / f"{ident}-{META[ident][0]}.md").write_text(nota(ident, bloco), encoding="utf-8")
    for slug, texto in investigacoes(decs["21a"]).items():
        (NOTAS / "investigacoes" / f"{slug}.md").write_text(texto, encoding="utf-8")
    for nome, (titulo, intro) in CABECALHO_GERAL.items():
        (NOTAS / f"{nome}.md").write_text(f"# {titulo}\n\n> {intro}\n\n{gerais[nome]}\n", encoding="utf-8")
    # índice das decisões, na ordem numérica
    def chave(i):
        m = re.match(r"(\d+)([a-z]?)", i)
        return (int(m.group(1)), m.group(2))
    linhas = ["# Decisões", "", "Uma nota por decisão. O `CLAUDE.md` traz a lista curta das que estão em vigor.", "",
              "| ID | Status | Resumo |", "|---|---|---|"]
    for i in sorted(decs, key=chave):
        slug, status, resumo, _ = META[i]
        linhas.append(f"| [{i}]({i}-{slug}.md) | {status} | {resumo} |")
    (NOTAS / "decisoes" / "README.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print(f"{len(decs)} decisões, {len(INVESTIGACOES_21A)} investigações, {len(CABECALHO_GERAL)} notas gerais")


if __name__ == "__main__":
    main()
