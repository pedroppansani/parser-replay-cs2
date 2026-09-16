# 01 — Parser de Replay CS2 com Dashboard de Estatísticas

Projeto 1 de 5 do portfólio. Ferramenta que lê replays (.dem) do CS2, extrai
estatísticas e gera dashboards — com foco em métricas que descrevem **como** o
jogo foi jogado em nível competitivo, não só quem fez mais kill.

**Status: Fases 1 a 4 implementadas.** Pipeline de parsing, métricas básicas,
métricas autorais (AWP, crosshair placement, posicionamento), clustering de
estilos de jogo, métricas de utility por efeito, função de jogador e dois
painéis (Streamlit para trabalho, página web autocontida para portfólio),
testados end-to-end numa partida real. Pendente: calibração manual dos
parâmetros de jogo e nomeação dos clusters (ver "O que ainda depende de
julgamento humano").

## Por que esse projeto

Sou jogador de CS2 de nível alto (Faceit Level 10 / Level 20 GC, flex AWPer) e
estudante de Engenharia de Computação com ênfase em IA. O parsing em si não é o
diferencial — a biblioteca [awpy](https://awpy.rtfd.io/) (que usa o parser Rust
`demoparser2`) já resolve isso. O diferencial é o desenho das métricas: cada uma
carrega uma decisão de jogo explícita no código, e várias delas foram corrigidas
justamente porque a versão ingênua contradizia o que acontece na prática.

## Arquitetura

```
.dem → awpy.Demo.parse() → tabelas brutas (rounds, kills, damages, shots,
                           grenades, player_blind, detonações, ticks)
     → metrics/  (Fases 1, 2 e 4) → métricas por jogador/round
     → clustering/ (Fase 3)       → PCA + KMeans sobre essas métricas
     → parquet em data/processed/ → dashboard (Streamlit + Plotly)
                                  → página web autocontida (sem servidor)
```

```
parsing/      wrapper do awpy.Demo (parse + persistência em parquet)
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles,
              positioning, grenades, player_roles
clustering/   playstyle (PCA + KMeans) e cluster_names.json
dashboard/    app Streamlit, tokens visuais e web/ (painel de portfólio)
scripts/      CLI de processamento, calibração de ângulos e build da página web
tests/        43 testes (dados sintéticos + validação contra a demo real)
demos/        .dem baixados do FACEIT (gitignored)
data/raw/     .dem originais (gitignored)
data/interim/ tabelas brutas em parquet (gitignored — ticks passa de 1M de linhas)
data/processed/ métricas calculadas (vai pro repositório e alimenta o dashboard)
```

---

## Fase 1 — métricas básicas

- **ADR**: dano a inimigos por round, usando `dmg_health_real` (dano travado no
  HP restante da vítima, sem overkill). Fogo amigo não conta.
- **KAST%**: rounds com Kill, Assist, Survived ou Traded.
- **Trade kills**: kills que vingaram um companheiro dentro de 5s.
- **Utility damage**: dano de granada (HE + fogo), sem bomba e sem fogo amigo.

---

## Fase 2 — métricas autorais

Aqui está o conteúdo do projeto. Cada métrica abaixo tem a justificativa de jogo
comentada no código, e três delas foram reescritas depois que os dados reais
mostraram que a primeira versão estava medindo a coisa errada.

### Geometria de mira — validada, não assumida

Crosshair placement depende de converter pitch/yaw em direção. Errar a convenção
do Source (pitch **positivo é olhar pra baixo**) inverteria toda a análise sem
dar erro nenhum. Em vez de confiar na documentação, a convenção é validada
contra os dados: **no tick de cada kill, a mira do atacante tem que estar
apontando pra vítima**.

| Convenção | Erro angular mediano no tick da kill | Kills com mira a menos de 5° |
|---|---|---|
| Adotada (pitch+ = baixo) | **1,76°** | **77,6%** |
| Invertida (controle) | 6,52° | 37,2% |

Isso roda como teste automatizado (`tests/test_geometry.py`), com a convenção
invertida junto como controle — se um dia o teste passar nas duas, ele não está
medindo nada.

### Uso de AWP

- **Conversão da briga**: das primeiras brigas de AWP do round, quantas foram
  ganhas. Tiro que errou mas não custou a vida entra numa categoria à parte
  (`no_trade`), fora do denominador: com AWP, muito tiro é de informação ou pra
  negar espaço, e contar isso como derrota infla a taxa de erro do AWPer.
- **Tempo até o primeiro contato**: AWP que busca pick aos 6s joga um papel
  diferente de AWP que aparece aos 40s.
- **Peek vs hold**: classificado pelo deslocamento líquido nos 3s antes do tiro.
  Usa deslocamento **líquido** e não distância percorrida de propósito — quem
  faz jiggle peek e volta pro mesmo lugar está jogando um ângulo, não avançando
  espaço (há teste travando essa decisão). **Peek e hold não são certo e errado**;
  a métrica reporta a distribuição, não dá nota.

**Achado de qualidade de dado:** a flag `is_scoped` do demo não é confiável. 40%
dos ticks marcados como "scopado" aparecem com velocidade acima de 150 u/s, o
que é impossível — AWP scopada anda a ~58 u/s (mediana medida) contra ~208 u/s
sem scope. A propriedade aparentemente fica presa no último valor entre
atualizações. Por isso a classificação usa **posição medida**, não a flag; a
`scoped_fraction` fica no output só como sinal secundário.

### Crosshair placement

O spec do projeto era explícito: **não** medir só distância angular até o inimigo
mais próximo, porque isso pune exatamente o comportamento certo — pré-mirar o
ângulo por onde o inimigo vai aparecer, antes dele aparecer. O score tem três
componentes:

1. **Altura da mira** (sempre vale): quanto a mira está fora da linha da cabeça.
   Sem a malha de navegação do mapa (o download dos assets do awpy exige rede
   liberada), o "nível correto" de cada região é estimado pela **mediana do pitch
   dos atacantes nas kills daquela região** — isso absorve a inclinação real do
   terreno (rampa, degrau) sem precisar da geometria do mapa.
2. **Direção na entrada da briga**: erro angular até o inimigo, mas **só** nas
   amostras que antecedem um contato real do jogador (tiro ou dano dentro de 1s).
   Sem esse filtro, o erro mediano até "o inimigo mais próximo" fica em 36-117°
   mesmo entre profissionais, porque na maior parte do tempo esse inimigo está
   atrás de uma parede. Com o filtro, cai pra 14-24° — que descreve briga de
   verdade.
3. **Crédito de pré-fire**: sem inimigo em alcance, a mira alinhada a um ângulo
   de entrada conhecido da região conta como **acerto**, não como "mira sem alvo".

Os ângulos de entrada são **derivados dos dados** (as direções em que as kills
daquela região de fato aconteceram), não constantes que eu inventei: um ângulo
chutado errado é pior que nenhum, porque premia placement ruim em silêncio. Há
hook de override manual (`MANUAL_ENTRY_ANGLES`) pro meu conhecimento de mapa ter
prioridade — é o principal ponto de calibração do projeto.

### Posicionamento

Heatmaps de presença por lado, e desvio de setup por round. O desvio compara
cada round com o **padrão do próprio time naquela partida**, não com um "setup
certo" escrito por mim: setup correto depende de economia, placar e do que o
adversário vem fazendo, então uma tabela fixa minha seria chute disfarçado de
métrica. O número é um índice relativo (`deviation_index` 1.0 = tão típico
quanto a mediana do time), não uma contagem de jogadores fora do lugar.

---

## Fase 3 — clustering de estilos de jogo

PCA + KMeans sobre 12 features de comportamento (não de resultado) por
**(jogador, round)** — não por jogador: o mesmo jogador é entry num round de
execução e âncora num round de save, e agregar por partida esconde exatamente
isso.

Resultado na partida de teste (4 clusters, 220 player-rounds):

| Cluster | Rounds | Perfil observado |
|---|---|---|
| 0 | 94 | Dano baixo, morre cedo, perto do time, contato aos ~8,8s |
| 1 | 64 | Longe do time (919u), contato tardio (~16s), sobrevive 44% |
| 2 | 41 | Dano alto (186), 2,1 kills, 0,85 trades, sobrevive 56% |
| 3 | 21 | Utility damage alto (41,8), contato mais cedo (~6,2s) |

Os dois eixos do PCA explicam 41% da variação: PCA1 é dominado por impacto
(dano, kills, trades), PCA2 por separação do time e sobrevivência.

**O KMeans agrupa, mas não nomeia.** "Lurker", "entry fragger", "suporte de
utility" são interpretações de jogo que o algoritmo não tem como fazer — a
nomeação é minha, feita olhando o perfil de cada cluster e os rounds
representativos que o dashboard lista, e fica registrada em
`clustering/cluster_names.json`. Enquanto não estiverem nomeados, o dashboard
mostra "Cluster 0, 1, 2..." e avisa que falta nomear, em vez de inventar rótulo.

**Limitação honesta:** a silhueta ficou em 0,205 (k=2) e 0,175 (k=4) — estrutura
fraca. Com 220 player-rounds de uma única partida isso é esperado; a separação
deve melhorar com mais demos processadas. O k=4 foi escolhido por dar grupos mais
interpretáveis que o k=2, mesmo com silhueta um pouco pior — decisão de
interpretação, registrada aqui pra não parecer que o número escolheu sozinho.

---

## Fase 4 — utility e função de jogador

### Utility medida por efeito, não por dano

A Fase 1 media utility como dano de granada. Isso descreve mal o que utility faz
em nível competitivo: a flash que cega dois defensores por 2s não aparece em
número de dano nenhum, e é ela que abre o round. Molotov que tira alguém de um
ângulo costuma causar 0 de dano — o efeito é o espaço.

A métrica principal passou a ser **tempo de cegueira imposto a inimigos**, vinda
do evento `player_blind`, que o awpy não parseia por padrão. É o único lugar do
demo que diz quem ficou cego, por quanto tempo e por culpa de quem.

| | flashes | inimigos cegados | cegueira imposta | flash assists | cegueira no próprio time |
|---|---|---|---|---|---|
| t1ltedbot | 18 | 20 | **74,2s** | 4 | 5,9s |
| 9amaterasu9 | 8 | 13 | 48,3s | 6 | 2,5s |
| donk666 | 9 | 2 | 8,0s | 2 | **25,0s** |

O jogador que lidera ADR na partida (donk666, 126) é o que mais cegou o próprio
time e quase não cegou adversário — o oposto do perfil de quem joga a utility. É
exatamente o tipo de coisa que a soma "utility damage" escondia.

Decisões registradas no código:

- **Flash abaixo de 1,0s não conta como inimigo cegado.** O adversário perde o
  HUD, não a briga. O tempo cru continua somado à parte, então nada fica
  escondido — o limiar filtra a contagem, não o dado.
- **Team flash e self flash não são descontados.** São erros diferentes com
  custos diferentes; um saldo único apagaria os dois.
- **Flash assist exige a vítima ainda cega pela minha flash** quando morreu, na
  janela daquele evento específico — não "morreu perto da minha flash". E matar
  você mesmo um inimigo que você cegou é kill, não assist: as duas ficam em
  colunas separadas.

### Um bug que dois dados independentes pegaram

A tabela `grenades` do awpy mistura duas entidades de nome quase igual:
`CFlashbangProjectile` é a flash arremessada; `CFlashbang` é a flash **parada no
inventário**, com uma amostra por tick do round inteiro na posição de quem a
carrega. Tratar as duas como arremesso dava 965 granadas onde havia 388, e
"primeira utility do round" sempre negativa — antes do fim do freeze time, o que
é impossível.

A correção é validada por duas fontes independentes do demo: a contagem de
projéteis na trajetória tem que bater com os eventos de detonação. Bate exato —
88 flashes, 102 HE, 96 smokes — e roda como teste parametrizado.

### Função de cada jogador

Rótulo de função sai de um limiar explícito sobre uma métrica em que o jogador
**lidera o próprio time**, e a evidência numérica anda junto do rótulo em toda
saída. A comparação é interna porque função é divisão de trabalho dentro do time:
"é quem mais joga AWP no time" descreve um papel; "joga mais AWP que a média dos
10" só descreve a partida.

Resultado na partida de teste:

| Time A | | Time B | |
|---|---|---|---|
| Z_o_R_o | AWPer (AWP em 32% dos rounds) | s-chilla | Abre o round (contato aos 5,4s) |
| donk666 | Principal fragger (126 de ADR) | HLEB | Segura atrás (contato aos 14,1s) |
| t1ltedbot | Suporte de utility (74s de cegueira) | 9amaterasu9 | Suporte de utility (48s) |
| _AmadeuS | *sem função dominante* | xhx | Joga afastado (702u do time) |
| rol1ng- | *sem função dominante* | KREEDZ666 | *sem função dominante* |

**Não existe cota de um de cada função por time.** O time B não teve AWPer acima
do piso e três jogadores ficaram sem função dominante. Isso é resultado, não
lacuna: distribuir rótulos até preencher cinco vagas seria inventar função pra
caber num molde.

**IGL não aparece.** Quem chama o time não deixa rastro no demo — não há áudio, e
liderança não tem assinatura estatística. Seria chute com cara de métrica.

E o rótulo por jogador não substitui o clustering: a mesma aba mostra, embaixo, a
**mistura de clusters** de cada jogador round a round. Ninguém joga o mesmo round
22 vezes, e é essa troca que o rótulo fixo não consegue mostrar.

---

## Dashboard

Streamlit + Plotly, lendo só os parquet leves de `data/processed/` (nunca o .dem).
A paleta foi validada por script (banda de luminosidade, piso de croma, separação
para daltonismo e contraste contra a superfície) em modo claro e escuro. Achado
dessa validação: com três séries a paleta passa em todos os pares, mas nenhuma
quarta cor passa no modo escuro junto das três primeiras. Como o clustering usa 4
grupos num scatter, a saída foi **facetar** — um painel por cluster, destacado
sobre os demais pontos em cinza. Resolve a acessibilidade e lê melhor pro que o
gráfico serve (olhar um cluster por vez pra nomeá-lo).

---

## O que ainda depende de julgamento humano

O projeto foi construído pra ter esses pontos de calibração explícitos, não pra
escondê-los:

1. **Nomear os clusters** — `clustering/cluster_names.json`, olhando o perfil e
   os rounds representativos no dashboard.
2. **Calibrar os ângulos de entrada** — rodar `python -m scripts.show_derived_angles <match_id>`,
   comparar com o conhecimento de mapa e preencher `MANUAL_ENTRY_ANGLES`. Ângulos
   com `n_kills` baixo (4-5) são os que mais precisam disso.
3. **Revisar os limiares** — janela de trade (5s), limiares de peek/hold
   (120u / 250u), janela de contato (1s), tolerância de pré-fire (25°), flash
   efetiva (1,0s). Todos são constantes nomeadas no topo dos módulos.
4. **Revisar os pisos de função** — `TRAIT_SPECS` em `metrics/player_roles.py`.
   Saíram da distribuição de uma única partida, então são o número mais frágil do
   projeto hoje. Há `MANUAL_ROLES` pro meu julgamento sobrepor o limiar, e o
   painel marca o rótulo como manual quando isso acontece.
5. **Validação round a round** — a aba "Detalhe por round" existe pra isso.

**Nota sobre a validação feita até aqui:** as demos usadas são partidas
profissionais do donk, não partidas minhas, então a validação foi por
consistência com o que se sabe do jogador (ele lidera ADR e KAST, como esperado
de um jogador MVP-tier) e por checagem de ordem de grandeza das métricas, não por
memória round a round. Um caso concreto que ficou pendente de julgamento: o donk
tem o **melhor** erro angular em briga (14,6°) e o **pior** score de crosshair
geral, porque a mira dele raramente coincide com os ângulos de consenso da
região — o que, pra um jogador conhecido por jogar off-angles, pode ser estilo e
não erro. É exatamente o tipo de caso que a calibração manual existe pra
resolver.

---

## Como rodar

```bash
pip install -r requirements.txt

# processar uma demo (parse + todas as métricas + clustering)
python -m scripts.process_demo data/raw/sua_partida.dem --match-id sua_partida

# reaproveitar um parse anterior (pula os ~14s de parsing)
python -m scripts.process_demo data/raw/sua_partida.dem --match-id sua_partida --from-interim

# ver os ângulos derivados pra calibrar
python -m scripts.show_derived_angles sua_partida

# testes
python -m pytest tests/ -v

# dashboard de trabalho
streamlit run dashboard/app.py

# página web autocontida (portfólio) — nessa ordem
python -m scripts.build_insights sua_partida
python -m scripts.export_replay sua_partida
python -m scripts.export_web_payload sua_partida
python -m scripts.build_web_page sua_partida    # -> dashboard/web/sua_partida.html
```

**Requer Python 3.11 a 3.13** (o awpy 2.0.2 ainda não suporta 3.14).

Opcional, pro overlay do radar do mapa nos heatmaps: `awpy get maps` (baixa os
assets de mapa; precisa de rede liberada para `awpycs.com`).

## Estratégia de hospedagem

Parsing de .dem é pesado (30-200MB por arquivo, ~14s de CPU por partida) e não
deve rodar num free tier a cada acesso. Por isso: o parsing roda localmente, só
os parquet de `data/processed/` (leves) vão pro repositório e alimentam o
dashboard público, e processar uma demo nova é um passo de CLI local.

## Próximos passos

- [ ] Nomear os clusters e calibrar ângulos/limiares (ver seção acima)
- [ ] Revisar os pisos das funções de jogador com mais partidas — hoje saíram da
      distribuição de uma só, e são o tipo de número que muda com o volume
- [ ] Processar mais demos — a estrutura dos clusters e os ângulos derivados
      melhoram com volume; hoje tudo vem de uma partida só
- [ ] Deploy do dashboard público com os dados pré-processados
- [ ] GIF no README mostrando o CLI processando uma demo nova
