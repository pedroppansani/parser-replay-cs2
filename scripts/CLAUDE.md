# scripts/: referências, calibração, biblioteca e build

Complementa o `CLAUDE.md` da raiz e não o substitui. Uma regra por linha; (N) = nota em
`notas/decisoes/`. As regras das métricas que os `fit_*` seguem estão copiadas no fim: de
`metrics/` (`fit_archetype_reference`, `fit_rating`, `fit_economia`, `fit_perfil_reference`,
`fit_erros_reference`) e de `clustering/` (`fit_global_clusters`).

## Dados

- `clean_match.limpa` recusa apagar sem uma cópia de mesmo sha256 nas pastas irmãs
  "<projeto> - BACKUP*", lida NA HORA dos dois lados (lista gravada não vale), mesmo chamada pelo
  Python com `confirmar=True`; sem `confirmar`, só lista arquivo, tamanho, cópia e hash (36)
- Escala dos papéis: mexer num componente também pede o reajuste com `fit_archetype_reference`
  (16); a tabela da economia regerada tem de dar exatamente o `economia_reference.json` gravado (8i)
- Os exemplos da seção 7.2 são fixados em `scripts/calibracao/exemplos_fixados.json`; `--sortear-de-novo`
  só quando as definições mudam (46)

## Rating

- Calibração só com partidas oficiais cobertas pela HLTV, nunca FACEIT; mínimo de 7 de treino + 3
  de teste, divisão por PARTIDA e nunca por jogador (22c)
- `componentes_do_corpus` recebe a referência: os pesos são ajustados na mesma escala em que o site
  os usa (22l)
- Refazer a referência de escala exige refazer os pesos (`fit_rating --fit-pesos`); o rating marca
  `pesos_desatualizados` (22l)

## Biblioteca, lugares e build

- `data/lineups/` é gerada LOCALMENTE por `scripts.build_lineups` (depende do interim, que não vai
  ao git nem ao CI); só entra arremesso com reprodução exata; regerar depois de mudar
  `metrics/grenade_throws.py` (32)
- Nome de lugar só do campo `place` dos ticks, em inglês como o jogo escreve (sem tradução); célula
  sem tick não tem nome; o mapa só ganha tabela com `MIN_PARTIDAS` (2) e `MIN_ACERTO` (93%) fora da
  amostra, e abaixo disso a tela fica sem nome (42)
- JSON dentro de `<script>` só por `scripts/json_em_script.py` (37)
- `cluster_names.json` entra no payload do site (8)
- Do build saem prontos o cabeçalho da partida (placar, "venceu", "começou CT/TR") e o `<title>`
  único (o evento entra quando dois títulos se repetiriam) (44)
- supabase-js entra em versão exata, com o sha256 conferido pelo build, e só é carregado ao criar ou
  entrar num grupo; sem `GRUPOS_ATIVOS`, URL e chave pública, a página é byte a byte a do build sem
  grupo (47)
- Toda página sai com a meta CSP de `scripts/csp.py` (via `meta_tags`); o host do Supabase só no `connect-src` da prancheta com grupo (47)

## Réguas do corpus (cópia de `metrics/`, para os `fit_*`)

<!-- copia de metrics/CLAUDE.md#regras-fit-metricas: inicio -->
- Traço é comparado DENTRO da função, com o esperado do corpus; cada braço do eixo contra a
  população da mesma função dominante (`quantis_por_funcao`); o valor absoluto fica ao lado do
  normalizado (15c, 15e)
- A escala dos papéis é do corpus (`archetype_reference.json`), nunca da partida (16)
- Lurker: sem os rounds com AWP, contra a taxa esperada da função daqueles rounds (a própria função
  lurker fica fora da régua), pelo `off_team_relativo`; abaixo de `MIN_ROUNDS_SEM_AWP` é DADO
  INSUFICIENTE, não "não qualifica" (29, 31)
- O perfil por jogador é a leitura, não média de cluster: taxa sempre com bruto (`_n`, `_d`),
  régua e amostra fraca (`_fraco`), também por lado (`_ct`, `_t`); cards de estilo pela maior
  fração dos próprios rounds (7a)
- Economia estimada no CORPUS por arma mais cara + colete, lida da compra no fim do freeze;
  empate de classe divide o round; eco, força e compra cheia são agregação dessas classes, a fonte
  única de economia do projeto, sem limiar novo (8i)
- Round Swing: regressão logística (não contagem por estado), bomba COM sinal; variação de
  probabilidade pura, sem corte de round perdido; soma zero por evento, com o fim do round e
  exceto morte sem matador inimigo; centrado em 1,00 e escalado pelo desvio
  (22a, 22b, 22f, 22h, 22k)
- Dividir pela média ou padronizar dá o mesmo rating com pesos ajustados: não "corrija" (22i)
- Rating por lado, com kill assistida e morte trocada como componentes, na mesma escala de
  referência da calibração (22l)
- Todo erro é de um lado só e nenhum tipo soma os dois; a régua é anônima por (lado, função), e
  os lados nunca se misturam, nem como queda (46)
- Ponto a melhorar só acima do percentil 90 da régua e com pelo menos 2 ocorrências; custo é
  ΔWPA "pela estimativa do modelo"; `DIST_TROCA` só muda depois da calibração do Pedro (46)
<!-- copia de metrics/CLAUDE.md#regras-fit-metricas: fim -->

## Agrupamento (cópia de `clustering/`, para `fit_global_clusters`)

<!-- copia de clustering/CLAUDE.md#regras-clustering: inicio -->
- Clustering é por (jogador, round), não por jogador (7)
- As features são só COMPORTAMENTO: `damage`, `kills`, `trade_kills`, `utility_damage` e
  `survived` não voltam para a lista; `sem_contato` não é feature (o tempo até o contato nulo é
  preenchido pela mediana do modelo global, `fill_medians`) (7b)
- O KMeans é ajustado UMA vez no corpus (`global_model.json`, JSON e não pickle, por
  `scripts/fit_global_clusters.py`), nunca por partida (11)
- O KMeans não nomeia os grupos: o nome é do Pedro (`cluster_names.json`); não gere rótulo
  automático. A descrição exibida sai de `describe_clusters` sobre o perfil GLOBAL, nunca do recorte
  da partida (8)
- `cluster_names.json` entra no payload do site; o agrupamento não tem seção própria no site (só
  aparece no "jeito de jogar mais frequente" do Perfil) (8)

## Calibração do Pedro (não resolva sozinho)

- Nomes dos grupos (`cluster_names.json`): todo reajuste que renumerar os grupos exige conferir os
  nomes de novo (`py -3.12 -m scripts.fit_global_clusters --dry-run`).
<!-- copia de clustering/CLAUDE.md#regras-clustering: fim -->
