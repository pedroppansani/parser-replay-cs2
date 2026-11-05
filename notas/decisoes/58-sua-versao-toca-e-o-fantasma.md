# Decisão 58: A sua versão toca, o real fica de fantasma e "O que mudou" diz a diferença (R3)

- **ID:** 58
- **Status:** vigente
- **Data:** 2026-11-05
- **Resumo:** No modo Reescrever o ▶ toca a sua versão do instante em diante: a peça editada anda em linha reta até o ponto novo na velocidade medida da prancheta e fica lá; o real aparece de fantasma só onde difere; "O que mudou" conta a diferença em texto, com o aviso da morte (D3 a). Sair com edições pede confirmação.

## Texto

58. **Sua versão toca (R3)** (design em `notas/design/reescrever/especificacao.md` §4.4 e §9; D3 (a) e a confirmação ao sair, pedidas pelo Pedro em 2026-11-05).

- **Como a peça anda.** Do ponto do real no instante até o ponto novo, em linha reta, na velocidade medida (`VELOCIDADE_U_S` correndo: AWP se a arma na mão no instante é a AWP, rifle nas outras; a mesma
  tabela e a mesma conta da decisão 43, entregue ao JS pelo build em `PAGINA.reescrever.velocidade`). Chegando, fica parada: não há dado depois disso. A peça olha para onde anda. O caminho não passa
  por paredes (o site não tem o mapa de navegação): é a linha reta que o usuário arrastou, e o texto diz "o ponto marcado", não "pelo caminho".
- **O que fica igual ao real.** Quem não foi editado toca como no real, mortes inclusive. A morte de quem foi editado só existe no real: aparece como ✕ no fantasma, e depois dela a peça da sua versão fica esmaecida (para não parecer viva e bem). O texto nunca diz que ele "não morre" nem "sobrevive": diz "No real, X morreu para Y às 0:47. Na sua versão, o site não refaz esse duelo." A morte de
  quem NÃO foi editado e morreu para alguém que foi editado acontece como no real (D3 a), e "O que mudou" avisa que o duelo não é refeito.
- **Granadas.** A granada lançada DEPOIS do instante por quem foi editado fica só no fantasma (tracejada), porque dependia da posição dele no real. A zona de smoke/fogo e a detonação são ligadas ao
  arremesso que as gerou (mesmo jogador, ponto de queda a até 60 u) para saber QUANDO foi lançada: a que já estava no ar no instante vale nos dois.
- **Fantasma.** Anel tracejado sem nome, maior que a peça (raio 12 px, escala 1,8), com halo, contorno e a cor do lado (o estado `fantasma` do `map_core.js`, que ganhou a opção `raio`; ou ✕ se o real morreu). Contraste medido por `scripts.design.mede_peca_reescrever`: o melhor entre halo e contorno contra o radar em 3.200 tracinhos por mapa, pior caso 3,85:1 (mínimo 3:1; o CI mostrou que a medida varia com o antisserrilhado do navegador, então o anel é grosso e a janela de medida acompanha a espessura) nos 8 mapas, ligado por linha pontilhada à peça da sua versão; só onde a diferença é de 8 u ou mais. Interruptor
  "Fantasma do real: Ligado/Desligado" no painel, com a legenda "real, onde difere". Quem está fora do andar em exibição não ganha fantasma (limite da Nuke, abaixo).
- **Controles.** O ▶ só liga com alguma peça movida, a velocidade passa a valer, a linha do tempo continua desligada. Tocar começa sempre no instante; pausar deixa a sua versão parada no quadro; "Voltar a editar"
  volta ao instante e à edição; "Voltar ao real" apaga as edições. Enquanto a sua versão toca ou está pausada nada é editável (decisão 35). Setas, espaço e `[ ]` continuam fora do modo (R6).
- **"O que mudou".** Lista em texto, `aria-live="polite"`, montada só do dado: o movimento (de onde, que horas, quando chega), a morte do real de quem foi editado, as mortes que ele causou (aviso D3) e as
  granadas que ficam só no real. Todas as frases vêm de `leitura/reescrever.py`. O destino não ganha nome de lugar: a página não tem a tabela de lugar por ponto, só as âncoras dos rótulos, e a âncora mais
  próxima seria inventar. A frase de honestidade vale em tudo: nada diz nem sugere que a sua versão ganharia (teste varre o painel).
- **Sair com edições.** "Sair", Esc, trocar de round e trocar de aba abrem um `<dialog>` modal ("Descartar a sua versão?", Continuar editando / Descartar). O foco abre em "Continuar editando", o Tab dá a volta dentro do aviso, o Esc do aviso
  é "Continuar editando" e o foco volta para quem abriu. Sem edição, sai direto como antes. Trocar de round ou de aba com edição abre o mesmo aviso (Descartar segue para o destino; Continuar editando fica onde estava).
- **Limites conhecidos.** A Nuke dentro do Reescrever (enquadramento por andar, marcas de borda, peça arrastada dentro da área do andar) e a peça do outro andar ficam para o R6 (pedido do Pedro); no celular o fantasma aparece por cima (o alternador
  Real | Sua versão é do R6); o teclado (mover, "Levar até") é do R6; a peça editada mantém o andar que tinha no instante.
- **Cegueira, plant e desarme do editado:** continuam como no real e entram em "O que mudou" como as mortes ("No real, X desarmou a bomba às Y. Na sua versão, o site mantém o que aconteceu no real.").
- **Limites do code-review que ficam:** o tempo "chega" pode passar do fim do round (a frase diz "não chega antes do fim do round").
- **Testes.** `tests/test_reescrever_r3.py`; os testes do R2 que saíam com edição passaram a confirmar o descarte (`_sai`), por causa da confirmação pedida.
