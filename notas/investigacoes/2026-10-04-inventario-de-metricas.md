# Inventário das métricas por jogador (fase 7, item 7.1, 2026-10-04)

Gerado por `py -3.12 -m pesquisa.inventario_metricas` (colunas das tabelas por jogador em
`data/processed/` e os campos por jogador do `insights.json`). "Na tela" procura o nome do campo
no template; as variantes de uma taxa do perfil (`_n`, `_d`, `_ref`, `_fraco`, `_ct`, `_t`) entram
como uma linha só.

## O que o inventário diz sobre os itens do 7.2

| pedido do 7.2 | o que já existe | o que falta |
|---|---|---|
| dano de HE e de molotov | `he_damage`, `fire_damage`, `utility_damage(_per_round)` (grenades) — **fora da tela** | por granada (dano / HE, dano / molotov) e por round de cada um |
| inimigos cegados e segundos de cegueira | `enemies_flashed`, `enemy_blind_seconds`, `blind_seconds_per_flash` — só o total aparece (Funções) | inimigos cegados por flash |
| flash que antecedeu kill no cegado | `flash_assists` (companheiro matou o cego por mim) e `flash_kills` (eu matei o cego pela minha flash) — **fora da tela** | nada a calcular: falta mostrar |
| cegueira nos companheiros | `team_blind_seconds`, `teammates_flashed` — **fora da tela** | nada a calcular: falta mostrar |
| fração das mortes trocadas | `pct_mortes_trocadas` (perfil, com régua) | — |
| kills de troca | `total_trade_kills`, `trade_kill_pct`, `pct_rounds_trade_kill` (perfil) | — |
| tempo mediano da troca | — | **novo** |
| rating, ADR e KAST por compra (eco, força, cheia) | — | **parado:** a regra 8i não tem eco/força/cheia (as classes são grupo da arma mais cara × colete) |
| kills contra compra cheia × anti-eco | — | **parado** pelo mesmo motivo |
| pós-plant (TR) e retake (CT) | — | **novo** |
| duelos de abertura por lado | `opening_kills` (total, insights), `pct_rounds_primeiro_contato_do_time_ct/_t` (contato, não duelo) | **novo:** tentativas, vitórias e taxa por lado |

215 métricas por jogador; na tela: 42; com referência: 33; com gabarito ou invariante: 28

| métrica | tabela | módulo | na tela | referência e amostra | gabarito ou invariante |
|---|---|---|---|---|---|
| `adr` | adr_summary | metrics/basic_metrics.py | Jogadores (funções), Jogadores (tabela) | não | degrau 3 (ADR) |
| `rounds_played` | adr_summary | metrics/basic_metrics.py | não | não | invariante: sem nulo |
| `total_damage` | adr_summary | metrics/basic_metrics.py | não | não | invariante: sem nulo |
| `hold_share` | anchor_summary | metrics/site_roles.py | não | não | não |
| `n_rounds` | anchor_summary | metrics/site_roles.py | não | não | não |
| `n_rounds_pressao_outro_lado` | anchor_summary | metrics/site_roles.py | não | não | não |
| `never_left_share` | anchor_summary | metrics/site_roles.py | não | não | não |
| `no_rotate_share` | anchor_summary | metrics/site_roles.py | não | não | não |
| `awp_conversion` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `awp_opening_picks` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `awp_round_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `awp_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `bait_no_trade_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `bait_opportunities` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `bait_return_per_opp` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `bait_untraded_per_round` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_attempts` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_conversion` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_damage_per_attempt` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_peso` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_peso_perdido` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_por_x` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `clutch_wins` | archetypes_summary | metrics/archetypes.py | não | não | degrau 4 (clutches) |
| `ct_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `damage_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `death_rate` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `distinct_places_mean` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `eco_sacrifice_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `effort_pct` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `engagements` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `first_contact_share` | archetypes_summary | metrics/archetypes.py | não | não | invariante: sem nulo |
| `frac_entering_fight` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `idx_awper` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_baiter` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_camper` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_carrega_piano` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_carry` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | invariante: sem nulo |
| `idx_mochila` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_rei_do_nt` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `idx_repick` | archetypes_summary | metrics/archetypes.py | não | percentil global (archetype_reference) | não |
| `impact_pct` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `isca_esperada` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `isca_observada` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `isca_relativa` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `isca_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `kill_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `multikill_rounds` | archetypes_summary | metrics/archetypes.py | não | não | degrau 4 (rounds de multi-kill) |
| `pagou_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `pagou_sem_retorno_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `path_per_round` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_ct_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_ct_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_eco_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_eco_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_t_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_t_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `piano_total_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `repick_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `rounds_played` | archetypes_summary | metrics/archetypes.py | não | não | invariante: sem nulo |
| `sacrifice_index` | archetypes_summary | metrics/archetypes.py | não | não | invariante: sem nulo |
| `sacrificio_com_flash_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `sacrificio_esperado` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `sacrificio_relativo` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `sacrificio_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `sacrificio_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `survival_rate` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `t_rounds` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `team_damage` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `team_kills` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `total_damage` | archetypes_summary | metrics/archetypes.py | não | não | invariante: sem nulo |
| `total_kills` | archetypes_summary | metrics/archetypes.py | não | não | degrau 1 (kills) |
| `traded_death_share` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `util_per_round` | archetypes_summary | metrics/archetypes.py | não | não | não |
| `awp_rounds` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `engagement_conversion_pct` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `engagements_lost` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `engagements_no_trade` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `engagements_won` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `median_time_to_first_shot_s` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `opening_pick_rate_pct` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `opening_picks` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `rounds_with_engagement` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `style_hold` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `style_intermediate` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `style_peek` | awp_summary | metrics/awp_metrics.py | não | não | não |
| `crosshair_score` | crosshair_summary | metrics/crosshair.py | Jogadores (tabela) | não | não |
| `direction_score` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `height_score` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `median_enemy_aim_error_deg` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `median_pitch_error_deg` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `median_prefire_match_deg` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `n_fight_samples` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `n_samples` | crosshair_summary | metrics/crosshair.py | não | não | não |
| `blind_seconds_per_flash` | grenades_summary | metrics/grenades.py | não | não | não |
| `decoy_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `enemies_flashed` | grenades_summary | metrics/grenades.py | não | não | não |
| `enemy_blind_seconds` | grenades_summary | metrics/grenades.py | Jogadores (funções) | não | não |
| `fire_damage` | grenades_summary | metrics/grenades.py | não | não | não |
| `flash_assists` | grenades_summary | metrics/grenades.py | não | não | não |
| `flash_kills` | grenades_summary | metrics/grenades.py | não | não | não |
| `flash_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `he_damage` | grenades_summary | metrics/grenades.py | não | não | não |
| `he_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `median_first_utility_s` | grenades_summary | metrics/grenades.py | não | não | não |
| `molotov_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `nades_per_round` | grenades_summary | metrics/grenades.py | não | não | não |
| `nades_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `rounds_played` | grenades_summary | metrics/grenades.py | não | não | invariante: sem nulo |
| `self_blind_seconds` | grenades_summary | metrics/grenades.py | não | não | não |
| `smoke_thrown` | grenades_summary | metrics/grenades.py | não | não | não |
| `team_blind_seconds` | grenades_summary | metrics/grenades.py | não | não | não |
| `teammates_flashed` | grenades_summary | metrics/grenades.py | não | não | não |
| `utility_damage` | grenades_summary | metrics/grenades.py | não | não | não |
| `utility_damage_per_round` | grenades_summary | metrics/grenades.py | não | não | não |
| `kast_pct` | kast_summary | metrics/basic_metrics.py | Jogadores (funções), Jogadores (tabela) | não | degrau 3 (KAST) |
| `kast_rounds` | kast_summary | metrics/basic_metrics.py | não | não | degrau 3 (KAST) |
| `rounds_played` | kast_summary | metrics/basic_metrics.py | não | não | invariante: sem nulo |
| `n_rounds` | lurk_summary | metrics/site_roles.py | não | não | não |
| `n_rounds_time_definido` | lurk_summary | metrics/site_roles.py | não | não | não |
| `off_team_share` | lurk_summary | metrics/site_roles.py | não | não | não |
| `abaixo_do_acaso` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `amostra_fraca` | structural_roles_summary | metrics/structural_roles.py | avisoDaRegua | não | não |
| `chance_ao_acaso` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `concentracao` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `empate_funcao` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `empate_vencido_pelo_awper` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `funcao` | structural_roles_summary | metrics/structural_roles.py | avisoDaRegua, iniciaAnotacoes | não | não |
| `funcao_mais_frequente` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `funcoes_empatadas` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `pontuacao_media` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `rounds_empatadas` | structural_roles_summary | metrics/structural_roles.py | não | não | não |
| `rounds_na_funcao` | structural_roles_summary | metrics/structural_roles.py | avisoDaRegua | não | não |
| `rounds_no_lado` | structural_roles_summary | metrics/structural_roles.py | avisoDaRegua | não | não |
| `total_kills` | trade_kills_summary | metrics/basic_metrics.py | não | não | degrau 1 (kills) |
| `total_trade_kills` | trade_kills_summary | metrics/basic_metrics.py | não | não | não |
| `trade_kill_pct` | trade_kills_summary | metrics/basic_metrics.py | não | não | não |
| `rounds_played` | utility_damage_summary | metrics/basic_metrics.py | não | não | invariante: sem nulo |
| `total_utility_damage` | utility_damage_summary | metrics/basic_metrics.py | não | não | não |
| `utility_damage_per_round` | utility_damage_summary | metrics/basic_metrics.py | não | não | não |
| `assistencias` | player_profile | metrics/player_profile.py | Jogadores (tabela), avisoDaRegua | não | não |
| `clutch_convertidos` | player_profile | metrics/player_profile.py | não | não | degrau 4 (clutches) |
| `clutch_tentativas` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_0` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_1` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_2` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_3` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_concentracao` | player_profile | metrics/player_profile.py | não | não | não |
| `grupo_dominante` | player_profile | metrics/player_profile.py | avisoDaRegua | não | não |
| `kills_de_awp` | player_profile | metrics/player_profile.py | não | não | não |
| `kills_totais` | player_profile | metrics/player_profile.py | Jogadores (tabela), avisoDaRegua | não | degrau 1 (kills) |
| `mortes` | player_profile | metrics/player_profile.py | Jogadores (tabela), avisoDaRegua | não | degrau 1 (mortes) |
| `mortes_trocadas` | player_profile | metrics/player_profile.py | não | não | não |
| `pct_kills_de_awp` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_mortes_trocadas` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_abertura_awp` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_ancorado` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_com_awp` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_contato_cedo` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_contato_tarde` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_em_clutch` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_isolado` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_longe_do_time` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_lurk` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_primeiro_contato_do_time` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_rotacionando` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_smg_ou_pistola_com_time_de_rifle` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_sobreviveu` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `pct_rounds_trade_kill` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `rounds` | player_profile | metrics/player_profile.py | avisoDaRegua, cabeçalho, loadRadars | não | não |
| `rounds_jogados` | player_profile | metrics/player_profile.py | avisoDaRegua | não | não |
| `taxa_conversao_clutch` | player_profile | metrics/player_profile.py | Perfil | régua do corpus (perfil_reference) + bruto + amostra fraca | não |
| `tempo_mediano_ate_contato_s` | player_profile | metrics/player_profile.py | avisoDaRegua | não | não |
| `adr` | player_roles | metrics/player_roles.py | Jogadores (funções), Jogadores (tabela) | piso do rótulo + amostra mínima (decisão 39) | degrau 3 (ADR) |
| `avg_distance_from_team` | player_roles | metrics/player_roles.py | Jogadores (funções) | não | não |
| `awp_rounds` | player_roles | metrics/player_roles.py | não | não | não |
| `awp_rounds_do_time` | player_roles | metrics/player_roles.py | não | não | não |
| `awp_share` | player_roles | metrics/player_roles.py | não | piso do rótulo + amostra mínima (decisão 39) | invariante: sem nulo |
| `awp_share_todos_rounds` | player_roles | metrics/player_roles.py | não | não | não |
| `distinct_places` | player_roles | metrics/player_roles.py | não | não | não |
| `enemies_flashed` | player_roles | metrics/player_roles.py | não | não | não |
| `enemy_blind_por_round` | player_roles | metrics/player_roles.py | não | piso do rótulo + amostra mínima (decisão 39) | não |
| `enemy_blind_seconds` | player_roles | metrics/player_roles.py | Jogadores (funções) | não | não |
| `first_contact_share` | player_roles | metrics/player_roles.py | não | piso do rótulo + amostra mínima (decisão 39) | invariante: sem nulo |
| `flash_assists` | player_roles | metrics/player_roles.py | não | não | não |
| `flash_thrown` | player_roles | metrics/player_roles.py | não | não | não |
| `hold_share` | player_roles | metrics/player_roles.py | não | não | não |
| `kast_pct` | player_roles | metrics/player_roles.py | Jogadores (funções), Jogadores (tabela) | não | degrau 3 (KAST) |
| `median_first_contact_s` | player_roles | metrics/player_roles.py | Jogadores (funções) | não | não |
| `n_rounds` | player_roles | metrics/player_roles.py | não | não | não |
| `n_rounds_pressao_outro_lado` | player_roles | metrics/player_roles.py | não | não | não |
| `n_rounds_sem_awp` | player_roles | metrics/player_roles.py | não | não | não |
| `n_rounds_time_definido` | player_roles | metrics/player_roles.py | não | não | não |
| `nades_per_round` | player_roles | metrics/player_roles.py | não | não | não |
| `never_left_share` | player_roles | metrics/player_roles.py | não | piso do rótulo + amostra mínima (decisão 39) | não |
| `no_rotate_share` | player_roles | metrics/player_roles.py | não | não | não |
| `off_team_esperado` | player_roles | metrics/player_roles.py | não | não | não |
| `off_team_relativo` | player_roles | metrics/player_roles.py | não | piso do rótulo + amostra mínima (decisão 39) | não |
| `off_team_share` | player_roles | metrics/player_roles.py | não | não | não |
| `off_team_share_sem_awp` | player_roles | metrics/player_roles.py | não | não | não |
| `role` | player_roles | metrics/player_roles.py | Jogadores (funções), cabeçalho, iniciaAnotacoes | não | não |
| `role_estabilidade` | player_roles | metrics/player_roles.py | não | não | não |
| `role_tendencia` | player_roles | metrics/player_roles.py | não | não | não |
| `rounds_jogados` | player_roles | metrics/player_roles.py | avisoDaRegua | não | não |
| `smoke_thrown` | player_roles | metrics/player_roles.py | não | não | não |
| `survival_rate` | player_roles | metrics/player_roles.py | não | não | não |
| `team_blind_seconds` | player_roles | metrics/player_roles.py | não | não | não |
| `total_kills` | player_roles | metrics/player_roles.py | não | não | degrau 1 (kills) |
| `total_trade_kills` | player_roles | metrics/player_roles.py | não | não | não |
| `trade_share` | player_roles | metrics/player_roles.py | Jogadores (funções) | piso do rótulo + amostra mínima (decisão 39) | não |
| `utility_damage` | player_roles | metrics/player_roles.py | não | não | não |
| `clutches` | insights.players | leitura/insights.py + metrics/rating.py | não | não | degrau 4 (clutches) |
| `opening_kills` | insights.players | leitura/insights.py + metrics/rating.py | não | não | degrau 4 (aberturas) |
| `rating` | insights.players | leitura/insights.py + metrics/rating.py | Jogadores (tabela) | referência de escala (rating_reference) + amostra fraca | rating contra a HLTV (catraca) |
| `rating_amostra_fraca` | insights.players | leitura/insights.py + metrics/rating.py | Jogadores (tabela) | não | não |
| `rating_sub` | insights.players | leitura/insights.py + metrics/rating.py | não | não | não |
