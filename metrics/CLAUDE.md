# metrics/: regras das métricas

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. `metrics/tactics.py` e `metrics/annotations.py` espelham o JS: as regras deles
estão em `dashboard/web/CLAUDE.md` e valem aqui.

## Posição, mira e duelo

- Peek ou hold pelo deslocamento LÍQUIDO da posição medida, não pela flag `is_scoped`; jiggle
  (sair e voltar) é hold (1, 2)
- Repick é jiggle MAIS evento no ângulo (atirou, causou ou sofreu dano, ou alguém morreu a menos de
  `BAIT_MAX_DISTANCE`); o número de saídas é qualidade, não critério; o desfecho é campo à parte,
  fora da identificação, e morte para utility fica fora de qualquer taxa de duelo (15d)
- Repick classifica CADA briga: a junção inclui `engagement_tick` (15b)
- Tiro de AWP que erra sem custar a vida é `no_trade`, fora do denominador da conversão (3)
- Crosshair NÃO é distância ao inimigo mais próximo: a direção só é cobrada nas amostras antes de
  contato real (tiro ou dano em até 1 s) (4)
- Ângulo de pré-fire sai dos dados por moda circular; nunca constante inventada nem bin fixo (5)
- Desvio de setup é contra o padrão do próprio time, não um setup "certo"; é índice relativo
  (`deviation_index`), não contagem de jogadores fora do lugar (6)

## Funções e papéis

- Função estrutural (`structural_roles`: o trabalho, por lado, de posição e tempo) e traço
  comportamental (`archetypes`: como executa) não se misturam nem viram ranking único; a função é
  por (jogador, round), a da partida é a dominante do lado, exibida com a concentração, e round sem
  função reconhecível fica sem função; `archetypes.py` não muda de nome (7d)
- Função dominante: as duas com mais rounds no lado; até 1 round de diferença é empate; no empate
  vence o AWPer só se for o AWPer do TIME (`awpers_do_time`); senão, "sem função dominante", com as
  empatadas e as contagens (28)
- Âncora, rotativo e coringa: dispersão da posição inicial entre rounds × distância do início ao
  primeiro contato; a posição inicial é a de setup (10 s após o freeze), não a do freeze (7e, 7f)
- Âncora e lurk por ÁREA (A/Mid/B), não por distância nem tempo; spawn fica fora da partição e
  passagem rápida pelo outro site não é rotação (`MIN_OTHER_SITE_SHARE`) (12, 14)
- Entry é AÇÃO: fração de rounds em que foi o primeiro do time a encostar no adversário, não
  segundos até o contato; empate no primeiro contato não é abertura de ninguém (13, 17)
- Trader é o segundo homem do entry, perto dele no primeiro contato do entry; a troca é resultado,
  não identificação; proximidade sozinha (0,40) fica abaixo do piso (0,45); o peso de trade não
  volta ao suporte (7h)
- "Longe do time" exige piso absoluto, não só o corte na mediana; com um companheiro dentro de
  `RAIO_COMPANHEIRO` ninguém está longe (7c)
- Carrega piano é PRODUTO esforço × benefício, nunca subtração, em três formas (morrer abrindo
  espaço, segurar bomb sozinho, arma pior para o companheiro comprar); não reduza a entry (15)
- Carrega piano e baiter são pontas de UM eixo (`sacrifice_index`), rótulo só além de ±0,5; "o time
  colheu" = venceu o round, vingou a morte dele ou matou quem ele cegou (15a)
- Traço é comparado DENTRO da função, com o esperado do corpus; cada braço do eixo contra a
  população da mesma função dominante (`quantis_por_funcao`); o valor absoluto fica ao lado do
  normalizado (15c, 15e)
- A escala dos papéis é do corpus (`archetype_reference.json`), nunca da partida (16)
- Lurker: sem os rounds com AWP, contra a taxa esperada da função daqueles rounds (a própria função
  lurker fica fora da régua), pelo `off_team_relativo`; abaixo de `MIN_ROUNDS_SEM_AWP` é DADO
  INSUFICIENTE, não "não qualifica" (29, 31)
- Rótulo de jogador: líder do time E acima do piso, com amostra mínima; suporte medido por round;
  estabilidade < 0,70 sai como "(tendência)", também na função estrutural (39)
- O perfil por jogador é a leitura, não média de cluster: taxa sempre com bruto (`_n`, `_d`),
  régua e amostra fraca (`_fraco`), também por lado (`_ct`, `_t`); cards de estilo pela maior
  fração dos próprios rounds (7a)
- Round sem contato tem tempo até o contato NULO, nunca um valor inventado (7b)

## Tempo, economia e KAST

- Timeline conta do fim do freeze e é exibida como relógio; tempo negativo levanta erro; evento
  depois do fim do round é pós-round, com tempo positivo (8a)
- KAST: o T é de quem teve a morte vingada; assistência por flash não é o A; sem dado novo, a
  definição não muda (8g)
- Economia estimada no CORPUS por arma mais cara + colete, lida da compra no fim do freeze;
  empate de classe divide o round; eco, força e compra cheia são agregação dessas classes, a fonte
  única de economia do projeto, sem limiar novo (8i)

## Round decisivo, cards e rating

- Decisivo = maior variação da chance de vitória; ponto sem retorno, déficit e placar apertado não
  voltam como peso; round isolado neutro (0,5), nunca a taxa da própria partida (19)
- Sem decisivo abaixo de 1,5× o round mais barato do formato (19b)
- Prorrogação: o alvo sobe 4 a cada uma, até `MAX_PRORROGACOES_MODELADAS` (estado 0,5 ali); a
  recursão recebe o alvo do FORMATO, nunca o ajustado (19e)
- Bottom frag a 1,5 MAD abaixo do PENÚLTIMO; mochila exige vitória; no empate do topo vence o
  negativo, sem afrouxar trava nenhuma (20b, 20d)
- Pontuação de função: concentração ponderada pela fração de companheiros que ela supera (20c)
- Clutch é 1vX com X ≥ 1; definição não é peso; nos cards, contagem e conversão juntas, com a
  quebra por X (22j)
- Round Swing: regressão logística (não contagem por estado), bomba COM sinal; variação de
  probabilidade pura, sem corte de round perdido; soma zero por evento, com o fim do round e
  exceto morte sem matador inimigo; centrado em 1,00 e escalado pelo desvio
  (22a, 22b, 22f, 22h, 22k)
- Dividir pela média ou padronizar dá o mesmo rating com pesos ajustados: não "corrija" (22i)
- Rating por lado, com kill assistida e morte trocada como componentes, na mesma escala de
  referência da calibração (22l)

## Arremesso

- Cada campo do arremesso declara a fonte (`lido` da demo ou `inferido` pela rota A), nunca
  misturadas em silêncio (21a)
- Inferido: velocidade relativa ao jogador; tolerância, guarda do voo e faixa de postura saem do
  gabarito (`metrics/gabarito_constantes.json`), nunca digitadas; o que for ambíguo fica NEUTRO,
  com o motivo; rótulo curto/médio/longo só com exatamente três grupos (21a)
- Mudança na biblioteca da rota A só entra com piora 0 (`py -3.12 -m pesquisa.piora_rota_a`) (21a)
- Com `grenade_thrown`, o tick do evento é a soltura e a ancoragem vira validação;
  `user_ducking` é transição de agachar, não postura; a postura sai da altura de saída corrigida
  pelo botão, com faixa neutra por quantil recalculada a cada gabarito novo (21c)

## Erros no Perfil (`erros.py`)

- Cada tipo é função pura sobre a partida processada, com nível escrito ("explícito" ou "depende
  da tática") pela primeira regra que se aplica; eco, pistola, time guardando arma e depois do fim
  do round ficam de fora; "perto" só no mesmo andar (46)
- Nada de tipo que o dado não mede (o inventário só é lido no fim do freeze: "utilidade no bolso"
  não existe nem se estima) (46)
- Todo erro é de um lado só e nenhum tipo soma os dois; a régua é anônima por (lado, função), e
  os lados nunca se misturam, nem como queda (46)
- Ponto a melhorar só acima do percentil 90 da régua e com pelo menos 2 ocorrências; custo é
  ΔWPA "pela estimativa do modelo"; `DIST_TROCA` só muda depois da calibração do Pedro (46)

## Calibração do Pedro (não resolva sozinho)

- `MANUAL_PLACE_AREAS` (a Nuke é a mais frágil) e `MANUAL_ENTRY_ANGLES`.
- Janela de trade (5,0 s) e limiares de peek/hold, contato, pré-fire e rotação.
- Pesos do crédito do Round Swing e todos os de `round_spectacle.py`.
- Altura dos olhos e diferença em pé/agachado (21c); mínimo por grupo da força (21a);
  `TICK_PELO_PROJETIL_SEM_EVENTO`, desligado.
- Limiares do destaque, do round decisivo, da autópsia, dos papéis e dos erros do Perfil (46).
- Pisos de função (31) e do eixo carrega piano/baiter; repick com mais de uma saída (15b).
