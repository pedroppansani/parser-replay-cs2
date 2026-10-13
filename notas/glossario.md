# Glossário

Termos que as notas e o código usam sem explicar. Saiu do `CLAUDE.md` (que precisa caber em 15.000 bytes para ser lido inteiro em toda sessão).

- **Gabarito:** arremessos de partidas com `.dem`, com o que a demo grava (força,
  velocidade, postura, chão), em `tests/fixtures/gabarito_arremessos_*`.
- **Rota A:** inferir botão, "no ar" e postura só com posição, pela rotina do jogo medida no gabarito.
- **Rota B:** ler esses valores da demo (parser 2) e declarar a fonte de cada campo.
- **Neutro:** arremesso ou rótulo sem afirmação, com o motivo; nunca um palpite.
- **Catraca:** teste que grava o melhor valor medido e falha se piorar.
- **Fora da amostra:** avaliado em dado que não entrou no ajuste.
- **Regra 36:** preservação de dados (demo, interim e backup).
- Nas notas antigas, "item 7" é a investigação da força do arremesso, "etapa N"
  são as etapas da prancheta e "Fase X" são fases de trabalho anteriores.
