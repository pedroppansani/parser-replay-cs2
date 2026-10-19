# metrics/erros/: regras dos erros do Perfil

Complementa o `CLAUDE.md` da raiz e não o substitui; vale além do `metrics/CLAUDE.md`, que
continua valendo aqui. Uma regra por linha; (N) = nota em `notas/decisoes/`.

## Erros no Perfil (`__init__.py`, `visao.py`)

- Cada tipo é função pura sobre a partida processada, com nível escrito ("explícito" ou "depende
  da tática") pela primeira regra que se aplica; eco, pistola, time guardando arma e depois do fim
  do round ficam de fora; "perto" (só em "morreu sozinho") só no mesmo andar (46)
- A troca é decidida pelo fato (o matador morreu por um aliado na janela), nunca pela distância; morte
  trocada não é erro em nenhum tipo; round com chance fora de 0,05–0,95 logo antes do evento fica fora (46)
- "Visível para o jogador" = linha de visão pelo mapa (`metrics/erros/visao.py`, malha conferida por sha256) +
  campo de visão (`MEIO_FOV_GRAUS`) + não cego; a visibilidade da demo é só conferência (46)
- Matador visível só com 0,5 s somados (`MIN_TEMPO_VISIVEL`); quem engajou conta só em "perdeu a
  troca"; bait exige recuo líquido de `MIN_RECUO_BAIT`; tipo abaixo de `MIN_CASOS_PARA_VALIDAR` casos
  (contados do corpus) não é validado (46)
- Nada de tipo que o dado não mede (o inventário só é lido no fim do freeze: "utilidade no bolso"
  não existe nem se estima) (46)

## Calibração do Pedro (não resolva sozinho)

- Limiares dos erros do Perfil (46): `MIN_RECUO_BAIT`, `MIN_TEMPO_VISIVEL`,
  `MIN_CASOS_PARA_VALIDAR`, `MEIO_FOV_GRAUS`, `LIMIAR_ROUND_GANHO`, `LIMIAR_ROUND_PERDIDO` e
  `CONE_DO_TIRO_GRAUS`.
