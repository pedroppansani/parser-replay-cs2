# Decisão 38: Time tem nome canônico, e todo agregado por time passa por ele

- **ID:** 38
- **Status:** vigente
- **Data:** 2026-10-02
- **Resumo:** Todo agregado por time usa `metrics/times.nome_canonico` (tabela em `data/reference/times_conhecidos.json`).

## Texto

38. **Time tem nome canônico, e todo agregado por time passa por ele** (decisão do Pedro,
2026-10-02). A demo grava o nome do time como estava no servidor, e o mesmo time aparece no
corpus escrito de mais de um jeito: "Vitality" e "Team Vitality", "Falcons" e "Team Falcons".
A contagem de times do corpus saía 11 em vez de 9, e cinco scripts tinham cada um a sua cópia
de "tira o prefixo Team" (um sexto não tirava nada).

É o mesmo espírito da decisão 25 para jogadores. Como time não tem identificador na demo, a
tabela é explícita: `data/reference/times_conhecidos.json` (alias -> nome), lida por
`metrics/times.nome_canonico`. Nome que não está na tabela é o próprio canônico; nada é
adivinhado ("Team Liquid" não vira "Liquid" sozinho).

`tests/test_times.py` falha se dois nomes do corpus se reduzirem à mesma chave sem estarem na
tabela, e se algum módulo voltar a normalizar nome de time por conta própria.
