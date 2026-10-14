# Contexto do projeto para o Claude Code

Lido em toda sessão: só o que está em vigor (o porquê e o histórico ficam em `notas/`). Os
`CLAUDE.md` das pastas complementam este e não o substituem (índice no fim).

## O que é

Parser de replay (.dem) do CS2 que gera um site estático por partida (replay, leitura da partida,
perfil, prancheta tática). O parsing é do `awpy`; **o diferencial é o desenho das métricas**: cada
uma carrega uma decisão de jogo explícita, e a validação final é o conhecimento de jogo do Pedro
(Faceit 10, flex AWPer). Ao propor ou mudar métrica, a justificativa de JOGO pesa tanto quanto a
corretude.

## Como rodar e testar

- Python 3.11 a 3.13 (`py -3.12` no Windows); o awpy 2.0.2 não suporta 3.14.
- `py -3.12 -m pytest tests/` · `py -3.12 -m scripts.reprocessa` (corpus a partir do interim) ·
  `py -3.12 -m scripts.build_site` · `py -3.12 -m scripts.escada_validacao`.
- Parse: ~14 s/partida; itere com `--from-interim`.

## Regras duras

Uma regra por linha; o número entre parênteses é a nota em `notas/decisoes/`.

### Dados e reprodutibilidade

- Nenhum `.dem`, nada de `data/interim/` e nenhum backup é apagado sem o Pedro confirmar uma LISTA
  EXPLÍCITA dos arquivos, com o tamanho de cada um e a prova de outra cópia conferida por sha256
  arquivo a arquivo (nunca por nome, caminho, tamanho ou "o git tem"); vale para
  `clean_match.py --confirmar`, `rm -rf` e qualquer limpeza de disco (36)
- Sem o interim a partida não é recalculável, e a maioria não tem mais o `.dem`: subir
  `VERSAO_DO_PARSER` se decide ANTES de subir (27)
- O demo é 64 tick; nunca assuma (`metrics/timing.py` detecta).
- Processamento determinístico: qualquer diferença entre execuções é bug, inclusive ordem de linha
  e último bit de float. `group_by`/`unique` com `maintain_order=True`; `unique` com subset usa
  `keep="first"`; `mode().sort().first()`; empate no corte (`.head(n)`) entra inteiro. Correção
  explícita no código, sem remendo global na biblioteca; paralelo só aceito por identidade (28)
- Todo ponto de entrada do interim (`load_interim`, o parse do zero, script que lê o parquet
  direto) aplica `parsing.kills_do_round_jogado`, `parsing.eventos_do_round_jogado` e
  `parsing.parser.dano_real_no_mesmo_tick`; script novo lê por `load_interim` (8b, 8j, 15b)
- Cada partida grava a versão do parser (a do INTERIM, não a do código), a das métricas e o commit
  (`sujo` se havia mudança não commitada). Sobe a versão quem muda NÚMERO, com linha de histórico
  no módulo; partida sem versão é "desconhecida", não velha (27)
- `scripts/reprocessa` não reajusta referência global por padrão (reajustar é decisão) e nunca
  refaz os pesos do rating (28)
- `docs/` (site gerado) não vai para o repositório; o Pages é artefato do CI. Depois de mexer
  nisso: clonar do zero, rodar a suíte (teste que depende de `data/interim/` é PULADO, nunca
  quebra) e gerar o site só com o versionado (24)

### Números, nomes e honestidade

- Não cite número de cabeça: os do projeto (corpus, rating, escada, arremessos, testes) vêm de
  `data/processed/numeros_citaveis.json` (`py -3.12 -m scripts.numeros_citaveis`); README, landing
  e páginas leem dali; número de corpus nunca é escrito no template (37)
- Todo número com bruto e referência; amostra pequena e neutro com tratamento próprio; intervalo
  como intervalo; nada de gráfico de radar (44)
- O rating é implementação própria da metodologia do Rating 3.0, nunca apresentado como "o da
  HLTV" na interface, no código ou no README; o rótulo vem do resumo do módulo (22)
- Catraca do rating (`tests/test_catraca_do_rating.py`): o patamar é o melhor valor medido e só
  melhora; regravá-lo exige o OK do Pedro, em commit próprio com os dois números (22a)
- Escada de validação: contagem exata antes de olhar o rating; print oficial casado com a partida
  pelo RATING, nunca pelo K-D (22g)
- Comando de console (`setpos`/`setang`) só é exato depois de o Pedro conferir no jogo; até lá
  (`COMANDO_CONFERIDO_NO_JOGO` falso) toda ficha avisa (21b, 32)
- Identidade é o steamid: `metrics/identidade.py` é o único lugar que resolve nome, e todo
  relatório entre partidas passa por ele; as réguas do corpus já agregam por (partida, steamid):
  não as "conserte" (25)
- Agregado por time usa `metrics/times.nome_canonico` (`data/reference/times_conhecidos.json`);
  nome fora da tabela é o próprio canônico, nada é adivinhado, e nenhum módulo normaliza nome de
  time por conta própria (38)
- IGL nunca é atribuído automaticamente: vem de `roles_manual.json`, preenchido à mão; o código
  nunca escreve nele e `pesquisa/igl_candidatos.py` só imprime (7g)
- Dinheiro só por `metrics.formatting.format_money` (`3.750$`), nunca f-string com `$` (8e)
- Pitch positivo olha para BAIXO (9)
- Regra de jogo usada por vários módulos é definida uma vez e importada: janela de trade e troca
  de lado em `metrics/constantes.py`, contato em `metrics/contato.primeiro_contato`, "é o AWPer do
  time" em `metrics/player_roles.awpers_do_time`, clutch em `metrics/clutch` (40, 22j)
- MR12 ou MR15 sai da troca de lado na demo, nunca se assume; se o detectado discorda de
  `HALFTIME_ROUND`, o `build_insights` AVISA em vez de seguir em silêncio (19c)

### O que a página afirma

- Frases dos cards saem do Python, prontas para o template; campo que não existe some da frase;
  papel sem sustentação devolve string vazia, não frase com zeros (18)
- Página da partida: números do jogador SÓ da partida aberta (proibido puxar o histórico dele);
  régua anônima do corpus (`metrics/perfil_reference.json`, sem nome nem steamid); sem seletor de
  base; partida única compara com os outros jogadores dela e AVISA (30)
- Entre partidas, só em `jogadores.html` (por steamid, encolhimento declarado); na partida, o
  "Comparar dois" é entre jogadores DAQUELA partida e a seleção é estado da tela (41)
- Sem atacante, o texto nunca usa o nome de alguém: diz o que aconteceu ("morreu para a bomba"),
  sem fallback que nomeie a vítima como matador; fogo amigo é "morto pelo companheiro X";
  abertura é o primeiro duelo ganho contra o adversário (8c)
- Aba de leitura com três blocos fixos (decisivo em cima, MVP e outro destaque embaixo). MVP =
  maior rating; a menos do erro do rating fora da amostra é empate, e a frase declara; sem rating,
  sem MVP; componentes no card como evidência, sem peso (20)
- Destaque negativo só com número E referência, senão o candidato é descartado e a vez passa;
  distingue-se por rótulo e hierarquia, nunca por vermelho de alarme (20a)
- Decisivo e impressionante são dois cards, nunca somados; os pesos do impressionante ficam
  expostos no card, componente por componente (19a)
- Partida sem round decisivo é resultado: frase própria, não card vazio (19b)
- Economia é leitura ao lado do round decisivo, nunca peso; o card mostra o equipamento médio e diz
  quando quem perdeu tinha equipamento igual ou superior (19d)
- Rating da partida com o modelo de round GLOBAL (`ModeloDeRound.da_referencia`), nunca treinado
  só na partida (22e)
- Erro no Perfil: nenhum tipo vai ao site antes de o Pedro confirmar 8 de 10 exemplos
  (`TIPOS_DE_ERRO_VALIDADOS`); sem tipo validado, nenhum dado de erro entra em `docs/`;
  `--mostrar-erros-nao-validados` gera só em `preview/`; `FORTES_POR_LADO_PUBLICADOS` só vira True
  com o OK do Pedro (46)
- Chave secreta do Supabase nunca no repositório; `GRUPOS_ATIVOS` só vira True depois da revisão de
  `notas/seguranca/grupos.md` e do OK do Pedro (47)

## Fluxo de trabalho

- Comentários e docstrings em português. Limiar é constante nomeada no topo do módulo, com a
  origem ao lado.
- Polars e Parquet. Toda métrica devolve `(per_round, summary)`; não troque o per_round pelo
  agregado.
- Uma branch por fase; um commit por passo, com a suíte passando; meça antes e depois. Merge só
  com a suíte inteira e o CI verdes; depois, push e relatório com o hash do merge.
- Teste existente não muda sem o Pedro aprovar.
- Ponto de calibração é do Pedro: não resolva nenhum sozinho, pergunte. Cada `CLAUDE.md` de pasta
  lista os seus; o histórico está em `notas/calibracao.md`.
- Decisão nova vira nota `notas/decisoes/<ID>-<nome>.md` (ID, Status `vigente`, `revogada` ou
  `substituída por N`, Data, Resumo) e uma linha num `CLAUDE.md`; o código a cita por ID
  ("decisão 21a"), e toda citação precisa de nota.
- Métrica nova que depende de outra tabela do processado: confira que o pipeline
  (`leitura/insights.py`) a recebe, senão a referência e a página ficam em escalas diferentes (15f)
- O documento de design dá a FORMA; onde ele pedir mudar um comportamento que o main já tem, vale o
  do main e o conflito vai para o relatório; mudança de forma deixa zero diferença numérica
  (`scripts/design/impressao_numeros.py`) (44)

## Índice

- `metrics/CLAUDE.md`: definição das métricas, papéis, rating, economia e arremesso.
- `parsing/CLAUDE.md`: o que o parse corta ou corrige (freeze, faca, dano, cegueira, rota B).
- `clustering/CLAUDE.md`: agrupamento de estilo (KMeans global, features, nomes).
- `scripts/CLAUDE.md`: referências do corpus, calibração do rating, biblioteca, lugares e build.
- `dashboard/web/CLAUDE.md`: template, mapa, cores, replay, anotação, prancheta e grupos.
- `tests/CLAUDE.md`: invariantes, controles e testes que pulam sem dado ou navegador.
- `notas/decisoes/README.md`: índice das decisões. `notas/glossario.md`: termos.
  `notas/design/entrega-sala-de-demo.md`: design (§12 é regra dura).
- Pendências: `notas/PENDENCIAS_PARA_O_PEDRO.md`, `PENDENCIAS_NO_JOGO.md`, `RECUPERACAO_DEMOS.md`,
  `notas/limitacoes.md`.
- `pesquisa/`: exploratórios (teste não importa) · `legado/`: sem uso · `data/processed/`
  versionado · `data/interim/`, `demos/` e `docs/` fora do git.
