# Decisão 67: Arrastar várias vezes no Reescrever (P2c)

- **ID:** 67
- **Status:** vigente
- **Data:** 2026-11-15
- **Resumo:** Com a sua versão pausada num quadro depois do instante, arrastar uma peça põe uma parada nova que parte daquele quadro; as anteriores continuam; arrastar
  num quadro anterior ao da última parada corta o que vinha depois. Complementa a 58 (a trilha com horário) e relaxa a regra de que nada é editável com a sua versão pausada.

## Texto

67. **Arrastar de novo** (P2c; pedido do Pedro).

- **Regra:** `editavel()` em `partida/10-reescrever.js`: no instante (como sempre) ou com a sua versão pausada num quadro >= o instante e antes do fim. O arrasto (e as setas) viram
  `poeParadaEm(nome, g, f)` com `f` = o quadro atual: as paradas com `f` menor ficam, a de `f` igual ou maior some e entra a nova. No instante o resultado é uma parada só, como antes.
- **Continuam valendo:** nada se arrasta tocando, antes do instante do "Reescrever daqui" nem depois da morte real da peça (ela só existe no real, D3); os comandos e a troca de
  granada continuam só no instante.
- **Desfazer:** cada arrasto é um item da pilha (a trilha de antes); desfazer tira uma parada por vez. "O que mudou": uma linha por parada, com o nick e o horário.
- **Mudaram com o OK do Pedro:** `test_o_play_so_vale_com_peca_movida...` (R3) e `test_a_sua_versao_tocando_desliga_o_desfazer_e_os_comandos` (CR2): a peça só não se arrasta TOCANDO.
