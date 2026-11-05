# Decisão 55: O dado do Reescrever (R0): lado e tempos na biblioteca, índice dos sugeridos

- **ID:** 55
- **Status:** vigente
- **Data:** 2026-11-04
- **Resumo:** Cada arremesso da biblioteca (`data/lineups/`) grava o lado de quem lançou, o tempo de voo e, no molotov, o de efeito, todos
  lidos da demo (nulo quando a demo não diz). O build grava `docs/sugeridos.json`, o índice pequeno dos rounds sugeridos, com o motivo de cada um.

## Texto

55. **O dado do Reescrever (R0)** (aprovado pelo Pedro em 2026-11-04, design do Iriun em `notas/design/reescrever/`).

- **Lado:** `lado` ("ct" ou "t") = o `side` de quem lançou, no tick da soltura (`ticks`). Conferido contra o `replay.json` de cada partida: 23.706
  de 23.706 entradas iguais. Sem isso a lista de alternativas do "Trocar a granada" mostrava arremesso do outro lado.
- **Voo** (`voo_s`): do soltar até a detonação, da demo. He, flash e smoke: o evento de detonação com o mesmo `entity_id`, o primeiro depois
  de soltar (o `entity_id` é reaproveitado na partida). Molotov: o início do fogo (`infernos`), casado por quem lançou e round (o fogo é outra
  entidade). Acima de 15 s ou negativo: nulo (casamento errado). Presente em 99,9% (smoke, flash, he) e 97,4% (molotov); decoy fica nulo.
- **Efeito** (`efeito_s`): só o molotov (início e fim do fogo, mediana 5,5 s, no máximo 7,03 s). A smoke NÃO tem tick de fim na demo
  (`smokes.end_tick` vazio nas 52 partidas): fica nulo e quem a usar usa a constante do projeto (`DURACAO_SMOKE_S`, 20 s), que é a duração da smoke NO JOGO e **não vem da demo**; o código e a tela nunca a apresentam como medida. He e flash: nulo.
- **Sugeridos** (`leitura/sugeridos.py`, `docs/sugeridos.json`, 58 KB): por partida, o round decisivo (com a frase do card), até 3 momentos do
  "Por que perdeu" com jogador (um por round; a abertura perdida primeiro) e até 2 erros do Perfil de tipo VALIDADO (os de maior perda de
  chance de vitória). **Os limites (3 momentos, 2 erros) e a ordem foram escolha do Claude, aceita pelo Pedro e ajustável** (constantes `MAX_MOMENTOS`, `MAX_ERROS` e `PRIORIDADE_DO_MOMENTO`); cada um com o motivo, o instante (`tick`) e o relógio do round. Nada novo é medido; tipo de erro não validado nunca entra.
- **Impressão dos números:** idêntica, salvo o hash de `biblioteca.arremessos` das 8 pranchetas, que muda porque as entradas ganharam três campos (os
  campos antigos são iguais byte a byte ao git). Diferença ACEITA pelo Pedro (2026-11-04); as outras 11.747 linhas são iguais.
- **Para o R4 (trocar a granada):** só entram como alternativa os arremessos do mesmo tipo, do mesmo lado e com `voo_s` conhecido; o decoy fica fora.
  Os 148 molotovs sem voo e 162 sem efeito: pendência 29, sem bloquear nada.
