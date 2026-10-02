# Decisão 39: Todo rótulo de jogador tem amostra mínima e estabilidade medida

- **ID:** 39
- **Status:** vigente
- **Data:** 2026-10-02
- **Resumo:** Rótulo de jogador só sai com amostra mínima; o suporte é medido por round; a estabilidade por reamostragem dos rounds é gravada e, abaixo de 0,70, a página diz "tendência".

## Texto

39. **Todo rótulo de jogador tem amostra mínima e estabilidade medida** (auditoria, item 4.5,
2026-10-02). Um rótulo é "líder do time na métrica E acima do piso" (`metrics/player_roles.py`).
Antes, só AWPer e Lurker exigiam amostra: o "Segundo homem" saía de 1 kill e a "Âncora de bomb"
de 1 round de CT ("não rotacionou em 100% dos rounds de CT").

**Amostra mínima** (valores que o projeto já usava, nenhum novo):

| rótulo | amostra | mínimo | de onde vem |
|---|---|---|---|
| Abre o round, Suporte, Principal fragger | rounds jogados | 8 | `MIN_ROUNDS_PARA_TAXA` do perfil |
| Segundo homem | kills | 8 | o mesmo 8 (o 4 do perfil só marca a célula) |
| Âncora de bomb | rounds de CT | 6 | `structural_roles.MIN_ROUNDS_POR_LADO` |
| AWPer, Lurker | (já tinham) | 4 e 8 | decisões 29 e 31 |

**Suporte por round.** O piso era 20 s de cegueira no total da partida, e por isso dependia da
duração: 24 s em 30 rounds valiam o rótulo. Agora é 20 / 21 = 0,952 s por round (21 é a mediana
de rounds do corpus). A frase continua mostrando o total.

**Estabilidade.** Reamostragem dos rounds da partida com reposição (500 sorteios, semente fixa):
a fração dos sorteios em que o jogador continuaria com o rótulo. Abaixo de 0,70 (valor do texto
da auditoria) a página mostra "Rótulo (tendência)" e a evidência diz a porcentagem. A conta usa
as tabelas por round (`sinais_por_round`), e sem reamostrar ela devolve exatamente os rótulos de
`assign_traits` nas 52 partidas (`tests/test_estabilidade_dos_rotulos.py`). A área de casa do
âncora não é reamostrada.

**Efeito medido nas 52** (`pesquisa/estabilidade_dos_rotulos.py`): 555 → 531 rótulos (saem 17
âncoras, 6 "Segundo homem" e 1 suporte; nenhum entra); 289 dos 531 ficam como tendência (AWPer
7 de 94; Lurker 46 de 56; Segundo homem 33 de 39). Rótulo principal: muda em 14 dos 520
jogador-partidas; 167 dos 358 com rótulo são tendência.

**Função dominante acima do acaso: pronta e desligada.** `structural_roles.chance_ao_acaso` é a
cauda da binomial contra a divisão uniforme entre as funções do lado (4 no CT, 5 no TR), com
alfa 0,05. Ligada (`EXIGE_FUNCAO_ACIMA_DO_ACASO`), tira a função de 324 dos 730 jogador-lados e
quase apaga o TR (251 → 48), além de 82 dos 166 AWPers (`pesquisa/funcao_acima_do_acaso.py`).
Isso muda o caráter da leitura; ligar é decisão do Pedro. Hoje a chance é só gravada.
