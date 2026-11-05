"""Os textos fixos do Reescrever (decisão 18: o rótulo de interface sai do Python, não do JS nem do template).

Um lugar só para a frase de honestidade e os rótulos do modo: a página de escolha (`scripts/build_reescrever.py`) e o modo dentro da página
da partida (`dashboard/web/partida/10-reescrever.js`, via `PAGINA.reescrever`) leem daqui. A regra do design (§5): a "Sua versão" é um plano
desenhado sobre o round real; o site nunca diz nem sugere que ela teria ganhado, e nunca mostra placar, porcentagem nem "venceria" nela.
"""
from __future__ import annotations

FRASE_FIXA_FORTE = "Não é uma previsão."
FRASE_FIXA_RESTO = "A sua versão é um plano desenhado sobre o round real: o site não simula o CS2 e não diz quem venceria os duelos."

TEXTOS_DO_MODO = {
    "fixa_forte": FRASE_FIXA_FORTE,
    "fixa_resto": FRASE_FIXA_RESTO,
    "curta": "Real e Sua versão · plano, não previsão",
    "entrar": "Reescrever este round",
    "daqui": "Reescrever daqui",
    "sair": "Sair",
    "pilula": "Reescrever",
    "titulo": "Reescrever este round",
    "comeca_em": "Sua versão começa em {relogio}",
    "dica": ("Arraste uma peça até onde ela iria; a lista à esquerda a seleciona. As peças mortas antes deste instante ficam onde "
             "morreram. Depois de mover, toque o ▶ para ver a sua versão. Mover pelo teclado chega numa próxima fase."),
    "voltar": "Voltar ao real",
    "banco": "Peças",
    "editado": "editado",
    "morto": "morto às {relogio}, antes de {inicio}",
    "toca_desligado": "Mova uma peça para poder tocar a sua versão",
    "toca": "Tocar a sua versão",
    "pausa": "Pausar a sua versão",
    "editar_de_novo": "Voltar a editar",
    "vendo": "Você está vendo a sua versão tocar. Volte ao instante para mexer nas peças.",
    "fantasma": "Fantasma do real",
    "fantasma_ligado": "Ligado",
    "fantasma_desligado": "Desligado",
    "fantasma_legenda": "real, onde difere",
    "chega": "chega {relogio}",
    "mudou_titulo": "O que mudou",
    "mudou_nada": "Nada ainda: mova uma peça.",
    "mudou_move": "{nome} sai de {de} às {relogio} e vai até o ponto marcado: chega às {chega}, {seg} s depois.",
    "mudou_move_sem_lugar": "{nome} sai às {relogio} e vai até o ponto marcado: chega às {chega}, {seg} s depois.",
    "mudou_morreu": "No real, {nome} morreu para {matador} às {relogio}; na sua versão ele não morre.",
    "mudou_d3": "No real, {nome} matou {vitima} às {relogio}. Na sua versão {nome} saiu do lugar, mas a morte acontece como no real: o site não refaz o duelo.",
    "mudou_morreu_sem_matador": "No real, {nome} morreu às {relogio}; na sua versão ele não morre.",
    "mudou_nao_chega": "{nome} sai às {relogio} e vai até o ponto marcado, mas não chega antes do fim do round.",
    "mudou_granada": "A {tipo} de {nome} das {relogio} fica só no real.",
    "granadas": {"smoke": "smoke", "flash": "flash", "he": "granada HE", "molotov": "molotov", "decoy": "decoy"},
    "descartar_titulo": "Descartar a sua versão?",
    "descartar_texto": "As peças que você moveu voltam para o lugar do round real.",
    "descartar": "Descartar",
    "continuar": "Continuar editando",
}
