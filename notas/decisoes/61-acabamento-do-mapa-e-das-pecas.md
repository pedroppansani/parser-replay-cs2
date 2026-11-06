# Decisão 61: O acabamento do mapa e das peças do Reescrever (R6a): a Nuke, a peça do outro andar e o nome esmaecido

- **ID:** 61
- **Status:** vigente
- **Data:** 2026-11-06
- **Resumo:** O Reescrever passa a funcionar bem na Nuke (a peça arrastada fica na área do andar dela e selecionar uma peça do outro andar leva a vista a esse andar), a peça de outro andar da prancheta usa o mesmo desenho do Replay (D4, cartão 22) e o nome da peça editada esmaece junto com ela depois da morte do real.

## Texto

61. **R6a** (design em `notas/design/reescrever/especificacao.md` §3 e D4; pedido do Pedro em 2026-11-05/06).

- **Nuke: a peça fica na área do andar.** A área é o retângulo das âncoras dos nomes de lugar do andar (a mesma tabela que o enquadramento do Replay usa, decisão 54) mais 28 px de folga. A peça arrastada para além dela para na borda. O editor é 2D e a peça nunca troca de andar (na Nuke o A fica em cima do B): ela fica presa à área do andar em que estava no instante da edição. Mapa de um andar só: vale o mapa inteiro, como antes.
- **Nuke: selecionar uma peça do outro andar leva a vista a esse andar** (o andar fica travado, o botão dele acende e o enquadramento é o do andar). Sair do modo devolve o andar de antes (em geral "auto"). Os fantasmas continuam aparecendo só no andar da peça (decisão 58): ficam à vista quando esse andar está na tela, o que a seleção garante. As marcas de borda (triângulo com a cor do lado) continuam sendo só de quem está no OUTRO andar e fora do quadro.
- **A peça do outro andar na prancheta (D4, cartão 22).** Sai o esmaecido (`ALFA_OUTRO_ANDAR`, 0,35) da peça: ela usa o desenho do Replay (`MapCore.desenhaJogador`, estado `outro_andar`: disco cinza, anel do lado, ▲/▼, nome em itálico), com a opacidade da própria peça. O que não é peça (granada, traço, relógio) continua esmaecido no outro andar. **A edição não mudou:** a peça do outro andar continua sendo mexida depois de trocar de andar pelo botão (mexer nela dali a moveria de andar). Teste: `test_nuke_peca_no_andar_de_baixo_vira_a_peca_do_outro_andar_do_replay_no_de_cima`; os testes da prancheta passam todos.
- **O nome da peça editada esmaece com ela** depois da morte do real (opacidade 0,4, a mesma do disco): a camada de rótulos não herda o `globalAlpha`, então o desenho passa `alfaDoNome`. As outras peças não mudam.
- **Ganchos de teste novos:** `__reescrever().andar`, `.area`, `pecas[].nivel` e `pecas[].tela` (a posição na tela com o zoom do andar); `__medicaoRotulos.caixas()[].alfa`.
- **Limites.** Granada trocada na Nuke continua sem nome de lugar do destino (a grade precisa do andar do destino; fila). O teste de marcas de borda confere a regra ("nunca marca quem está no andar mostrado"), não que apareça uma marca numa cena específica.
