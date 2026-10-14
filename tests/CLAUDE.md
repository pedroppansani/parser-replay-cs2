# tests/: como os testes são escritos

Complementa o `CLAUDE.md` da raiz e não o substitui (lá: teste existente não muda sem o Pedro
aprovar). Uma regra por linha; (N) = nota em `notas/decisoes/`.

- Os dez invariantes de `test_invariantes_corpus.py` valem para toda partida que entrar; a média do
  rating é comparada com a OFICIAL dos mesmos jogador-partidas, nunca com 1,00 (26)
- Teste que depende de `data/interim/` ou `data/processed/` é PULADO quando falta o dado, nunca
  quebra; o de navegador roda num Chrome de verdade (Playwright) e é pulado sem ele (24, 26, 23)
- O teste da convenção de ângulos roda a invertida como controle: se passar nas duas, não mede
  nada (9)
- A soma zero do Round Swing é teste de integridade permanente, exceto morte sem matador inimigo
  (`test_swing_soma_zero_por_round_exceto_morte_sem_matador_inimigo`) (22k)
- `test_escada.py` trava os degraus 1 e 2 da escada de validação (22g)
