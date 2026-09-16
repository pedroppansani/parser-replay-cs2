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
- Demos ficam em `data/raw/` (gitignored). São arquivos de 200MB+ que expiram no
  FACEIT em 30 dias.
- Parsing leva ~14s por partida. Use `--from-interim` para reaproveitar um parse
  já feito em vez de reparsear enquanto itera nas métricas.

## Estrutura

```
parsing/      wrapper do awpy.Demo
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles,
              positioning, grenades, player_roles
clustering/   playstyle (PCA + KMeans) + cluster_names.json
dashboard/    app Streamlit + theme + web/ (template do painel de portfólio)
docs/         site publicado no GitHub Pages (gerado por build_site.py)
assets/radars/ radares + calibração oficiais, extraídos do CS2 local
scripts/      process_demo, process_all_demos, extract_radars, build_site,
              build_insights, build_breakdown, export_replay, export_web_payload
tests/        43 testes
demos/        .dem baixados do FACEIT (gitignored)
data/raw/     .dem originais (gitignored)
data/interim/ tabelas brutas em parquet (gitignored, ticks tem 1M+ linhas)
data/processed/ métricas calculadas (versionadas — é o que o dashboard usa)
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

2. **A flag `is_scoped` do demo é não confiável e está fora da classificação.**
   40% dos ticks marcados como scopado mostram velocidade acima de 150 u/s,
   impossível com AWP scopada (mediana medida: 58 u/s scopado vs 208 u/s sem
   scope). A propriedade parece ficar presa no último valor entre atualizações.
   A classificação usa posição medida; `scoped_fraction` fica só como sinal
   informativo. **Não reintroduza a flag como critério.**

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
   que se quer medir.

8. **O KMeans não nomeia os clusters.** A nomeação é interpretação de jogo e
   cabe ao Pedro, via `clustering/cluster_names.json`. Enquanto vazio, o
   dashboard mostra "Cluster 0, 1..." e avisa. **Não gere rótulos automáticos.**

9. **Convenção de ângulos do CS2: pitch positivo = olhar para BAIXO.** Validada
   empiricamente (erro mediano de 1,76° no tick da kill, contra 6,52° na
   convenção invertida). O teste roda a convenção invertida como controle — se
   um dia passar nas duas, o teste não está medindo nada.

10. **Paleta do dashboard foi validada para daltonismo e contraste.** O scatter
    de clusters é facetado (um painel por cluster) porque nenhuma quarta cor
    passa nos critérios junto das três primeiras no modo escuro. Não troque por
    4 cores num gráfico só.

11. **Só entidade `*Projectile` conta como granada arremessada.** A tabela
    `grenades` do awpy mistura o projétil em voo (`CFlashbangProjectile`) com a
    granada parada no inventário (`CFlashbang`), que tem uma amostra por tick do
    round inteiro na posição de quem a carrega. Contar as duas inflava os
    arremessos em ~2,5x (965 entidades contra 388 arremessos reais) e dava
    "primeira utility do round" sempre negativa. A contagem de projéteis bate
    exatamente com os eventos de detonação do demo, e há teste parametrizado
    travando isso contra a demo real. **Não volte a aceitar as classes sem
    sufixo Projectile.**

12. **Utility é medida por EFEITO, não por dano.** Dano é a parte menos
    importante da utility: a flash que cega dois defensores por 2s não aparece em
    número de dano nenhum, e é ela que abre o round. A métrica principal é tempo
    de cegueira imposto a inimigos, vindo do evento `player_blind` (que o awpy
    não parseia por padrão — ver `EXTRA_EVENTS` em `parsing/parser.py`).

13. **Team flash e self flash não são descontados do número de inimigos
    cegados.** São erros diferentes com custos diferentes; um saldo único
    apagaria os dois. Ficam em colunas próprias, e há teste travando.

14. **Função de jogador exige liderar o próprio time E passar de um piso
    absoluto.** Sem o piso, quem menos evita a AWP num time que não usa AWP
    viraria "AWPer". Sem a comparação interna, "joga mais utility que a média dos
    10" descreveria a partida, não um papel. Consequência aceita de propósito:
    **não existe cota de um de cada função por time** — na partida de teste um
    time não teve AWPer nenhum e dois jogadores ficaram sem função dominante.
    Não "conserte" isso distribuindo rótulos até preencher cinco vagas.

15. **IGL não é deduzido.** Quem chama o time não deixa rastro no demo (não há
    áudio, e liderança não tem assinatura estatística). Rotular alguém de IGL
    seria chute com cara de métrica.

16. **Radar e calibração vêm da instalação local do CS2, não de download.**
    `scripts/extract_radars.py` lê `pak01_dir.vpk` e usa o `pos_x/pos_y/scale`
    do overview oficial da Valve — conversão exata, no lugar do encaixe
    heurístico do `prepare_radar.py` (que fica como alternativa pra quem não tem
    o jogo instalado). Não troque por radar baixado: vem recortado e obriga a
    recalibrar no olho.

17. **Andar de jogador sai do `verticalsections` do overview, não de limiar
    inventado.** Na Nuke o corte oficial é Z = -495, e é ele que separa o A do
    B num mapa 2D. Confere com o mapa real: abaixo do corte caem exatamente
    BombsiteB, Vents, Tunnels, Secret, Observation, Decon e Ramp.

## Pontos de calibração — pertencem ao Pedro, não ao código

Não "resolva" nenhum destes automaticamente; pergunte.

- Nomear os clusters (`clustering/cluster_names.json`).
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`).
  Rode `python -m scripts.show_derived_angles <match_id>` para ver os derivados.
  Os com `n_kills` baixo (4-5) são os que mais precisam de julgamento humano.
- Limiares: janela de trade (5s), peek/hold (120u / 250u), janela de contato
  (1s), tolerância de pré-fire (25°), flash efetiva (1,0s) e folga de flash
  assist (0,5s) em `metrics/grenades.py`.
- Pisos das funções de jogador (`TRAIT_SPECS` em `metrics/player_roles.py`):
  AWP 25% dos rounds, entry 8s até o contato, suporte 20s de cegueira, lurk 600u,
  âncora 10s, trade 35%, fragger 85 de ADR. Saíram da distribuição de UMA
  partida — revisar com mais demos.
- Override manual de função: `MANUAL_ROLES` em `metrics/player_roles.py` (o
  painel marca o rótulo como manual quando vem daí).

## Limitações conhecidas

- Tudo veio de **uma única partida** até agora. Silhueta do clustering em 0,205
  (estrutura fraca) — esperado com 220 player-rounds. Processar mais demos
  melhora clusters e ângulos derivados.
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
py -3.12 -m pytest tests/ -v          # 43 testes
py -3.12 -m scripts.process_demo <caminho.dem> --match-id match_01 --from-interim
py -3.12 -m streamlit run dashboard/app.py
```

O painel web de portfólio é uma cadeia, nessa ordem — mexer numa métrica sem
refazer a cadeia deixa a página mostrando número velho:

```bash
py -3.12 -m scripts.build_insights match_01      # insights.json
py -3.12 -m scripts.build_breakdown match_01     # breakdown.json (autópsia do round)
py -3.12 -m scripts.export_replay match_01       # replay.json (trajetórias, pops, blinds, andar, callouts)
py -3.12 -m scripts.export_web_payload match_01  # web_payload.json
py -3.12 -m scripts.build_site                   # docs/ (site publicado, todas as partidas)
```

`scripts/process_all_demos.py` roda a cadeia inteira para toda demo da pasta
`demos/` — é o caminho normal. Os radares são extraídos uma vez só, com
`scripts/extract_radars.py`, e não dependem de rede.

O site publicado fica em `docs/` e é servido pelo GitHub Pages em
https://pedroppansani.github.io/parser-replay-cs2/ (repositório público — Pages
não funciona em repositório privado no plano gratuito).

Ao mexer numa métrica, confira o efeito na tabela round a round, não só no
agregado — número agregado plausível pode esconder lógica errada.

O demo de origem do `match_01` é o de_ancient de 22 rounds em `demos/`
(`1-0007ce25-…`); os outros oito arquivos de lá são de outros mapas.
