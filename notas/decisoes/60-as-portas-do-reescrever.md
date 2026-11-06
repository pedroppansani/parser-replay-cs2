# Decisão 60: As portas de entrada do Reescrever dentro da partida (R5) e o relógio do round no "Por que perdeu"

- **ID:** 60
- **Status:** vigente
- **Data:** 2026-11-06
- **Resumo:** Cada momento do bloco "Por que … perdeu este round" que tem jogador e cai dentro do round ganha um botão "Reescrever", e cada chip de round do Perfil ganha um ao lado dele. Os dois abrem o round 3 s antes do instante, já editando e com o jogador selecionado. O bloco passa a mostrar o relógio do round (cartão 28), não o tempo decorrido.

## Texto

60. **As portas (R5)** (design em `notas/design/reescrever/especificacao.md` §4.6 e D5).

- **Momentos do bloco.** O botão fica fora do botão do momento (botão dentro de botão não vale): a linha é `.mrow` com o momento e o "Reescrever". Sem botão: momento sem jogador, momento depois do fim do round (`pos_round`) e momento fora da janela exportada. Na virada numérica o selecionado é a vítima.
- **Chips do Perfil.** Cada chip com instante ganha o "Reescrever" ao lado, na mesma moldura (um par, uma borda só). O jogador selecionado é o dono do Perfil que está aberto. Chip sem instante não tem porta. O clique no chip continua abrindo o Replay como antes.
- **O que a porta faz** (`reescrever.abreEm(round, t, quem)`): abre o Replay no round, `t − 3 s` (o mesmo pré-roll do Replay e dos chips), entra no modo, seleciona `quem` se a peça está viva nesse instante e leva o palco à vista (no computador, a rolagem do palco; no celular, o topo do palco logo abaixo das faixas grudadas). Se já está no modo com edições, pergunta antes de descartar (a mesma confirmação de trocar de round); sem edições, reabre direto.
- **Acessibilidade.** O `aria-label` diz o resto: "Reescrever a partir de 1:45 no relógio, 3 s antes, com flameZ selecionado" (bloco) e "Reescrever o round 9 a partir de 3 s antes de 0:33, com FalleN selecionado" (chip). A frase do fim do bloco ganhou "Ou clique em Reescrever para mudar a jogada a partir de 3 s antes." Nenhuma frase promete resultado.
- **Cartão 28 (duas bases de tempo).** O tempo de cada momento do bloco agora é o relógio do round (descendo; depois do plant, o da bomba), o mesmo do resto do Replay, o que o "Reescrever" abre 3 s antes e o que "O que mudou" usa. Antes era o tempo decorrido. Momento depois do fim do round mostra só "após o fim do round" (não há relógio a mostrar).
- **Celular.** O botão do bloco desce para baixo do texto, alinhado a ele, com 44 px de altura. Os chips do Perfil quebram para a linha de baixo (a faixa não rola mais de lado), então nenhum par chip + "Reescrever" passa da largura do cartão nem é cortado (teste a 375 e a 1366).
- **A aba ativa à vista.** Ao trocar de aba (clique, porta do Perfil, bloco ou endereço), a faixa de abas rola de lado até a aba ativa ficar visível (`scrollLeft` da faixa; nunca `scrollIntoView`, que rolaria a página). Teste a 375: abrir em `#estilos` deixa a aba à vista com a página em 0, e o caminho Perfil → porta → Replay também.
- **Molotov trocado** tem o mesmo teste de área da smoke: nada de área antes da queda, uma área com o raio do molotov do real no destino depois dela, até o `efeito_s` da alternativa, e some depois.
- **Limites.** A porta do bloco só existe para round que tem Replay (todo round da página tem).
