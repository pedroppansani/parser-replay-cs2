# Contexto do projeto, ambiente, estrutura e convenções

> As seções gerais do CLAUDE.md como estavam antes da reestruturação de 2026-10-02. A versão atual e curta está no `CLAUDE.md`. Onde este texto cita contagens (testes, partidas), valem as de `data/processed/numeros_citaveis.json`.

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
  **Apagar demo, interim ou backup exige a confirmação da decisão 36** (lista
  explícita, tamanho e outra cópia conferida por sha256).
- Parsing leva ~14s por partida. Use `--from-interim` para reaproveitar um parse
  já feito em vez de reparsear enquanto itera nas métricas.

## Estrutura

```
parsing/      wrapper do awpy.Demo
metrics/      geometry, basic_metrics, awp_metrics, crosshair, map_angles,
              positioning, grenades, map_areas, site_roles, player_roles,
              clutch, archetypes (+ archetype_reference.json), player_profile,
              structural_roles, formatting, win_probability, round_spectacle,
              match_highlights, grenade_throws, rating (+ rating_reference.json),
              tactics (modelo da prancheta tática)
clustering/   playstyle (PCA + KMeans), global_model.json e cluster_names.json
dashboard/    app Streamlit + theme + web/
scripts/      process_demo (CLI), reprocessa (corpus inteiro a partir do interim,
              em paralelo), fit_global_clusters, fit_archetype_reference,
              build_player_profiles, show_derived_angles e show_map_areas
              (calibração), narrative, build_site, manifest, clean_match,
              build_lineups e build_tactics_page (prancheta)
tests/        ~985 testes (os de navegador usam Playwright + Chrome; sem eles, pulados)
dashboard/web/map_core.js  núcleo compartilhado do mapa (decisão 33)
demos/       .dem originais (gitignored)
data/manifest.json origem de cada partida (versionado; scripts/manifest.py)
data/interim/ tabelas brutas em parquet (gitignored, ticks tem 1M+ linhas)
data/processed/ métricas calculadas (versionadas — é o que o dashboard usa)
data/lineups/ biblioteca de arremessos reais por mapa (versionada; build_lineups)
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
