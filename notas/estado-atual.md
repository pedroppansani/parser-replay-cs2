# Estado atual do trabalho (para abrir uma sessão limpa)

Atualizado em 2026-10-19, ao fim da divisão do `metrics/CLAUDE.md`. Os prompts de origem citados estão em
`C:\Users\User\Desktop\Claude outputs\` (os mais antigos já não estão no disco; o que eles pediram está nos cartões
de `notas/PENDENCIAS_PARA_O_PEDRO.md` e nas notas de decisão).

## Regras temporárias em vigor

- `GRUPOS_ATIVOS = False` (`scripts/grupos_config.py`): só vira `True` com o LIBERADO do agente `seguranca` e a
  confirmação do Pedro. A palavra do papel de serviço do Supabase não aparece em nenhum arquivo versionado (há teste).
- `TIPOS_DE_ERRO_VALIDADOS`: seis tipos (flash no time validada em 2026-10-21, 10/10, branch
  `calibracao-flash-validada`, não mesclada). `FORTES_POR_LADO_PUBLICADOS = True`.
- `MIN_CASOS_PARA_VALIDAR = 10`: hoje só o "possível bait" (9 casos) fica fora.
- Merge sem confirmação só quando o prompt da fase autoriza por escrito (regra da raiz).
- Limites dos CLAUDE.md (tests/test_claude_md.py): raiz 15.000 no teste e meta 10.000; `metrics/` 12.000;
  `scripts/` e `dashboard/web/` 6.000; as outras pastas, inclusive `metrics/erros/`, 5.000. Se um precisar passar
  do limite, não suba de novo: pare e traga uma proposta de divisão.
- A branch `fase-6-decisivo` e as tags `baseline-*` não são apagadas.
- Dados: `data/interim` e `demos/` só por junction de leitura nos worktrees, removida no fim (regra 36). O
  reprocesso grava caminhos absolutos de demo no `data/manifest.json`: restaurar `caminho` e `existe` (só versão,
  commit, data e `sujo` podem mudar).
- Versão das métricas na `main`: 26. A 27 está em DUAS branches não mescladas: `calibracao-pisos` (pisos) e
  `calibracao-erros-validados` (flash no time); a segunda a ser mesclada sobe para 28.

## Feito (merges na `main`, todos com CI verde)

| item | merge |
|---|---|
| Fase 11: granadas como desenho | `977e3da5` |
| Fase 12: erros na aba Perfil | `9b1b108a` |
| Fase 13: grupos na prancheta (desligados) | `190a0f0e` |
| Fase 12b: referência por lado e função, convite ao mapa certo, glossário | `af3b7533` |
| Fase 15: componentes do design (§19) | `5aa4ab00` |
| Fase 14: CLAUDE.md por pasta | `fb2a81bb` |
| Fase 16a: pendências da fase 15 | `cc2b7242` |
| Fase 16b: correções de segurança dos grupos | `6739b475` |
| Fase 17a: regras, notas, material, teste de rede, cópias entre pastas | `542b9363`, `eb54ac93`, `fcce4c98` |
| Fase 17: ponto atrasado, contador, sem `CAMINHO_POR_CLIQUE` | `e7a02092`, `f0e0ad11`, `48fcd6b5` |
| Fase 17: roteiro do NVDA (cartão 11) e intervalo de 95% | `4f0c3c94` |
| Fase 18: tipos de erro revistos (visão, troca pelo fato, round decidido) | `d02b0e7e` |
| `metrics/CLAUDE.md` com limite 12.000 | `b3efc9da` |
| Fase 17: Galil/FAMAS (fica em força) | `ce576956` |
| Fase 17: cartão 8 (branches apagadas) | `f7b78968` |
| Fase 17: cartões 2, 3 e 4 | `36a991bf` |
| Fase 18b: calibração dos erros, bait com amostra insuficiente | `921aa334` |
| "Quanto cada round pesou" no lugar da curva repetida | `16749e2e` |
| Fase 17: degrau 4b da escada (assistência de flash; não bate) | `4a48c75f` |
| Tickrate lido da demo na flash e na utilidade (versão 26, cartão 12) | `a7db5dc9` |
| Divisão do `metrics/CLAUDE.md` (`metrics/erros/CLAUDE.md`) | `0f487a09` |

## Em andamento

- **Calibração, item 1 (pisos de função)**, branch `calibracao-pisos` (worktree `.claude/worktrees/cal-pisos`),
  NÃO mesclada. Origem: `PROMPT-respostas-calibracao-pedro.md`. Duas paradas aguardam o Pedro:
  1. o piso de suporte em 40 s ainda deixa sh1ro (match_38), w0nderful (match_25) e donk (match_05, FACEIT)
     acima do corte; o piso ficou em 20 s;
  2. a `jogadores.html` mudaria 3.187 dos 5.120 números exibidos (15 jogadores mudam de função no corpus, e a
     página puxa cada número para a média da função): conta como "rótulo autorizado" ou a função da página fica
     separada do rótulo?
  A linha de regra nova dos pisos (264 bytes) entra no `metrics/CLAUDE.md` depois da divisão.

## Fila (na ordem)

1. Calibração, item 1 (acima), item 2 (grupos de estilo: reajustar o KMeans e gravar os nomes pelo perfil) e
   item 3 (erros validados, `MIN_CEGUEIRA_FLASH_ALIADO = 2,0 s`, três exemplos novos de flash, duas investigações
   e duas propostas, as respostas gravadas como dado). Origem: `PROMPT-respostas-calibracao-pedro.md`. A frase
   "as respostas da seção 7 foram dadas em 2026-10-16, a partir das colunas da tabela, e não assistindo aos
   replays" entra na nota 46 no item 3.
2. `fix-tickrate-resto`: os lugares que ainda assumem 64 tick (lista de pendentes em
   `tests/test_tickrate_lido_da_demo.py`), sem mudar nenhum número (prova por sha256 dos dados do corpus) e com
   testes de 128 tick. Origem: `PROMPT-resposta-tickrate-resto-divisao-claude-md.md`.
3. Atualizar a contagem de testes em `numeros_citaveis` (autorizado; pode ir junto do próximo merge).
4. Cartão 5 (`TICK_PELO_PROJETIL_SEM_EVENTO`, com a sua própria subida de versão e tabela antes → depois), cartão 6
   (histograma da força da rota B) e cartão 7 (os `.rar`: espaço em disco ≥ 12 GB, pasta `demos/entrada/_extraido/`
   conferida antes, sha256 de cada `.dem`). Origem: os cartões de `notas/PENDENCIAS_PARA_O_PEDRO.md`.
5. Cartão 9, a refatoração, por último. Trazer junto a proposta de gerar a contagem de testes no build pela coleta
   do pytest (só propor).
6. Parado do lado do Pedro: o cartão 10 (Supabase) e depois a parte B dos grupos e a nova revisão do `seguranca`;
   o dano de utilidade na escada (cartão 1, prints da HLTV); o roteiro do NVDA (cartão 11).
