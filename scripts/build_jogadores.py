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
    "aviso": ("Esta é a visão do corpus, não de uma partida: cada número soma todas as partidas processadas do "
              "jogador. A página de uma partida mostra só os números dela (regra dos três níveis) e não traz nada daqui."),
    "rotulo_mapa": "Mapa",
    "rotulo_lado": "Lado",
    "rotulo_media": "Comparar com",
    "rotulo_jogadores": "Jogadores (até 3)",
    "rotulo_adiciona": "Adicionar jogador",
    "escolher": "— escolher —",
    "maximo": "Máximo de 3",
    "tirar": "Tirar {nome}",
    "todos_os_mapas": "Todos os mapas",
    "lados": [["", "CT e TR"], ["ct", "Só CT"], ["t", "Só TR"]],
    "opcoes_media": [["funcao", "a média da função de cada um"], ["corpus", "a média do corpus"]],
    "legenda_media": "linha tracejada: média de comparação (a da função de cada jogador, ou a do corpus)",
    "partida": "partida",
    "partidas": "partidas",
    "em_rounds": "em {rounds} rounds",
    "de": "{n} de {d}",
    "amostra_pequena": "amostra pequena",
    "peso_do_jogador": "puxado para a média quando há poucas partidas",
    "sem_separacao": "o corpus não separa jogadores nesta métrica: o número é a média",
    "titulo_barra": ("bruto {bruto} em {partidas} partidas; encolhido {encolhido} (peso do jogador {peso}); "
                     "intervalo de {inferior} a {superior}; média de comparação {media}"),
    "nada_selecionado": "Nenhum jogador escolhido.",
    "vazio": "Nenhum round desses jogadores com esse filtro.",
    "como_ler": ("Como ler: o ponto é o número do jogador puxado para a média da função dele, com peso "
                 "partidas / (partidas + k) -- o k de cada métrica é estimado no corpus (variação de uma "
                 "partida para outra do mesmo jogador contra a variação entre jogadores). A faixa é o intervalo "
                 "de 95% por reamostragem das partidas dele (não precisa ser simétrica em volta do ponto) e a "
                 "linha tracejada é a média de comparação. À direita, o valor e o bruto. Taxa com menos de 10 "
                 "tentativas aparece só como bruto; com menos de 3 partidas não há faixa. Nenhum gráfico de "
                 "radar: a ordem dos eixos muda a impressão."),
    "nomes_dos_mapas": NOME_DO_MAPA,
}


def build_html(site: str | None = None) -> str:
    from scripts.design_head import aplica  # tokens e fontes (decisão 44)
    dados = para_a_pagina()
    from scripts.build_tactics_page import arquivo_da_pagina, mapas_disponiveis
    from scripts.build_web_page import REPO
    from scripts.design_head import topo_do_site
    mapas = mapas_disponiveis()
    topo = topo_do_site("jogadores", arquivo_da_pagina("de_mirage" if "de_mirage" in mapas else mapas[0]) if mapas else None, REPO)
    return aplica((WEB / "jogadores.html").read_text(encoding="utf-8")
            .replace("<!--__TOPO__-->", topo)
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
