"""
Formatação dos números que aparecem na interface.

Existe para haver UM lugar onde se decide como um valor é escrito. O gatilho foi
dinheiro: a autópsia mostrava "equipamento médio de 960", sem símbolo e sem
separador, e o conserto óbvio (espalhar um `$` em f-string por aí) garante que
daqui a três telas alguém escreva de outro jeito.
"""
from __future__ import annotations

# Separador de milhar do padrão brasileiro. O símbolo vai DEPOIS do número, como
# se fala em CS ("comprei de 3.750") e como o próprio jogo mostra no HUD.
SEPARADOR_MILHAR = "."


def format_money(valor: float | int | None) -> str:
    """Valor de dinheiro do CS2: `3.750$`.

    Devolve "—" para ausente. Zero é um valor legítimo (round de pistola sem
    compra) e sai como `0$`, não como ausente — a diferença entre "não comprou"
    e "não medi" é justamente o que um traço esconderia.
    """
    if valor is None:
        return "—"
    inteiro = int(round(float(valor)))
    negativo = inteiro < 0
    texto = f"{abs(inteiro):,}".replace(",", SEPARADOR_MILHAR)
    return ("-" if negativo else "") + texto + "$"


def format_clock(segundos: float | int | None) -> str:
    """Tempo decorrido no formato `1:09`.

    Segundos crus com sinal ("-69,0s") não dizem de onde o tempo é contado e
    escondem que o número não deveria existir. O relógio força a pergunta:
    1:09 de quê? A resposta está declarada em metrics/round_breakdown.py — a
    origem é o fim do freeze time.

    Negativo é ERRO, não caso a tratar: com a origem no fim do freeze time, um
    evento antes disso não pertence ao round. Quem chama deve barrar antes.
    """
    if segundos is None:
        return "—"
    total = int(round(float(segundos)))
    if total < 0:
        raise ValueError(
            f"tempo negativo no timeline ({total}s): a origem é o fim do freeze time, "
            "então evento anterior a ela não pertence ao round. Ver "
            "pesquisa/debug_timeline.py."
        )
    return f"{total // 60}:{total % 60:02d}"


def format_pct(fracao: float | None) -> str:
    """Probabilidade como percentual inteiro: `62%`.

    Inteiro de propósito. O modelo de probabilidade de vitória supõe rounds
    independentes e p = 0,5 por round (ver metrics/win_probability.py); escrever
    "62,4%" daria à saída uma precisão que a suposição não sustenta.
    """
    if fracao is None:
        return "—"
    return f"{round(float(fracao) * 100)}%"


def format_pct_par(a: float | None, b: float | None) -> tuple[str, str]:
    """Duas porcentagens que a frase COMPARA ("moveu X, abaixo dos Y").

    Inteiras, como `format_pct`, a não ser que o arredondamento as iguale: aí
    as duas ganham uma casa, senão a frase diz "moveu 12%, abaixo dos 12%"
    (auditoria 5.2; match_11 e match_23).
    """
    if a is None or b is None or round(float(a) * 100) != round(float(b) * 100):
        return format_pct(a), format_pct(b)
    def uma_casa(x: float) -> str:
        return f"{float(x) * 100:.1f}".replace(".", ",") + "%"
    return uma_casa(a), uma_casa(b)
