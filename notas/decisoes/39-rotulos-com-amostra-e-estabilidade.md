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

**A marca cobre também a função estrutural** (fase 12b, 2026-10-13). A aba Perfil escreve "Função
(tendência)" para a função dominante de cada lado, pelo mesmo método e com o mesmo limiar 0,70:
`structural_roles.estabilidade_da_funcao` reamostra os rounds daquele lado (500 sorteios, semente
fixa) e aplica a regra de `resume_por_lado`. O resumo por lado gravado não muda. Teste:
`test_funcao_estrutural_instavel_sai_com_tendencia` (9 rounds de uma função e 6 de outra: 0,61, sai
"(tendência)"; 14 e 2: estável).

**Função acima do acaso: ligada só como aviso** (resposta do Pedro ao cartão 2 de
`notas/PENDENCIAS_PARA_O_PEDRO.md`, 2026-10-16). Resposta, como veio: "Opção 3: ligar só como aviso.
A função continua aparecendo. Quando a chance ao acaso passar de 0,05, ela ganha uma marca. Uma
condição: a marca é a mesma da decisão 39. Use '(tendência)', com o mesmo tratamento visual, e não
'(pode ser acaso)'. Para quem lê, as duas querem dizer a mesma coisa: 'o dado sugere, mas não
sustenta com firmeza'. Duas marcas diferentes para isso confundem. O motivo específico de cada marca
vai no `title` ou na dica da marca: 'Função dominante neste lado, mas com 12 rounds pode ser acaso
(chance de 9%)' para a função estrutural; o texto atual da decisão 39 para os traços. Os rótulos não
mudam, então nenhum número muda."

Como ficou: `EXIGE_FUNCAO_ACIMA_DO_ACASO` segue `False` e a função dominante não muda. A marca
"(tendência)" da função estrutural tem agora dois motivos, e continua UMA marca: a reamostragem
instável (fase 12b) OU a `chance_ao_acaso` gravada fora do alfa (≥ 0,05, o complemento de "acima do
acaso"; nenhum valor do corpus cai em 0,05 exato). A dica (`title` da etiqueta no cabeçalho da aba
Perfil) diz o motivo, ou os dois, e sai do Python (`structural_roles.dica_da_tendencia`): "Função
dominante neste lado, mas com 12 rounds pode ser acaso (chance de 21%)", "... mas se mantém em 61%
das reamostragens dos rounds", ou os dois unidos por "e". A chance é inteira, com uma casa quando o
inteiro cairia no próprio corte (6 de 12 no CT: "5,4%"). A conta lê o que já está gravado
(`structural_roles_summary.parquet`), sem reprocesso; a marca é aplicada ao bloco da aba Perfil por
`leitura/marca_da_funcao.py` no build. Os traços não mudam: a evidência deles já traz o texto desta
decisão ("tendência: o rótulo se mantém em N% das reamostragens dos rounds"). O nível dos erros do
Perfil (regra 5 da decisão 46, "função só tendência") continua só com a reamostragem. Medido nas 52:
dos 730 jogador-lados com função dominante, 324 têm a chance fora do alfa; 174 deles já tinham a
marca pela reamostragem e 150 a ganham agora; 16 a têm só pela reamostragem (340 marcas no total).
Teste: `tests/test_marca_da_funcao.py`.

**O limiar 0,70 fica** (resposta do Pedro ao cartão 4, "As 289 tendências", 2026-10-16). Resposta,
como veio: "Opção 1: mantém 0,70. Lurker e segundo homem com marca de tendência são o achado, não um
defeito. Feche o cartão." `LIMIAR_DE_TENDENCIA` continua 0,70 (`metrics/player_roles.py`), e os
289 dos 531 rótulos de traço com "(tendência)" são a leitura pretendida, não um limiar alto demais.
