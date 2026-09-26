# Fixtures

## `tatica_v1.json` e `tatica_v1_estado.json`

Tática no **formato 1** da prancheta, exportada pelo código da tag
`baseline-antes-tatica` (commit e5a01a8), antes de qualquer mudança no modelo.
É a referência da migração para o formato 2: aplicar `tatica_v1.json` com o
código novo tem que dar `tatica_v1_estado.json`, acrescido só dos campos novos
com os seus padrões.

- Gerada pela INTERFACE da página no Chrome (Playwright), não escrita à mão:
  `gera_tatica_v1.py`, que só reproduz o arquivo num checkout daquela tag.
- Usa as 10 operações do formato 1 (`renomeia`, `cria_passo`, `renomeia_passo`,
  `remove_passo`, `cria_peca`, `move_peca`, `remove_peca`, `cria_granada`,
  `move_granada`, `remove_granada`), com uma granada de arremesso REAL (da
  biblioteca da Mirage, com o comando de console) e um passo removido.
- O estado é o `S.estado` da página naquele momento; o gerador conferiu que ele
  é igual ao de `metrics.tactics.aplica` e ao de `valida` no Python.
