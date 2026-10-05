# Decisão 42: Tática com horário toca no relógio; o nome do lugar vem do corpus

- **ID:** 42
- **Status:** vigente
- **Data:** 2026-10-04
- **Resumo:** A reprodução no relógio do round vale para a tática que tem horário; a que só tem passos toca passo a passo como antes. O roteiro nomeia o lugar pelo campo `place` dos ticks do corpus, com tabela medida por mapa, ou não nomeia.

## Texto

42. **Tática com horário toca no relógio; o nome do lugar vem do corpus** (fase 8, item 8.5,
2026-10-04).

**Qual tática toca no relógio.** A que tem alguma operação do formato 3 (`cria_caminho`,
`move_ponto`, `remove_ponto`, `define_funcao`, `planta_bomba`, `nota_de_evento`) ou uma granada
com horário (`cria_granada` com `t`). A versão do arquivo não decide: a migração sobe todo
arquivo das versões 1 e 2 para a 3 sem mudar nenhuma operação, e o significado de uma operação
existente não pode mudar. A tática só com passos continua tocando passo a passo (decisão 35); os
testes de reprodução existentes ficam como estão. No relógio, a reprodução vai do primeiro
evento ao último horário em que algo acontece ou termina (ponto-chave, granada com voo e efeito,
plant, marco), é função pura do tempo (`cenaNoRelogio`), e as setas vão de evento em evento.

**Nome do lugar.** O awpy 2.0.2 desta máquina não tem as áreas de navegação (`~/.awpy/navs` não
existe). O dado que existe é o campo `place` dos ticks: o nome que o próprio jogo dá ao lugar,
em inglês, como o jogo escreve (sem tradução, que seria inventar). A tabela por mapa é uma grade
sobre o radar com o lugar mais comum de cada célula (`metrics/lugares.py`), gerada por
`scripts/build_lugares.py` em `data/lugares/` (o interim não vai para o git, como
`data/lineups/`). O lado da célula é o de maior acerto fora da amostra (partidas pares montam,
ímpares conferem) entre 4, 8, 16 e 32 px que cabem no limite de 300 KB por mapa do documento da
fase 8. Célula sem tick não tem nome. Mapa com menos de 2 partidas não tem medida fora da amostra
e fica sem tabela (hoje o Train). Números em
`notas/investigacoes/2026-10-04-nome-do-lugar.md`.
