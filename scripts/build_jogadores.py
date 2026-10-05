"""Gera a página jogadores.html: a visão agregada por jogador no CORPUS (fase 7, item 7.3).

É o "lugar separado e explícito" da decisão 30: nada daqui entra na página de
uma partida. Autocontida, abre como arquivo local; os dados e todo o texto vêm
do Python (metrics/agregado_jogadores.py e os textos abaixo).

Uso:
    py -3.12 -m scripts.build_jogadores            # grava dashboard/web/jogadores_gerada.html
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

from metrics.agregado_jogadores import para_a_pagina
from metrics.constantes import NOME_DO_MAPA
from scripts.json_em_script import js
from scripts.meta_da_pagina import meta_tags

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "dashboard" / "web"
ARQUIVO = "jogadores.html"

TITULO = "Jogadores no corpus"
TEXTOS = {
    "titulo": TITULO,
    "aviso": ("Visão do CORPUS, não de uma partida: cada número soma todas as partidas processadas do jogador. "
              "A página de uma partida mostra só os números dela (regra dos três níveis) e não traz nada daqui."),
    "volta_inicio": "← Início",
    "volta_partidas": "Partidas",
    "busca": "buscar jogador",
    "ajuda_selecao": "Marque até três jogadores para comparar lado a lado.",
    "rotulo_mapa": "mapa",
    "rotulo_lado": "lado",
    "rotulo_media": "comparar com",
    "todos_os_mapas": "todos os mapas",
    "lados": [["", "os dois lados"], ["ct", "só CT"], ["t", "só TR"]],
    "opcoes_media": [["funcao", "a média da função de cada um"], ["corpus", "a média do corpus"]],
    "legenda_media": "média de comparação",
    "partida": "partida",
    "partidas": "partidas",
    "peso_do_jogador": "puxado para a média quando há poucas partidas",
    "sem_separacao": "o corpus não separa jogadores nesta métrica: o número é a média",
    "titulo_barra": ("bruto {bruto} em {partidas} partidas; encolhido {encolhido} (peso do jogador {peso}); "
                     "média de comparação {media}"),
    "nada_selecionado": "Nenhum jogador marcado.",
    "como_ler": ("Como ler: a barra é o número do jogador puxado para a média da função dele, com peso "
                 "partidas / (partidas + k) -- o k de cada métrica é estimado no corpus (variação de uma "
                 "partida para outra do mesmo jogador contra a variação entre jogadores). O traço fino é o "
                 "número bruto, a linha horizontal é o intervalo de 95% por reamostragem das partidas dele e a "
                 "linha cinza vertical é a média de comparação. Nenhum gráfico de radar: a ordem dos eixos "
                 "muda a impressão."),
    "nomes_dos_mapas": NOME_DO_MAPA,
}


def build_html(site: str | None = None) -> str:
    dados = para_a_pagina()
    return ((WEB / "jogadores.html").read_text(encoding="utf-8")
            .replace("<!--__TITULO__-->", html.escape(TITULO))
            .replace("<!--__META__-->", meta_tags(TITULO, TEXTOS["aviso"], site, ARQUIVO))
            .replace("/*__MAP_CORE__*/", (WEB / "map_core.js").read_text(encoding="utf-8"))
            .replace("/*__DADOS__*/null", js(dados))
            .replace("/*__TEXTOS__*/null", js(TEXTOS)))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    saida = WEB / "jogadores_gerada.html"
    texto = build_html()
    saida.write_text(texto, encoding="utf-8")
    print(f"{saida.relative_to(RAIZ).as_posix()} ({len(texto.encode('utf-8')) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
