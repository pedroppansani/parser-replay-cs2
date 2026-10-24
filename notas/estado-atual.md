# Estado atual do trabalho (para abrir uma sessão limpa)

Atualizado em 2026-10-21, depois do item 3 da calibração e da resposta do Pedro sobre o plano da v2 e o Supabase. Os prompts de origem citados estão em
`C:\Users\User\Desktop\Claude outputs\` (os mais antigos já não estão no disco; o que eles pediram está nos cartões
de `notas/PENDENCIAS_PARA_O_PEDRO.md` e nas notas de decisão).

## Regras temporárias em vigor

- `GRUPOS_ATIVOS = False` (`scripts/grupos_config.py`): só vira `True` com o LIBERADO do agente `seguranca` e a
  confirmação do Pedro. A palavra do papel de serviço do Supabase não aparece em nenhum arquivo versionado (há teste).
- `TIPOS_DE_ERRO_VALIDADOS`: seis tipos na `main` (não trocou, perdeu a troca, morreu sozinho, primeira morte sem
  troca, dano de utilidade no time e flash no time, esta validada em 2026-10-21, 10/10). O possível bait fica fora
  (9 casos, abaixo de `MIN_CASOS_PARA_VALIDAR`). `FORTES_POR_LADO_PUBLICADOS = True`.
- `MIN_CASOS_PARA_VALIDAR = 10`: hoje só o "possível bait" (9 casos) fica fora.
- Merge sem confirmação só quando o prompt da fase autoriza por escrito (regra da raiz).
- Limites dos CLAUDE.md (tests/test_claude_md.py): raiz 15.000 no teste e meta 10.000; `metrics/` 12.000;
  `scripts/` e `dashboard/web/` 6.000; as outras pastas, inclusive `metrics/erros/`, 5.000. Se um precisar passar
  do limite, não suba de novo: pare e traga uma proposta de divisão.
- A branch `fase-6-decisivo` e as tags `baseline-*` não são apagadas.
- Comando longo (suíte, reprocesso, build, capturas): um por chamada, com `timeout` e a saída em `notas/logs/`
  (fora do git); se passar do limite, parar e dizer ao Pedro qual foi (pedido dele, 2026-10-24).
- Dados: `data/interim` e `demos/` só por junction de leitura nos worktrees, removida no fim (regra 36). O
  reprocesso grava caminhos absolutos de demo no `data/manifest.json`: restaurar `caminho` e `existe` (só versão,
  commit, data e `sujo` podem mudar).
- Versão das métricas na `main`: 29 (cartão 13, referência do rating regravada; a 28 foi os pisos). O cartão 5
  sobe para 30.
- **Supabase (resposta do Pedro, 2026-10-21):** push protection ligado no GitHub e plano Free sem cartão. O projeto
  `parser-cs2-grupos` está PAUSADO por inatividade (o Free pausa depois de 7 dias sem uso). **(1) A parte B está
  destravada, mas antes de começar ela eu peço ao Pedro para reativar o projeto e espero ele confirmar.** A ordem
  não muda: a parte B fica para DEPOIS da v2-7. **(2) Pendência para a revisão de segurança:** no Free o projeto
  pausa depois de 7 dias sem uso, então os grupos no ar podem parar se ninguém usar; isso precisa de uma decisão
  do Pedro antes de ligar o `GRUPOS_ATIVOS`.

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
| `notas/estado-atual.md` criado | `f138103c` |
| Calibração, item 2: grupos de estilo (nomes pelo perfil; o reajuste reproduz o modelo) | `3c4afd79` |
| Calibração, item 3: cinco tipos de erro validados, `MIN_CEGUEIRA_FLASH_ALIADO`, versão 27 | `7775cd27` |
| Flash no time validada (10/10) e no Perfil | `33a9159d` |
| Calibração, item 1: pisos de função (suporte 40 s, versão 28; 21 jogadores mudam de função na `jogadores.html`, nota 31) | `d5562e76` |
| Cartão 13: referência do rating regravada e presa por teste (byte a byte no Windows, 1e-12 no CI), versão 29 | `2d547d7b` |
| `fix-tickrate-resto`: tickrate lido da demo em todo lugar, sem mudar nenhum número (sha256 dos dados igual ao da `main`); contagem de testes 1.678 | `47c0f840` |

## Em andamento

Nada.

## Fila (na ordem; o Pedro mudou em 2026-10-24)

1. Cartão 5 (`TICK_PELO_PROJETIL_SEM_EVENTO`, com a sua própria subida de versão, 30, e a tabela antes → depois).
2. A v2 (GOAT.demo), plano aprovado em `C:/Users/User/Desktop/Claude outputs/PLANO-v2-0.md`: v2-1 base (não
   muda a aparência; o escuro atual vira `data-tema="escuro"`), v2-2 marca, v2-3 e v2-4 em sequência numa branch de
   integração e para a `main` no mesmo push, v2-5 e v2-6 em paralelo depois de a v2-4 mesclar o `map_core.js`, v2-7
   verificação final. Condições de cada fase: suíte verde, impressão dos números idêntica, só as capturas e os
   testes autorizados mudam. Dúvidas do plano respondidas (todas as recomendações aceitas); só os testes de visual
   da seção 4.4 podem mudar; o `scripts/CLAUDE.md` não ganha linha (se precisar, parar e propor divisão). **A cada
   fase, uma prévia local: o site da branch em `preview-v2/` (no `.gitignore`), e o caminho do `index.html` no
   relatório, para o Pedro testar no navegador antes do merge.** Na v2-7: pôr no PENDENCIAS o `curl` do
   `Content-Encoding` dos dois agentes depois do deploy e o fallback da fonte mono no macOS. Fase própria depois
   da v2: a comparação por grupos do Perfil, com a regra de empate do Pedro.
3. Depois da v2-7: cartão 6 (histograma da força da rota B), cartão 7 (os `.rar`: espaço em disco ≥ 12 GB,
   `demos/entrada/_extraido/` conferida antes, sha256 de cada `.dem`, regra 36) e cartão 9 (a refatoração, com a
   proposta, só propor, de gerar a contagem de testes no build pela coleta do pytest). A refatoração passou para
   depois da v2 por decisão do Pedro; ela continua tendo de provar que nenhum número muda.
4. Parte B dos grupos, DEPOIS da v2-7 e só depois de o Pedro reativar o projeto Supabase e confirmar (ver as
   regras temporárias). Junto: plano Free, a maior tática real (máximo, mediana e p95 de operações), `gitleaks`,
   `npm audit` e `pip-audit`, e o `.claude/worktrees/` no `.gitignore`; depois o `grupos.md` para o `seguranca`.
5. Do lado do Pedro: o dano de utilidade na escada (cartão 1, prints da HLTV); o roteiro do NVDA (cartão 11); o
   cartão 10 (Supabase); a fase 6 (`fase-6-decisivo`); a investigação do awpy 3 fica numa sessão separada.
