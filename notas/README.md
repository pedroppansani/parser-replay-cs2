# Notas técnicas

O `CLAUDE.md` traz só o que está em vigor, uma linha por regra. Aqui fica o
porquê de cada uma.

- [`decisoes/`](decisoes/): uma nota por decisão, com o ID que o código cita
  ("decisão 21a"), o status (vigente, substituída ou revogada), a data, um
  resumo e o texto integral. Onde o texto antigo afirma algo que deixou de
  valer, a nota abre com "O que vale hoje". O índice está em
  [`decisoes/README.md`](decisoes/README.md).
- [`investigacoes/`](investigacoes/): a narrativa das investigações longas
  (o que foi testado, o que foi refutado, onde se parou). A decisão guarda só a
  regra final e aponta para cá.
- [`calibracao.md`](calibracao.md): os pontos que dependem de julgamento do
  Pedro, com o histórico de cada um.
- [`limitacoes.md`](limitacoes.md): as limitações conhecidas e como validar uma mudança.
- [`contexto.md`](contexto.md): as seções gerais do `CLAUDE.md` como estavam
  antes da reestruturação de 2026-10-02.
- [`registro_tecnico_do_readme.md`](registro_tecnico_do_readme.md): o README
  antigo, com o histórico de cada métrica.

Os números do projeto não moram aqui: estão em
`data/processed/numeros_citaveis.json`.
