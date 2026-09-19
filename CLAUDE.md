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
- Demos ficam em `demos/` (gitignored, e `*.dem` é ignorado em qualquer pasta).
  São arquivos de 200-500MB. A origem de cada partida (times, evento, hash do
  .dem inteiro, link da HLTV quando conferido) fica em `data/manifest.json`,
  versionado, atualizado por `scripts/process_all_demos.py` e
  `scripts/manifest.py`. `scripts/clean_match.py` apaga demo e interim de uma
  partida só depois de conferir o processado, e registra no manifesto. **Sem o
  interim a partida não pode ser recalculada** (insights, replay, calibração do
  rating leem de lá) sem baixar a demo de novo.
- Parsing leva ~14s por partida. Use `--from-interim` para reaproveitar um parse
  já feito em vez de reparsear enquanto itera nas métricas.

## Estrutura

```
parsing/      wrapper do awpy.Demo
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles,
              positioning, grenades, map_areas, site_roles, player_roles,
              clutch, archetypes (+ archetype_reference.json), player_profile,
              structural_roles, formatting, win_probability, round_spectacle,
              match_highlights, grenade_throws, rating (+ rating_reference.json)
clustering/   playstyle (PCA + KMeans), global_model.json e cluster_names.json
dashboard/    app Streamlit + theme + web/
scripts/      process_demo (CLI), fit_global_clusters, fit_archetype_reference,
              build_player_profiles, show_derived_angles e show_map_areas
              (calibração), narrative, build_site, manifest, clean_match
tests/        ~725 testes (os de navegador usam Playwright + Chrome; sem eles, pulados)
demos/       .dem originais (gitignored)
data/manifest.json origem de cada partida (versionado; scripts/manifest.py)
data/interim/ tabelas brutas em parquet (gitignored, ticks tem 1M+ linhas)
data/processed/ métricas calculadas (versionadas — é o que o dashboard usa)
docs/         site GERADO por build_site.py (NÃO versionado; ver decisão 24)
.github/workflows/pages.yml  publica o site no Pages a cada push
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

   Os grupos chegam à pessoa por `player_profile.cards_de_estilo`: um card por
   grupo com os 3 jogadores de MAIOR FRAÇÃO dos próprios rounds nele ("7 de 22
   rounds — 32%"; ordenar pela contagem favoreceria quem jogou mais rounds), e
   a lista de quem não passa de `CONCENTRACAO_MINIMA_GRUPO` em grupo nenhum
   ("sem grupo dominante"). Texto todo gerado em Python.

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

7d. **Duas camadas de função, e elas NÃO se misturam.**
   - **Estrutural** (`metrics/structural_roles.py`): qual é o trabalho dele no
     round — AWPer, âncora, coringa, rotativo, entry, trader, lurker, suporte.
     Depende do LADO e sai de posição e tempo.
   - **Comportamental** (`metrics/archetypes.py`): como ele executa esse trabalho
     — carrega piano, baiter, mochila, rei do NT, camper, repick.

   Um âncora pode ser carrega piano ou baiter; um entry pode ser carry ou
   mochila. (O plano de trabalho chama o segundo módulo de
   `behavior_traits.py`; ele é `metrics/archetypes.py` -- nome mantido de
   propósito, para não quebrar imports, testes e esta decisão.) São leituras independentes e **nunca colapsam num ranking único**.

   A função é atribuída por (jogador, round), e a da partida é a DOMINANTE nos
   rounds daquele lado, sempre exibida com a concentração ("âncora em 9 de 12
   rounds de CT"). Round sem função reconhecível fica sem função definida — é
   resultado, não lacuna. Isso **substituiu** o `player_roles.py`, que media a
   mesma coisa por partida e sem separar lado.

   Isto não conflita com a decisão 8: lá o KMeans descobre o grupo e por isso não
   pode batizá-lo; aqui as funções são definidas a priori por critério de jogo
   escrito antes de olhar o dado, e o código só mede quem se encaixa.

7h. **O trader é definido POR RELAÇÃO ao entry, e a proximidade sozinha não
   basta.** Ele é o segundo homem da entrada: entra junto com o entry para que a
   morte do entry não saia de graça. A identificação é a distância até o entry no
   instante em que o entry toma o primeiro contato (`RAIO_ATRAS_DO_ENTRY`, o
   mesmo raio de apoio do resto do projeto); a troca efetiva é o RESULTADO, não a
   identificação — trader que tentou e não conseguiu continua sendo o trader
   daquele round, do mesmo jeito que um entry que perde a abertura continua
   sendo entry.

   Os pesos são escolhidos para que proximidade sozinha (0,40) fique ABAIXO do
   piso (0,45): andar perto do entry acontece em qualquer execução de bomb, e sem
   ser o segundo no contato nem trocar a morte, isso é o time junto e não um
   trader. Junto disso, o peso de trade SAIU do suporte: com ele nos dois, as
   duas funções disputavam o mesmo sinal e o resumo por lado passava a depender
   de arredondamento. Medido: o trader aparece em 97 dos 935 rounds de TR e é a
   função dominante em 14 dos 90 jogador-lados; a cobertura de TR subiu de 41%
   para 47%.

7e. **As três funções de CT saem de DUAS dimensões, não de regras soltas:**
   dispersão da posição inicial entre rounds × distância do início ao primeiro
   contato. Âncora = início consistente + briga onde começou; rotativo = início
   consistente + briga longe dali; coringa = início inconsistente. Medido nas 9
   partidas, a dispersão separa bem: 35–251u para quem tem posição fixa contra
   546–631u para quem varia.

7f. **A "posição inicial" é a de SETUP (10s depois do freeze), não a do tick em
   que o freeze acaba.** No instante exato do freeze todos os CTs ainda estão no
   spawn: usar aquele tick zera a dispersão de todo mundo, tira todos do
   bombsite e manda 859 dos 935 rounds de CT para "rotativo" — a classificação
   inteira colapsa numa função só. Foi um teste sintético que fez a troca
   parecer certa; o dado real mostrou que não era.

7g. **IGL nunca é atribuído automaticamente.** O áudio EXISTE no demo
   (`parse_voice` devolve 124–162 mil pacotes por partida, nas 9), mas sem
   transcrição só dá para medir TEMPO DE FALA — e tempo de fala não acha o
   capitão: medido, o jogador com 32% de toda a voz de uma partida era o astro
   do time, não quem chamava. O rótulo vem de `roles_manual.json`, preenchido à
   mão, e há teste que falha se o código escrever nesse arquivo.
   `scripts/igl_candidatos.py` ranqueia CANDIDATOS por time com cinco proxies
   (doa arma, compra menos que o time, contato tardio, granadas por round,
   rating baixo), cada um comparado dentro do time, com aviso de confiança
   baixa. Só imprime; há teste garantindo que ele não escreve nada.

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

8a. **A origem do tempo do timeline é o FIM DO FREEZE TIME (`freeze_end`).**
   Declarada em `metrics/round_breakdown.py` e exibida como relógio (`1:09`), não
   como segundos crus com sinal — número sem referência não se audita. Com essa
   origem, **tempo negativo é impossível**: o módulo levanta erro em vez de
   renderizar. Evento depois do fim do round é legítimo (dá pra morrer nos
   segundos seguintes) e sai marcado como pós-round, com tempo positivo.

8b. **Mortes dentro do freeze time não pertencem a round nenhum.** O demo
   registra mortes entre o `start` e o `freeze_end` — não é warmup (o
   `is_warmup_period` acaba antes do primeiro `start`), é gente se matando no
   tempo parado do pré-partida, e em match_08 o freeze do round 1 dura 93s contra
   20s dos demais. Medido: 11 mortes assim nas 9 partidas, 4 com
   `attacker_steamid == victim_steamid`. Elas produziam DOIS sintomas de uma vez:
   timestamp negativo no timeline e jogador ganhando +1 kill por se matar.
   Exceção decidida pelo Pedro: depois do fim do round que FECHA A METADE (há
   troca de lado em seguida) a morte não conta -- o jogo já foi para o
   intervalo. Caso real: a bomba matou donk (match_24) e ropz (match_26) depois
   do fim do round 12; a HLTV não conta essas mortes e conta as da cauda dos
   outros rounds (6 de 6 conferidos). A sobrevivência do KAST sai da MESMA
   lista de mortes contadas (`basic_metrics.deaths_per_round`), não da vida
   no último tick do round: pelo tick, 71 jogador-rounds apareciam vivos tendo
   morrido (último round da partida, cauda depois do fim), e K-D e KAST se
   contradiziam. O
   filtro é `parsing.kills_do_round_jogado` e precisa ser aplicado em **todo**
   ponto de entrada de kills — `load_interim`, o parse do zero e os scripts que
   leem o parquet direto. A cauda depois do fim do round fica.
   Danos, tiros e cegueiras recebem o MESMO corte do freeze time
   (`parsing.eventos_do_round_jogado`, aplicado em `load_interim` e nos scripts
   que leem direto): medido, 100 danos no freeze time em 9 partidas, sempre em
   blocos de 10 com atacante e vítima do mesmo lado -- restart de round pelo
   servidor. O ADR não era afetado (só soma dano em inimigo), mas o primeiro
   contato ("causou ou sofreu dano") era. A tabela `grenades` fica de fora: as
   linhas dela no freeze time são granada no inventário, com posição nula.

8f. **Round de faca gravado na demo sai no parse, e os rounds são renumerados.**
   Algumas demos profissionais trazem a faca que decide o lado como round 1. A
   regra de lados (`metrics/sides.py`) supõe que o round 1 é o primeiro do
   jogo, e depois da faca o vencedor escolhe o lado: Vitality x Spirit (Mirage)
   saía 15-9 em 24 rounds, placar impossível; sem a faca, 13-10 e K-D idêntico
   ao da HLTV. Critério: primeiro round com dano e nenhum dano de arma de fogo
   (`parsing.remove_round_de_faca`, aplicado em `save_interim`). Há teste que
   varre todas as partidas atrás de placar impossível -- ele pega esta classe
   de bug (lado errado, round a mais) em qualquer demo nova.

8g. **O T do KAST vai para quem teve a MORTE VINGADA.** Até aqui o KAST
   marcava a vítima do kill de trade -- o inimigo que matou e morreu na troca,
   que já tinha o K --, e o T nunca acrescentava nada: trocar a janela de 3s
   para 10s não mudava um único KAST, e o KAST ficava ~5 pontos abaixo do da
   HLTV. Corrigido (`basic_metrics.traded_deaths`), a janela de 5s que o projeto
   já usava é a que mais bate: 24 de 30 jogadores com KAST idêntico ao da HLTV
   em 3 partidas conferidas, erro médio 1,2 ponto (antes, 13 de 30 e viés de
   -4,5). O mesmo `was_traded` alimenta o carrega piano de TR e as "mortes
   trocadas" do perfil, que também estavam desligados. Não é feature do KMeans.
   **Assistência por flash não é o A do KAST**, como na HLTV (decisão do
   Pedro): contra o KAST oficial de 50 jogadores, 38 idênticos sem ela e 33
   com ela.
   **Os 12 que não batem foram investigados (Fase B) e nenhuma regra os
   explica** -- não mude a definição sem dado novo. 9 dos 12 têm KAST A MAIS
   (+1 ou +2), 3 a menos; não é categoria faltando (o A existe: assistência
   comum conta). Testado contra os 50, e todas pioram ou empatam os 38 atuais:
   janela de trade 3/4/6s; trade "por qualquer um" em vez de "por
   companheiro"; sobrevivência medida no fim do round em vez de na cauda;
   contar assistência por flash; KAST só no tempo regulamentar nas partidas
   com prorrogação (cai para 1 de 10); descontar sobrevivência ou trade
   isolados nos rounds de fronteira (12, 24, fim de prorrogação, último).
   Ninguém dos 12 deixou de jogar algum round. Os trades "a mais" se espalham
   de 0,02s a 4,8s, igual aos dos jogadores exatos: não é a janela.
   Com 310 KASTs oficiais (data/reference/hltv_componentes.json) o quadro se
   confirma: 230 de 310 idênticos (74%), excesso de +45 rounds, e o excesso
   está nos rounds creditados SÓ por trade (correlação +0,39; a HLTV não conta
   ~1 em 5 deles). Também descartados: marcar só a última ou só a primeira
   vítima de um matador que matou várias, e ignorar vingança depois do fim do
   round. A regra que separa esses trades não é recuperável dos dados.
   A hipótese "falta a assistência" também foi testada nos 310 e cai: o A já
   conta (assistência comum), 59 dos 80 errados têm KAST A MAIS -- categoria a
   menos não explica excesso --, e dos 21 abaixo só 1 fecha com flash assist.
   Assistência por dano (quem feriu a vítima que um companheiro matou) com
   limite de 41 dá os mesmos 230 (41 é o limite do próprio jogo); sem limite,
   129. Caso isolado sem explicação: SH1R0 na match_38, 13 contra 16 oficial.

8h. **Cegueira por flash é RECONSTRUÍDA nas demos de campeonato** (elas não
   gravam `player_blind`; só as de FACEIT gravam). `parsing/cegueira.py`:
   `flash_duration` recebe a duração TOTAL no tick em que a flash pega, fica
   parado e volta a zero no fim -- e TROCA de valor sem passar por zero quando
   outra flash pega o jogador ainda cego. Início = toda mudança para um valor
   positivo (não só 0 -> positivo). Dono = detonação de flash no mesmo tick
   (janela de 2 ticks); duas candidatas indistinguíveis deixam a cegueira SEM
   DONO. Validado contra o evento real nas 9 de FACEIT: **1.578 de 1.578 com o
   arremessador certo e a duração exata, nenhuma inventada**. Nas 43
   profissionais: 11.736 cegueiras, 41 (0,35%) sem dono por detonação
   simultânea. A tabela reconstruída leva `origem = "reconstruida"`. Medido: a
   proporção de companheiros cegados por flash lançada é a mesma do evento real
   (0,32 contra 0,34) -- cegar o próprio time é assim frequente mesmo.
8i. **Economia do rating estimada no CORPUS, por arma mais cara + colete**
   (`metrics/economia.py`, `scripts/fit_economia.py` ->
   `metrics/economia_reference.json`, refazer a cada demo nova). A versão por
   partida tinha ~20 rounds para dezenas de células e mal agia. Classe lida da
   COMPRA no fim do freeze time; colete importa (pistola inicial sem colete
   vence 4-10%, com colete ~50%). Encolhimento em dois níveis: célula com
   colete -> mesma sem colete -> taxa do lado (K = 20). Conferido contra a
   HLTV: rifle x rifle TR 49,4% (HLTV 48%); o "matar pistola inicial 75%" da
   HLTV bate com rifle contra QUALQUER pistola (75,9%), não com pistola inicial
   (96%) -- o grupo deles é mais largo que o nome. Só a taxa entra na
   conversão em peso, então a diferença de nome não a afeta. Efeito, com os
   pesos congelados: erro contra o rating oficial 0,109 -> 0,094.
8j. **`dmg_health_real` do awpy é recalculado no parsing.** O awpy trava cada
   acerto na vida do INÍCIO do tick; com vários acertos na mesma vítima no mesmo
   tick (balins de escopeta, dois atiradores juntos) a soma passava da vida --
   dois balins de MAG-7 de 79 numa vítima de 100 contavam 158. Correção em
   `parsing.parser.dano_real_no_mesmo_tick` (aplicada no `save_interim`, no
   `load_interim` e nos scripts que leem o parquet direto; idempotente): cada
   acerto travado no que os anteriores do tick deixaram. A base é o dano
   INTEIRO, não a queda de `health` -- a vida é fracionária no jogo, e travar
   pela queda de `health` derrubou o ADR para 131 de 410. Medido contra 410
   ADRs oficiais: 380 -> 401 idênticos no arredondamento, maior diferença 2,74
   -> 0,76. 28 acertos em 22 partidas (584 de dano). Os 9 que sobram estão
   listados em `tests/test_escada.py`, todos abaixo do oficial, sem regra que os
   explique. Há teste varrendo o interim atrás de tick com dano acima da vida.
8c. **Sem atacante, o texto nunca usa o nome de alguém.** E fogo amigo diz
   "morto pelo companheiro X" (5 casos nas 52 partidas), nunca "morreu para X"
   como se X fosse adversário. A ABERTURA do round é o primeiro duelo ganho
   contra o adversário: teamkill, bomba ou queda antes dele não é abertura de
   ninguém (`round_situations` e `opening_kills_with_awp`). O fim de cada
   metade (12, 24, 27, 30...) é marcado na autópsia (`sides.fim_de_metade`). Morte por queda, bomba
   ou dano de zona vem com `attacker_steamid` nulo, e o demo às vezes preenche o
   atacante com a própria vítima. O código diz o que aconteceu ("morreu para a
   bomba") em vez de cair num fallback que nomeia a vítima como matador. Há teste
   varrendo todas as partidas para `attacker_steamid == victim_steamid`.

8d. **Navegação do replay usa o TICK, não o tempo em segundos.** O tick é o dado
   primário; segundos são apresentação. Derivar a navegação do tempo permitiu que
   um `Math.max(0, ...)` no caminho do clique mascarasse o timestamp negativo — a
   interface ficava plausível e o dado continuava errado. Se o tick cair fora da
   janela exportada do replay, a entrada não é clicável e o motivo vai no
   `title`: melhor não navegar que navegar para o lugar errado em silêncio.

8e. **Dinheiro é formatado por `metrics.formatting.format_money`.** `3.750$`, com
   separador brasileiro e símbolo depois. Um lugar só para decidir isso; espalhar
   f-string com `$` garante que a próxima tela escreva de outro jeito.

9. **Convenção de ângulos do CS2: pitch positivo = olhar para BAIXO.** Validada
   empiricamente (erro mediano de 1,76° no tick da kill, contra 6,52° na
   convenção invertida). O teste roda a convenção invertida como controle — se
   um dia passar nas duas, o teste não está medindo nada.

10. **Paleta do dashboard foi validada para daltonismo e contraste.** O scatter
    de clusters é facetado (um painel por cluster) porque nenhuma quarta cor
    passa nos critérios junto das três primeiras no modo escuro. Não troque por
    4 cores num gráfico só.

    Nos gráficos da partida (vantagem e probabilidade de vitória), por pedido
    do Pedro: Time A azul, Time B laranja, round decisivo **roxo escuro
    `#4a3aa7`**. Validado com o script da skill dataviz, os três juntos e em
    todos os pares: pior par para daltônico ΔE 13,0, visão normal 16,3,
    contraste >= 3:1. Esmeralda passava por menos (9,2) e com contraste 2,8:1;
    roxos mais claros falhavam contra o azul. A linha da diferença de rounds é
    uma medida só e fica em tinta neutra; a cor de cada time está nas áreas e
    nas bolinhas, e empate é cinza.

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

15a. **Carrega piano e baiter são as duas pontas de UM eixo** (`sacrifice_index`
    em `metrics/archetypes.py`): percentil dos rounds em que ele pagou a conta E
    o time colheu, menos o percentil das mortes de companheiro por perto sem
    troca. De -1 a +1; rótulo só além de `PISO_CARREGA_PIANO` (0,5) ou
    `PISO_BAITER` (-0,5), então os dois nunca caem no mesmo jogador -- por
    construção, não por desempate. "O time colheu" é igual nas três formas:
    venceu o round, vingou a morte dele, OU matou alguém que ele cegou (a flash
    entrou aqui; antes o piano não usava flash). O retorno é o que separa
    carrega piano de jogador ruim, e isso foi medido: pagar a conta SEM retorno
    correlaciona -0,31 com o rating, COM retorno -0,05. A flash como único
    retorno é rara (43 de 2.308 rounds). Achado para o Pedro julgar: a ponta do
    baiter tem rating médio 1,15 contra 1,05 do meio -- "usa o time de isca
    para conseguir kills" pega muito astro que joga de segundo.

15b. **Repick classifica CADA briga, e a junção é pelo tick da briga.**
    REGRESSÃO: `awp_metrics.classify_engagement_style` foi escrito para a
    primeira briga de AWP (uma por jogador e round) e juntava o resultado por
    (round, jogador). O repick o reusa para todas as brigas, e as k brigas de um
    jogador no round cruzavam com os k estilos dele (k² linhas: 916 em vez de
    480 numa partida), ponderando o `repick_share` errado. A chave agora inclui
    `engagement_tick`. Junto: `scripts/fit_archetype_reference.py` lia o
    interim CRU (sem o filtro de kills do round jogado, sem a correção de dano,
    sem a cegueira) e passou a usar `load_interim` -- a referência era ajustada
    sobre um dado diferente do que ela depois escala.
    Os 10 casos de `scripts/casos_repick.py` mostram 9 com UMA saída e volta só:
    a métrica pega um jiggle, não necessariamente o "fica repickando" repetido.
    Se exige 2+ saídas, é decisão do Pedro.
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

19. **Round decisivo é medido por VARIAÇÃO DA PROBABILIDADE DE VITÓRIA, não
    por soma de pontos.** O esquema antigo somava pesos inventados (ponto sem
    retorno 40, déficit 12 por jogador, clutch 20, multikill 6x, placar apertado
    15, defuse 8) e não havia resposta para "por que clutch vale 20 e defuse vale
    8" — é exatamente o que a decisão 6 chama de chute disfarçado de métrica.

    Agora sai de uma conta só (`metrics/win_probability.py`): programação
    dinâmica sobre os estados de placar até o fim da partida, e o round decisivo
    é o que mais moveu a chance de o time vencer. Três dos componentes antigos
    caem de graça da matemática e **não devem ser reintroduzidos como peso**:
    ponto sem retorno (um round que leva de 40% a 8% tem variação enorme por
    construção), déficit (estado desequilibrado move pouco) e placar apertado
    (11-11 é o pico natural da curva).

    A probabilidade de ganhar um round isolado é **neutra (0,5)** de propósito:
    alavancagem é propriedade do ESTADO DO PLACAR, não de qual time é melhor.
    Usar a taxa observada na própria partida seria circular — o time que venceu
    teve taxa alta justamente porque venceu. Há um ajuste por lado
    (`PROB_ROUND_CT`) desligado por padrão, para quando houver corpus suficiente.

19a. **Impressionante e decisivo são perguntas SEPARADAS, e por isso são dois
    cards.** "Que round mais mudou o resultado" e "que round foi mais
    impressionante de assistir" não são a mesma pergunta: um clutch de 1v3 em
    3-13 é lindo e não decidiu nada; um round banal em 11-11 decidiu muito.
    Somar os dois num score só produz resposta que não serve para nenhuma das
    duas. O impressionante vive em `metrics/round_spectacle.py`, onde **pesos
    relativos são legítimos** porque a pergunta é subjetiva — e ficam todos
    expostos no card, componente por componente, para recalibrar olhando caso
    concreto. Medido: nas 9 partidas os dois rounds coincidem em 1 e divergem em
    8, e os dois casos estão testados.

19b. **Partida sem round decisivo é RESULTADO, não lacuna.** Numa partida de
    placar largo a diferença se construiu ao longo do jogo, e eleger um round à
    força inventa uma virada que não houve — era o que a soma de pontos fazia,
    porque sempre existe um máximo. O piso não é número solto: é 1,5x o round
    mais barato possível daquele formato (`P(1,0) - P(0,0)`, 0,081 no MR12), o
    mesmo fator com que o projeto ancora o piso de entry ao acaso. Medido: ficam
    sem round decisivo exatamente as 5 partidas de placar largo (13-5, 13-6,
    13-7, 13-8, 4-13) e ficam com as 4 apertadas (dois 13-9, dois 11-13). A
    interface renderiza esse caso com frase própria, não com card vazio.

19c. **O formato (MR12/MR15) sai da demo, pela TROCA DE LADO.** Não se assume
    MR12. Pelo placar os dois são indistinguíveis num caso real: MR12 com
    prorrogação termina em 16-14 exatamente como um MR15 sem prorrogação. A troca
    de lado separa. Ressalva registrada: `HALFTIME_ROUND = 12` ainda está fixo em
    sete módulos, e `build_insights` **avisa** quando o formato detectado
    discorda dele em vez de seguir em silêncio — o placar por time depende disso.

19d. **Economia é LEITURA ao lado do round decisivo, nunca peso no score.** Se o
    dinheiro entrasse na conta que elege o round, a decisividade passaria a
    depender de quanto os times tinham, e isso é outra pergunta. O card mostra o
    equipamento médio dos dois lados (`format_money`) e, quando quem perdeu
    estava com equipamento igual ou superior, diz isso — é a informação mais útil
    do card, porque aí a derrota não tem desculpa de economia.

20. **A aba de leitura tem estrutura FIXA de três blocos:** round decisivo em
    cima, MVP embaixo à esquerda, outro destaque embaixo à direita. Estrutura
    fixa é o que torna duas partidas comparáveis de relance -- se o layout
    mudasse conforme o que a partida teve, cada página ensinaria a ser lida de
    novo. O gráfico de probabilidade de vitória saiu daqui e vive só na aba
    Placar: a mesma informação duas vezes na mesma página só gasta espaço.

    O card do MVP mostra os COMPONENTES e não só o índice, cada um com o melhor
    valor entre os outros jogadores ao lado ("126,1 de ADR contra 107,3 de
    s-chilla"). Índice agregado sozinho não deixa conferir nada.

20a. **O segundo card admite destaque NEGATIVO**, e o tom é fato com número.
    "Terminou com 38 de ADR contra 71 do segundo pior, e o time venceu mesmo
    assim" é análise; adjetivo sem número atrás é xingamento. Card negativo sem
    número E sem referência **não renderiza** -- o candidato é descartado e a vez
    passa para o próximo. O negativo se diferencia por rótulo e hierarquia, não
    por vermelho de alarme (decisão 10).

20b. **Bottom frag exige distância destacada, não a última posição.** Alguém
    sempre é o último; isso é aritmética, não observação. Ele só vira card se
    estiver a `MIN_DISPERSOES_BOTTOM_FRAG` (1,5) abaixo do PENÚLTIMO, medido em
    desvios absolutos medianos dos outros. MAD e não desvio padrão: o próprio
    afundamento inflaria o desvio padrão e viraria parte da "dispersão normal".
    Pela mesma lógica, **mochila exige vitória do time** -- número ruim em time
    que perdeu é jogador ruim, não alguém carregado.

20d. **No empate do topo, vence o destaque NEGATIVO.** O percentil satura:
    vários candidatos batem em 0,99-1,00 e a pontuação perde resolução
    justamente no topo. Medido: o match_03 tinha um bottom frag em 1,00 empatado
    com um repick em 1,00, e vencia quem tivesse sido inserido antes na lista --
    acidente, não critério. O desempate é explícito e prefere o negativo, porque
    o card da esquerda já é um destaque positivo: um segundo positivo repete o
    tipo de informação, um negativo acrescenta. **Isso não afrouxa trava
    nenhuma** -- o negativo continua tendo que passar pela distância do bottom
    frag, pela vitória da mochila e pela evidência com número.

    Registro de um diagnóstico errado meu: antes de olhar os candidatos, a
    recomendação foi afrouxar `MIN_DISPERSOES_BOTTOM_FRAG` para fazer o card
    negativo aparecer. Era errado -- os negativos já competiam e já venciam
    empates; o defeito estava na ordenação.

20c. **Comparabilidade entre funções: cada pontuação significa "o quanto isto
    está acima do normal".** Papéis comportamentais já vêm como percentil contra
    o conjunto das partidas (decisão 16, que é mais forte que padronizar dentro
    da partida). Funções estruturais usam a concentração **ponderada pela fração
    de companheiros que ela supera** -- a concentração crua não serve, porque
    "coringa em 12 de 12 rounds" dá 1,0 e é o caso COMUM: medido, isso elegia o
    card da direita em 6 das 9 partidas e afogava carrega piano e AWPer
    legítimos. Ponderada, quando todos são igualmente fixos a pontuação vai a
    zero, que é a resposta certa.

21. **O tick de soltura de uma granada é derivado por ANCORAGEM GEOMÉTRICA, não
    por atraso fixo de animação.** O `weapon_fire` marca o clique; a granada sai
    da mão depois, e é o ângulo da soltura que importa. Varre-se a janela entre
    o clique e o primeiro sample do projétil e vence o tick cuja geometria
    (olhos + deslocamento na direção da mira) melhor reproduz o ponto observado.

    A separação que faz isso funcionar: o deslocamento da mão age no plano
    HORIZONTAL e a altura dos olhos age só na VERTICAL. O ajuste horizontal
    determina o tick e o deslocamento sem nenhum parâmetro livre por arremesso,
    e a altura cai depois como MEDIÇÃO. É isso que mantém o resíduo honesto como
    medida de confiança.

    Medido em 3.020 arremessos: resíduo mediano 0,51u, 99,9% abaixo do limiar, e
    o atraso da animação sai em 7 ticks (109 ms) em vez de chutado. A altura dos
    olhos derivada dá **64,17u**, o que VALIDA as 64 unidades que o projeto já
    supunha -- e revelou um deslocamento vertical de +3,2u no ponto de
    nascimento da granada, igual em pé e agachado, que ninguém tinha modelado.

    Quando o jogador está parado e a mira quieta, o resíduo é plano na janela e o
    tick fica indeterminado. É inofensivo (a mira varia 0,29° na mediana) mas o
    empate é desfeito pelo tick mais próximo do projétil -- sem isso, 312 dos
    3.020 saíam com soltura ANTES do clique.

21a. **A força do arremesso é inferida da velocidade RELATIVA ao jogador.** Sem
    descontar a velocidade de quem arremessou, todo run-throw curto vira
    arremesso longo. O desconto é vetorial (projetar o módulo na direção da
    granada superestima quem corria de lado) e usa `FATOR_HERANCA = 1,25`,
    medido: a inclinação de (v_relativa ~ v_jogador) cruza zero em 1,250 e o IQR
    do grupo dominante é mínimo no mesmo ponto. Dois critérios independentes
    coincidindo num 1,25 redondo dizem que é constante do jogo. Efeito: parado x
    correndo saiu de 674 x 727 u/s para 672,0 x 672,7.

    Os três grupos saem por moda (decisão 5, nada de bin fixo): 201, 440 e 674
    u/s. **Os rótulos curto/médio/longo são do Pedro** -- o código mostra
    "força A/B/C" com a velocidade ao lado até ele confirmar, mesmo princípio da
    decisão 8.

21b. **A reprodução por console depende de validação prática do Pedro, não do
    código.** Origem do `setpos`, sinal do `setang` e pré-requisitos de servidor
    só se confirmam rodando no jogo. Enquanto não houver essa conferência, o
    módulo não pode afirmar que um lineup é exato -- um lineup errado é pior que
    nenhum, porque o cara treina errado.

22. **O rating é uma REIMPLEMENTAÇÃO da metodologia do Rating 3.0, não o
    Rating 3.0 da HLTV.** A HLTV publicou a metodologia; os coeficientes e os
    pesos de cada sub-rating são **fechados**. Então este número não é o oficial
    e não pode ser apresentado como se fosse -- em nenhum lugar da interface, do
    código ou do README. O rótulo obrigatório vem no próprio resumo do módulo, e
    há teste que falha se ele deixar de dizer isso.

    O que É honesto afirmar: os seis sub-ratings seguem a metodologia publicada,
    o ajuste de economia usa a única reta que passa pelos dois pontos que a HLTV
    divulgou (rifle x rifle 48% -> 1,10; pistola inicial 75% -> 0,54), e os pesos
    do agregado são provisórios até serem estimados por regressão contra ratings
    oficiais.

22a. **O Round Swing usa MODELO PARAMÉTRICO, não contagem por estado.** O espaço
    de estados (vivos x vivos x bomba x equipamento x lado) tem centenas de
    combinações e o corpus tem ~200 rounds por partida: frequência empírica por
    estado daria "100% de vitória" a partir de dois casos. Uma regressão
    logística com quatro entradas generaliza e nunca devolve certeza absoluta.
    Medido nas 9 partidas: AUC 0,897 e Brier 0,129 sobre 2.692 amostras.

    **A qualidade do Round Swing depende do tamanho do corpus e melhora a cada
    demo processada.** O desempenho é reportado no resumo de propósito, para não
    virar fé.

    Registro de um bug de modelagem: cada evento gera DUAS linhas, uma por lado,
    com rótulos opostos. Com a bomba entrando como flag `plantada` (1 nas duas),
    ela ficava perfeitamente não-informativa por construção e o coeficiente saiu
    em -0,0001. Bomba plantada é vantagem de quem plantou, então ela entra COM
    SINAL: +1 para o TR, -1 para o CT. Com o sinal, o coeficiente é +0,71.

22b. **O Round Swing é normalizado por desvio, não por razão.** A regra da HLTV
    de que round perdido não gera swing positivo corta os positivos de quem
    perdeu e deixa os débitos inteiros, então a média do corpus é NEGATIVA
    (-0,043). Dividir pela média inverteria o sinal de todo mundo -- foi o que
    aconteceu na primeira versão. Ele é centrado em 1,00 e escalado pelo desvio,
    com a dispersão-alvo saindo da mediana do desvio relativo dos outros cinco
    sub-ratings, não de um número escolhido.

22c. **As 9 demos do corpus NÃO servem para calibrar contra a HLTV.** São
    partidas de FACEIT -- arquivos identificados por UUID de FACEIT, elencos que
    são pugs (donk com companheiros diferentes a cada partida), não line-ups
    profissionais. **A HLTV não publica rating para partidas de FACEIT.** A
    calibração exige demos de partidas oficiais cobertas por ela, e o mínimo
    estatístico está em `scripts/fit_rating.py`: 7 de treino + 3 de teste, com a
    divisão feita por PARTIDA e nunca por jogador.

22e. **O rating aparece na aba Jogadores** (coluna ordenável, com a nota de
    implementação própria vinda do Python) e sai do `build_insights`, com o
    modelo de round GLOBAL reconstruído da referência
    (`ModeloDeRound.da_referencia`) -- nunca treinado só na partida.

22f. **O Round Swing soma zero por evento e inclui o fim do round** (Fase D,
    conferido contra o Swing OFICIAL de 310 jogadores em
    `data/reference/hltv_componentes.json`). REGRESSÃO: o matador levava só
    CREDITO_KILL (55%) e a parte sem destinatário (sem dano de outro, sem
    flash, sem trade) sumia -- média -4,67 p.p. contra -0,01 oficial, escala
    0,70. Agora o matador fica com a sobra, e o salto final da chance (do
    último estado a 1 ou 0) vai em partes iguais para quem terminou vivo:
    correlação 0,892, escala 1,01, erro 1,93 p.p. Plantar a bomba como evento
    foi testado e não muda nada (fica de fora). A média ainda sai -0,81 por
    causa da regra do round perdido, que a HLTV declara mas aplica de um jeito
    que fecha em zero; como cada sub-rating é centrado na média do corpus, o
    deslocamento não afeta o rating. Rating: erro de TESTE 0,085, correlação
    0,956, erro por time entre 0,078 e 0,093 nos 6 times grandes.
22g. **Escada de validação: contagem exata antes de olhar o rating**
    (`scripts/escada_validacao.py`, K-D-ADR oficiais de 410 jogadores em
    `data/reference/hltv_placar.json`; `tests/test_escada.py` trava os degraus 1
    e 2). Rounds 41/41, kills e mortes 410/410, ADR 401/410, KAST 230/310.
    Multi-kills e aberturas sem dado oficial ainda. Cada print foi casado com a
    partida pelo RATING, não pelo K-D, para o degrau 1 não ser circular.
22j. **Degrau 4 pela página "Detailed stats" da HLTV** (`data/reference/
    hltv_detalhado.json`, POR SÉRIE -- os nossos mapas são somados; 5 séries
    inteiras no corpus, 50 jogadores). Aberturas feitas e sofridas, rounds de
    multi-kill, kills, headshots e mortes: 50/50 exatos (travado em teste).
    Abertura = primeira kill em INIMIGO do round; as da HLTV somam exatamente um
    por round. O que ainda não bate, medido:
    - clutch (1vsX vencido): 32/50 com o antigo "último vivo contra 2+"; 41/50
      contando o 1v1. DECISÃO DO PEDRO: clutch é 1vX com X >= 1, alinhado à
      HLTV, e é a definição ÚNICA do projeto (`metrics/clutch.MIN_ENEMIES_ALIVE`,
      usada também no `build_insights`). DEFINIÇÃO não é PESO: o rei do NT pondera
      cada tentativa pelo X (1v1 perdido pesa 1, 1v3 perdido pesa 3), porque o
      papel é sobre o quase-clutch difícil, não sobre perder duelo; e no round
      mais impressionante o clutch só pontua de 1v2 para cima
      (`MIN_INIMIGOS_CLUTCH_ESPETACULO`). Nos cards, contagem e conversão
      aparecem sempre juntas, com a quebra por X ("1v1: 1/3, 1v2: 0/2"). Os 9
      que ainda não batem ficam em aberto.
    - assistência: 19/50, faltando 44 no total, 41 delas de FLASH. O evento de
      kill do jogo guarda UM assistente; a HLTV conta a flash à parte. Pela
      cegueira reconstruída, "cegou e a vítima morreu ainda cega para um
      companheiro" acerta o total (+6) mas só 22/50 por jogador.
    - morte trocada (D(t)): 19/50 com a janela de 5s, e 30 a MAIS -- é a origem
      direta do excesso do KAST (8g). O total bate com janela de ~4,25s, mas nenhuma
      janela (2 a 6s), nem "vingada por qualquer um", nem "só a última vítima do
      matador", nem "companheiro matou qualquer inimigo" passa de 20/50 por
      jogador. A HLTV atribui a troca por uma regra que os dados não mostram.
22h. **O Swing OFICIAL soma zero -- confirmado, não suposto.** Nos 310 Swings
    oficiais, a soma dos 10 de uma partida dá zero (dentro do arredondamento) em
    28 de 31, e as três exceções são exatamente as partidas com uma morte DENTRO
    do round sem matador inimigo (fogo amigo do FalleN e do molodoy no KSCERATO,
    queda do TeSeS): a vítima paga e ninguém recebe. Morte pela bomba e morte
    depois do fim do round somam zero -- o round já estava decidido. Nosso código
    faz o mesmo com fogo amigo (match_43: -0,54 nosso, -0,54 oficial). Isto
    REFUTA a regra do round perdido aplicada como corte: cortar o positivo de
    quem perdeu deixa a soma negativa em TODA partida (a nossa: mediana -8,7 por
    partida). Nosso Swing ainda vaza em três pontos, medidos: perdedor sem
    ninguém vivo no fim (o salto final não é debitado de ninguém), vencedor sem
    ninguém vivo (bomba explodindo com o TR todo morto: os CTs pagam e ninguém
    recebe), e eventos com o round já decidido (morte pela bomba, cauda). Com os
    três fechados a soma zera em 28 de 31, as mesmas três do oficial, e o erro
    por time cai de 4,89 para 3,29 p.p. A correção no código ESPERA a decisão do
    Pedro sobre como fica a regra do round perdido (sem a regra ou devolvendo o
    corte ao próprio time -- os dados não separam as duas).
22i. **Dividir pela média e padronizar pelo desvio dão o MESMO rating aqui.**
    Com agregado linear, pesos ajustados e intercepto livre, x/média e
    (x - média)/desvio são a mesma família de funções: medido, previsões
    idênticas até 1e-15 em validação deixa-uma-partida-fora. A mudança do
    Rating 2.0 para desvio-padrão só pesa com pesos FIXOS. Não "corrija" isso.
    O defeito de forma que existe é outro: `fit_rating.componentes_do_corpus`
    normaliza cada partida pela PRÓPRIA média (não passa a referência), e o site
    aplica os pesos sobre a normalização do CORPUS -- os pesos são ajustados numa
    escala e usados em outra. Medido, custou pouco desta vez (site 0,081 contra
    0,083 dentro da amostra), mas tem que ser alinhado na próxima calibração.
    Onde o resíduo do rating se concentra (430 jogadores, controlando o nível):
    kill com menos de 60 de dano próprio +0,105, morte trocada -0,178, kills de
    CT menos de TR +0,112 -- os três no sentido dos detalhes que a HLTV publicou
    (penalidade da kill "assistida", morte trocada punida menos, cálculo por
    lado), mas juntos explicam só 5,3% da variância do resíduo. O resto é
    espalhado: forma do modelo de probabilidade, não componente.
23. **Anotação no mapa: coordenada de jogo, um único ponto de redimensionamento,
    camada sempre transparente.** A camada vive em `dashboard/web/annotations.js`
    e `annotations.css`, injetados no build; o template não tem texto nem estilo
    dela (há teste).
    - Traço é guardado em **unidade de jogo**, com mapa e impressão da
      calibração do radar em CADA traço. A impressão sai de
      `metrics.annotations.impressao_da_calibracao` no build, a mesma função que
      valida o arquivo exportado.
    - Atribuir `width`/`height` a um canvas APAGA o conteúdo. Todo
      redimensionamento (carga, janela, tela cheia, densidade de pixel, aba que
      aparece) passa por `reprojetaTudo()`, que redesenha o mapa E as anotações
      a partir dos dados. Nunca redesenhe a partir do que está pintado.
    - **Regressão registrada:** o mapa "sumiu" porque a regra geral
      `.board canvas { background: #161d26 }` do template pegava as camadas de
      anotação, que ficavam opacas por cima do mapa. O mapa estava desenhado o
      tempo todo. Diagnóstico por captura de tela real, não por leitura do
      canvas: é o pixel composto que a pessoa vê.
    - Persistência: memória -> localStorage (chave por partida e round, com
      atraso) -> exportar/importar JSON. A página abre como arquivo local ou no
      GitHub Pages, e nenhum dos dois aceita escrita no servidor.
    - Os testes de comportamento rodam num Chrome de verdade
      (`tests/test_annotations_browser.py`, Playwright); sem navegador eles são
      pulados, e os estruturais de `test_annotations.py` ficam como rede de
      segurança.

24. **Saída gerada não vai para o repositório.** O que se versiona é o que gera a
    saída (código e `data/processed/`), não a saída. O site em `docs/` era 54% do
    histórico (120 de 224 MB, 24 versões) e foi PURGADO em 2026-09-19 com
    `git filter-repo`, com a concordância do Pedro (repositório nunca
    compartilhado): pacote local 219 -> 96 MB, clone do GitHub com `.git` de 105
    MB. `docs/` está no `.gitignore`, e o Pages é gerado pelo GitHub Actions
    (`.github/workflows/pages.yml`) a partir do código, como artefato -- não
    entra em branch nenhum. Backup de antes da reescrita: a pasta irmã
    "...- BACKUP antes da reescrita 2026-09-19", com `historico-completo.bundle`.
    Teste obrigatório depois de qualquer mudança nisso: clonar do zero, rodar a
    suíte (os testes que dependem de `data/interim/` são PULADOS, nunca
    quebram) e gerar o site só com o que está versionado.
    Peso que continua crescendo, e é deliberado: `replay.json` (50 MB do
    histórico) e `web_payload.json` (16 MB) em `data/processed/`. O replay sai
    do interim, que não é versionado, então sem ele um clone não reconstrói o
    replay.

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
- Ratings oficiais da HLTV em `data/reference/hltv_ratings.json`, e demos de
  partidas oficiais para preenchê-lo. Sem isso os pesos do rating continuam
  provisórios.
- Pesos dos seis sub-ratings: **ajustados** contra os ratings oficiais de 43
  partidas (430 jogador-mapas) e gravados em `metrics/rating_weights.json` por
  `fit_rating --fit-pesos --gravar` -- regressão com pesos >= 0 e intercepto
  livre, validada deixando uma partida fora (erro médio 0,111, correlação
  0,921). `PESOS_PROVISORIOS` ficou só como plano B sem o arquivo. Os pesos
  valem para a referência de escala em que foram ajustados: refazer a
  referência exige refazer os pesos (o rating marca `pesos_desatualizados`).
  Os da divisão de crédito do Round Swing (`CREDITO_KILL` e companhia)
  continuam do Pedro.
  `py -3.12 -m scripts.fit_rating --fit-pesos` mostra os pesos ajustados ao
  lado dos atuais, com erro fora da amostra.
- Rótulos dos três grupos de força de arremesso (201 / 440 / 674 u/s): confirmar
  se A/B/C são curto/médio/longo. Rode o diagnóstico de `metrics/grenade_throws`.
- Limiares do card de destaque (`metrics/match_highlights.py`): piso de evidência
  (0,70), limiar de empate (0,05) e as dispersões do bottom frag (1,5 a 3,0).
- Limiares do round decisivo e do impressionante: o fator do piso de
  decisividade (`FATOR_MINIMO_DECISIVO`, 1,5), a distância que declara empate no
  topo (`LIMIAR_EMPATE_WPA`, 0,02) e **todos os pesos de
  `metrics/round_spectacle.py`** — clutch (26 + 11 por inimigo extra), multikill
  (8 por kill acima de 2), desvantagem (9 por jogador), desarme no limite (20) e
  abertura limpa (12). Os pesos do espetáculo são subjetivos por natureza; o card
  mostra quanto cada componente deu em cada round justamente para recalibrar
  olhando caso concreto. Frequência medida nas 9 partidas: multikill 85x,
  abertura limpa 48x, desvantagem 23x, clutch 19x, desarme no limite 1x.
- Limiares da autópsia de round (`metrics/round_breakdown.py`): equipamento médio
  que caracteriza economia (2000$), diferença de equipamento que torna a economia
  explicativa (1500$) e a cauda pós-round (8s). Registro da medição: dos 56
  rounds abaixo do limiar de eco nas 9 partidas, **18 são round de pistola com os
  dois times igualmente pobres** — ali a economia não explica a derrota, e o
  texto passou a dizer isso em vez de tratar os dois casos igual.
- Limiares dos papéis (`metrics/archetypes.py`): distância máxima para uma morte
  de companheiro contar como "do seu lado" (900u), assinatura de repick (250u de
  percurso, razão 3x), mínimo de tentativas de clutch (3), mínimo de rounds com
  AWP (4), compra abaixo da média do time (-400), fração do time de rifle (60%),
  e o quanto um papel crítico precisa se destacar para virar card (0,85).
- Distribuição de todo índice de função, antes (9 de FACEIT) e depois (corpus
  inteiro): `py -3.12 -m scripts.calibration_report`. Tabela de funções com os
  componentes abertos, por jogador: `py -3.12 -m scripts.tabela_funcoes`.
- Pisos do eixo carrega piano <-> baiter (`PISO_CARREGA_PIANO` 0,5 e
  `PISO_BAITER` -0,5) e se o repick exige mais de uma saída e volta
  (`scripts/casos_repick.py`).
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
- O modelo de probabilidade de vitória supõe **independência entre rounds**, e
  momentum e economia violam isso: depois de perder um round o time perde também
  a compra do seguinte, e a chance real do próximo round não é mais 0,5. Modelar
  economia exigiria um estado (placar, dinheiro, armas) grande demais para 9
  partidas. Fica registrado como simplificação, não como descuido.
- **Prorrogação é 50/50 a partir do empate** (12-12 no MR12). O OT tem formato
  próprio — MR3, e um novo empate leva a outro OT — e modelar isso exigiria uma
  segunda cadeia de estados com critério de parada arbitrário para a sequência de
  prorrogações. Nenhuma das 9 partidas do corpus foi para OT, então a
  simplificação nunca foi exercitada em dado real.

## Como validar mudanças

```bash
py -3.12 -m pytest tests/ -v          # 291 testes
py -3.12 -m scripts.process_demo data/raw/match_01.dem --match-id match_01 --from-interim
py -3.12 -m streamlit run dashboard/app.py
py -3.12 -m scripts.escada_validacao     # rating: contagens contra a HLTV, de baixo para cima
```

Ao mexer numa métrica, confira o efeito na tabela round a round, não só no
agregado — número agregado plausível pode esconder lógica errada.
