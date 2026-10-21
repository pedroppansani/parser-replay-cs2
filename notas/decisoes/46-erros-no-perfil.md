# Decisão 46: Erros na aba Perfil: tipos puros, explícito ou "depende da tática", e só o que foi conferido vai à tela

- **ID:** 46
- **Status:** vigente
- **Data:** 2026-10-13
- **Resumo:** A aba Perfil responde onde cada jogador custou rounds, o que fez bem e como se compara com outro jogador da partida. Cada tipo de erro é uma função pura de `metrics/erros.py` com filtros e um nível (explícito ou depende da tática) escrito; o custo é o ΔWPA pela estimativa do modelo; nenhum tipo aparece no site antes de o Pedro conferir 8 de 10 exemplos (`TIPOS_DE_ERRO_VALIDADOS`, vazia).

## Texto

46. **Erros na aba Perfil** (fase 12, 2026-10-13).

- **O que a aba responde, nesta ordem.** Cabeçalho (nome, time com "começou CT/TR", função por lado
  com "(tendência)" e uma frase-resumo do Python); até 3 **pontos a melhorar**; até 2 **pontos
  fortes**; **comparar com** outro jogador desta partida; **Detalhes** (fechado), com o que a aba
  mostrava antes. Todo texto sai de `leitura/perfil_erros.py` (decisão 18); o JS só monta o HTML.
- **Tipos** (`metrics/erros.py`, cada um uma função pura sobre a partida processada): não trocou o
  aliado, possível bait (sempre "possível"), perdeu a troca, morreu isolado, primeira morte sem
  troca, flash no time, dano de utilidade no time. A troca e a janela são as da fase 7
  (`basic_metrics._pares_de_trade`, `JANELA_DE_TRADE_S`); a economia é a regra 8i (eco e round de
  pistola pela agregação da fase 7); a função é a dominante do lado (`structural_roles`).
  Distâncias no plano, só no mesmo andar (`map_areas.floor_split_z`); andares diferentes nunca
  estão "perto". Constantes novas, cada uma com a origem no código e histograma e varredura no
  material de calibração (seção 7): `DIST_TROCA` 600 (o raio de apoio do projeto), `S_DUELO` 2 s,
  `SEG_CEGUEIRA_ALIADO` 27 s e `SEG_CEGUEIRA_ALIADO_UMA` 4,8 s (p90 do corpus),
  `DANO_UTILIDADE_ALIADO` 20 (p95 do corpus).
- **"Utilidade no bolso" não existe.** O inventário só é lido no fim do freeze time
  (`PROPS_DA_COMPRA` em `parsing/parser.py`), não na hora da morte. Pela regra do pedido o tipo
  não foi criado e nada foi estimado; `MIN_GRANADAS_NO_BOLSO` também não.
- **Filtros e níveis** (a primeira regra que se aplica decide): (1) round de eco ou pistola do
  time, ou time guardando arma (evento depois do plant num round que o time perdeu; o "save
  declarado" não existe no dado), ou depois do fim do round: fica de fora; (2) morreu isolado sendo
  lurker, (3) primeira morte sendo entry, (4) morreu isolado ou primeira morte do AWPer no duelo de
  abertura do round (a morte que abre o round: a primeira kill de inimigo do round, a mesma abertura
  de `impacto._aberturas_por_round`; confirmado na fase 12b): depende da tática, com o motivo; (5) função só tendência: o motivo acrescenta
  "a função não é firme nesta partida"; (6) não trocou, possível bait, perdeu a troca, flash no time
  e dano de utilidade no time: explícito; (7) o resto: depende da tática ("o dado mostra posição e
  tempo, não o que o time pediu"). Consequência: morreu isolado e primeira morte sem troca saem
  sempre como "depende da tática". "Explícito" usava o rótulo afirmado (`.tag.decisivo`, verde); **muda na fase 15** (ver abaixo); "depende
  da tática", o neutro tracejado (`.tag.neutro`). `--erro` e `--aviso` nunca marcam erro de
  jogador; o ▲ de `--aviso` só aparece para dado degradado.
- **Fase 15 (2026-10-14): forma do card, lado e horário.** (a) "Explícito" deixa de usar `.tag.decisivo`: um
  erro em verde se lê como "bom", e o verde volta a significar só "afirmado e bom" (barra do ponto forte,
  função afirmada). O explícito passa a ser forma e peso, sem cor nova: barra esquerda cheia de 4 px em
  `--tinta`, etiqueta invertida (`.tag.explicito`, texto `--fundo` sobre `--tinta`), título em 700 com o número
  de ordem; o "depende da tática" é a versão tracejada do mesmo desenho (barra e etiqueta tracejadas). A ordem
  continua explícitos antes e, dentro do nível, o maior custo. `--erro` e `--aviso` seguem proibidos em erro de
  jogador. (b) Todo erro é de um lado só e nenhum tipo soma os dois: cada ocorrência leva o lado e o relógio do
  round (coluna `relogio` de `erros_do_jogador.parquet`, o mesmo de `metrics.tactics.relogio`, que o Replay
  mostra); o card diz "no TR" e o chip "R12 · 1:14". "Flash no time" e "dano de utilidade no time" eram somas
  da partida e passam a somar e a aplicar o mesmo limiar POR LADO (ocorrências que seguem na tela no corpus:
  flash 880 antes, 530 depois; dano de utilidade 32 antes, 28 depois; avisado na seção 7 do material de
  calibração). `VERSAO_DAS_METRICAS` 23; só `erros_do_jogador.parquet` e a régua `erros_reference.json` mudam.

- **Tendência da função** (decisão 39 aplicada à função estrutural):
  `structural_roles.estabilidade_da_funcao` reamostra os rounds de cada lado (500 sorteios, a
  semente e o limiar 0,70 do `player_roles`) e aplica a mesma regra de `resume_por_lado`; sem
  reamostrar, devolve a função gravada nas 52 partidas (1.040 jogador-lados, 0 diferenças); 190
  ficam como tendência. O resumo por lado gravado não muda.
- **Custo (ΔWPA), pela estimativa do modelo.** O modelo de vitória da partida
  (`win_probability`) é por round: não há ΔWPA de partida por evento pronto. O custo de um evento é
  a variação da chance de vencer o ROUND naquela kill (o mesmo modelo e estado do Round Swing,
  `rating.variacao_por_kill`, que reparte com `swing_por_evento` a conta `_delta_da_kill`) vezes a
  alavanca do round na partida (chance de vencer a partida se o time vence o round menos se perde).
  Diferença declarada para o Swing: a kill no próprio tick do fim do round entra (o Swing a reparte
  no "fim do round"; aqui ela é a morte que mais custou). Flash no time não tem custo no modelo
  (a frase diz isso); o dano de utilidade só tem quando a granada matou o aliado. A tela escreve
  "custou cerca de N pontos de chance de vitória, pela estimativa do modelo".
- **Ordem e mínimos.** Explícitos antes; dentro do nível, o maior custo. **Fase 12b:** um par (tipo,
  lado) só vira ponto a melhorar se a contagem do jogador ficar ACIMA do percentil
  `PERCENTIL_PONTO_A_MELHORAR` = 90 da referência (75 na fase 12b; 90 desde a fase 16a, ver abaixo) (interpolação linear sobre o histograma da célula
  escolhida) E tiver pelo menos `MIN_OCORRENCIAS_PARA_PONTO` = 2 ocorrências. Igual ou abaixo, ou
  com menos de 2, o item vai para Detalhes ("dentro do normal para a função", ou "dentro do normal
  para os jogadores de TR" quando a referência é o lado inteiro; "aconteceu uma vez" abaixo do
  mínimo). O estado vazio é "Nada acima do normal para a função nesta partida". Motivo da mudança:
  "não trocou o aliado" aparecia em quase todos (~3,5 por jogador-partida). `DIST_TROCA` NÃO mudou
  (só depois da calibração do Pedro); a subseção "Quantos pontos a melhorar cada jogador teria" do
  material de calibração (seção 7) mostra o efeito do percentil (50, 75, 90) e de três valores de
  `DIST_TROCA`. O card traz `limite` (o percentil usado) e a frase "o normal vai até N". Pontos fortes: das métricas que já existem no perfil em que mais é
  melhor (`METRICAS_DE_PONTO_FORTE`), as 2 mais acima da régua da função, só acima de 15% da régua
  (a mesma `MARGEM_DESTAQUE` da aba), sem amostra fraca, com o bruto ao lado.
- **Percentil 90 (fase 16a, decisão do Pedro).** Com 7 tipos em 2 lados são 14 células por jogador; no
  p75 cada célula tem 25% de chance de passar só por acaso, e isso deu 77% dos jogadores com algum
  ponto a melhorar; no p90 ficam 47%. Tabela regerada do código (`py -3.12 -m scripts.calibracao.erros_do_jogador`,
  seção 7.1b do material de calibração; 520 jogador-partidas, a contagem bruta, sem o corte de 3 da tela):

  | percentil | com pelo menos 1 ponto | % | média por jogador-partida |
  |---|---|---|---|
  | 50 | 481 | 92% | 2,78 |
  | 75 | 401 | 77% | 1,58 |
  | 90 (em uso) | 244 | 47% | 0,71 |

  (Os números citados no pedido, 402 e 1,67 no p75 e 2,88 no p50, vinham de uma geração do material
  anterior à fase 15, que ainda somava a flash e o dano de utilidade no time dos dois lados; com os dois
  por lado a tabela é a de cima. As porcentagens 77% e 47% não mudam.) O limiar de ocorrências
  (`MIN_OCORRENCIAS_PARA_PONTO` = 2) e `DIST_TROCA` não mudaram.
- **Régua anônima por (lado, função)** (fase 12b; `metrics/erros_reference.json`,
  `scripts/fit_erros_reference.py`). Substitui a régua "por função principal" da fase 12, que usava
  a função do lado com mais rounds e o corpus inteiro como queda: isso misturava os lados (lurker
  de TR contra âncoras de CT). Agora: (a) as ocorrências são separadas por lado e um ponto a
  melhorar é um par (tipo, lado); o card diz "no TR"; (b) a referência é a distribuição do mesmo
  tipo entre os jogador-lados do corpus (um jogador numa partida, num lado) com a mesma função no
  mesmo lado; (c) célula com menos de `MIN_REF_LADO_FUNCAO` = 20 jogador-lados (a origem está ao
  lado da constante) usa o lado inteiro, e a tela diz "referência: todos os jogadores de TR (poucos
  lurkers no corpus)"; no corpus de 52 partidas só Suporte do TR (17) cai aí; (d) os lados nunca se
  misturam, nem como queda; (e) a régua continua anônima (histograma das contagens e medianas, sem
  nome nem steamid; decisão 30); (f) vale também para "Pontos fortes", cujas métricas são
  recalculadas só com os rounds de cada lado (`metrics.erros.metricas_por_lado`, mesmos
  numeradores e denominadores do resumo da partida; a soma dos dois lados reproduz o perfil). Pós-plant
  e retake já são de um lado só (TR e CT) pela definição. **Publicado (fase 16a):** `FORTES_POR_LADO_PUBLICADOS` = True por decisão do Pedro. Os
  pontos fortes e o resumo do jogador seguem a mesma regra dos pontos a melhorar, por lado, com a
  referência do mesmo lado e função, também no site publicado: os cards ganham `lado` e a frase
  "referência: ...; a mediana é N". Isso muda a aba Perfil publicada (esperado e autorizado; nos 52
  jogadores-partida mudam só `fortes`, `resumo` e `textos`; valores, melhorar e detalhes ficam
  idênticos). O cálculo antigo da fase 12 (`_pontos_fortes_fase12`, `TEXTOS_FASE12`,
  `erros_reference_fase12.json`) foi removido. Antes (fases 12b a 15) o publicado mantinha a fase 12;
  conferido contra o main em match_01, 02 e 47. Nenhum parquet por partida mudou:
  `VERSAO_DAS_METRICAS` não sobe (a régua e a página são lidas, não gravadas por partida).
- **Publicação.** `TIPOS_DE_ERRO_VALIDADOS` começa vazia: a seção "Pontos a melhorar" diz "Em
  validação: os tipos de erro aparecem depois de conferidos" com o link "como é conferido" (seção 7
  do material). Um tipo entra quando o Pedro confirma pelo menos 8 dos 10 exemplos. `py -3.12 -m
  scripts.build_site --mostrar-erros-nao-validados` gera o site em `preview/` (fora do git, nunca
  publicado) com todos os tipos marcados "em validação". Sem tipo validado, nenhum dado de erro
  entra nas páginas de `docs/`.
- **Replay com tempo.** `#replay?round=12&t=34.5` abre o replay naquele round, 3 s antes do
  instante (como ao clicar num evento), parado; `#replay` sozinho continua como antes. Os chips de
  round dos pontos a melhorar usam o mesmo caminho.
- **Dado novo, nenhum número antigo muda.** `erros_do_jogador.parquet` por partida (todas as
  ocorrências, com o filtro de cada uma); `VERSAO_DAS_METRICAS` 22. O reprocesso do corpus deixou
  todos os arquivos que já existiam idênticos (só `match_meta.json` registra a versão nova). A guarda
  dos números (`scripts/design/impressao_numeros.py`) trata o bloco `PAGINA.perfil` como dado novo.

## Inventário da aba antiga (item 12.1)

| o que a aba mostrava | destino | motivo |
|---|---|---|
| rótulo "Frequência, não média" e o parágrafo sobre frequência | Detalhes | explicam a tabela de taxas, que foi para lá |
| botões dos jogadores, por time | topo | viram o seletor; abre o de maior rating |
| "Comparar com" e o seletor | topo (seção Comparar com) | agora oferece só os outros jogadores da partida e compara os pontos da aba |
| aviso da régua ("comparado com N jogador-partidas…") | topo (seção Comparar com) | diz de onde vem a régua (decisão 30) |
| "Como X joga": título, resumo e traços com taxa, bruto e régua | Detalhes | leitura do estilo, não do erro |
| cabeçalho: nome e rounds | topo (cabeçalho novo) e Detalhes | o nome no cabeçalho; os rounds na frase-resumo |
| cabeçalho: kills / assists / mortes | sai | repete K, A e M da aba Jogadores |
| cabeçalho: função no round por lado, com a concentração | topo (o rótulo, com "tendência") e Detalhes (a concentração) | a concentração "9 de 12" também está na aba Estilos |
| cabeçalho: jeito de jogar mais frequente | Detalhes | leitura do estilo |
| tabela das taxas (5 categorias, barra, %, bruto, amostra fraca, régua, coluna do comparado) | Detalhes | o número completo continua a um clique |
| tempo mediano até o primeiro contato | Detalhes | idem |
| "quem joga em cada jeito de jogar" (cards de estilo) | Detalhes | não está em outra aba |
| nota "Como ler" | Detalhes | explica a tabela |

- **Fase 18 (2026-10-15): definições do Pedro.** A troca é decidida pelo fato (o matador morreu por um aliado
  dentro da janela, `_pares_de_trade`), nunca pela distância, e toda morte trocada sai de todos os tipos (cada
  morte grava `trocada` e por quem em `mortes.parquet`). Round decidido sai de todos os tipos
  (`LIMIAR_ROUND_GANHO` 0,95 e `LIMIAR_ROUND_PERDIDO` 0,05, chance do round logo antes do evento). "Visível para o
  jogador" = linha de visão pelo mapa (colisão do awpy-data em `.tri`, com as smokes) + campo de visão
  (`MEIO_FOV_GRAUS` 53,13) + não estar cego (`metrics/visao.py`; fonte e conferência contra a demo em
  `notas/investigacoes/2026-10-15-fonte-de-visao.md`). **Limitação conhecida:** a malha do awpy-data (conferida
  por sha256) não tem portas nem objetos móveis: uma porta fechada ou um objeto que se move não bloqueia a linha
  de visão. "Não trocou" exige o matador visível na janela; "possível
  bait" = sem engajar (sem tiro no cone `CONE_DO_TIRO_GRAUS` 6 e sem dano) e recuo acima de `RECUO_MINIMO` (120)
  ou saída da linha de visão andando; o "atrás do aliado" saiu. "Perdeu a troca" exige engajar o matador e sai com
  dois ou mais inimigos visíveis ao mesmo tempo ("enfrentou dois ou mais", registrado, nunca erro). "Morreu
  isolado" virou "morreu sozinho" (nenhum aliado com o matador à vista nem a até `DIST_TROCA`). A situação conta os
  vivos pelas mortes (o "0 contra 0" vinha das posições gravadas só nos ticks das kills); evento com 0 de dano ou
  de cegueira não é ocorrência. `VERSAO_DAS_METRICAS` 24; só `erros_do_jogador.parquet`, `mortes.parquet` e a régua
  mudam. Os exemplos da seção 7.2 ficam fixados em `scripts/calibracao/exemplos_fixados.json`.

- **Fase 18b (2026-10-16): calibração do Pedro.** (1) Quem engajou o matador (atirou nele no cone, deu dano ou andou
  na direção dele com ele visível) conta só em "perdeu a troca", se morreu; "não trocou" fica para quem viu o matador e
  não engajou (nenhum lance conta nos dois). (2) Bait exige `MIN_RECUO_BAIT` = 64 u de recuo LÍQUIDO:
  `recuo = d(J(t_fim), M(t_v)) − d(J(t_v), M(t_v))`, no plano, com `t_v` a primeira amostra em que o jogador vê o
  matador, `t_fim` a última amostra da janela de troca (até 5 s, cortada na morte de um dos dois e no fim do round) e
  o matador parado onde estava em `t_v`; sair da linha de visão com menos que isso não é bait. O mesmo valor, ao
  contrário (deslocamento líquido na direção do matador visível), é o "andou na direção dele" de "perdeu a troca".
  O `RECUO_MINIMO` (120, pelo máximo) da fase 18 foi removido. (3) `MIN_TEMPO_VISIVEL` = 0,5 s, SOMADAS as amostras
  visíveis da janela (não contínuo): vale para o matador visível em "não trocou" e no bait e para o aliado que tira
  "morreu sozinho"; não vale para os dois ou mais visíveis de "perdeu a troca". (4) `MIN_CASOS_PARA_VALIDAR` = 10,
  contado dos dados (`erros.casos_no_corpus`): um tipo abaixo não entra na validação nem em
  `TIPOS_DE_ERRO_VALIDADOS` (teste), continua calculado e gravado, e no material ganha uma seção à parte com todos os
  casos, fora de `exemplos_fixados.json`. Hoje só o bait (9 casos) fica abaixo. `VERSAO_DAS_METRICAS` 25.

  Sensibilidade do recuo no corpus (informação para o futuro, não proposta): baits com recuo líquido de pelo menos

  | recuo mínimo (u) | 0 | 16 | 32 | 48 | 64 |
  |---|---|---|---|---|---|
  | baits | 30 | 18 | 15 | 15 | 9 |

- **Calibração de 2026-10-16 (respostas do Pedro à seção 7 do material; aplicadas em 2026-10-19).** As respostas
  da seção 7 foram dadas em 2026-10-16, **a partir das colunas da tabela do material (visibilidade, dano, recuo,
  situação, chance), e não assistindo aos replays**. Ficam gravadas por exemplo, com a data e esse "como", em
  `scripts/calibracao/respostas_do_pedro.json`; o gerador mostra a resposta dada no lugar da pergunta e nunca
  sorteia um exemplo respondido como substituto.

  | tipo | confirmados | resultado |
  |---|---|---|
  | não trocou o aliado | 8/10 (depende no #2 e no #3, visíveis só 0,5 s) | validado |
  | perdeu a troca | 9/10 (depende no #4) | validado |
  | morreu sozinho | 8/10 (não no #1 e no #10) | validado |
  | primeira morte sem troca | 10/10 | validado |
  | dano de utilidade no time | 10/10 | validado |
  | flash no time | 7/10 (não no #4, #7 e #8: cegueira de ~1 s) | não valida agora |
  | possível bait | a regra pega bait em 8 dos 9 (o #2 não é bait) | continua fora (amostra insuficiente) |

  As frases de como melhorar dos seis tipos servem como estão. (1) `TIPOS_DE_ERRO_VALIDADOS` recebe os cinco
  validados: a aba Perfil publicada passa a mostrá-los com as regras que já existiam (percentil 90 da referência,
  pelo menos 2 ocorrências, no máximo 3 por jogador). (2) Regra nova em "flash no time":
  `MIN_CEGUEIRA_FLASH_ALIADO` = 2,0 s. A flash cuja cegueira nos aliados (a coluna "cegueira desta flash") fica
  abaixo disso não é ocorrência (`FILTRO_CEGUEIRA_CURTA`), mesmo com a soma do lado acima do limiar; a soma
  continua contando todas as flashes, porque mede o padrão (o corte é aplicado depois da soma). Segundos do
  evento do jogo, sem conversão de tick. No corpus: 485 -> 372 ocorrências (113 saem; CT 151 -> 127, TR 334 ->
  245); nenhum outro tipo muda e a soma do lado é idêntica. `VERSAO_DAS_METRICAS` 27 (a branch não mesclada
  `calibracao-pisos` também usa 27); só `erros_do_jogador.parquet` (17 partidas) e os histogramas de
  `flash_no_time` em `erros_reference.json` mudam. Os 3 exemplos reprovados foram substituídos sem
  `--sortear-de-novo` (marcados "substituído em 2026-10-19"); com 3 de 3 nos novos, o tipo fecha 10/10 e entra.
