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
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles, positioning
clustering/   playstyle (PCA + KMeans) + cluster_names.json
dashboard/    app Streamlit + theme
scripts/      process_demo (CLI) e show_derived_angles (calibração)
tests/        29 testes
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

## Pontos de calibração — pertencem ao Pedro, não ao código

Não "resolva" nenhum destes automaticamente; pergunte.

- Nomear os clusters (`clustering/cluster_names.json`).
- Ângulos de entrada manuais (`MANUAL_ENTRY_ANGLES` em `metrics/map_angles.py`).
  Rode `python -m scripts.show_derived_angles <match_id>` para ver os derivados.
  Os com `n_kills` baixo (4-5) são os que mais precisam de julgamento humano.
- Limiares: janela de trade (5s), peek/hold (120u / 250u), janela de contato
  (1s), tolerância de pré-fire (25°).

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
py -3.12 -m pytest tests/ -v          # 29 testes
py -3.12 -m scripts.process_demo data/raw/match_01.dem --match-id match_01 --from-interim
py -3.12 -m streamlit run dashboard/app.py
```

Ao mexer numa métrica, confira o efeito na tabela round a round, não só no
agregado — número agregado plausível pode esconder lógica errada.
