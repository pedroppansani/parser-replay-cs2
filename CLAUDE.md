# Contexto do projeto para o Claude Code

Este arquivo é lido automaticamente no início de cada sessão. Ele registra as
decisões já tomadas e por quê — a ideia é não refazer discussões resolvidas nem
desfazer escolhas sem saber que elas foram deliberadas.

## O que é este projeto

Parser de replay (.dem) do CS2 com dashboard de estatísticas. Projeto 1 de 5 de
um portfólio para LinkedIn/GitHub.

O dono do projeto (Pedro) é jogador de CS2 de nível alto (Faceit Level 10 /
Level 20 GC, flex AWPer) e estudante de Engenharia de Computação com ênfase em
IA. **O diferencial do projeto não é o parsing** — a biblioteca `awpy` já
resolve isso. O diferencial é o desenho das métricas: cada uma carrega uma
decisão de jogo explícita, e a validação final é o conhecimento de jogo dele.

Consequência prática: ao propor ou alterar uma métrica, a justificativa de JOGO
importa tanto quanto a corretude do código. Métrica genérica de dashboard
pronto não serve aqui.

## Ambiente

- **Python 3.11 a 3.13.** O awpy 2.0.2 NÃO suporta 3.14. A máquina tem as duas
  versões; use `py -3.12` no Windows.
- **O demo é 64 tick, não 128.** Nunca assuma; `metrics/timing.py` detecta pelo
  timer da bomba (40s fixos no CS2) e confere pela velocidade máxima dos
  jogadores (~250 u/s). Todo cálculo de tempo depende disso.
- Demos ficam em `data/raw/` (gitignored). São arquivos de 200MB+ que expiram no
  FACEIT em 30 dias.
- Parsing leva ~14s por partida. Use `--from-interim` para reaproveitar um parse
  já feito em vez de reparsear enquanto itera nas métricas.

## Estrutura

```
parsing/      wrapper do awpy.Demo
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles,
              positioning, grenades, map_areas, site_roles, player_roles,
              clutch, archetypes (+ archetype_reference.json), player_profile
clustering/   playstyle (PCA + KMeans), global_model.json e cluster_names.json
dashboard/    app Streamlit + theme + web/
scripts/      process_demo (CLI), fit_global_clusters, fit_archetype_reference,
              build_player_profiles, show_derived_angles e show_map_areas
              (calibração), narrative, build_site
tests/        124 testes
data/raw/     .dem originais (gitignored)
data/interim/ tabelas brutas em parquet (gitignored, ticks tem 1M+ linhas)
data/processed/ métricas calculadas (versionadas — é o que o dashboard usa)
data/global_clusters/ clustering ajustado no conjunto das partidas
data/player_profiles/ perfil por jogador acumulado em todas as partidas
```

## Convenções do código

- **Comentários e docstrings em português.** O código é para o Pedro revisar e
  recalibrar, não para distribuição internacional.
- **Toda métrica devolve `(per_round, summary)`.** O cálculo round a round vem
  primeiro e a agregação depois, porque a validação manual acontece round a
  round. Não substitua uma tabela per_round por só o agregado.
- **Limiares são constantes nomeadas no topo do módulo**, com comentário
  explicando a escolha. São botões de calibração, não números mágicos.
- Polars (não pandas). Parquet para persistência.

## Decisões de design que NÃO devem ser desfeitas sem discussão

Cada uma dessas foi tomada depois de olhar os dados reais. A versão "óbvia" foi
testada e estava errada.

1. **Peek vs hold usa deslocamento LÍQUIDO, não distância percorrida.**
   Jiggle peek (sair e voltar) é jogar um ângulo, não avançar espaço. Há teste
   travando isso (`test_jiggle_peek_counts_as_hold_not_peek`).

2. **A classificação peek/hold usa posição medida, não a flag `is_scoped`.**
   Posição é o sinal mais direto de deslocamento. (Registro: uma versão anterior
   afirmava que `is_scoped` era não confiável — aquilo era consequência do bug de
   tickrate, não defeito do dado. Com 64 tick as velocidades batem com a física
   do jogo: 29 u/s scopado, 104 u/s sem scope.)

3. **Tiro de AWP que erra mas não custa a vida é `no_trade`, não derrota.**
   Fica fora do denominador da conversão. Com AWP, muito tiro é de informação ou
   para negar espaço; contar como derrota infla a taxa de erro do AWPer.

4. **Crosshair placement NÃO é distância angular até o inimigo mais próximo.**
   Essa métrica pune o comportamento certo (pré-mirar antes do inimigo
   aparecer). A direção só é cobrada nas amostras que antecedem contato real
   (tiro ou dano em até 1s). Sem esse filtro o erro mediano fica em 36-117° até
   entre profissionais, porque o inimigo mais próximo geralmente está atrás de
   uma parede. Com o filtro, cai para 14-24°.

5. **Ângulos de pré-fire são derivados dos dados, não constantes inventadas.**
   Um ângulo chutado errado premia placement ruim em silêncio. A derivação usa
   agrupamento circular por moda — **não volte para bins de largura fixa**, que
   perdem ângulos caindo na borda do bin (bug real, pego por teste).

6. **Desvio de setup compara com o padrão do próprio time, não com um setup
   "certo".** Setup correto depende de economia, placar e adversário; uma tabela
   fixa seria chute disfarçado de métrica. O número é índice relativo
   (`deviation_index`), não contagem de jogadores fora do lugar.

7. **Clustering é por (jogador, round), não por jogador.** O mesmo jogador é
   entry num round e âncora em outro; agregar por partida esconde exatamente o
   que se quer medir. Confirmado nos dados: todo jogador visita 3 ou 4 dos 4
   grupos numa única partida.

7a. **O perfil por jogador é a leitura principal dos dados comportamentais; o
   agrupamento existe para DESCOBRIR os grupos, não para descrever pessoas.**
   As médias de um grupo ("distância média do time 1.100u", "8 regiões") não
   pertencem a jogador nenhum: os rounds de um mesmo jogador se espalham por
   todos os grupos. Quem responde sobre uma pessoa é `metrics/player_profile.py`,
   com a frequência de cada comportamento nos rounds DELE ("puxa AWP em 40% dos
   rounds"). Ao adicionar uma leitura sobre jogador, ela vai no perfil — não em
   mais uma média de cluster.

   Três contratos do perfil, e nenhum é decoração:
   - **taxa sempre com o bruto** (`_n` e `_d`): com 22 rounds, 41% e 50% são o
     mesmo número, e só o percentual inventa precisão;
   - **taxa sempre com referência** (`_ref`, mediana dos OUTROS jogadores,
     leave-one-out): "60% longe do time" não diz se é muito ou pouco;
   - **amostra pequena marcada** (`_fraco`): 1 de 1 não é 100%.

   E lado importa: distância, ancoragem e contato cedo saem também em `_ct` e
   `_t`, com a referência calculada dentro do lado.

7c. **"Longe do time" precisa de piso absoluto, não só do corte na mediana.**
   Corte na mediana marca metade dos rounds como "longe" por construção,
   inclusive num time em que todo mundo joga colado — basta ser marginalmente
   menos colado que os outros. Vale também `RAIO_COMPANHEIRO`: com um
   companheiro dentro do raio de apoio, o jogador não está longe do time em
   leitura nenhuma. Foi um teste sintético (jogador colado no time) que pegou
   isso, e ele está travado.

7b. **As features do clustering são só COMPORTAMENTO.** `damage`, `kills`,
   `trade_kills`, `utility_damage` e `survived` saíram da lista: são resultado, e
   com elas dentro o KMeans agrupava os rounds por como terminaram — o que a
   tabela de ADR já diz. Tirando as cinco, a silhueta foi de 0,168 para 0,216
   (k=4) e os dois eixos do gráfico passaram a explicar 56% em vez de 40%. Os
   grupos viraram estilo (fica parado longe / entra sem a mira pronta / roda o
   mapa / joga junto e rápido). **Não devolva features de resultado para a
   lista** — a lista removida está nomeada no módulo.

8. **O KMeans não nomeia os grupos.** Apelido de jogo ("lurker", "âncora",
   "entry") é interpretação e cabe ao Pedro, via `clustering/cluster_names.json`.
   **Não gere rótulos automáticos.**

   O nome que aparece é uma DESCRIÇÃO derivada da medição (`describe_clusters`):
   "longe do time, chega a se afastar muito" é releitura dos números, não
   leitura de jogo. Ela sai do perfil GLOBAL, não do recorte da partida, senão o
   mesmo grupo mudaria de texto de uma página para a outra.

   O `cluster_names.json` entra no payload do site: sem isso o arquivo só teria
   efeito no dashboard local e a nomeação nunca chegaria à página.

   **O agrupamento não tem mais seção própria no site.** Ele existe como insumo:
   o único lugar onde aparece é o "jeito de jogar mais frequente" da aba Perfil.
   A seção que o desenhava foi removida porque descrevia GRUPOS DE ROUNDS — média
   que não pertence a jogador nenhum — e o perfil por jogador responde a mesma
   pergunta direto. Junto saiu a última ocorrência da palavra "cluster" no texto
   visível das páginas, e as 220 atribuições round a round que iam no payload de
   cada página sem ninguém ler.

9. **Convenção de ângulos do CS2: pitch positivo = olhar para BAIXO.** Validada
   empiricamente (erro mediano de 1,76° no tick da kill, contra 6,52° na
   convenção invertida). O teste roda a convenção invertida como controle — se
   um dia passar nas duas, o teste não está medindo nada.

10. **Paleta do dashboard foi validada para daltonismo e contraste.** O scatter
    de clusters é facetado (um painel por cluster) porque nenhuma quarta cor
    passa nos critérios junto das três primeiras no modo escuro. Não troque por
    4 cores num gráfico só.

11. **O KMeans é ajustado UMA vez no conjunto das partidas, não por partida.**
    O rótulo numérico do KMeans é arbitrário: treinando por partida, o "cluster
    3" de uma não tem relação com o da outra — e `cluster_names.json` é um
    arquivo único aplicado a todas. Medido nas 9 partidas: o grupo de dano alto
    era o cluster 3 em match_01, o 2 em match_02 e o 0 em match_04. O modelo vive
    em `clustering/global_model.json` (JSON, não pickle) e é ajustado por
    `scripts/fit_global_clusters.py`. Há teste travando a propriedade e um teste
    de controle mostrando que o modo antigo não a tinha.

12. **Âncora e lurk são medidos por ÁREA do mapa, não por distância nem por
    tempo.** Definição de jogo do Pedro: âncora é o CT que fica no mesmo bombsite
    mesmo quando os T indicam o outro lado; lurker é o T que joga outra área
    enquanto o time executa. As versões antigas (contato tardio e distância média
    do time) mediam outra coisa — dois CTs em bombsites opostos estão à mesma
    distância um do outro que um lurker do time. `metrics/map_areas.py` particiona
    o mapa em A/Mid/B a partir dos plants do próprio demo.

13. **Entry é AÇÃO, não relógio.** Quem dá o primeiro contato é entry mesmo que
    o round já esteja em 20s restantes. Por isso a métrica é a fração de rounds
    em que o jogador foi o primeiro do time a encostar no adversário, e não a
    mediana de segundos até o contato — essa media o quão rápida foi a partida.
    Registro: com piso em segundos, o rótulo "Abre o round" nunca foi atribuído a
    ninguém em 90 jogador-partidas.

15. **Carrega piano é PRODUTO de esforço por benefício, não `esforço −
    recompensa`.** A subtração está errada por construção: quem tem recompensa
    baixa vence a diferença, e recompensa baixa é quase sempre jogar mal — a
    fórmula elegia o pior jogador e colava nele um rótulo que significa outra
    coisa. E o papel tem **três formas**, não uma: entrar e morrer abrindo espaço
    (T), segurar bomb sozinho (CT), e ficar com a arma pior para o companheiro
    comprar (economia). Não reduza a uma fórmula de entry: dá para ser carrega
    piano a partida inteira sem nunca ter sido o primeiro a morrer.

16. **A escala dos papéis é ajustada no conjunto das partidas, não dentro da
    partida.** `metrics/archetype_reference.json`, mesmo padrão do
    `global_model.json`. Normalizar dentro da partida faz alguém ficar em 1,0
    mesmo quando ninguém se destacou, e o card de destaque mostraria um jogador
    mediano como retrato da partida. Reajuste com
    `scripts/fit_archetype_reference.py` sempre que processar demo nova ou mexer
    num componente.

17. **Empate no primeiro contato não é abertura de ninguém.** Quando uma granada
    pega vários do time no MESMO tick, todos empatam em primeiro lugar. Medido:
    24 de 374 lados-round nas 9 partidas, um deles com quatro jogadores em
    10,359375s. Contar os quatro como quem abriu o round inflava o entry do time
    inteiro. O empate sai do numerador nos dois módulos que usam a métrica
    (`archetypes` e `player_roles`), com teste de regressão.

18. **As frases dos cards são geradas em Python, não em JavaScript.** Ficam em
    `scripts/narrative.py` e chegam prontas ao template. O motivo é testabilidade:
    a regra "campo que não existe some da frase" vira teste. Antes disso as três
    frases eram texto fixo escrito para a match_01, e todas as páginas
    renderizavam o placar e os nicks daquela partida. **Papel sem sustentação
    devolve string vazia**, não frase com zeros — "AWP na mão em 0 rounds"
    descreve a ausência do papel como se fosse o papel.

14. **Spawn não é área de jogo e fica fora da partição do mapa.** O CTSpawn da
    Ancient cai geometricamente do lado do A; contá-lo fazia todo CT "ir pro A"
    em todo round e zerava a métrica de não-rotação para times inteiros. Pelo
    mesmo motivo, passar rapidamente pela área do outro site não conta como
    rotação (`MIN_OTHER_SITE_SHARE`): os corredores de ligação caem de um dos
    lados. Ambos têm teste de regressão.

## Pontos de calibração — pertencem ao Pedro, não ao código

Não "resolva" nenhum destes automaticamente; pergunte.

- Nomear os clusters (`clustering/cluster_names.json`). Rode
  `py -3.12 -m scripts.fit_global_clusters --dry-run` para ver o perfil de cada
  um e os rounds representativos.
- Revisar a partição A/Mid/B dos mapas (`MANUAL_PLACE_AREAS` em
  `metrics/map_areas.py`). Rode `py -3.12 -m scripts.show_map_areas`. A Nuke é a
  mais frágil: os dois sites ficam empilhados na vertical.
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`).
  Rode `python -m scripts.show_derived_angles <match_id>` para ver os derivados.
  Os com `n_kills` baixo (4-5) são os que mais precisam de julgamento humano.
- Limiares: janela de trade (5s), peek/hold (120u / 250u), janela de contato
  (1s), tolerância de pré-fire (25°), permanência mínima para contar rotação
  (15% do round).
- Limiares dos papéis (`metrics/archetypes.py`): distância máxima para uma morte
  de companheiro contar como "do seu lado" (900u), assinatura de repick (250u de
  percurso, razão 3x), mínimo de tentativas de clutch (3), mínimo de rounds com
  AWP (4), compra abaixo da média do time (-400), fração do time de rifle (60%),
  e o quanto um papel crítico precisa se destacar para virar card (0,85).
- Pisos de função (`TRAIT_SPECS` em `metrics/player_roles.py`). Sensibilidade
  medida: lurker (0,40) é estável (±10% muda 1 rótulo), âncora (0,80) é sensível
  só para cima (+10% perde 28% dos rótulos) e **entry (0,32) é sensível dos dois
  lados**. Depois da correção do empate no primeiro contato, 0,32 ficou ACIMA do
  p90 da métrica e só 5 jogadores recebem o rótulo. Recomendação registrada:
  ancorar o piso ao acaso (com 5 jogadores, 1/5 = 0,20) em vez de a um número
  absoluto — 1,5x o acaso = 0,30 dá 10 de 25 times-partida com entry definido. É
  decisão do Pedro.

## Limitações conhecidas

- São **9 partidas** (1.870 player-rounds). A silhueta do clustering é 0,168
  (k=4) no conjunto — estrutura fraca, e ela **não melhorou com volume**: 1.870
  player-rounds dão praticamente a mesma silhueta que 220. A previsão registrada
  antes (de que melhoraria com mais demos) não se confirmou, e isso muda a
  leitura: estilo de jogo num round é um contínuo, não caixas separadas. Os
  grupos servem como descrição, não como classificação de fronteira nítida.
- 8 das 9 partidas são de 4 mapas (5 Mirage, 2 Ancient, 1 Anubis, 1 Nuke). A
  partição de áreas da Nuke é a menos confiável e nunca foi revisada à mão.
- As demos disponíveis são partidas profissionais do donk, não do Pedro. A
  validação feita foi por consistência (ele lidera ADR e KAST, como esperado) e
  ordem de grandeza, não por memória round a round.
- Caso em aberto: o donk tem o melhor erro angular em briga (14,6°) e o pior
  score de crosshair, porque a mira dele raramente coincide com os ângulos de
  consenso. Para um jogador conhecido por off-angles, pode ser estilo e não
  erro. É julgamento do Pedro.
- Overlay do radar do mapa nos heatmaps depende de `awpy get maps` (download dos
  assets). Sem isso o heatmap funciona em coordenadas de jogo.

## Como validar mudanças

```bash
py -3.12 -m pytest tests/ -v          # 124 testes
py -3.12 -m scripts.process_demo data/raw/match_01.dem --match-id match_01 --from-interim
py -3.12 -m streamlit run dashboard/app.py
```

Ao mexer numa métrica, confira o efeito na tabela round a round, não só no
agregado — número agregado plausível pode esconder lógica errada.
