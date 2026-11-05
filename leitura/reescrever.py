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
             "morreram. Mover pelo teclado e tocar a sua versão chegam nas próximas fases."),
    "voltar": "Voltar ao real",
    "banco": "Peças",
    "editado": "editado",
    "morto": "morto às {relogio}, antes de {inicio}",
    "toca_desligado": "Tocar a sua versão chega na próxima fase",
}
